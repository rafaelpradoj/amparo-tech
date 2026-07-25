import os
from flask import Flask, render_template
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
load_dotenv()

# Inicializa a instância principal da aplicação Flask
app = Flask(__name__)

# Informa ao Flask que ele está atrás de um Proxy
# Isso permite que ele leia o cabeçalho 'X-Forwarded-For' e pegue o IP real do atacante
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Define a chave secreta essencial para criptografar os cookies de sessão (session) do Flask
app.secret_key = os.getenv("SECRET_KEY")

app.config.update(
    # Exige que o cookie só seja transmitido em conexões HTTPS (criptografadas)
    SESSION_COOKIE_SECURE=True,
    # Impede que o cookie seja enviado por requisições originadas de outros sites
    SESSION_COOKIE_SAMESITE='Lax'
)

# Inicializa a proteção global contra CSRF blindando todas as rotas
csrf = CSRFProtect(app)

# Inicializa o Rate Limiter (Limita requisições abusivas por IP)
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://", # Armazena a contagem na memória do servidor
    default_limits=["1000 per day", "200 per hour"] # Limite global grande para não atrapalhar o uso normal
)

# Permite apenas 5 tentativas por minuto nas rotas de Login e Recuperação de Senha (Rate Limiter)
limiter.limit("5 per minute")(auth_bp)

# Permite apenas 10 ações por minuto nas rotas públicas (Impede o Spam de doações falsas)
limiter.limit("10 per minute")(public_bp)

# Registra os componentes de rotas (Blueprints) no núcleo do ecossistema do app
app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# Captura o erro 429 globalmente e exibe uma página customizada
@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template("429.html"), 429

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
    
    # Content-Security-Policy (CSP) - A última linha de defesa contra XSS
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com https://cdn.datatables.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdn.datatables.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data:; "
        "img-src 'self' data:;"
    )
    response.headers['Content-Security-Policy'] = csp
    
    return response


# Verifica se o script está sendo executado diretamente pelo terminal
if __name__ == "__main__":
    # Inicia o servidor de desenvolvimento local com o modo de depuração (debug) ativo.
    # O debug=True reinicia o servidor automaticamente a cada alteração salva no código.
    app.run(debug=True)