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
    Gerencia a intenção de doação para uma campanha específica, contendo validação rigorosa de inputs (Backend Validation).
    """
    if request.method == "POST":
        # Captura os dados inseridos no formulário (pode vir texto, negativo ou vazio)
        quantidade_raw = request.form.get("quantidade")
        nome_doador = request.form.get("doador")

        # Try/except para travar quantidade doações e retornar apenas números > 0 (Improper Input Validation Mitigation)
        try:
            # Tenta converter obrigatoriamente para inteiro numérico
            quantidade_doada = int(quantidade_raw)
            
            if quantidade_doada <= 0:
                raise ValueError("Quantidade negativa ou zero.")
                
        except (ValueError, TypeError):
            flash("Quantidade informada inválida. Insira apenas números positivos!", "danger")
            return redirect(url_for('public.doar', id_campanha=id_campanha))

        if not nome_doador or nome_doador.strip() == "":
            nome_doador = 'Doador Anônimo'

        # POST: Registra a promessa de doação no banco de dados com o status inicial 'Pendente'
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Verifica se a campanha existe e está ATIVA antes de aceitar a doação (IDOR Mitigation)
            cursor.execute("SELECT ativo FROM campanhas WHERE id = %s", (id_campanha,))
            campanha_status = cursor.fetchone()
            
            if not campanha_status or not campanha_status[0]:
                flash("Operação negada: Esta campanha foi encerrada ou não está mais recebendo doações.", "warning")
                return redirect(url_for('public.index'))

            cursor.execute("""
                INSERT INTO doacoes (id_campanha, quantidade, doador, status) 
                VALUES (%s, %s, %s, 'Pendente')
            """, (id_campanha, quantidade_doada, nome_doador))
            conn.commit()
            
        flash("Promessa recebida com sucesso! Você tem até 7 dias corridos para realizar a entrega. Contamos com você!", "success")
        return redirect(url_for('public.index'))

    # GET: Apresenta os dados da campanha escolhida em um formulário de intenção.
    with get_db_connection() as conn, conn.cursor() as cursor:
        # Impede carregar a tela se o ativo for FALSE (IDOR Mitigation)
        cursor.execute("""
            SELECT c.id, p.nome, p.categoria, c.arrecadado, c.meta 
            FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE c.id = %s AND c.ativo = TRUE
        """, (id_campanha,))
        campanha = cursor.fetchone()
        
        # Se o atacante tentar forçar o link de uma campanha oculta, ele é barrado aqui
        if not campanha:
            flash("A campanha solicitada não foi encontrada ou já foi arquivada!", "danger")
            return redirect(url_for('public.index'))
            
    return render_template("doar.html", item=campanha)