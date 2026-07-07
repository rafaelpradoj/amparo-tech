import os
from flask import Flask
from dotenv import load_dotenv

# Importação dos Blueprints (módulos de rotas) divididos por responsabilidade
from routes.public import public_bp
from routes.auth import auth_bp
from routes.admin import admin_bp

# Carrega as variáveis de ambiente globais a partir do arquivo .env (ex: SECRET_KEY, DATABASE_URL)
load_dotenv()

# Inicializa a instância principal da aplicação Flask
app = Flask(__name__)

# Define a chave secreta essencial para criptografar os cookies de sessão (session) do Flask
app.secret_key = os.getenv("SECRET_KEY")

# Registra os componentes de rotas (Blueprints) no núcleo do ecossistema do app
app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# Verifica se o script está sendo executado diretamente pelo terminal
if __name__ == "__main__":
    # Inicia o servidor de desenvolvimento local com o modo de depuração (debug) ativo.
    # O debug=True reinicia o servidor automaticamente a cada alteração salva no código.
    app.run(debug=True)