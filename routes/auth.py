from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from utils.db import get_db_connection

# Inicialização do Blueprint para as rotas de autenticação
auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Gerencia o fluxo de autenticação dos operadores.
    Exibe o formulário no método GET e processa as credenciais no método POST,
    validando o hash da senha e iniciando a sessão do Flask.
    """
    if request.method == "POST":
        # Coleta os dados enviados pelo formulário de login
        usuario_digitado = request.form.get("login")
        senha_digitada = request.form.get("senha")
        
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Busca apenas operadores que estejam explicitamente com a flag 'ativo = TRUE'
            cursor.execute("SELECT id, senha, is_master FROM operadores WHERE login = %s AND ativo = TRUE", (usuario_digitado,))
            operador = cursor.fetchone()
            
            # Valida se o usuário existe e se a senha informada corresponde ao hash seguro do banco
            if operador and check_password_hash(operador[1], senha_digitada):
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
                
                flash(f"Olá, {usuario_digitado}. Vamos gerenciar as doações de hoje?", "success")
                return redirect(url_for('admin.painel'))
            else:
                # Retorna erro genérico caso o usuário não exista ou o hash não bata (boa prática de segurança)
                flash("Usuário ou senha inválidos!", "danger")
            
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    """
    Encerra a sessão do operador atual, limpando os dados salvos 
    no cookie de sessão do Flask e redirecionando para a tela de login.
    """
    session.pop('operador_id', None)
    session.pop('operador_login', None)
    session.pop('is_master', None)
    
    flash("Você saiu do sistema com segurança!", "success")
    return redirect(url_for('auth.login'))

@auth_bp.route("/recuperar_senha", methods=["POST"])
def recuperar_senha():
    """
    Processa a redefinição de senha baseada na palavra-chave de recuperação.
    Gera um novo hash seguro para a nova senha caso as validações coincidam e registra a alteração.
    """
    usuario = request.form.get("login_recup")
    palavra = request.form.get("palavra_recup")
    nova_senha = request.form.get("nova_senha")
    confirma_senha = request.form.get("confirma_nova_senha")

    # Validação inicial: impede o avanço se a confirmação de senha falhar
    if nova_senha != confirma_senha:
        flash("As senhas não coincidem! Por favor, tente novamente.", "danger")
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
            flash("Senha redefinida com sucesso! Você já pode realizar o login.", "success")
        else:
            # Mensagem de erro caso o login ou a palavra-chave estejam incorretos
            flash("Usuário ou Palavra-Chave incorretos! Verifique o termo e tente novamente.", "danger")

    return redirect(url_for('auth.login'))