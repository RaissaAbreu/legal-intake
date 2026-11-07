
import unicodedata
from datetime import date, datetime


# =====================================================
# 1. NORMALIZACAO DE TEXTO
# =====================================================

def normalizar_texto(texto):
    """
    Remove acentos e transforma o texto em minusculas.
    Isso permite identificar palavras mesmo com acentos.
    """

    texto = str(texto).lower()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )

    return texto


# =====================================================
# 2. DICIONARIO DE CATEGORIAS JURIDICAS
# =====================================================

CATEGORIAS = {

    "Contratos": {
        "palavras": [
            "contrato",
            "contratos",
            "clausula",
            "assinatura",
            "fornecedor",
            "prestacao de servicos",
            "rescisao contratual",
            "aditivo",
            "renovacao contratual",
            "multa contratual"
        ],
        "responsavel": "Equipe de Contratos"
    },

    "Trabalhista": {
        "palavras": [
            "funcionario",
            "empregado",
            "demissao",
            "ferias",
            "salario",
            "rescisao trabalhista",
            "hora extra",
            "vinculo empregaticio",
            "reclamacao trabalhista",
            "fgts"
        ],
        "responsavel": "Equipe Trabalhista"
    },

    "Consumidor": {
        "palavras": [
            "consumidor",
            "cliente",
            "reclamacao",
            "reembolso",
            "devolucao",
            "produto defeituoso",
            "procon",
            "garantia",
            "atendimento ao cliente",
            "direito do consumidor"
        ],
        "responsavel": "Equipe de Direito do Consumidor"
    },

    "Regulatório": {
        "palavras": [
            "regulatorio",
            "regulacao",
            "licenca",
            "fiscalizacao",
            "agencia reguladora",
            "normativa",
            "autorizacao",
            "orgao regulador",
            "conformidade regulatoria"
        ],
        "responsavel": "Equipe Regulatória"
    },

    "Privacidade": {
        "palavras": [
            "lgpd",
            "dados pessoais",
            "dados sensiveis",
            "privacidade",
            "consentimento",
            "vazamento de dados",
            "tratamento de dados",
            "titular de dados",
            "protecao de dados",
            "incidente de seguranca"
        ],
        "responsavel": "Equipe de Privacidade e Proteção de Dados"
    },

    "Societário": {
        "palavras": [
            "sociedade",
            "acionista",
            "acionistas",
            "assembleia",
            "quotas",
            "participacao societaria",
            "contrato social",
            "estatuto social",
            "alteracao societaria",
            "conselho de administracao"
        ],
        "responsavel": "Equipe Societária"
    }
}


# =====================================================
# 3. CLASSIFICACAO JURIDICA
# =====================================================

def classificar_categoria(titulo, descricao):

    texto = normalizar_texto(
        str(titulo) + " " + str(descricao)
    )

    pontuacoes = {}

    for categoria, dados in CATEGORIAS.items():

        pontuacao = 0

        for palavra in dados["palavras"]:

            palavra_normalizada = normalizar_texto(palavra)

            if palavra_normalizada in texto:

                # O titulo recebe peso maior
                if palavra_normalizada in normalizar_texto(titulo):
                    pontuacao += 2
                else:
                    pontuacao += 1

        pontuacoes[categoria] = pontuacao

    maior_pontuacao = max(pontuacoes.values())

    if maior_pontuacao == 0:
        return {
            "categoria": "Não identificada",
            "responsavel": "Triagem manual",
            "confianca": "Sem correspondência"
        }

    categorias_vencedoras = [
        categoria
        for categoria, pontuacao in pontuacoes.items()
        if pontuacao == maior_pontuacao
    ]

    # Evita escolher automaticamente quando há empate
    if len(categorias_vencedoras) > 1:
        return {
            "categoria": "Revisão necessária",
            "responsavel": "Triagem manual",
            "confianca": "Classificação ambígua"
        }

    categoria = categorias_vencedoras[0]

    return {
        "categoria": categoria,
        "responsavel": CATEGORIAS[categoria]["responsavel"],
        "confianca": "Correspondência por palavras-chave"
    }


# =====================================================
# 4. IDENTIFICACAO DE URGENCIA
# =====================================================

def identificar_urgencia(titulo, descricao, prazo=None):

    texto = normalizar_texto(
        str(titulo) + " " + str(descricao)
    )

    palavras_urgentes = [
        "urgente",
        "urgentemente",
        "imediato",
        "imediatamente",
        "emergencia",
        "risco iminente",
        "prazo fatal",
        "prazo hoje",
        "assinatura amanha",
        "vencimento amanha"
    ]

    for palavra in palavras_urgentes:

        if palavra in texto:
            return "Alta"

    # Avaliacao do prazo informado
    if prazo is not None:

        try:

            if isinstance(prazo, datetime):
                data_prazo = prazo.date()

            elif isinstance(prazo, date):
                data_prazo = prazo

            else:
                data_prazo = date.fromisoformat(
                    str(prazo)[:10]
                )

            dias_restantes = (
                data_prazo - date.today()
            ).days

            if dias_restantes <= 2:
                return "Alta"

            elif dias_restantes <= 7:
                return "Média"

            else:
                return "Normal"

        except (ValueError, TypeError):
            pass

    return "Normal"


# =====================================================
# 5. FUNCAO PRINCIPAL DE TRIAGEM
# =====================================================

def analisar_solicitacao(titulo, descricao, prazo=None):

    resultado_categoria = classificar_categoria(
        titulo,
        descricao
    )

    urgencia = identificar_urgencia(
        titulo,
        descricao,
        prazo
    )

    return {
        "categoria": resultado_categoria["categoria"],
        "urgencia": urgencia,
        "responsavel": resultado_categoria["responsavel"],
        "confianca": resultado_categoria["confianca"]
    }
