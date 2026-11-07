# Legal Intake — Sistema Inteligente de Triagem Jurídica

Sistema web desenvolvido em Python para automatizar e organizar a triagem de solicitações jurídicas, facilitando a classificação de demandas, a identificação de urgências e o acompanhamento do fluxo de revisão jurídica.

O projeto foi desenvolvido como aplicação prática de conhecimentos em programação, análise de dados, persistência de informações e desenvolvimento de interfaces web.

## Objetivo do projeto

O Legal Intake busca tornar mais organizado o recebimento e o encaminhamento de demandas jurídicas, oferecendo uma interface centralizada para cadastrar solicitações, sugerir classificações e acompanhar decisões de revisão.

## Funcionalidades

- **Cadastro de solicitações:** registro de solicitante, área de origem, título, descrição e prazo.
- **Triagem automatizada:** identificação de categorias jurídicas e níveis de urgência com base em palavras-chave e regras.
- **Sugestão de responsáveis:** indicação de equipes responsáveis conforme a classificação da demanda.
- **Painel executivo:** visualização de indicadores e gráficos sobre as solicitações cadastradas.
- **Revisão jurídica:** possibilidade de aprovar ou reprovar solicitações, com registro do advogado revisor.
- **Histórico de solicitações:** consulta de decisões, observações e eventos relacionados às demandas.
- **Persistência de dados:** armazenamento local utilizando SQLite.

## Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Linguagem principal |
| Streamlit | Desenvolvimento da interface web |
| Pandas | Manipulação e organização de dados |
| Altair | Construção de gráficos |
| SQLite | Banco de dados relacional |
| Git e GitHub | Versionamento e hospedagem do código |

## Estrutura do projeto

```text
Projeto-Legal-Intake/
│
├── app.py                 # Aplicação e interface principal
├── classifier.py          # Regras de classificação das demandas
├── database.py            # Operações e estrutura do banco de dados
├── .gitignore             # Arquivos que não devem ser versionados
├── requirements.txt       # Dependências do projeto
└── README.md              # Documentação do projeto
```

## Como executar o projeto

### 1. Pré-requisitos

- Python 3 instalado
- Git instalado
- VS Code ou outro editor de código

### 2. Clonar o repositório

```bash
git clone URL_DO_REPOSITORIO
cd Projeto-Legal-Intake
```

### 3. Criar o ambiente virtual

No Ubuntu/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 5. Executar a aplicação

```bash
streamlit run app.py
```

A aplicação será disponibilizada localmente pelo Streamlit. Acesse o endereço apresentado no terminal, normalmente `http://localhost:8501`.

## Classificação das solicitações

A triagem utiliza regras e palavras-chave para sugerir:

- Categoria jurídica;
- Nível de urgência;
- Equipe ou responsável sugerido.

As classificações são sugestões automatizadas e podem ser avaliadas e ajustadas durante a revisão jurídica.

## Aprendizados e competências desenvolvidas

Durante o desenvolvimento, foram trabalhados conceitos de:

- Programação em Python;
- Organização de código em módulos;
- Desenvolvimento de aplicações web com Streamlit;
- Manipulação de dados com Pandas;
- Persistência e consultas em banco de dados SQLite;
- Operações CRUD;
- Implementação de regras de negócio;
- Versionamento de código com Git;
- Organização de projetos e documentação técnica.

## Melhorias futuras

- Implementação de autenticação e controle de acesso por perfil;
- Aprimoramento da classificação automática;
- Implementação de testes automatizados;
- Melhorias na segurança e proteção de dados;
- Possibilidade de implantação em ambiente de hospedagem.

## Observação

Este projeto possui finalidade acadêmica e demonstrativa. Não deve ser utilizado para armazenar informações jurídicas reais ou dados pessoais sem a implementação de mecanismos adequados de segurança, controle de acesso, privacidade e proteção de dados.

---

**Desenvolvido como projeto de portfólio para demonstrar conhecimentos em Python, desenvolvimento web, análise de dados e bancos de dados.**