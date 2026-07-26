import os
import sys

# Garante a inclusão do diretório pai no path do sistema
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from utils.db import get_db_connection
from werkzeug.security import generate_password_hash

# Carrega as variáveis de ambiente do arquivo .env (como as credenciais do banco)
load_dotenv(override=True)

print("Iniciando a injeção de dados para a apresentação...")

with get_db_connection() as conn, conn.cursor() as cursor:
    
    # 1. Criação de um Operador Comum para popular a auditoria
    senha_hash = generate_password_hash("123456")
    cursor.execute("""
        INSERT INTO operadores (login, senha, is_master, palavra_recuperacao, ativo)
        VALUES ('operador_banca', %s, FALSE, %s, TRUE) RETURNING id;
    """, (senha_hash, senha_hash))
    id_op = cursor.fetchone()[0]
    print("- Operador 'operador_banca' criado.")

    # 2. Inserção de Produtos no Estoque Físico
    produtos = [
        ("Arroz Tipo 1 - 5kg", "Alimentos", 150),
        ("Feijão Carioca - 1kg", "Alimentos", 80),
        ("Sabonete Líquido Neutro - 200ml", "Higiene", 300),
        ("Fralda Descartável - P", "Higiene", 0),
        ("Caderno Universitário - 10 Matérias", "Material Escolar", 45)
    ]
    ids_produtos = []
    for p in produtos:
        cursor.execute("INSERT INTO produtos (nome, categoria, estoque_fisico) VALUES (%s, %s, %s) RETURNING id;", p)
        ids_produtos.append(cursor.fetchone()[0])
    print("- Estoque interno abastecido.")

    # 3. Criação de Campanhas Ativas (com dados para gerar o gráfico Chart.js)
    campanhas = [
        (ids_produtos[0], 500, 150), # Arroz: Meta 500, 150 arrecadados
        (ids_produtos[1], 300, 80),  # Feijão: Meta 300, 80 arrecadados
        (ids_produtos[3], 200, 0)    # Fralda: Meta 200, Zerado
    ]
    ids_campanhas = []
    for c in campanhas:
        cursor.execute("INSERT INTO campanhas (id_produto, meta, arrecadado) VALUES (%s, %s, %s) RETURNING id;", c)
        ids_campanhas.append(cursor.fetchone()[0])
    print("- Campanhas vinculadas.")

    # 4. Injeção de Doações (O Segredo para testar os filtros do DataTables)
    
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
    
    # C. Doação APROVADA (Para demonstrar o histórico de sucesso)
    cursor.execute("""
        INSERT INTO doacoes (doador, quantidade, status, data, id_campanha, id_operador) 
        VALUES ('Maria Oliveira', 100, 'Aprovado', CURRENT_TIMESTAMP - INTERVAL '15 days', %s, %s);
    """, (ids_campanhas[0], id_op))
    
    # D. Doação RECUSADA (Para demonstrar a filtragem completa)
    cursor.execute("""
        INSERT INTO doacoes (doador, quantidade, status, data, id_campanha, id_operador) 
        VALUES ('Doador Fake', 999, 'Recusado', CURRENT_TIMESTAMP - INTERVAL '1 days', %s, %s);
    """, (ids_campanhas[2], id_op))
    print("- Doações diversificadas injetadas (Incluindo expiradas!).")

    # 5. Preenchimento de Auditoria Cruzada (Gera o menu dropdown dinâmico)
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', 'Cadastrou a campanha Arroz Tipo 1 - 5kg', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Aprovação', 'Aprovou a entrada de 100x Arroz Tipo 1 - 5kg doados por Maria Oliveira', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Exclusão', 'Recusou a promessa de 999x Fralda Descartável - P de Doador Fake', %s);", (id_op,))
    
    conn.commit()

print("✅ Tudo pronto! O palco está montado. Vá arrasar na apresentação!")