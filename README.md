# AmparoTech - Plataforma de Gestão Social e Estoque Híbrido

O **AmparoTech** é uma plataforma web desenvolvida para conectar a solidariedade da comunidade com as demandas reais de Organizações Não Governamentais (ONGs). O sistema organiza promessas públicas de doação e unifica o controle de inventário físico de forma automatizada, transparente e auditável.

## 🚀 Funcionalidades Principais

### 🌐 Interface Pública
* **Painel de Necessidades:** Exibe em tempo real as campanhas de arrecadação ativas e o progresso percentual de cada meta.
* **Registro de Intenções:** Permite que doadores registrem promessas de mantimentos de forma nominada ou totalmente anônima.
* **Manifesto e Informações:** Seções institucionais detalhando a história da aliança social e canais diretos de contato como chave PIX.

### 🔐 Painel Administrativo (Acesso Restrito)
* **Triagem de Pendências:** Gerenciador cronológico para aprovação ou recusa de doações entregues, contendo travas automáticas para monitoramento de prazos de expiração de 7 dias.
* **Gestão de Campanhas:** Controle centralizado para criação, arquivamento automático (soft delete) e edição de metas públicas de itens arrecadados.
* **Estoque Interno:** Módulo híbrido que gerencia o inventário real de mantimentos, permitindo entradas e saídas manuais com justificativas mandatórias.
* **Auditoria de Segurança:** Histórico imutável de logs focado em rastrear todas as ações de criação, edição, exclusão e logins efetuados por operadores.
* **Gestão de Contas Master:** Controle de permissões avançado restrito a administradores Master para inclusão e revogação de acessos de operadores padrão.
* **Relatórios Gráficos:** Exibição analítica do desempenho das arrecadações comparando o saldo atual com as metas necessárias por meio de gráficos de barras dinâmicos.

### 🛡️ Segurança Avançada (Pentest Mitigations)
* **Prevenção de CSRF:** Proteção global contra *Cross-Site Request Forgery* via tokens criptográficos dinâmicos exigidos em todas as mutações de estado (POST).
* **Mitigação de Race Conditions:** Travas de concorrência atômicas executadas nativamente no banco de dados (`UPDATE ... AND status = 'Pendente'`) para impedir duplicação de saldo por *exploits* automatizados.
* **Rate Limiting:** Regras rígidas de limite de requisições por IP implementadas para bloquear tentativas de ataques de Força Bruta no login e *Spam* de formulários no banco de dados (Prevenção de DoS).
* **Bloqueio de Soft Delete Bypass:** Validação estrita de estado (`ativo = TRUE`) injetada diretamente nas queries de alteração, impedindo que requisições forçadas via API manipulem produtos ou campanhas já arquivadas.
* **Política de Complexidade e Acesso:** Trava lógica para tamanho mínimo de credenciais na criação e recuperação de senhas, somada à exigência do método POST para encerramento de sessões (Prevenção contra *Logout CSRF*).

## 🛠️ Tecnologias Utilizadas
* **Containerização:** Docker e Docker Compose.
* **Backend:** Python 3 + Flask (Arquitetura modular baseada em Blueprints).
* **Banco de Dados:** PostgreSQL com a biblioteca Psycopg 3 para gerenciamento assíncrono e transações seguras.
* **Segurança e Autenticação:** 
  * Werkzeug Security (Hashes de senhas criptografadas).
  * Flask-WTF (Prevenção contra falsificação de requisições).
  * Flask-Limiter integrado ao **Redis** (Controle global e barreira de requisições abusivas distribuídas em múltiplos workers).
* **Frontend:** Bootstrap 5 (Tema Escuro), DataTables (com plugins para ordenação alfabética sem acentos e exportação integrada para planilhas Excel) e Chart.js.
* **Hospedagem / Infraestrutura:** Deploy nativo no Heroku (PaaS), com banco de dados Heroku Postgres, provedor Redis Cloud e servidor WSGI Gunicorn.

## 📂 Estrutura de Diretórios Recomendada

```text
amparotech/
├── routes/
│   ├── admin.py
│   ├── auth.py
│   └── public.py
├── scripts/
│   ├── banco_setup.py
|   ├── popular_apresentacao.py
│   └── setup_master.py
├── static/
│   ├── css/
│   │   ├── admin.css
│   │   └── globais.css
│   └── js/
│       ├── admin.js
|       ├── pt-BR.json
│       └── utilidades.js
├── templates/
│   ├── partials/
│   │   └── footer.html
|   ├── 429.html
│   ├── admin.html
│   ├── base.html
│   ├── doar.html
│   ├── index.html
│   ├── login.html
│   └── sobre.html
├── utils/
│   ├── db.py
│   └── decorators.py
├── .env.example
├── app.py
├── docker.compose.yml
├── Dockerfile
├── Procfile
└── requirements.txt
```

## 🔧 Configuração e Instalação (Via Docker)

### 1. Pré-requisitos
Certifique-se de possuir o Docker e o Docker Compose instalados em sua máquina operacional.

### 2. Clonar o Repositório
```bash
# Clonar repositório
git clone https://github.com/rafaelpradoj/amparo-tech.git

# Entrar no diretório
cd amparo-tech
```

### 3. Configuração das Variáveis de Ambiente
Crie uma cópia do arquivo `.env.example` nomeando-a como `.env`

```bash
cp .env.example .env
```
💡 Sobre a `SECRET_KEY`: o arquivo `.env` já vem com valores padrão para facilitar a configuração em ambiente local. Se nenhuma chave for informada, a aplicação gera automaticamente uma `SECRET_KEY` segura. Se necessário, você também pode alterar as demais credenciais no arquivo `.env`.

### 4. Executar a Aplicação com Docker
Para construir a imagem e subir os containers (Aplicação Web + Banco de Dados PostgreSQL), execute:

```bash
docker compose up --build
```

### 5. Inicialização do Banco de Dados
Com os containers rodando, abra um novo terminal no mesmo diretório e execute os scripts utilitários para criar as tabelas e o usuário administrador Master:

```bash
# Passo A: Criação das tabelas no banco de dados
docker compose exec web python scripts/banco_setup.py

# Passo B: Criação da conta de acesso Master
docker compose exec web python scripts/setup_master.py

# Passo C (Opcional): Injeção de dados fake para testes
docker compose exec web python scripts/popular_apresentacao.py
```

## 💻 Acesso ao Sistema
Após a inicialização dos containers e do banco de dados, a aplicação estará disponível em:

👉 http://localhost:5000

Para acessar o painel administrativo, utilize as credenciais `MASTER_LOGIN` e `MASTER_PASSWORD` configuradas no seu arquivo `.env`.

## 👥 Equipe de Desenvolvimento
Plataforma inteiramente idealizada e implementada por universitários de Análise e Desenvolvimento de Sistemas como aplicação prática de Engenharia de Software voltada ao Impacto Social.
