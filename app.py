from pathlib import Path
import sqlite3
from datetime import date, datetime

import altair as alt
import pandas as pd
import streamlit as st

from database import (
    criar_tabela,
    inserir_solicitacao,
    listar_solicitacoes,
)
from classifier import analisar_solicitacao


# =====================================================
# 1. CONFIGURACOES GERAIS
# =====================================================

DB_NAME = str(
    Path(__file__).resolve().parent / "legal_intake.db"
)

st.set_page_config(
    page_title="Legal Intake | Executive Platform",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

criar_tabela()


# =====================================================
# 2. BANCO: REVISAO E HISTORICO
# =====================================================

def conectar_local():
    return sqlite3.connect(DB_NAME)


def preparar_revisao():
    """
    Acrescenta os campos de revisão sem apagar os registros existentes.
    Também cria uma tabela própria para registrar o histórico de ações.
    """
    conexao = conectar_local()
    cursor = conexao.cursor()

    cursor.execute("PRAGMA table_info(solicitacoes)")
    colunas = {linha[1] for linha in cursor.fetchall()}

    novas_colunas = {
        "status_aprovacao": "TEXT DEFAULT 'Pendente de revisão'",
        "revisor": "TEXT",
        "observacao_revisao": "TEXT",
        "revisado_em": "DATETIME",
    }

    for nome, tipo in novas_colunas.items():
        if nome not in colunas:
            cursor.execute(
                f"ALTER TABLE solicitacoes ADD COLUMN {nome} {tipo}"
            )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitacao_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            status_anterior TEXT,
            status_novo TEXT,
            observacao TEXT,
            usuario TEXT,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
        # ==========================================
        # MIGRACAO DA TABELA DE HISTORICO
        # ==========================================

    cursor.execute(
            "PRAGMA table_info(historico_solicitacoes)"
        )

    colunas_historico = {
            coluna[1]
            for coluna in cursor.fetchall()
        }

    colunas_necessarias = {
            "solicitacao_id": "INTEGER",
            "acao": "TEXT",
            "status_anterior": "TEXT",
            "status_novo": "TEXT",
            "observacao": "TEXT",
            "usuario": "TEXT",
            "criado_em": "DATETIME"
        }

    for nome, tipo in colunas_necessarias.items():

            if nome not in colunas_historico:

                cursor.execute(
                    f"""
                    ALTER TABLE historico_solicitacoes
                    ADD COLUMN {nome} {tipo}
                    """
                )

    conexao.commit()

    # Garante que registros antigos também apareçam na fila de revisão.
    cursor.execute("""
        UPDATE solicitacoes
        SET status_aprovacao = 'Pendente de revisão'
        WHERE status_aprovacao IS NULL OR TRIM(status_aprovacao) = ''
    """)

    conexao.commit()
    conexao.close()


def registrar_evento(
    solicitacao_id,
    acao,
    status_anterior=None,
    status_novo=None,
    observacao="",
    usuario="",
):
    conexao = conectar_local()
    cursor = conexao.cursor()
    cursor.execute("""
        INSERT INTO historico_solicitacoes (
            solicitacao_id,
            acao,
            status_anterior,
            status_novo,
            observacao,
            usuario
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        int(solicitacao_id),
        acao,
        status_anterior,
        status_novo,
        observacao,
        usuario,
    ))
    conexao.commit()
    conexao.close()


def atualizar_revisao(
    solicitacao_id,
    categoria,
    urgencia,
    responsavel,
    novo_status,
    revisor,
    observacao,
):
    conexao = conectar_local()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT status_aprovacao
        FROM solicitacoes
        WHERE id = ?
    """, (int(solicitacao_id),))
    linha = cursor.fetchone()

    if linha is None:
        conexao.close()
        raise ValueError("Solicitação não encontrada.")

    status_anterior = linha[0] or "Pendente de revisão"

    cursor.execute("""
        UPDATE solicitacoes
        SET categoria = ?,
            urgencia = ?,
            responsavel = ?,
            status_aprovacao = ?,
            revisor = ?,
            revisado_por = ?,
            observacao_revisao = ?,
            revisado_em = CURRENT_TIMESTAMP
        WHERE id = ?

    """, 
        (
    
        categoria,
        urgencia,
        responsavel,
        novo_status,
        revisor,
        revisor,
        observacao,
        int(solicitacao_id),
    )
    )

    # O status operacional continua separado do status da aprovação.
    conexao.commit()
    conexao.close()

    registrar_evento(
        solicitacao_id=solicitacao_id,
        acao="Revisão jurídica",
        status_anterior=status_anterior,
        status_novo=novo_status,
        observacao=observacao,
        usuario=revisor,
    )


def carregar_historico():
    conexao = conectar_local()
    try:
        return pd.read_sql_query("""
            SELECT
                h.id,
                h.solicitacao_id,
                s.titulo,
                h.acao,
                h.status_anterior,
                h.status_novo,
                h.observacao,
                h.usuario,
                h.criado_em
            FROM historico_solicitacoes h
            LEFT JOIN solicitacoes s
                ON s.id = h.solicitacao_id
            ORDER BY h.criado_em DESC, h.id DESC
        """, conexao)
    finally:
        conexao.close()


preparar_revisao()


# =====================================================
# 3. IDENTIDADE VISUAL
# =====================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Manrope:wght@400;500;600;700&display=swap');

:root {
    --navy: #101C2D;
    --navy-light: #1B2B40;
    --gold: #B99A62;
    --gold-light: #D6BF91;
    --ivory: #F7F6F2;
    --white: #FFFFFF;
    --text: #202B3A;
    --muted: #667085;
    --border: #E8E5DE;
}

.stApp {
    background-color: var(--ivory);
    font-family: 'Manrope', sans-serif;
}

#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }

.block-container {
    max-width: 1380px;
    padding-top: 2.5rem;
    padding-bottom: 4rem;
}

html, body, [class*="css"] {
    font-family: 'Manrope', sans-serif;
}

h1, h2, h3, .main-title, .section-title {
    font-family: 'Cormorant Garamond', serif !important;
    font-weight: 600 !important;
    color: #17263A !important;
}

[data-testid="stSidebar"] {
    background-color: var(--navy);
    border-right: 1px solid #29394C;
}

[data-testid="stSidebar"] * { color: #F4F1EA; }

.brand-name {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 31px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: #FFFFFF;
}

.brand-subtitle {
    font-family: 'Manrope', sans-serif;
    font-size: 9px;
    letter-spacing: 3px;
    color: var(--gold-light);
    margin-top: 5px;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: 9px 8px;
    border-radius: 7px;
    font-size: 13px;
}

.eyebrow {
    color: #8B6B35;
    font-size: 10px;
    letter-spacing: 2.5px;
    font-weight: 700;
    text-transform: uppercase;
}

.main-title {
    font-size: 38px !important;
    letter-spacing: -0.5px;
    margin-top: 8px;
}

.subtitle {
    color: #667085;
    font-size: 13px;
    margin-top: 7px;
}

.section-number {
    color: #8B6B35;
    font-size: 10px;
    letter-spacing: 2px;
    font-weight: 700;
    font-family: 'Manrope', sans-serif;
}

.section-title {
    font-size: 27px !important;
    margin-top: 5px;
}

.section-description {
    color: #667085;
    font-size: 12px;
    margin-top: 5px;
    margin-bottom: 20px;
}

[data-testid="stForm"] {
    background-color: #FFFFFF;
    border: 1px solid #E6E0D5;
    border-radius: 14px;
    padding: 32px;
    box-shadow: 0 8px 30px rgba(16, 28, 45, 0.045);
}

.stTextInput label, .stTextArea label, .stSelectbox label,
.stDateInput label, .stMultiSelect label {
    color: #354255 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
}

.stTextInput input, .stTextArea textarea, .stDateInput input {
    background-color: #FFFFFF !important;
    border: 1px solid #D0D5DD !important;
    border-radius: 7px !important;
    color: #202B3A !important;
}

.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: #7A8492 !important;
    opacity: 1 !important;
}

.stSelectbox [data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border-color: #D0D5DD !important;
    color: #202B3A !important;
}

.stSelectbox [data-baseweb="select"] * { color: #202B3A !important; }

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #B99A62 !important;
    box-shadow: 0 0 0 1px #B99A62 !important;
}

.stFormSubmitButton button, .stButton button {
    border-radius: 7px !important;
    min-height: 43px;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
}

.stFormSubmitButton button {
    background: linear-gradient(135deg, #C7A66A, #A9854C) !important;
    color: #14243A !important;
    border: none !important;
    min-height: 48px;
}

.stFormSubmitButton button:hover {
    background: #D6BF91 !important;
    color: #14243A !important;
}

.stButton button[kind="primary"] {
    background: #14243A !important;
    color: #FFFFFF !important;
    border: 1px solid #14243A !important;
}

.stButton button[kind="secondary"] {
    background: #FFFFFF !important;
    color: #14243A !important;
    border: 1px solid #C9C4B8 !important;
}

[data-testid="stAlert"] { border-radius: 8px; }
hr { border-color: #E8E5DE !important; }

.system-status {
    background-color: #EAF1E9;
    color: #315B3A;
    border: 1px solid #D5E3D2;
    border-radius: 20px;
    padding: 10px 12px;
    font-size: 11px;
    font-weight: 700;
    text-align: center;
    white-space: nowrap;
}

.metric-card {
    background: #FFFFFF;
    border: 1px solid #E5E0D6;
    border-radius: 12px;
    padding: 23px 22px;
    min-height: 145px;
    box-shadow: 0 5px 18px rgba(16, 28, 45, 0.04);
}

.metric-label {
    color: #52627A;
    font-size: 12px;
    font-weight: 700;
}

.metric-value {
    color: #14243A;
    font-family: 'Cormorant Garamond', serif;
    font-size: 43px;
    font-weight: 700;
    margin-top: 8px;
    line-height: 1.2;
}

.metric-foot {
    color: #667085;
    font-size: 10px;
    margin-top: 5px;
}

.metric-accent {
    height: 3px;
    width: 38px;
    background: #B99A62;
    border-radius: 5px;
    margin-top: 12px;
}

.review-card {
    background: #FFFFFF;
    border: 1px solid #E5E0D6;
    border-radius: 12px;
    padding: 20px;
    margin: 8px 0 16px 0;
}

.review-label {
    color: #52627A;
    font-size: 12px;
    font-weight: 700;
    margin-bottom: 5px;
}

.review-value {
    color: #14243A;
    font-size: 16px;
    font-weight: 700;
    overflow-wrap: anywhere;
}

.small-muted {
    color: #667085;
    font-size: 12px;
}

/* =========================================
   CORREÇÃO DE CONTRASTE - CENTRAL JURÍDICA
   ========================================= */

/* Indicadores */
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p {
    color: #354255 !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] div {
    color: #14243A !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}

/* Textos e descrições da área principal */
.main .stMarkdown p,
.main [data-testid="stCaptionContainer"],
.main [data-testid="stCaptionContainer"] p {
    color: #52627A !important;
    opacity: 1 !important;
}

/* Títulos dos dados da solicitação */
.review-label {
    color: #354255 !important;
    font-size: 13px !important;
    font-weight: 700 !important;
}

.review-value {
    color: #14243A !important;
    font-size: 16px !important;
    font-weight: 700 !important;
}

/* Títulos e descrições dentro dos cartões */
.main [data-testid="stMarkdownContainer"] strong {
    color: #14243A !important;
}

/* Decisão da revisão */
.main [data-testid="stMarkdownContainer"] p {
    opacity: 1 !important;
}

/* Legibilidade dos campos */
.stTextInput label,
.stTextArea label,
.stSelectbox label {
    color: #26364B !important;
    font-weight: 700 !important;
}

/* ==========================================
   DADOS DA SOLICITAÇÃO - CONTRASTE
   ========================================== */

.dados-solicitacao {
    background-color: #FFFFFF !important;
    border: 1px solid #D8D2C7 !important;
    border-radius: 12px;
    padding: 22px;
}

.dados-solicitacao .campo-titulo {
    color: #354255 !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    margin-bottom: 8px;
}

.dados-solicitacao .campo-valor {
    color: #14243A !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    line-height: 1.6 !important;
    opacity: 1 !important;
}

/* Separadores */
.dados-solicitacao hr {
    border-color: #E5E0D7 !important;
}


</style>
""", unsafe_allow_html=True)


# =====================================================
# 4. MENU LATERAL
# =====================================================

with st.sidebar:
    st.markdown(
        '<div style="text-align:center;font-size:38px;color:#C6A66B;">⚖</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h2 style="text-align:center;color:white;'
        'font-family:Cormorant Garamond,serif;'
        'letter-spacing:2px;">LEGAL INTAKE</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center;color:#D6BF91;'
        'font-size:9px;letter-spacing:3px;">'
        'EXECUTIVE PLATFORM</p>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("W O R K S P A C E")

    pagina = st.radio(
        "Navegação",
        [
            "Nova solicitação",
            "Painel de demandas",
            "Revisão jurídica",
            "Histórico",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("L E G A L   O P E R A T I O N S")
    st.markdown("Gestão inteligente de demandas jurídicas.")
    st.divider()
    st.caption("VERSÃO 1.1.0")


# =====================================================
# 5. CABECALHO INSTITUCIONAL
# =====================================================

col_titulo, col_status = st.columns([5, 1.5], vertical_alignment="center")

with col_titulo:
    st.markdown(
        '<div class="eyebrow">LEGAL OPERATIONS / WORKSPACE</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="main-title">Gestão de demandas jurídicas</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">Inteligência, organização e controle jurídico.</div>',
        unsafe_allow_html=True,
    )

with col_status:
    st.markdown(
        '<div class="system-status">● Sistema operacional</div>',
        unsafe_allow_html=True,
    )

st.divider()


# =====================================================
# 6. NOVA SOLICITACAO
# =====================================================

if pagina == "Nova solicitação":
    st.markdown("""
    <div class="section-number">INTAKE MANAGEMENT / 01</div>
    <div class="section-title">Abertura de solicitação</div>
    <div class="section-description">
        Registre uma nova demanda para análise do departamento Jurídico.
    </div>
    """, unsafe_allow_html=True)

    resultado_cadastro = None

    with st.form("form_solicitacao"):
        st.markdown(
            '<p style="font-size:14px;font-weight:700;color:#17263A;">'
            '01 &nbsp; Identificação do solicitante</p>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            solicitante = st.text_input(
                "Nome completo *",
                placeholder="Informe seu nome",
            )
        with col2:
            area_solicitante = st.selectbox(
                "Área de origem *",
                [
                    "Comercial",
                    "Recursos Humanos",
                    "Financeiro",
                    "Marketing",
                    "Tecnologia",
                    "Operações",
                    "Outra",
                ],
            )

        st.divider()
        st.markdown(
            '<p style="font-size:14px;font-weight:700;color:#17263A;">'
            '02 &nbsp; Detalhamento da demanda</p>',
            unsafe_allow_html=True,
        )

        titulo = st.text_input(
            "Título da solicitação *",
            placeholder="Ex.: Revisão de contrato de prestação de serviços",
        )
        descricao = st.text_area(
            "Descrição detalhada *",
            placeholder=(
                "Apresente o contexto da solicitação, os fatos relevantes "
                "e a necessidade jurídica..."
            ),
            height=150,
        )

        st.divider()
        st.markdown(
            '<p style="font-size:14px;font-weight:700;color:#17263A;">'
            '03 &nbsp; Prazo e encaminhamento</p>',
            unsafe_allow_html=True,
        )

        col3, col4 = st.columns(2)
        with col3:
            prazo = st.date_input(
                "Prazo desejado *",
                value=date.today(),
                format="DD/MM/YYYY",
            )
        with col4:
            tipo = st.selectbox(
                "Natureza da solicitação",
                [
                    "Análise jurídica",
                    "Elaboração de documento",
                    "Revisão contratual",
                    "Orientação jurídica",
                    "Outro",
                ],
            )

        st.divider()
        st.caption("* Campos obrigatórios para o registro da solicitação.")
        enviar = st.form_submit_button(
            "Registrar solicitação  →",
            use_container_width=True,
        )

    if enviar:
        if not solicitante.strip():
            st.error("Informe o nome do solicitante.")
        elif not titulo.strip():
            st.error("Informe o título da solicitação.")
        elif not descricao.strip():
            st.error("Informe a descrição da demanda.")
        elif prazo < date.today():
            st.error("O prazo informado não pode estar no passado.")
        else:
            try:
                resultado_cadastro = analisar_solicitacao(
                    titulo,
                    descricao,
                    prazo.isoformat(),
                )

                inserir_solicitacao(
                    solicitante,
                    area_solicitante,
                    titulo,
                    descricao,
                    prazo.isoformat(),
                    categoria=resultado_cadastro.get("categoria", "Pendente"),
                    urgencia=resultado_cadastro.get("urgencia", "Pendente"),
                    responsavel=resultado_cadastro.get("responsavel", "A definir"),
                )

                # Recupera o identificador da solicitação recém-criada.
                conexao = conectar_local()
                cursor = conexao.cursor()
                cursor.execute("SELECT MAX(id) FROM solicitacoes")
                linha_id = cursor.fetchone()
                conexao.close()

                if linha_id and linha_id[0] is not None:
                    novo_id = int(linha_id[0])
                    registrar_evento(
                        novo_id,
                        "Solicitação cadastrada",
                        None,
                        "Pendente de revisão",
                        "Cadastro recebido e encaminhado para revisão jurídica.",
                        solicitante,
                    )

                st.success("Solicitação registrada com sucesso!")

                st.markdown("---")
                st.subheader("Resultado da triagem automática")
                st.caption(
                    "Análise preliminar da solicitação realizada pelo sistema."
                )

                m1, m2, m3 = st.columns([1, 1, 1.5])
                with m1:
                    st.metric(
                        "Categoria jurídica",
                        resultado_cadastro.get("categoria", "Não identificada"),
                    )
                with m2:
                    st.metric(
                        "Nível de urgência",
                        resultado_cadastro.get("urgencia", "Não identificada"),
                    )
                with m3:
                    st.metric(
                        "Responsável sugerido",
                        resultado_cadastro.get("responsavel", "A definir"),
                    )

                st.info(
                    "A classificação é realizada automaticamente por regras "
                    "de palavras-chave. A validação final cabe à equipe jurídica."
                )

            except Exception as erro:
                st.error(f"Não foi possível registrar a solicitação: {erro}")

            # ==========================================
            # MENSAGEM DE CONFIRMAÇÃO DA REVISÃO
            # ==========================================

            if "mensagem_revisao" in st.session_state:

                tipo, mensagem = st.session_state["mensagem_revisao"]

                if tipo == "sucesso":
                    st.success(mensagem)

                elif tipo == "erro":
                    st.error(mensagem)

                elif tipo == "aviso":
                    st.warning(mensagem)

                del st.session_state["mensagem_revisao"]


# =====================================================
# 7. PAINEL EXECUTIVO
# =====================================================

elif pagina == "Painel de demandas":
    st.markdown("""
    <div class="section-number">MANAGEMENT / 02</div>
    <div class="section-title">Painel executivo</div>
    <div class="section-description">
        Visão gerencial e acompanhamento das demandas jurídicas.
    </div>
    """, unsafe_allow_html=True)

    df = listar_solicitacoes()

    if df.empty:
        st.info(
            "Ainda não existem solicitações cadastradas. "
            "Cadastre uma demanda para visualizar os indicadores."
        )
    else:
        status = (
            df["status"].fillna("Aberta").astype(str).str.strip().str.lower()
        )
        urgencia = (
            df["urgencia"].fillna("Pendente").astype(str).str.strip().str.lower()
        )
        prazo_dt = pd.to_datetime(df["prazo"], errors="coerce")
        hoje = pd.Timestamp(date.today())

        status_finais = [
            "concluída", "concluida", "finalizada", "cancelada", "reprovada"
        ]

        abertas = int((~status.isin(status_finais)).sum())
        urgentes = int(urgencia.isin(["alta", "urgente", "crítica", "critica"]).sum())
        proximas = int((
            (prazo_dt >= hoje)
            & (prazo_dt <= hoje + pd.Timedelta(days=7))
            & (~status.isin(status_finais))
        ).sum())
        concluidas = int(status.isin(["concluída", "concluida", "finalizada"]).sum())
        atrasadas = int((
            (prazo_dt < hoje)
            & prazo_dt.notna()
            & (~status.isin(status_finais))
        ).sum())

        st.markdown("### Indicadores gerais")
        colunas_metricas = st.columns(4)

        indicadores = [
            ("Demandas abertas", abertas, "Solicitações em andamento"),
            ("Alta prioridade", urgentes, "Demandas classificadas como urgentes"),
            ("Prazos próximos", proximas, "Vencimento em até 7 dias"),
            ("Concluídas", concluidas, "Solicitações finalizadas"),
        ]

        for coluna, (rotulo, valor, descricao) in zip(colunas_metricas, indicadores):
            with coluna:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">{rotulo}</div>'
                    f'<div class="metric-value">{valor}</div>'
                    f'<div class="metric-foot">{descricao}</div>'
                    f'<div class="metric-accent"></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.divider()
        st.markdown("### Monitoramento de prazos")
        if atrasadas:
            st.error(f"Existem {atrasadas} demanda(s) com prazo vencido.")
        else:
            st.success("Nenhuma demanda com prazo vencido.")

        st.markdown("### Distribuição por categoria")
        categorias = (
            df["categoria"].fillna("Pendente").replace("", "Pendente")
            .value_counts().rename_axis("Categoria")
            .reset_index(name="Quantidade")
        )

        grafico = (
            alt.Chart(categorias)
            .mark_bar(color="#B99A62", cornerRadiusEnd=5)
            .encode(
                x=alt.X(
                    "Categoria:N",
                    title="Categoria",
                    axis=alt.Axis(
                        labelColor="#344054",
                        titleColor="#344054",
                        labelAngle=0,
                        grid=False,
                    ),
                ),
                y=alt.Y(
                    "Quantidade:Q",
                    title="Número de demandas",
                    axis=alt.Axis(
                        labelColor="#667085",
                        titleColor="#344054",
                        tickMinStep=1,
                        gridColor="#EAE7E0",
                    ),
                ),
                tooltip=["Categoria:N", "Quantidade:Q"],
            )
            .properties(height=300, background="#FFFFFF")
            .configure_view(stroke=None)
            .configure(background="#FFFFFF")
        )

        st.altair_chart(grafico, use_container_width=True, theme=None)

        st.markdown("### Solicitações recentes")
        colunas = [
            coluna for coluna in [
                "id", "titulo", "categoria", "urgencia", "prazo",
                "status", "status_aprovacao"
            ] if coluna in df.columns
        ]
        tabela = df[colunas].head(10).copy()
        tabela = tabela.rename(columns={
            "id": "ID",
            "titulo": "Título",
            "categoria": "Categoria",
            "urgencia": "Prioridade",
            "prazo": "Prazo",
            "status": "Status operacional",
            "status_aprovacao": "Revisão jurídica",
        })
        st.dataframe(tabela, use_container_width=True, hide_index=True)
        st.caption("Informações consultadas diretamente no banco de dados SQLite.")


# =====================================================
# 8. CENTRAL DE REVISAO JURIDICA
# =====================================================

elif pagina == "Revisão jurídica":


        
    st.markdown("""
    <div class="section-number">LEGAL CONTROL / 03</div>
    <div class="section-title">Central de revisão jurídica</div>
    <div class="section-description">
        Analise a triagem automática, ajuste a classificação e registre a decisão.
    </div>
    """, unsafe_allow_html=True)

    df = listar_solicitacoes()

    if df.empty:
        st.info("Ainda não existem solicitações para revisar.")
    else:
        if "status_aprovacao" not in df.columns:
            df["status_aprovacao"] = "Pendente de revisão"

        df["status_aprovacao"] = (
            df["status_aprovacao"]
            .fillna("Pendente de revisão")
            .replace("", "Pendente de revisão")
        )

        pendentes = df[
            df["status_aprovacao"].astype(str).str.lower()
            .eq("pendente de revisão")
        ].copy()

        aprovadas = int(
            df["status_aprovacao"].astype(str).str.lower().eq("aprovada").sum()
        )
        reprovadas = int(
            df["status_aprovacao"].astype(str).str.lower().eq("reprovada").sum()
        )

        k1, k2, k3 = st.columns(3)
        k1.metric("Aguardando revisão", len(pendentes))
        k2.metric("Aprovadas", aprovadas)
        k3.metric("Reprovadas", reprovadas)

        st.divider()

        if pendentes.empty:
            st.success("Não há solicitações pendentes de revisão.")
        else:
            opcoes = {
                f'#{int(linha["id"])} — {linha["titulo"]}': int(linha["id"])
                for _, linha in pendentes.iterrows()
            }

            selecionada = st.selectbox(
                "Selecione uma solicitação pendente",
                options=list(opcoes.keys()),
            )
            id_selecionado = opcoes[selecionada]
            item = df[df["id"] == id_selecionado].iloc[0]

            st.markdown("### Dados da solicitação")
            with st.container(border=True):
                a, b = st.columns(2)
                with a:
                    st.markdown(
                        f'<div class="review-label">SOLICITANTE</div>'
                        f'<div class="review-value">{item.get("solicitante", "—")}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="review-label" style="margin-top:16px;">ÁREA DE ORIGEM</div>'
                        f'<div class="review-value">{item.get("area_solicitante", "—")}</div>',
                        unsafe_allow_html=True,
                    )
                with b:
                    st.markdown(
                        f'<div class="review-label">PRAZO DESEJADO</div>'
                        f'<div class="review-value">{item.get("prazo", "—")}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="review-label" style="margin-top:16px;">CADASTRADA EM</div>'
                        f'<div class="review-value">{item.get("criado_em", "—")}</div>',
                        unsafe_allow_html=True,
                    )

                
                    st.markdown("---")

                    st.markdown(
                        f"""
                        <div style="margin-top: 18px; margin-bottom: 8px;
                                    color: #354255; font-size: 14px;
                                    font-weight: 700;">
                            TÍTULO
                        </div>
                        <div style="color: #14243A; font-size: 17px;
                                    font-weight: 600; line-height: 1.6;">
                            {item.get("titulo", "—")}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"""
                        <div style="margin-top: 22px; margin-bottom: 8px;
                                    color: #354255; font-size: 14px;
                                    font-weight: 700;">
                            DESCRIÇÃO DETALHADA
                        </div>
                        <div style="color: #14243A; font-size: 15px;
                                    font-weight: 500; line-height: 1.7;
                                    white-space: pre-wrap;">
                            {item.get("descricao", "—")}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


            st.markdown("### Classificação sugerida pelo sistema")
            st.caption(
                "Confira os campos abaixo. Você pode corrigir a sugestão automática "
                "antes de registrar sua decisão."
            )

            categorias_validas = [
                "Contratos",
                "Trabalhista",
                "Tributário",
                "Cível",
                "Societário",
                "Proteção de Dados",
                "Propriedade Intelectual",
                "Compliance",
                "Regulatório",
                "Outros",
                "Não identificada",
            ]
            urgencias_validas = ["Baixa", "Média", "Alta", "Crítica"]

            categoria_atual = str(item.get("categoria") or "Não identificada")
            urgencia_atual = str(item.get("urgencia") or "Média")
            responsavel_atual = str(item.get("responsavel") or "A definir")

            if categoria_atual not in categorias_validas:
                categorias_validas.insert(0, categoria_atual)
            if urgencia_atual not in urgencias_validas:
                urgencias_validas.insert(0, urgencia_atual)

            with st.form(f"form_revisao_{id_selecionado}"):
                c1, c2 = st.columns(2)
                with c1:
                    categoria_revisada = st.selectbox(
                        "Categoria jurídica",
                        categorias_validas,
                        index=categorias_validas.index(categoria_atual),
                    )
                    urgencia_revisada = st.selectbox(
                        "Nível de urgência",
                        urgencias_validas,
                        index=urgencias_validas.index(urgencia_atual),
                    )
                with c2:
                    responsavel_revisado = st.text_input(
                        "Equipe / responsável",
                        value=responsavel_atual,
                    )
                    nome_revisor = st.text_input(
                        "Nome do advogado revisor *",
                        placeholder="Informe seu nome",
                    )

                observacao = st.text_area(
                    "Observações da revisão",
                    placeholder="Registre justificativas, ajustes ou orientações...",
                    height=110,
                )

                st.markdown("**Decisão da revisão**")
                botao1, botao2 = st.columns(2)
                with botao1:
                    aprovar = st.form_submit_button(
                        "Aprovar solicitação",
                        type="primary",
                        use_container_width=True,
                    )
                with botao2:
                    reprovar = st.form_submit_button(
                        "Reprovar solicitação",
                        use_container_width=True,
                    )
            # ==========================================
            # EXIBIR MENSAGEM DE CONFIRMAÇÃO
            # ==========================================

            if "mensagem_revisao" in st.session_state:

                tipo, mensagem = st.session_state["mensagem_revisao"]

                if tipo == "sucesso":
                    st.success(mensagem)

                elif tipo == "erro":
                    st.error(mensagem)

                del st.session_state["mensagem_revisao"]

            if aprovar or reprovar:
                if not nome_revisor.strip():
                    st.error("Informe o nome do advogado revisor.")
                elif not responsavel_revisado.strip():
                    st.error("Informe a equipe ou o responsável.")
                else:
                    decisao = "Aprovada" if aprovar else "Reprovada"
                    try:
                        atualizar_revisao(
                            solicitacao_id=id_selecionado,
                            categoria=categoria_revisada,
                            urgencia=urgencia_revisada,
                            responsavel=responsavel_revisado.strip(),
                            novo_status=decisao,
                            revisor=nome_revisor.strip(),
                            observacao=observacao.strip(),
                        )
                        if decisao == "Aprovada":

                                st.session_state["mensagem_revisao"] = (
                                    "sucesso",
                                    f"Solicitação nº {id_selecionado} aprovada com sucesso!"
                                )

                        else:

                                st.session_state["mensagem_revisao"] = (
                                    "sucesso",
                                    f"Solicitação nº {id_selecionado} reprovada com sucesso!"
                                )

                        st.rerun()
                    except Exception as erro:
                        st.error(f"Não foi possível salvar a revisão: {erro}")

        st.divider()
        st.markdown("### Visão geral das decisões")
        resumo = df[[
            coluna for coluna in [
                "id", "titulo", "categoria", "urgencia",
                "responsavel", "status_aprovacao"
            ] if coluna in df.columns
        ]].copy()
        resumo = resumo.rename(columns={
            "id": "ID",
            "titulo": "Título",
            "categoria": "Categoria",
            "urgencia": "Urgência",
            "responsavel": "Responsável",
            "status_aprovacao": "Status da revisão",
        })
        st.dataframe(resumo, use_container_width=True, hide_index=True)



# =====================================================
# 9. HISTORICO DE SOLICITACOES
# =====================================================

elif pagina == "Histórico":

    st.markdown("""
    <div class="section-number">RECORDS MANAGEMENT / 04</div>
    <div class="section-title">Histórico de solicitações</div>
    <div class="section-description">
        Consulte, pesquise e acompanhe o histórico das demandas jurídicas.
    </div>
    """, unsafe_allow_html=True)

    df = listar_solicitacoes()

    if df.empty:

        st.info("Ainda não existem solicitações cadastradas.")

    else:

        # ---------------------------------------------
        # 1. PREPARACAO DOS DADOS
        # ---------------------------------------------

        df["status_aprovacao"] = (
            df["status_aprovacao"]
            .fillna("Pendente de revisão")
            .replace("", "Pendente de revisão")
        )

        df["categoria"] = (
            df["categoria"]
            .fillna("Não identificada")
            .replace("", "Não identificada")
        )

        df["status"] = (
            df["status"]
            .fillna("Aberta")
        )

        # ---------------------------------------------
        # 2. INDICADORES
        # ---------------------------------------------

        total = len(df)

        aprovadas = (
            df["status_aprovacao"] == "Aprovada"
        ).sum()

        reprovadas = (
            df["status_aprovacao"] == "Reprovada"
        ).sum()

        pendentes = (
            df["status_aprovacao"] == "Pendente de revisão"
        ).sum()

        c1, c2, c3, c4 = st.columns(4)

        indicadores = [
            ("Total de demandas", total),
            ("Aprovadas", aprovadas),
            ("Reprovadas", reprovadas),
            ("Pendentes", pendentes),
        ]

        for coluna, (titulo, valor) in zip(
            [c1, c2, c3, c4],
            indicadores
        ):

            with coluna:

                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">{titulo}</div>
                        <div class="metric-value">{valor}</div>
                        <div class="metric-accent"></div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.divider()

        # ---------------------------------------------
        # 3. FILTROS
        # ---------------------------------------------

        st.markdown("### Pesquisa e filtros")

        f1, f2 = st.columns(2)

        with f1:

            pesquisa = st.text_input(
                "Pesquisar solicitação",
                placeholder="Digite o título ou nome do solicitante..."
            )

        with f2:

            filtro_status = st.selectbox(
                "Status da aprovação",
                [
                    "Todos",
                    "Pendente de revisão",
                    "Aprovada",
                    "Reprovada"
                ]
            )

        f3, f4 = st.columns(2)

        with f3:

            categorias = [
                "Todas"
            ] + sorted(
                df["categoria"].dropna().unique().tolist()
            )

            filtro_categoria = st.selectbox(
                "Categoria jurídica",
                categorias
            )

        with f4:

            status_operacionais = [
                "Todos"
            ] + sorted(
                df["status"].dropna().unique().tolist()
            )

            filtro_operacional = st.selectbox(
                "Status operacional",
                status_operacionais
            )

        # ---------------------------------------------
        # 4. APLICAR FILTROS
        # ---------------------------------------------

        filtrado = df.copy()

        if pesquisa.strip():

            termo = pesquisa.strip()

            correspondencia = (
                filtrado["titulo"].astype(str).str.contains(
                    termo,
                    case=False,
                    na=False
                )
                |
                filtrado["solicitante"].astype(str).str.contains(
                    termo,
                    case=False,
                    na=False
                )
            )

            filtrado = filtrado[correspondencia]

        if filtro_status != "Todos":

            filtrado = filtrado[
                filtrado["status_aprovacao"] == filtro_status
            ]

        if filtro_categoria != "Todas":

            filtrado = filtrado[
                filtrado["categoria"] == filtro_categoria
            ]

        if filtro_operacional != "Todos":

            filtrado = filtrado[
                filtrado["status"] == filtro_operacional
            ]

        # ---------------------------------------------
        # 5. TABELA DE SOLICITACOES
        # ---------------------------------------------

        st.markdown("### Registro de demandas")

        st.caption(
            f"Exibindo {len(filtrado)} de {total} solicitações."
        )

        colunas_exibicao = [
            "id",
            "titulo",
            "solicitante",
            "categoria",
            "urgencia",
            "prazo",
            "status",
            "status_aprovacao"
        ]

        tabela = filtrado[colunas_exibicao].rename(
            columns={
                "id": "ID",
                "titulo": "Título",
                "solicitante": "Solicitante",
                "categoria": "Categoria",
                "urgencia": "Urgência",
                "prazo": "Prazo",
                "status": "Status operacional",
                "status_aprovacao": "Revisão jurídica"
            }
        )

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True
        )

        # ---------------------------------------------
        # 6. CONSULTA DETALHADA
        # ---------------------------------------------

        st.divider()

        st.markdown("### Consulta detalhada")

        if filtrado.empty:

            st.info(
                "Nenhuma solicitação corresponde aos filtros selecionados."
            )

        else:

            opcoes = {
                f'#{int(linha["id"])} — {linha["titulo"]}':
                int(linha["id"])
                for _, linha in filtrado.iterrows()
            }

            selecionada = st.selectbox(
                "Selecione uma demanda para consultar",
                list(opcoes.keys())
            )

            id_consulta = opcoes[selecionada]

            item = df[
                df["id"] == id_consulta
            ].iloc[0]

            
            with st.container(border=True):

                st.markdown(
                    """
                    <h3 style="color:#14243A; font-size:23px; margin-bottom:22px;">
                        Dados gerais
                    </h3>
                    """,
                    unsafe_allow_html=True,
                )

                d1, d2 = st.columns(2)

                with d1:
                    st.markdown(
                        f"""
                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">SOLICITANTE</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item["solicitante"]}</p>

                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">ÁREA DE ORIGEM</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item["area_solicitante"]}</p>

                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">CATEGORIA JURÍDICA</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item["categoria"]}</p>
                        """,
                        unsafe_allow_html=True,
                    )

                with d2:
                    st.markdown(
                        f"""
                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">PRAZO</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item["prazo"]}</p>

                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">URGÊNCIA</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item["urgencia"]}</p>

                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">RESPONSÁVEL SUGERIDO</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item["responsavel"]}</p>
                        """,
                        unsafe_allow_html=True,
                    )

                st.divider()

                st.markdown(
                    '<h3 style="color:#14243A; font-size:23px;">Descrição da demanda</h3>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f"""
                    <p style="color:#14243A; font-size:17px; font-weight:600;">
                        {item["titulo"]}
                    </p>
                    <p style="color:#354255; font-size:15px; line-height:1.8; white-space:pre-wrap;">
                        {item["descricao"]}
                    </p>
                    """,
                    unsafe_allow_html=True,
                )

                st.divider()

                st.markdown(
                    '<h3 style="color:#14243A; font-size:23px;">Revisão jurídica</h3>',
                    unsafe_allow_html=True,
                )

                r1, r2 = st.columns(2)

                with r1:
                    st.markdown(
                        f"""
                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">STATUS DA APROVAÇÃO</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item["status_aprovacao"]}</p>

                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">ADVOGADO REVISOR</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item.get("revisado_por") or "Não informado"}</p>
                        """,
                        unsafe_allow_html=True,
                    )

                with r2:
                    st.markdown(
                        f"""
                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">DATA DA REVISÃO</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item.get("revisado_em") or "Não realizada"}</p>

                        <p style="color:#52627A; font-weight:700; margin-bottom:4px;">RESPONSÁVEL CONFIRMADO</p>
                        <p style="color:#14243A; font-size:17px; margin-top:0;">{item.get("responsavel_confirmado") or item["responsavel"] or "Não definido"}</p>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    '<p style="color:#52627A; font-weight:700; margin-bottom:4px;">OBSERVAÇÕES DA REVISÃO</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p style="color:#354255; font-size:15px; line-height:1.8;">{item.get("observacao_revisao") or "Nenhuma observação registrada."}</p>',
                    unsafe_allow_html=True,
                )

                st.divider()

                st.markdown(
                    '<h3 style="color:#14243A; font-size:23px;">Encaminhamento</h3>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f"""
                    <p style="color:#52627A; font-weight:700; margin-bottom:4px;">STATUS OPERACIONAL</p>
                    <p style="color:#14243A; font-size:17px; margin-top:0;">{item["status"]}</p>

                    <p style="color:#52627A; font-weight:700; margin-bottom:4px;">DATA DO ENCAMINHAMENTO</p>
                    <p style="color:#354255; font-size:15px; margin-top:0;">{item.get("encaminhado_em") or "Ainda não encaminhada."}</p>
                    """,
                    unsafe_allow_html=True,
                )

            # -----------------------------------------
            # 7. LINHA DO TEMPO
            # -----------------------------------------

            st.markdown("### Linha do tempo da solicitação")

            eventos = carregar_historico()

            if not eventos.empty:

                eventos_demanda = eventos[
                    eventos["solicitacao_id"] == id_consulta
                ].copy()

                if not eventos_demanda.empty:

                    colunas_eventos = [
                        "criado_em",
                        "acao",
                        "status_anterior",
                        "status_novo",
                        "usuario",
                        "observacao"
                    ]

                    linha_tempo = eventos_demanda[
                        colunas_eventos
                    ].rename(
                        columns={
                            "criado_em": "Data e hora",
                            "acao": "Evento",
                            "status_anterior": "Status anterior",
                            "status_novo": "Status novo",
                            "usuario": "Responsável pelo registro",
                            "observacao": "Observações"
                        }
                    )

                    st.dataframe(
                        linha_tempo,
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info(
                        "Ainda não existem eventos registrados "
                        "para esta solicitação."
                    )

            else:

                st.info("Histórico de eventos ainda não disponível.")
