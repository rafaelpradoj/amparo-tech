import os
import sys

# Garante a inclusão do diretório pai no path do sistema
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from utils.db import get_db_connection
from werkzeug.security import generate_password_hash

# Carrega as variáveis de ambiente do arquivo .env (como as credenciais do banco)
load_dotenv(override=True)

print("Iniciando a injeção de dados variados para teste do fluxo atual...")

with get_db_connection() as conn, conn.cursor() as cursor:
    
    # 1. Criação de um Operador Comum para popular a auditoria
    senha_hash = generate_password_hash("123456")
    cursor.execute("""
        INSERT INTO operadores (login, senha, is_master, palavra_recuperacao, ativo)
        VALUES ('operador_banca', %s, FALSE, %s, TRUE) RETURNING id;
    """, (senha_hash, senha_hash))
    id_op = cursor.fetchone()[0]
    print("- Operador 'operador_banca' criado.")

    # 1.1 Garantir que todas as categorias usadas no script existam no banco
    categorias_necessarias = ['Alimentos', 'Vestuário', 'Higiene', 'Eletrônicos']
    for cat in categorias_necessarias:
        cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING;", (cat,))
    print(f"- Categorias garantidas: {', '.join(categorias_necessarias)}")

    # 2. Inserção de Produtos variados distribuídos em categorias.
    #    Alguns SEM campanha, para testar o filtro Status Campanha.
    produtos = [
        # Categoria: Alimentos (4 itens)
        ("Arroz", "Alimentos", 150),
        ("Feijão", "Alimentos", 80),
        ("Óleo", "Alimentos", 40),
        ("Macarrão", "Alimentos", 0),  # Sem campanha, estoque zerado

        # Categoria: Vestuário (2 itens)
        ("Camiseta", "Vestuário", 50),
        ("Calça Jeans", "Vestuário", 0),  # Sem campanha

        # Categoria: Higiene (2 itens)
        ("Sabonete", "Higiene", 300),
        ("Fralda", "Higiene", 0),

        # Categoria: Eletrônicos (2 itens)
        ("Fone de Ouvido", "Eletrônicos", 20),
        ("Carregador", "Eletrônicos", 0),  # Sem campanha
    ]
    
    ids_produtos = {}
    for nome, categoria, estoque in produtos:
        cursor.execute(
            "INSERT INTO produtos (nome, categoria, estoque_fisico) VALUES (%s, %s, %s) RETURNING id;",
            (nome, categoria, estoque)
        )
        ids_produtos[f"{nome}|{categoria}"] = cursor.fetchone()[0]
    print("- Estoque interno populado com 4 categorias e alguns itens sem campanha.")

    # 3. Criação de Campanhas Ativas vinculadas aos produtos do estoque.
    #    Nem todos os produtos possuem campanha, para permitir teste do filtro Status Campanha.
    #    Uma campanha é criada pausada para teste da nova funcionalidade.
    campanhas = [
        # Alimentos
        (ids_produtos["Arroz|Alimentos"], 500, 150),
        (ids_produtos["Feijão|Alimentos"], 300, 80),
        (ids_produtos["Óleo|Alimentos"], 100, 100),  # Meta atingida
        
        # Vestuário
        (ids_produtos["Camiseta|Vestuário"], 50, 12),
        
        # Higiene
        (ids_produtos["Sabonete|Higiene"], 400, 200),
        
        # Eletrônicos
        (ids_produtos["Fone de Ouvido|Eletrônicos"], 150, 45),
    ]
    
    ids_campanhas = []
    for c in campanhas:
        cursor.execute("INSERT INTO campanhas (id_produto, meta, arrecadado) VALUES (%s, %s, %s) RETURNING id;", c)
        ids_campanhas.append(cursor.fetchone()[0])
    
    # Cria uma campanha pausada para teste da funcionalidade de pausar/reativar
    cursor.execute("INSERT INTO campanhas (id_produto, meta, arrecadado, pausada) VALUES (%s, %s, %s, TRUE) RETURNING id;", 
                   (ids_produtos["Macarrão|Alimentos"], 80, 10))
    id_campanha_pausada = cursor.fetchone()[0]
    print("- 6 Campanhas ativas criadas. 1 campanha pausada criada para teste.")
    print(f"  Campanha pausada: ID {id_campanha_pausada}")

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
    """, (ids_campanhas[4], id_op))
    print("- Doações de teste injetadas.")

    # 5. Preenchimento de Auditoria com ações compatíveis com o fluxo atual
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', 'Cadastrou nova campanha para Arroz com meta 500', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', 'Cadastrou nova campanha para Feijão com meta 300', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', 'Cadastrou nova campanha para Óleo com meta 100', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', 'Cadastrou nova campanha para Camiseta com meta 50', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Aprovação', 'Aprovou a entrada de 100x Arroz doados por Maria Oliveira', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Exclusão', 'Arquivou a campanha de Fralda', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Edição', 'Editou a Meta da campanha Fone de Ouvido para 150', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Edição', 'Editou o produto Sabonete de Higiene para Higiene', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Pausamento', 'Pausou a campanha Macarrão', %s);", (id_op,))
    cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Reativação', 'Reativou a campanha Macarrão', %s);", (id_op,))
    
    conn.commit()

print("✅ Banco de dados populado com sucesso!")
print("   - 1 operador comum")
print("   - 8 produtos em 4 categorias (3 sem campanha para teste de filtro)")
print("   - 6 campanhas ativas + 1 campanha pausada")
print("   - 4 doações de exemplo (Pendente no prazo, Pendente expirada, Aprovada, Recusada)")
print("   - 10 registros de auditoria (inclui Pausamento e Reativação)")