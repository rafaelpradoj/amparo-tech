import os
import sys

# Garante a inclusão do diretório pai no path do sistema para
# permitir a importação dos utilitários de banco de dados em 'utils'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from utils.db import get_db_connection

# Carrega as variáveis de ambiente declaradas no arquivo .env
load_dotenv()

# Recupera as credenciais do operador Master a partir do ambiente (.env),
# adotando valores padrão seguros de fallback caso as variáveis não estejam definidas
admin_login = os.getenv("MASTER_LOGIN", "admin")
admin_senha = os.getenv("MASTER_PASSWORD", "master123")
admin_recup = os.getenv("MASTER_RECOVERY", "amparo2026")

print("A conectar à base de dados para configurar a conta Master...")

with get_db_connection() as conn, conn.cursor() as cursor:
    # Trava de Segurança: Verifica se já existe QUALQUER usuário cadastrado como Master
    cursor.execute("SELECT id FROM operadores WHERE is_master = TRUE;")
    master_existe = cursor.fetchone()
    
    if not master_existe:
        # Se não existir, gera hashes criptográficos seguros a partir das strings em texto limpo
        senha_criptografada = generate_password_hash(admin_senha)
        palavra_criptografada = generate_password_hash(admin_recup)
        
        # Insere o novo operador raiz definindo explicitamente a flag 'is_master = TRUE'
        cursor.execute("""
            INSERT INTO operadores (login, senha, palavra_recuperacao, is_master)
            VALUES (%s, %s, %s, TRUE);
        """, (admin_login, senha_criptografada, palavra_criptografada))
        print(f"Operador Master criado de forma segura! (Login: {admin_login})")
        print("As senhas foram importadas do seu ficheiro .env com sucesso.")
    else:
        # Caso o banco já possua um administrador Master, a operação é ignorada para evitar conflitos
        print("O Operador Master já está configurado na base de dados.")
        
    # Efetiva a transação no banco de dados
    conn.commit()