import os
import sys

# Garante que o diretório pai seja adicionado ao path do sistema,
# permitindo a importação correta dos módulos dentro de 'utils'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from utils.db import get_db_connection

# Carrega as variáveis de ambiente forçando a sobrescrita (override=True)
load_dotenv(override=True)

# 1. TRAVA DE SEGURANÇA CRÍTICA: Impede execução em Produção
if os.getenv("FLASK_ENV") != "development" and os.getenv("FLASK_DEBUG") != "1":
    sys.exit("⚠️ ERRO CRÍTICO: Execução bloqueada! Este script apaga as tabelas e não pode ser executado em produção.")

# 2. RECUPERAÇÃO E VALIDAÇÃO DE CREDENCIAIS MASTER (.env)
admin_login = os.getenv("MASTER_LOGIN")
admin_senha = os.getenv("MASTER_PASSWORD")
admin_recup = os.getenv("MASTER_RECOVERY")

if not admin_login or not admin_senha or not admin_recup:
    print("Falha ao iniciar: As credenciais Master não foram encontradas nas variáveis de ambiente.")
    print("Ação abortada (Fail-Fast). O sistema foi impedido de usar credenciais padrão inseguras.")
    sys.exit(1)

print("A tentar conectar à base de dados...")

with get_db_connection() as conn, conn.cursor() as cursor:
    print("Ligação estabelecida com sucesso! A iniciar a limpeza e recriação das tabelas...")

    # Remove as tabelas existentes usando CASCADE para garantir que tabelas dependentes
    # (com chaves estrangeiras) também sejam limpas sem bloquear a operação
    cursor.execute("DROP TABLE IF EXISTS doacoes CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS auditoria CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS campanhas CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS produtos CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS categorias CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS operadores CASCADE;")

    # --- TABELA: CATEGORIAS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL UNIQUE
        );
    """)

    # --- TABELA: OPERADORES ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operadores (
            id SERIAL PRIMARY KEY,
            login VARCHAR(30) NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            is_master BOOLEAN,
            palavra_recuperacao TEXT NOT NULL,
            ativo BOOLEAN DEFAULT TRUE
        );
    """)

    # --- TABELA: PRODUTOS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(150) NOT NULL UNIQUE,
            categoria VARCHAR(100) NOT NULL,
            estoque_fisico INTEGER NOT NULL DEFAULT 0 CHECK (estoque_fisico >= 0),
            ativo BOOLEAN DEFAULT TRUE
        );
    """)

    # --- TABELA: CAMPANHAS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campanhas (
            id SERIAL PRIMARY KEY,
            id_produto INTEGER NOT NULL,
            meta INTEGER NOT NULL CHECK (meta > 0),
            arrecadado INTEGER DEFAULT 0 CHECK (arrecadado >= 0),
            ativo BOOLEAN DEFAULT TRUE,
            pausada BOOLEAN DEFAULT FALSE,
            
            CONSTRAINT fk_campanhas_produtos
                FOREIGN KEY(id_produto) REFERENCES produtos(id) ON DELETE RESTRICT
        );
    """)

    # --- TABELA: DOAÇÕES ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doacoes (
            id SERIAL PRIMARY KEY,
            doador VARCHAR(100) DEFAULT 'Doador Anônimo',
            quantidade INTEGER DEFAULT 1 CHECK (quantidade > 0),
            status TEXT NOT NULL CHECK (status IN ('Pendente', 'Aprovado', 'Recusado')),
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            id_campanha INTEGER NOT NULL,
            id_operador INTEGER,
            
            CONSTRAINT fk_doacoes_campanhas
                FOREIGN KEY(id_campanha) REFERENCES campanhas(id) ON DELETE RESTRICT,
            
            CONSTRAINT fk_doacoes_operadores
                FOREIGN KEY(id_operador) REFERENCES operadores(id) ON DELETE RESTRICT
        );
    """)

    # --- TABELA: AUDITORIA ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria(
            id SERIAL PRIMARY KEY,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acao TEXT NOT NULL CHECK (acao IN ('Criação', 'Aprovação', 'Exclusão', 'Edição', 'Login', 'Pausamento', 'Reativação')),
            descricao TEXT NOT NULL,
            id_operador INTEGER,

            CONSTRAINT FK_auditoria_operadores
                FOREIGN KEY(id_operador)
                REFERENCES operadores(id)
                ON DELETE RESTRICT
        );
    """)

    # --- POPULANDO DADOS INICIAIS ---
    print("A criar categorias padrão...")
    cursor.execute("""
        INSERT INTO categorias (nome) 
        VALUES ('Alimentos'), ('Geral');
    """)

    print("A configurar a conta Master...")
    senha_criptografada = generate_password_hash(admin_senha)
    palavra_criptografada = generate_password_hash(admin_recup)
    
    # Insere o novo operador raiz definindo explicitamente a flag 'is_master = TRUE'
    cursor.execute("""
        INSERT INTO operadores (login, senha, palavra_recuperacao, is_master)
        VALUES (%s, %s, %s, TRUE);
    """, (admin_login, senha_criptografada, palavra_criptografada))

    print(f"Operador Master criado de forma segura! (Login: {admin_login})")

    # Efetiva todas as criações e inserções
    conn.commit()
    print("Base de dados recriada na Nova Arquitetura de Estoque Híbrido com sucesso!")