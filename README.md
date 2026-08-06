# AmparoTech - Plataforma de Gestão Social e Estoque Híbrido

A **AmparoTech** é uma plataforma web desenvolvida para conectar a solidariedade da comunidade com as demandas reais de Organizações Não Governamentais (ONGs). O sistema organiza promessas públicas de doação e unifica o controle de inventário físico de forma automatizada, transparente e auditável.

## 🚀 Funcionalidades Principais

### 🌐 Interface Pública
* **Painel de Necessidades:** Exibe em tempo real as campanhas de arrecadação ativas e o progresso percentual de cada meta.
* **Registro de Intenções:** Permite que doadores registrem promessas de mantimentos de forma nominada ou totalmente anônima, com sanitização rígida de dados.
* **Manifesto e Informações:** Seções institucionais detalhando a história da aliança social e canais diretos de contato como chave PIX.

### 🔐 Painel Administrativo (Acesso Restrito)
* **Triagem de Pendências:** Gerenciador cronológico para aprovação ou recusa de doações entregues, contendo travas automáticas para monitoramento de prazos de expiração de 7 dias.
* **Gestão de Campanhas:** Controle centralizado para criação, arquivamento automático (soft delete) e edição de metas públicas de itens arrecadados.
* **Estoque Interno:** Módulo híbrido que gerencia o inventário real de mantimentos, permitindo entradas e saídas manuais com justificativas mandatórias.
* **Auditoria de Segurança:** Histórico imutável de logs focado em rastrear todas as ações de criação, edição, exclusão e logins efetuados por operadores.
* **Gestão de Contas Master:** Controle de permissões avançado restrito a administradores Master para inclusão e revogação de acessos de operadores padrão.
* **Relatórios Gráficos:** Exibição analítica do desempenho das arrecadações comparando o saldo atual com as metas necessárias por meio de gráficos de barras dinâmicos.

## 🛡️ Segurança Avançada (Auditoria e Pentest Mitigations)
A arquitetura do AmparoTech foi desenhada visando a resiliência contra as principais vulnerabilidades listadas pela OWASP:

* **Blindagem de Infraestrutura (Docker Rootless):** Contêineres executados com usuário não-privilegiado (`appuser`), restringindo acesso de root, isolando capacidades do kernel e aplicando verificações ativas nativas de integridade (`healthchecks`).
* **Proteção XSS e Injeção de Scripts:** Implementação estrita de *Content Security Policy* (CSP Level 3) com geração dinâmica de *nonces* criptográficos de 128 bits a cada requisição, invalidando qualquer execução de scripts *inline* não autorizados.
* **Segurança de Transporte e Sessão:** Forçamento de HTTPS via `Strict-Transport-Security` (HSTS), cookies de sessão rigidamente configurados (`HttpOnly`, `Secure`, `SameSite=Strict`) e middleware forçando redirecionamento de tráfego HTTP claro.
* **Prevenção de CSRF:** Proteção global contra *Cross-Site Request Forgery* via tokens criptográficos dinâmicos exigidos em todas as mutações de estado (POST).
* **Mitigação de Race Conditions:** Travas de concorrência atômicas executadas nativamente no banco de dados (`UPDATE ... AND status = 'Pendente'`) para impedir duplicação de saldo e fraude de estoque por *exploits* automatizados simultâneos.
* **Rate Limiting e Defesa de DoS:** Regras rígidas de limite de requisições por IP via *Flask-Limiter* (Redis), somado ao bloqueio temporário dinâmico de contas (*Account Lockout*) por tentativas sucessivas de quebra de credenciais (Força Bruta). Limite imposto também sobre o tamanho máximo da carga de dados (`MAX_CONTENT_LENGTH`).
* **Bloqueio de Soft Delete Bypass:** Validação estrita de estado (`ativo = TRUE`) injetada diretamente nas queries de alteração, impedindo que requisições forçadas via API manipulem produtos ou campanhas já arquivadas.

## 🛠️ Tecnologias Utilizadas
* **Containerização e DevOps:** Docker, Docker Compose e orquestração de rede isolada.
* **Backend:** Python 3.14 + Flask (Arquitetura modular baseada em Blueprints).
* **Banco de Dados:** PostgreSQL 15 com a biblioteca Psycopg 3 para gerenciamento assíncrono e transações seguras.
* **Segurança e Autenticação:** 
  * Werkzeug Security (Hashes de senhas criptografadas).
  * Flask-WTF (Prevenção contra falsificação de requisições).
  * Flask-Limiter integrado ao **Redis** (Controle global e barreira de requisições abusivas distribuídas em múltiplos workers).
* **Frontend:** Bootstrap 5 (Tema Escuro), DataTables (com plugins para ordenação alfabética sem acentos e exportação integrada para planilhas Excel), Choices.js e Chart.js.
* **Hospedagem / Infraestrutura:** Deploy nativo em PaaS (Heroku), com banco de dados gerenciado, provedor Redis Cloud e servidor WSGI Gunicorn multi-worker.

## 📂 Estrutura de Diretórios Recomendada

```text
amparotech/
├── routes/
│   ├── admin.py
│   ├── auth.py
│   └── public.py
├── scripts/
│   ├── banco_setup.py
│   └── reset_master.py
├── static/
│   ├── css/
│   │   ├── adapt.css
│   │   ├── admin.css
│   │   └── globais.css
│   ├── img/
│   │   └── favicon.png
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
💡 A aplicação possui fallback automático para geração de chaves. Se necessário, adapte as credenciais do Master e as informações institucionais listadas no arquivo.

### 4. Executar a Aplicação com Docker
Para construir a imagem e subir os contêineres blindados (Aplicação Web + Banco de Dados PostgreSQL), execute a limpeza de volumes legados e inicie no modo detached:

```bash
docker compose down -v
docker compose up -d --force-recreate
```
(Aguarde alguns segundos até que o healthcheck valide a disponibilidade do banco de dados).

### 5. Inicialização do Banco de Dados
Com a infraestrutura confirmada como saudável, instancie as tabelas e a sua credencial administrativa:

```bash
# Passo A: Criação das tabelas e relacionamentos DDL
docker compose exec web python scripts/banco_setup.py

# Passo B (Opcional): Reset da conta master, caso digitado algo errado no .env
docker compose exec web python scripts/reset_master.py
```

## 💻 Acesso ao Sistema
Após a inicialização com sucesso, a interface pública da plataforma estará disponível em:

👉 http://localhost:5000

Para acessar o painel administrativo restrito (/login), utilize as credenciais injetadas nas variáveis `MASTER_LOGIN` e `MASTER_PASSWORD` definidas no seu arquivo .env.

## 🛑 Encerrar o Sistema
Para parar e remover os containers em execução, rode o seguinte comando na raiz do projeto:
```bash
docker compose down
```

## 👥 Equipe de Desenvolvimento
Plataforma inteiramente idealizada e implementada por universitários de Análise e Desenvolvimento de Sistemas como aplicação prática de Engenharia de Software voltada ao Impacto Social.
