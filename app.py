import os
import secrets
from datetime import timedelta
from flask import Flask, render_template, g, request, redirect, url_for
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

# Importação dos Blueprints (módulos de rotas) divididos por responsabilidade
from routes.public import public_bp
from routes.auth import auth_bp
from routes.admin import admin_bp

# Carrega as variáveis de ambiente globais a partir do arquivo .env (ex: SECRET_KEY, DATABASE_URL)
load_dotenv(override=True)

# Inicializa a instância principal da aplicação Flask
app = Flask(__name__)

# Informa ao Flask que ele está atrás de um Proxy
# Isso permite que ele leia o cabeçalho 'X-Forwarded-For' e pegue o IP real do atacante
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Define a chave secreta essencial para criptografar os cookies de sessão (session) do Flask
# Se a chave não existir ou for a string padrão do .env.example, gera uma chave segura em tempo de execução
secret_key = os.getenv("SECRET_KEY")
is_dev = os.getenv("FLASK_DEBUG") == "1" or os.getenv("FLASK_ENV") == "development" or os.getenv("DEBUG") == "1"

if not secret_key or secret_key == "sua_chave_super_secreta_aqui":
    if not is_dev:
        # Fail-Fast em Produção: Se não houver chave no Heroku, derruba o app para alertar o admin
        raise RuntimeError("⚠️ SEGURANÇA: SECRET_KEY não configurada no ambiente de Produção!")
    # Apenas em desenvolvimento local geramos uma chave aleatória
    secret_key = secrets.token_hex(32)

app.secret_key = secret_key

app.config.update(
    # Exige que o cookie só seja transmitido em conexões HTTPS (criptografadas)
    SESSION_COOKIE_SECURE=not is_dev,
    # Impede que o cookie seja acessível via JavaScript (mitigação de XSS/sequestro de sessão)
    SESSION_COOKIE_HTTPONLY=True,
    # Impede que o cookie seja enviado por requisições originadas de outros sites
    SESSION_COOKIE_SAMESITE='Strict',
    # Limita o tamanho do payload para evitar DoS por requisições grandes.
    MAX_CONTENT_LENGTH= 1 * 1024 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=15),
)

# Inicializa a proteção global contra CSRF blindando todas as rotas
csrf = CSRFProtect(app)

# Tenta ler a variável do Redis Cloud (Produção); se ausente, usa memória (Local)
redis_url = os.getenv("REDISCLOUD_URL", "memory://")

# Inicializa o Rate Limiter (Limita requisições abusivas por IP)
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=redis_url, # Usa Redis em produção; memória como fallback local
    default_limits=["1000 per day", "200 per hour"] # Limite global grande para não atrapalhar o uso normal
)

# Permite apenas 5 tentativas por minuto nas rotas de Login e Recuperação de Senha (Rate Limiter)
limiter.limit("5 per minute")(auth_bp)

# Permite apenas 30 ações por minuto nas rotas públicas (Impede o Spam de doações falsas)
limiter.limit("30 per minute")(public_bp)

# Registra os componentes de rotas (Blueprints) no núcleo do ecossistema do app
app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# Gera um nonce criptográfico único por requisição para uso na CSP
def get_csp_nonce():
    """Gera o nonce sob demanda para evitar falhas com interceptadores como o Limiter"""
    if not hasattr(g, 'csp_nonce'):
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce

# Disponibiliza o nonce e as variáveis globais para os templates
@app.context_processor
def inject_global_context():
    return {
        # Variável CSP
        'csp_nonce': get_csp_nonce(), # Chamada segura sob demanda
        'rua': os.getenv('RUA', 'Rua Exemplo'),
        'numero': os.getenv('NUMERO', '123'),
        'bairro': os.getenv('BAIRRO', 'Centro'),
        'cidade': os.getenv('CIDADE', 'São Paulo'),
        'estado': os.getenv('ESTADO', 'SP'),
        'cep': os.getenv('CEP', '00000-000'),
        'telefone': os.getenv('TELEFONE', '(11) 99999-9999'),
        'pix': os.getenv('PIX', 'pix@exemplo.com'),
        'instagram': os.getenv('INSTAGRAM', '@sua_ong'),
        'facebook': os.getenv('FACEBOOK', 'sua_ong'),
        'nome_ong': os.getenv('NOME_ONG', 'AmparoTech'),
        'paroquia_url': os.getenv('PAROQUIA_URL', 'AmparoTech'),
        'diocese_url': os.getenv('DIOCESE_URL', 'AmparoTech'),       
    }


# Captura o erro 429 globalmente e exibe uma página customizada
@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template("429.html"), 429

# Captura o erro 404 globalmente e exibe uma página customizada
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# Security Headers HTTP
@app.after_request
def adicionar_cabecalhos_seguranca(response):
    """
    Injeta cabeçalhos HTTP de segurança em todas as respostas do servidor.
    Mitigações exigidas por auditorias SAST/DAST modernas.
    """

    # Previne Clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Bloqueia MIME Sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Referrer Policy 
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy 
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # Strict-Transport-Security (HSTS) — Força navegadores a usar HTTPS
    # max-age=31536000 (1 ano), includeSubDomains cobre todos os subdomínios,
    # preload permite inclusão em listas pré-carregadas de navegadores
    if not is_dev:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # Resgata o nonce de forma segura garantindo sua existência
    nonce = get_csp_nonce()
    nonce_directive = f"'nonce-{nonce}'"

    csp = (
        f"default-src 'self'; "
        f"script-src 'self' {nonce_directive} https://cdn.jsdelivr.net https://code.jquery.com https://cdn.datatables.net https://cdnjs.cloudflare.com; "
        f"style-src 'self' {nonce_directive} https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdn.datatables.net; "
        f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data:; "
        f"img-src 'self' data:;"
    )

    response.headers['Content-Security-Policy'] = csp    
    return response


# Middleware para redirecionar HTTP para HTTPS
@app.before_request
def enforce_https():
    if not is_dev and not request.is_secure:
        return redirect(request.url.replace('http://', 'https://'), code=301)


# Verifica se o script está sendo executado diretamente pelo terminal
if __name__ == "__main__":
    '''Inicia o servidor de desenvolvimento local.
     
     O modo debug é ativado apenas quando FLASK_DEBUG=1 ou FLASK_ENV=development,
     conforme a variável is_dev definida acima.
     
     host='0.0.0.0' torna o app acessível em todas as interfaces de rede, não só localhost.
     
     port=5000 define a porta padrão onde o servidor irá escutar por requisições.'''
    app.run(host='0.0.0.0', port=5000, debug=is_dev)
