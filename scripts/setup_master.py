import os
import sys

# Garante a inclusão do diretório pai no path do sistema para
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from utils.db import get_db_connection

# Carrega as variáveis de ambiente forçando a sobrescrita (override=True)
load_dotenv(override=True)

# Recupera as credenciais do operador Master a partir do ambiente (.env)
admin_login = os.getenv("MASTER_LOGIN")
admin_senha = os.getenv("MASTER_PASSWORD")
admin_recup = os.getenv("MASTER_RECOVERY")

if not admin_login or not admin_senha or not admin_recup:
    print("Falha ao iniciar: As credenciais Master não foram encontradas nas variáveis de ambiente.")
    print("Ação abortada (Fail-Fast). O sistema foi impedido de usar credenciais padrão inseguras.")
    sys.exit(1) # Desliga o script imediatamente devolvendo erro ao sistema operacional

print("A conectar à base de dados para configurar a conta Master...")

with get_db_connection() as conn, conn.cursor() as cursor:
    # Trava de Segurança: Verifica se já existe QUALQUER usuário cadastrado como Master
    cursor.execute("SELECT id FROM operadores WHERE is_master = TRUE;")
    master_existe = cursor.fetchone()
    
    # Gera os hashes independentemente de ser INSERT ou UPDATE
    senha_criptografada = generate_password_hash(admin_senha)
    palavra_criptografada = generate_password_hash(admin_recup)
    
    if not master_existe:
        # Insere o novo operador raiz definindo explicitamente a flag 'is_master = TRUE'
        cursor.execute("""
            INSERT INTO operadores (login, senha, palavra_recuperacao, is_master)
            VALUES (%s, %s, %s, TRUE);
        """, (admin_login, senha_criptografada, palavra_criptografada))
        print(f"Operador Master criado de forma segura! (Login: {admin_login})")
    else:
        # Atualiza o administrador Master existente com as novas credenciais do .env
        id_master = master_existe[0]
        cursor.execute("""
            UPDATE operadores 
            SET login = %s, senha = %s, palavra_recuperacao = %s 
            WHERE id = %s;
        """, (admin_login, senha_criptografada, palavra_criptografada, id_master))
        print(f"Operador Master já existia e foi atualizado com sucesso! (Novo Login: {admin_login})")
        
    # Efetiva a transação no banco de dados
    conn.commit()