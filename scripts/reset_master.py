import os
import sys

# Garante a inclusão do diretório pai no path do sistema
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from utils.db import get_db_connection

# Carrega as variáveis de ambiente
load_dotenv(override=True)

admin_login = os.getenv("MASTER_LOGIN")
admin_senha = os.getenv("MASTER_PASSWORD")
admin_recup = os.getenv("MASTER_RECOVERY")

if not admin_login or not admin_senha or not admin_recup:
    sys.exit("Falha: Credenciais Master ausentes no arquivo .env.")

print("A verificar conta Master...")

with get_db_connection() as conn, conn.cursor() as cursor:
    cursor.execute("SELECT id FROM operadores WHERE is_master = TRUE;")
    master_existe = cursor.fetchone()
    
    senha_criptografada = generate_password_hash(admin_senha)
    palavra_criptografada = generate_password_hash(admin_recup)
    
    if not master_existe:
        cursor.execute("""
            INSERT INTO operadores (login, senha, palavra_recuperacao, is_master)
            VALUES (%s, %s, %s, TRUE);
        """, (admin_login, senha_criptografada, palavra_criptografada))
        print(f"Master recriado! (Login: {admin_login})")
    else:
        id_master = master_existe[0]
        cursor.execute("""
            UPDATE operadores 
            SET login = %s, senha = %s, palavra_recuperacao = %s 
            WHERE id = %s;
        """, (admin_login, senha_criptografada, palavra_criptografada, id_master))
        print(f"Credenciais do Master atualizadas com sucesso sem perda de dados! (Login: {admin_login})")
        
    conn.commit()