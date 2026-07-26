import os
import sys

# Garante a inclusão do diretório pai no path do sistema
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from utils.db import get_db_connection
from werkzeug.security import generate_password_hash

# Carrega as variáveis de ambiente do arquivo .env (como as credenciais do banco)
load_dotenv(override=True)

print("Iniciando a injeção de dados variados para teste de categorias...")

with get_db_connection() as conn, conn.cursor() as cursor:
    
    # 1. Criação de um Operador Comum para popular a auditoria
    senha_hash = generate_password_hash("123456")
    cursor.execute("""
        INSERT INTO operadores (login, senha, is_master, palavra_recuperacao, ativo)
        VALUES ('operador_banca', %s, FALSE, %s, TRUE) RETURNING id;
    """, (senha_hash, senha_hash))
    id_op = cursor.fetchone()[0]
    print("- Operador 'operador_banca' criado.")

    # 2. Inserção de Produtos variados distribuídos em todas as categorias
    produtos = [
        # Categoria: Alimentos (3 Itens)
        ("Arroz Tipo 1 - 5kg", "Alimentos", 150),
        ("Feijão Carioca - 1kg", "Alimentos", 80),
        ("Óleo de Soja - 900ml", "Alimentos", 40),
        
        # Categoria: Geral (2 Itens)
        ("Cesta Básica Completa", "Geral", 10),
        ("Lâmpada LED 9W", "Geral", 100),
        
        # Categoria: Higiene (2 Itens)
        ("Sabonete Líquido Neutro - 200ml", "Higiene", 300),
        ("Fralda Descartável - P", "Higiene", 0),
        
        # Categoria: Materiais De Construcao (Sem acento - 1 Item)
        ("Saco de Cimento 50kg", "Materiais De Construcao", 5),
        
        # Categoria: Materiais De Construção (Com acento - 2 Itens)
        ("Tinta Látex Branca - 18L", "Materiais De Construção", 12),
        ("Pincel para Pintura 2 polegadas", "Materiais De Construção", 50),
        
        # Categoria: Material Escolar (2 Itens)
        ("Caderno Universitário - 10 Matérias", "Material Escolar", 45),
        ("Caixa de Lápis de Cor - 12 Cores", "Material Escolar", 60)
    ]
    
    ids_produtos = []
    for p in produtos:
        cursor.execute("INSERT INTO produtos (nome, categoria, estoque_fisico) VALUES (%s, %s, %s) RETURNING id;", p)
        ids_produtos.append(cursor.fetchone()[0])
    print("- Estoque interno abastecido com 6 categorias.")

    # 3. Criação de Campanhas Ativas com metas e arrecadações variadas
    campanhas = [
        # Alimentos
        (ids_produtos[0], 500, 150), # Arroz
        (ids_produtos[1], 300, 80),  # Feijão
        (ids_produtos[2], 100, 100), # Óleo (Meta Atingida)
        
        # Geral
        (ids_produtos[3], 50, 12),   # Cesta Básica
        (ids_produtos[4], 200, 50),  # Lâmpada
        
        # Higiene
        (ids_produtos[5], 400, 200), # Sabonete
        (ids_produtos[6], 200, 0),   # Fralda
        
        # Materiais De Construcao (Sem acento)
        (ids_produtos[7], 30, 5),    # Cimento
        
        # Materiais De Construção (Com acento)
        (ids_produtos[8], 15, 3),    # Tinta
        (ids_produtos[9], 80, 80),   # Pincel (Meta Atingida)
        
        # Material Escolar
        (ids_produtos[10], 150, 45), # Caderno
        (ids_produtos[11], 100, 90)  # Lápis de cor
    ]
    
    ids_campanhas = []
    for c in campanhas:
        cursor.execute("INSERT INTO campanhas (id_produto, meta, arrecadado) VALUES (%s, %s, %s) RETURNING id;", c)
        ids_campanhas.append(cursor.fetchone()[0])
    print("- 12 Campanhas vinculadas às categorias.")

    # 4. Injeção de Doações de Exemplo
    
    # A. Doação PENDENTE NO PRAZO (Feita há 2 dias)
    cursor.execute("""
        INSERT INTO doacoes (doador, quantidade, status, data, id_campanha) 
        VALUES ('Empresa Alfa', 50, 'Pendente', CURRENT_TIMESTAMP - INTERVAL '2 days', %s);
    """, (ids_campanhas[0],))
    
    # B. Doação PENDENTE EXPIRADA (Feita há 10 dias para estourar o limite de 7 dias)
    cursor.execute("""
        INSERT INTO doacoes (doador, quantidade, status, data, id_campanha) 
        VALUES ('João da Silva', 10, 'Pendente', CURRENT_TIMESTAMP - INTERVAL '10 days', %s);
    """, (ids_campanhas[1],))
    
    # C. Doação APROVADA
    cursor.execute("""
        INSERT INTO doacoes (doador, quantidade, status, data, id_campanha, id_operador) 
        VALUES ('Maria Oliveira', 100, 'Aprovado', CURRENT_TIMESTAMP - INTERVAL '15 days', %s, %s);
    """, (ids_campanhas[0], id_op))
    
    # D. Doação RECUSADA
    cursor.execute("""
        INSERT INTO doacoes (doador, quantidade, status, data, id_campanha, id_operador) 
        VALUES ('Doador Fake', 999, 'Recusado', CURRENT_TIMESTAMP - INTERVAL '1 days', %s, %s);
    """, (ids_campanhas[6], id_op))
    print("- Doações de teste injetadas.")

    # 5. Preenchimento de Auditoria
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', 'Cadastrou a campanha Arroz Tipo 1 - 5kg', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Aprovação', 'Aprovou a entrada de 100x Arroz Tipo 1 - 5kg doados por Maria Oliveira', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Exclusão', 'Recusou a promessa de 999x Fralda Descartável - P de Doador Fake', %s);", (id_op,))
    
    conn.commit()

print("✅ Banco de dados populado com sucesso com 6 categorias e 12 campanhas!")