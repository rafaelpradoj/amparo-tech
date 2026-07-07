from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.db import get_db_connection

# Inicialização do Blueprint para as rotas da interface pública
public_bp = Blueprint('public', __name__)

@public_bp.route("/")
def index():
    """
    Rota da página inicial pública.
    Busca todas as campanhas que estão atualmente ativas no sistema
    e as exibe para os visitantes e potenciais doadores.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        # Seleciona dados essenciais das campanhas e produtos relacionados (apenas as ativas)
        cursor.execute("""
            SELECT c.id, p.nome, p.categoria, c.arrecadado, c.meta 
            FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE c.ativo = TRUE;
        """)
        lista_campanhas = cursor.fetchall()
            
    return render_template("index.html", produtos=lista_campanhas)

@public_bp.route("/sobre")
def quem_somos():
    """
    Rota institucional simples.
    Apenas renderiza a página informativa "Sobre" o projeto.
    """
    return render_template("sobre.html")

@public_bp.route("/doar/<int:id_campanha>", methods=["GET", "POST"])
def doar(id_campanha):
    """
    Gerencia a intenção de doação para uma campanha específica.
    GET: Apresenta os dados da campanha escolhida em um formulário de intenção.
    POST: Registra a promessa de doação no banco de dados com o status inicial 'Pendente'.
    """
    if request.method == "POST":
        # Captura os dados inseridos pelo doador no formulário
        quantidade_doada = request.form.get("quantidade")
        nome_doador = request.form.get("doador")

        # Fallback de segurança: Caso o nome não seja preenchido ou possua apenas espaços, define como anônimo
        if not nome_doador or nome_doador.strip() == "":
            nome_doador = 'Doador Anônimo'

        with get_db_connection() as conn, conn.cursor() as cursor:
            # Insere a nova promessa de doação (aguardando a confirmação física no painel admin)
            cursor.execute("""
                INSERT INTO doacoes (id_campanha, quantidade, doador, status) 
                VALUES (%s, %s, %s, 'Pendente')
            """, (id_campanha, quantidade_doada, nome_doador))
            conn.commit()
            
        # Alerta o usuário sobre o prazo de 7 dias para efetivar a entrega física (regra alinhada ao painel admin)
        flash("Promessa recebida com sucesso! Você tem até 7 dias corridos para realizar a entrega. Contamos com você!", "success")
        return redirect(url_for('public.index'))

    # Comportamento para o método GET: Busca os dados da campanha selecionada para montar a tela de doação
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, p.nome, p.categoria, c.arrecadado, c.meta 
            FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE c.id = %s
        """, (id_campanha,))
        campanha = cursor.fetchone()
            
    return render_template("doar.html", item=campanha)