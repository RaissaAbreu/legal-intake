from pathlib import Path
import sqlite3
import pandas as pd

# =====================================================
# 1. CONFIGURACOES
# =====================================================

DB_NAME = str(
    Path(__file__).resolve().parent / "legal_intake.db"
)


# =====================================================
# 2. CONEXAO
# =====================================================

def conectar():
    """Abre conexao com o banco SQLite."""

    conexao = sqlite3.connect(DB_NAME)
    conexao.execute("PRAGMA foreign_keys = ON")

    return conexao


# =====================================================
# 3. CRIACAO E MIGRACAO DAS TABELAS
# =====================================================

def criar_tabela():
    """
    Cria as tabelas e adiciona novas colunas
    sem apagar os registros existentes.
    """

    conexao = conectar()
    cursor = conexao.cursor()

    try:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solicitacoes (

                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitante TEXT NOT NULL,
                area_solicitante TEXT NOT NULL,
                titulo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT,
                urgencia TEXT,
                prazo TEXT,
                responsavel TEXT,
                status TEXT DEFAULT 'Aberta',
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP

            )
        """)

        # Verificar colunas existentes
        cursor.execute("PRAGMA table_info(solicitacoes)")

        colunas = [
            coluna[1]
            for coluna in cursor.fetchall()
        ]

        # Novas colunas do fluxo juridico
        novas_colunas = {

            "status_aprovacao":
                "TEXT NOT NULL DEFAULT 'Pendente de revisão'",

            "categoria_revisada":
                "TEXT",

            "urgencia_revisada":
                "TEXT",

            "responsavel_confirmado":
                "TEXT",

            "revisado_por":
                "TEXT",

            "observacao_revisao":
                "TEXT",

            "revisado_em":
                "DATETIME",

            "encaminhado_em":
                "DATETIME"

        }

        for coluna, tipo in novas_colunas.items():

            if coluna not in colunas:

                cursor.execute(
                    f"ALTER TABLE solicitacoes "
                    f"ADD COLUMN {coluna} {tipo}"
                )

        # Tabela de historico
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_solicitacoes (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                solicitacao_id INTEGER NOT NULL,

                acao TEXT NOT NULL,

                detalhes TEXT,

                usuario TEXT,

                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (solicitacao_id)
                    REFERENCES solicitacoes(id)

            )
        """)

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


# =====================================================
# 4. REGISTRAR HISTORICO
# =====================================================

def registrar_historico(
    solicitacao_id,
    acao,
    detalhes="",
    usuario="Sistema"
):
    """Registra uma movimentacao da solicitacao."""

    conexao = conectar()

    try:

        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO historico_solicitacoes (
                solicitacao_id,
                acao,
                detalhes,
                usuario
            )
            VALUES (?, ?, ?, ?)
        """, (
            solicitacao_id,
            acao,
            detalhes,
            usuario
        ))

        conexao.commit()

    finally:
        conexao.close()


# =====================================================
# 5. INSERIR SOLICITACAO
# =====================================================

def inserir_solicitacao(
    solicitante,
    area_solicitante,
    titulo,
    descricao,
    prazo,
    categoria="Pendente",
    urgencia="Pendente",
    responsavel="A definir"
):
    """
    Registra uma nova solicitacao com classificacao
    automatica e aguardando revisao juridica.
    """

    conexao = conectar()

    try:

        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO solicitacoes (

                solicitante,
                area_solicitante,
                titulo,
                descricao,
                prazo,
                categoria,
                urgencia,
                responsavel,
                status,
                status_aprovacao

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (
            solicitante,
            area_solicitante,
            titulo,
            descricao,
            prazo,
            categoria,
            urgencia,
            responsavel,
            "Aberta",
            "Pendente de revisão"
        ))

        id_solicitacao = cursor.lastrowid

        cursor.execute("""
            INSERT INTO historico_solicitacoes (
                solicitacao_id,
                acao,
                detalhes,
                usuario
            )
            VALUES (?, ?, ?, ?)
        """, (
            id_solicitacao,
            "Solicitação cadastrada",
            "Demanda registrada e classificada automaticamente.",
            "Sistema"
        ))

        conexao.commit()

        return id_solicitacao

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


# =====================================================
# 6. LISTAR SOLICITACOES
# =====================================================

def listar_solicitacoes():
    """Retorna todas as solicitacoes em DataFrame."""

    conexao = conectar()

    try:

        consulta = """
            SELECT
                id,
                solicitante,
                area_solicitante,
                titulo,
                descricao,
                categoria,
                urgencia,
                prazo,
                responsavel,
                status,
                status_aprovacao,
                categoria_revisada,
                urgencia_revisada,
                responsavel_confirmado,
                revisado_por,
                observacao_revisao,
                revisado_em,
                encaminhado_em,
                criado_em

            FROM solicitacoes

            ORDER BY criado_em DESC
        """

        return pd.read_sql_query(
            consulta,
            conexao
        )

    finally:
        conexao.close()


# =====================================================
# 7. CONSULTAR UMA SOLICITACAO
# =====================================================

def obter_solicitacao(id_solicitacao):
    """Consulta uma solicitacao pelo ID."""

    conexao = conectar()

    try:

        cursor = conexao.cursor()

        cursor.execute("""
            SELECT *
            FROM solicitacoes
            WHERE id = ?
        """, (id_solicitacao,))

        return cursor.fetchone()

    finally:
        conexao.close()


# =====================================================
# 8. REVISAR E APROVAR SOLICITACAO
# =====================================================

def revisar_solicitacao(
    id_solicitacao,
    categoria,
    urgencia,
    responsavel,
    revisado_por,
    observacao="",
    aprovada=True
):
    """
    Registra a revisao juridica e a aprovacao
    ou reprovacao da solicitacao.
    """

    if not all([
        categoria,
        urgencia,
        responsavel,
        revisado_por
    ]):
        raise ValueError(
            "Preencha todos os campos obrigatorios da revisao."
        )

    conexao = conectar()

    try:

        cursor = conexao.cursor()

        cursor.execute("""
            SELECT id
            FROM solicitacoes
            WHERE id = ?
        """, (id_solicitacao,))

        if cursor.fetchone() is None:
            raise ValueError("Solicitacao nao encontrada.")

        novo_status = (
            "Aprovada" if aprovada else "Reprovada"
        )

        cursor.execute("""
            UPDATE solicitacoes

            SET
                categoria_revisada = ?,
                urgencia_revisada = ?,
                responsavel_confirmado = ?,
                revisado_por = ?,
                observacao_revisao = ?,
                revisado_em = CURRENT_TIMESTAMP,
                status_aprovacao = ?

            WHERE id = ?

        """, (
            categoria,
            urgencia,
            responsavel,
            revisado_por,
            observacao,
            novo_status,
            id_solicitacao
        ))

        cursor.execute("""
            INSERT INTO historico_solicitacoes (
                solicitacao_id,
                acao,
                detalhes,
                usuario
            )
            VALUES (?, ?, ?, ?)
        """, (
            id_solicitacao,
            f"Revisao {novo_status.lower()}",
            (
                f"Categoria: {categoria}; "
                f"Urgencia: {urgencia}; "
                f"Responsavel: {responsavel}; "
                f"Observacao: {observacao}"
            ),
            revisado_por
        ))

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


# =====================================================
# 9. ENCAMINHAR SOLICITACAO
# =====================================================

def encaminhar_solicitacao(
    id_solicitacao,
    usuario="Sistema"
):
    """
    Encaminha uma solicitacao somente depois
    da aprovacao juridica.
    """

    conexao = conectar()

    try:

        cursor = conexao.cursor()

        cursor.execute("""
            SELECT status_aprovacao, responsavel_confirmado
            FROM solicitacoes
            WHERE id = ?
        """, (id_solicitacao,))

        resultado = cursor.fetchone()

        if resultado is None:
            raise ValueError("Solicitacao nao encontrada.")

        status_aprovacao, responsavel = resultado

        if status_aprovacao != "Aprovada":
            raise ValueError(
                "A solicitacao precisa ser aprovada antes do encaminhamento."
            )

        if not responsavel:
            raise ValueError(
                "Defina um responsavel antes do encaminhamento."
            )

        cursor.execute("""
            UPDATE solicitacoes

            SET
                status = 'Em andamento',
                encaminhado_em = CURRENT_TIMESTAMP

            WHERE id = ?

        """, (id_solicitacao,))

        cursor.execute("""
            INSERT INTO historico_solicitacoes (
                solicitacao_id,
                acao,
                detalhes,
                usuario
            )
            VALUES (?, ?, ?, ?)
        """, (
            id_solicitacao,
            "Solicitacao encaminhada",
            f"Encaminhada para {responsavel}.",
            usuario
        ))

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


# =====================================================
# 10. CONSULTAR HISTORICO
# =====================================================

def listar_historico(id_solicitacao):
    """Consulta o historico de uma solicitacao."""

    conexao = conectar()

    try:

        consulta = """
            SELECT
                id,
                solicitacao_id,
                acao,
                detalhes,
                usuario,
                criado_em

            FROM historico_solicitacoes

            WHERE solicitacao_id = ?

            ORDER BY criado_em DESC, id DESC
        """

        return pd.read_sql_query(
            consulta,
            conexao,
            params=(id_solicitacao,)
        )

    finally:
        conexao.close()


# =====================================================
# 11. ATUALIZAR STATUS OPERACIONAL
# =====================================================

def atualizar_status(id_solicitacao, novo_status):
    """Atualiza o andamento operacional."""

    status_permitidos = [
        "Aberta",
        "Em andamento",
        "Concluída",
        "Cancelada"
    ]

    if novo_status not in status_permitidos:
        raise ValueError("Status operacional invalido.")

    conexao = conectar()

    try:

        cursor = conexao.cursor()

        cursor.execute("""
            UPDATE solicitacoes
            SET status = ?
            WHERE id = ?
        """, (
            novo_status,
            id_solicitacao
        ))

        if cursor.rowcount == 0:
            raise ValueError("Solicitacao nao encontrada.")

        cursor.execute("""
            INSERT INTO historico_solicitacoes (
                solicitacao_id,
                acao,
                detalhes,
                usuario
            )
            VALUES (?, ?, ?, ?)
        """, (
            id_solicitacao,
            "Status atualizado",
            f"Novo status: {novo_status}",
            "Sistema"
        ))

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


# =====================================================
# 12. EXECUCAO DIRETA
# =====================================================

if __name__ == "__main__":

    criar_tabela()

    print("Banco de dados preparado com sucesso!")

    dados = listar_solicitacoes()

    print(
        f"Solicitacoes cadastradas: {len(dados)}"
    )

    print(
        "Novos campos de revisao e historico preparados."
    )
