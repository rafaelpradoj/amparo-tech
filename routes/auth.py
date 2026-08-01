from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from utils.db import get_db_connection
import redis
import os
import time as _time

# Inicialização do Blueprint para as rotas de autenticação
auth_bp = Blueprint('auth', __name__)

# Configuração do bloqueio de conta
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 60  # 1 minuto em segundos

# Conexão Redis para rastreamento de tentativas falhas (compartilha infraestrutura com Flask-Limiter)
_redis_url = os.getenv("REDISCLOUD_URL")
if _redis_url and _redis_url != "memory://":
    _redis_client = redis.from_url(_redis_url, decode_responses=True)
    _redis_available = True
else:
    _redis_client = None
    _redis_available = False

# Chave para o armazenamento de bloqueio no app.config
_LOCKOUT_STORE_KEY = "_login_lockout_store"


def _get_lockout_store():
    """Retorna o dicionário de bloqueio no app.config (persiste entre requests)."""
    if _LOCKOUT_STORE_KEY not in current_app.config:
        current_app.config[_LOCKOUT_STORE_KEY] = {}
    return current_app.config[_LOCKOUT_STORE_KEY]


def _is_account_locked(login):
    """Verifica se a conta está bloqueada por excesso de tentativas falhas."""
    store = _get_lockout_store()
    entry = store.get(login)
    if not entry:
        return False
    if entry["locked_until"]:
        if _time.time() < entry["locked_until"]:
            return True
        # Bloqueio expirado — remove o registro
        del store[login]
    return False


def _record_failed_attempt(login):
    """Registra uma tentativa falha e bloqueia a conta se o limite for atingido."""
    store = _get_lockout_store()
    entry = store.get(login, {"count": 0, "locked_until": None})
    entry["count"] += 1
    if entry["count"] >= MAX_FAILED_ATTEMPTS:
        entry["locked_until"] = _time.time() + LOCKOUT_DURATION
    store[login] = entry


def _reset_failed_attempts(login):
    """Zera o contador de tentativas falhas após login bem-sucedido."""
    store = _get_lockout_store()
    store.pop(login, None)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Gerencia o fluxo de autenticação dos operadores.
    Exibe o formulário no método GET e processa as credenciais no método POST,
    validando o hash da senha, verificando bloqueio por tentativas falhas e
    iniciando a sessão do Flask.
    """
    if request.method == "POST":
        # Coleta os dados enviados pelo formulário de login
        usuario_digitado = (request.form.get("login") or "").strip()
        senha_digitada = request.form.get("senha")

        if not usuario_digitado or not senha_digitada:
            flash("Usuário ou senha inválidos!", "danger")
            return render_template("login.html")

        # Verifica se a conta está bloqueada por excesso de tentativas
        if _is_account_locked(usuario_digitado):
            flash("Conta bloqueada temporariamente! Tente novamente em 1 minuto.", "danger")
            return render_template("login.html")

        with get_db_connection() as conn, conn.cursor() as cursor:
            # Busca apenas operadores que estejam explicitamente com a flag 'ativo = TRUE'
            cursor.execute("SELECT id, senha, is_master FROM operadores WHERE login = %s AND ativo = TRUE", (usuario_digitado,))
            operador = cursor.fetchone()
            
            # Valida se o usuário existe e se a senha informada corresponde ao hash seguro do banco
            if operador and check_password_hash(operador[1], senha_digitada):
                # Zera o contador de tentativas falhas
                _reset_failed_attempts(usuario_digitado)

                # Armazena os dados de controle de acesso na sessão criptografada do Flask
                session['operador_id'] = operador[0]
                session['operador_login'] = usuario_digitado
                session['is_master'] = operador[2]
                
                # Registra o sucesso do login na tabela de auditoria
                cursor.execute("""
                    INSERT INTO auditoria (acao, descricao, id_operador) 
                    VALUES ('Login', 'Login realizado no painel administrativo', %s)
                """, (operador[0],))
                conn.commit()
                
                flash(f"Login realizado com sucesso, {usuario_digitado}.", "success")
                return redirect(url_for('admin.painel'))
            else:
                # Registra a tentativa falha e bloqueia a conta se o limite for atingido
                _record_failed_attempt(usuario_digitado)

                # Tenta encontrar o ID do operador para o registro de auditoria (mesmo se inativo)
                with get_db_connection() as conn2, conn2.cursor() as cursor2:
                    cursor2.execute("SELECT id FROM operadores WHERE login = %s", (usuario_digitado,))
                    op_row = cursor2.fetchone()
                    op_id = op_row[0] if op_row else None
                    cursor2.execute("""
                        INSERT INTO auditoria (acao, descricao, id_operador) 
                        VALUES ('Login', 'Tentativa de login falha', %s)
                    """, (op_id,))
                    conn2.commit()

                # Retorna erro genérico caso o usuário não exista ou o hash não bata (boa prática de segurança)
                flash("Usuário ou senha inválidos!", "danger")
            
    return render_template("login.html")

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Encerra a sessão do operador atual, limpando os dados salvos 
    no cookie de sessão do Flask e redirecionando para a tela de login.
    """
    session.pop('operador_id', None)
    session.pop('operador_login', None)
    session.pop('is_master', None)
    
    flash("Você saiu do sistema.", "success")
    return redirect(url_for('auth.login'))

@auth_bp.route("/recuperar_senha", methods=["POST"])
def recuperar_senha():
    """
    Processa a redefinição de senha baseada na palavra-chave de recuperação.
    Gera um novo hash seguro para a nova senha caso as validações coincidam e registra a alteração.
    """
    usuario = (request.form.get("login_recup") or "").strip()
    palavra = request.form.get("palavra_recup")
    nova_senha = request.form.get("nova_senha")
    confirma_senha = request.form.get("confirma_nova_senha")

    if not usuario or not palavra:
        flash("Usuário ou Palavra-Chave incorretos. Tente novamente!", "danger")
        return redirect(url_for('auth.login'))

    # Validação de complexidade mínima de senha
    if not nova_senha or len(nova_senha) < 6:
        flash("A nova senha deve ter no mínimo 6 caracteres!", "danger")
        return redirect(url_for('auth.login'))

    # Validação inicial: impede o avanço se a confirmação de senha falhar
    if nova_senha != confirma_senha:
        flash("As senhas não coincidem. Tente novamente!", "danger")
        return redirect(url_for('auth.login'))

    with get_db_connection() as conn, conn.cursor() as cursor:
        # Coleta o hash da palavra de recuperação cadastrada para o usuário ativo informado
        cursor.execute("SELECT id, palavra_recuperacao FROM operadores WHERE login = %s AND ativo = TRUE", (usuario,))
        operador = cursor.fetchone()

        # Verifica se o operador foi localizado e valida o hash da palavra-chave enviada
        if operador and operador[1] and check_password_hash(operador[1], palavra):
            # Gera um novo hash criptográfico forte para a nova senha definida
            novo_hash = generate_password_hash(nova_senha)
            
            # Atualiza a credencial no banco de dados
            cursor.execute("UPDATE operadores SET senha = %s WHERE id = %s", (novo_hash, operador[0]))
            
            # Registra a alteração de auto-serviço na tabela de auditoria
            cursor.execute("""
                INSERT INTO auditoria (acao, descricao, id_operador) 
                VALUES ('Edição', 'Recuperou a própria senha de acesso via palavra-chave', %s)
            """, (operador[0],))
            
            conn.commit()
            flash("Senha redefinida com sucesso! Faça login para acessar.", "success")
        else:
            # Mensagem de erro caso o login ou a palavra-chave estejam incorretos
            flash("Usuário ou Palavra-Chave incorretos. Tente novamente!", "danger")

    return redirect(url_for('auth.login'))
