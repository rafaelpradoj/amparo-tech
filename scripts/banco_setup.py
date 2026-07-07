import os
import sys

# Garante que o diretório pai seja adicionado ao path do sistema,
# permitindo a importação correta dos módulos dentro de 'utils'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from utils.db import get_db_connection

# Carrega as variáveis de ambiente do arquivo .env (como as credenciais do banco)
load_dotenv()

print("A tentar conectar à base de dados...")

with get_db_connection() as conn, conn.cursor() as cursor:
    print("Ligação estabelecida com sucesso! A iniciar a limpeza e recriação das tabelas...")

    # Remove as tabelas existentes usando CASCADE para garantir que tabelas dependentes
    # (com chaves estrangeiras) também sejam limpas sem bloquear a operação
    cursor.execute("DROP TABLE IF EXISTS doacoes CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS auditoria CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS campanhas CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS produtos CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS itens CASCADE;") 
    cursor.execute("DROP TABLE IF EXISTS categorias CASCADE;")

    # --- TABELA: CATEGORIAS ---
    # Armazena as categorias para classificação dos produtos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL UNIQUE
        );
    """)

    # Popula o banco inicialmente com as categorias padrão do sistema
    cursor.execute("""
        INSERT INTO categorias (nome) 
        VALUES ('Alimentos'), ('Higiene'), ('Material Escolar'), ('Geral');
    """)

    # --- TABELA: OPERADORES ---
    # Armazena os usuários administradores/operadores do painel
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
    # Representa o estoque físico interno. Possui uma trava para evitar estoque negativo
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
    # Gerencia as metas públicas de arrecadação. Depende diretamente da tabela de produtos.
    # ON DELETE RESTRICT impede a exclusão de um produto que possua uma campanha vinculada.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campanhas (
            id SERIAL PRIMARY KEY,
            id_produto INTEGER NOT NULL,
            meta INTEGER NOT NULL CHECK (meta > 0),
            arrecadado INTEGER DEFAULT 0 CHECK (arrecadado >= 0),
            ativo BOOLEAN DEFAULT TRUE,
            
            CONSTRAINT fk_campanhas_produtos
                FOREIGN KEY(id_produto) REFERENCES produtos(id) ON DELETE RESTRICT
        );
    """)

    # --- TABELA: DOAÇÕES ---
    # Registra as promessas e intenções de doações. 
    # Possui chaves estrangeiras que apontam para a campanha e para o operador que a processou.
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
    # Tabela de segurança responsável por rastrear todas as ações críticas feitas no sistema.
    # Armazena o tipo de ação (restrito pelo CHECK), descrição legível e o autor (operador).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditoria(
            id SERIAL PRIMARY KEY,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acao TEXT NOT NULL CHECK (acao IN ('Criação', 'Aprovação', 'Exclusão', 'Edição', 'Login')),
            descricao TEXT NOT NULL,
            id_operador INTEGER,

            CONSTRAINT FK_auditoria_operadores
                FOREIGN KEY(id_operador)
                REFERENCES operadores(id)
                ON DELETE RESTRICT
        );
    """)

    # Efetiva todas as criações e inserções estruturadas acima no banco de dados
    conn.commit()
    print("Base de dados recriada na Nova Arquitetura de Estoque Híbrido com sucesso!")