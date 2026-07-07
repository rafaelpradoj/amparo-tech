import os
import psycopg

def get_db_connection():
    """
    Estabelece e retorna uma nova conexão ativa com o banco de dados PostgreSQL.
    A função busca a string de conexão nas variáveis de ambiente e utiliza a biblioteca
    psycopg para abrir o canal de comunicação.
    """
    # Recupera a URL de conexão (string com host, usuário, senha e porta) do arquivo .env ou ambiente
    url_banco = os.getenv("DATABASE_URL")
    
    # Cria e retorna o objeto de conexão do psycopg para ser gerenciado pelos cursores das rotas
    return psycopg.connect(url_banco)