# AmparoTech - Plataforma de Gestão Social e Estoque Híbrido

O **AmparoTech** é uma plataforma web desenvolvida para conectar a solidariedade da comunidade com as demandas reais de Organizações Não Governamentais (ONGs). O sistema organiza promessas públicas de doação e unifica o controle de inventário físico de forma automatizada, transparente e auditável.

## 🚀 Funcionalidades Principais

### Interface Pública
* **Painel de Necessidades:** Exibe em tempo real as campanhas de arrecadação ativas e o progresso percentual de cada meta.
* **Registro de Intenções:** Permite que doadores registrem promessas de mantimentos de forma nominada ou totalmente anônima.
* **Manifesto e Informações:** Seções institucionais detalhando a história da aliança social e canais diretos de contato como chave PIX.

### Painel Administrativo (Acesso Restrito)
* **Triagem de Pendências:** Gerenciador cronológico para aprovação ou recusa de doações entregues, contendo travas automáticas para monitoramento de prazos de expiração de 7 dias.
* **Gestão de Campanhas:** Controle centralizado para criação, arquivamento automático (soft delete) e edição de metas públicas de itens arrecadados.
* **Estoque Interno:** Módulo híbrido que gerencia o inventário real de mantimentos, permitindo entradas e saídas manuais com justificativas mandatórias.
* **Auditoria de Segurança:** Histórico imutável de logs focado em rastrear todas as ações de criação, edição, exclusão e logins efetuados por operadores.
* **Gestão de Contas Master:** Controle de permissões avançado restrito a administradores Master para inclusão e revogação de acessos de operadores padrão.
* **Relatórios Gráficos:** Exibição analítica do desempenho das arrecadações comparando o saldo atual com as metas necessárias por meio de gráficos de barras dinâmicos.

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python 3 + Flask (Arquitetura modular baseada em Blueprints).
* **Banco de Dados:** PostgreSQL com a biblioteca Psycopg 3 para gerenciamento assíncrono e transações seguras.
* **Autenticação:** Werkzeug Security para criptografia e validação forte de hashes de senhas e chaves de segurança.
* **Frontend:** Bootstrap 5 (Tema Escuro), DataTables (com plugins para ordenação alfabética sem acentos e exportação integrada para planilhas Excel) e Chart.js.

## 📂 Estrutura de Diretórios Recomendada

```text
amparotech/
├── routes/
│   ├── admin.py
│   ├── auth.py
│   └── public.py
├── static/
│   ├── css/
│   │   ├── admin.css
│   │   └── globais.css
│   └── js/
│       ├── admin.js
│       └── utilidades.js
├── templates/
│   ├── partials/
│   │   └── footer.html
│   ├── admin.html
│   ├── base.html
│   ├── doar.html
│   ├── index.html
│   ├── login.html
│   └── sobre.html
├── utils/
│   ├── db.py
│   └── decorators.py
├── scripts/
│   ├── banco_setup.py
│   └── setup_master.py
├── .env
├── app.py
└── requirements.txt
```
## 🔧 Configuração e Instalação

### 1. Pré-requisitos
Certifique-se de possuir o Python 3.x e o banco de dados PostgreSQL devidamente configurados em sua máquina operacional.

### 2. Clonar e Instalar Dependências
Crie um ambiente virtual em seu terminal e instale as bibliotecas requeridas:

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar no Linux/macOS
source venv/bin/activate

# Ativar no Windows
venv\Scripts\activate

# Instalar dependências de produção e desenvolvimento
pip install -r requirements.txt
```

### 3. Configuração de Variáveis de Ambiente
Crie um arquivo nomeado `.env` na raiz do projeto e configure as chaves de acesso conforme o modelo abaixo:

```env
DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/nome_do_banco
SECRET_KEY=sua_chave_secreta_flask_aqui

# Credenciais de Inicialização do Administrador Root
MASTER_LOGIN=admin
MASTER_PASSWORD=master123
MASTER_RECOVERY=amparo2026
```

### 4. Inicialização do Banco de Dados
Execute os scripts utilitários na ordem descrita para estruturar as tabelas relacionais do PostgreSQL e criar a primeira conta administrativa Master de segurança:

```bash
# Passo A: Limpeza e criação estrutural da arquitetura das tabelas
python scripts/banco_setup.py

# Passo B: Provisionamento seguro da conta raiz administrativa
python scripts/setup_master.py
```

## 💻 Como Rodar a Aplicação

Com o banco de dados configurado e as credenciais inseridas, execute o comando principal na raiz do projeto:

```bash
python app.py
```

O servidor de desenvolvimento iniciará automaticamente no endereço local http://127.0.0.1:5000. O modo de depuração (debug=True) está ativo para recarregar o servidor a cada alteração efetuada nos arquivos de código.

## 👥 Equipe de Desenvolvimento
Plataforma inteiramente idealizada e implementada por universitários de Análise e Desenvolvimento de Sistemas como aplicação prática de Engenharia de Software voltada ao Impacto Social.