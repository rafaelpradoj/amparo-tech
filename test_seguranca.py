import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    """Configura o ambiente de testes do Flask simulando um navegador"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False # Desativa a validação do token CSRF apenas para simplificar os testes lógicos
    with app.test_client() as client:
        yield client

def test_logout_rejeita_get(client):
    """
    Testa a Correção da Vulnerabilidade 3 (CSRF de Indisponibilidade)
    Garante que a rota /logout só aceita POST.
    """
    # Tenta acessar o logout via GET (como uma tag <img src="/logout"> faria)
    response = client.get('/logout')
    
    # 405 Method Not Allowed comprova que a rota está blindada contra GET
    assert response.status_code == 405 

def test_senha_fraca_rejeitada(client):
    """
    Testa a Correção da Vulnerabilidade 4 (Complexidade de Senha)
    Garante que o sistema barra senhas menores que 6 caracteres.
    """
    # Força um login de Administrador Master na sessão de teste
    with client.session_transaction() as sess:
        sess['operador_id'] = 1
        sess['is_master'] = True

    # Dispara um formulário POST tentando criar uma senha de 3 caracteres ("123")
    response = client.post('/admin/operador/novo', data={
        'login': 'hacker',
        'senha': '123',
        'confirma_senha': '123',
        'palavra_chave': 'segredo'
    }, follow_redirects=True)

    # Verifica se a trava atuou retornando a mensagem flash de erro no HTML renderizado
    html_retornado = response.data.decode('utf-8')
    assert "A senha deve ter pelo menos 6 caracteres!" in html_retornado

@patch('routes.admin.get_db_connection')
def test_soft_delete_bypass_bloqueado(mock_db, client):
    """
    Testa a Correção da Vulnerabilidade 2 (Soft Delete Bypass)
    Garante que não é possível injetar saldo em produto inativo.
    """
    with client.session_transaction() as sess:
        sess['operador_id'] = 1

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Simula o banco respondendo "None" (produto não encontrado ou inativo)
    mock_cursor.fetchone.return_value = None

    # Tenta ajustar o estoque do produto inativo
    response = client.post('/admin/estoque/ajustar/99', data={
        'tipo_ajuste': 'entrada',
        'quantidade': '50',
        'motivo': 'Ataque Bypass'
    }, follow_redirects=True)

    # 1. Verifica se o sistema barrou a operação e emitiu o alerta na tela
    html_retornado = response.data.decode('utf-8')
    assert "Produto inexistente ou arquivado!" in html_retornado
    
    # 2. PROVA DE FOGO: Extrai todas as queries SQL que o sistema tentou rodar no banco
    queries_executadas = [chamada.args[0] for chamada in mock_cursor.execute.call_args_list]
    
    # 3. Verifica se alguma das queries continha o comando de alterar o banco (UPDATE)
    teve_update = any("UPDATE" in query.upper() for query in queries_executadas)
    
    # Se "teve_update" for False, significa que a blindagem funcionou com maestria!
    assert teve_update == False, "Falha Crítica: Um comando UPDATE vazou e tentou ser executado!"
@patch('routes.admin.get_db_connection')
def test_race_condition_bloqueado(mock_db, client):
    """
    Testa a Correção da Vulnerabilidade 1 (Race Condition no Estoque)
    Garante que o saldo não fica negativo se 2 requisições tentarem tirar o último item.
    """
    with client.session_transaction() as sess:
        sess['operador_id'] = 1

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Simula que o produto existe e tem apenas 10 no estoque físico atual
    mock_cursor.fetchone.return_value = ("Produto Teste", 10)
    
    # Simula o comportamento protetor atômico do banco: rowcount = 0 
    # (significa que o UPDATE falhou porque o estoque já tinha sido consumido por outra Thread)
    mock_cursor.rowcount = 0

    # Tenta tirar 10 unidades
    response = client.post('/admin/estoque/ajustar/1', data={
        'tipo_ajuste': 'saida',
        'quantidade': '10',
        'motivo': 'Retirada Concorrente'
    }, follow_redirects=True)

    html_retornado = response.data.decode('utf-8')
    assert "Estoque já alterado por outra operação. Saldo insuficiente!" in html_retornado