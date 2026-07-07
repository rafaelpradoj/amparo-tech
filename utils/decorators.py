from functools import wraps
from flask import session, flash, redirect, url_for

def login_required(f):
    """
    Decorator para garantir que o operador esteja autenticado no sistema.
    Bloqueia o acesso a qualquer rota protegida se o identificador 'operador_id'
    não estiver presente na sessão do Flask, redirecionando para a tela de login.
    """
    @wraps(f) # Garante que os metadados (como o nome) da função original 'f' sejam preservados
    def decorated_function(*args, **kwargs):
        # Verifica se a chave do operador não existe na sessão ativa
        if 'operador_id' not in session:
            flash("Acesso negado! Faça login para continuar.", "danger")
            return redirect(url_for('auth.login'))
        
        # Segue adiante com a execução da rota caso esteja autenticado
        return f(*args, **kwargs)
    return decorated_function

def master_required(f):
    """
    Decorator para restringir o acesso exclusivo a operadores com nível Master.
    Geralmente aplicado em rotas críticas como criação de novos operadores ou exclusões básicas.
    Caso o operador não seja Master, redireciona-o de volta ao painel geral.
    """
    @wraps(f) # Preserva o contexto e as propriedades da função original
    def decorated_function(*args, **kwargs):
        # Verifica se a flag 'is_master' avalia como Falsa ou não existe na sessão
        if not session.get('is_master'):
            flash("Acesso negado: restrito a administradores master!", "danger")
            return redirect(url_for('admin.painel'))
        
        # Concede o acesso e executa a função da rota se o privilégio for confirmado
        return f(*args, **kwargs)
    return decorated_function