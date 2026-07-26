import os
import psycopg
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (como as credenciais do banco)
load_dotenv(override=True)

def get_db_connection():
    """
    Estabelece e retorna uma nova conexão ativa com o banco de dados PostgreSQL.
    A função busca a string de conexão nas variáveis de ambiente e utiliza a biblioteca
    psycopg para abrir o canal de comunicação.
    """
    # Recupera a URL de conexão (string com host, usuário, senha e porta) do arquivo .env ou ambiente
    url_banco = os.getenv("DATABASE_URL")

    if not url_banco or not url_banco.strip():
        raise RuntimeError("DATABASE_URL não configurada. Defina a variável de ambiente DATABASE_URL antes de iniciar a aplicação.")
    
    # Cria e retorna o objeto de conexão do psycopg para ser gerenciado pelos cursores das rotas
    return psycopg.connect(url_banco)