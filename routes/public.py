from flask import Blueprint, render_template, request, redirect, url_for, flash
from markupsafe import escape
from utils.db import get_db_connection

# Inicialização do Blueprint para as rotas da interface pública
public_bp = Blueprint('public', __name__)

@public_bp.route("/")
def index():
    """
    Rota da página inicial pública.
    Busca as categorias unificando variações de acentuação/caixa do texto.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        # Usa TRANSLATE para remover acentos e INITCAP/LOWER para padronizar maiúsculas/minúsculas
        cursor.execute("""
            SELECT 
                INITCAP(TRANSLATE(LOWER(p.categoria), 'áéíóúâêôãõç', 'aeiouaeoaoc')) as categoria_limpa, 
                COUNT(c.id) as total_campanhas
            FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE c.ativo = TRUE AND c.pausada = FALSE
            GROUP BY INITCAP(TRANSLATE(LOWER(p.categoria), 'áéíóúâêôãõç', 'aeiouaeoaoc'))
            ORDER BY categoria_limpa ASC;
        """)
        categorias = cursor.fetchall()
            
    return render_template("index.html", categorias=categorias, categoria_ativa=None)

@public_bp.route("/categoria/<path:nome_categoria>")
def ver_categoria(nome_categoria):
    """
    Rota para listar as campanhas ativas pertencentes a uma categoria específica.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        # Aplica a mesma regra no WHERE para encontrar produtos acentuados e não acentuados
        cursor.execute("""
            SELECT c.id, p.nome, p.categoria, c.arrecadado, c.meta 
            FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE c.ativo = TRUE AND c.pausada = FALSE
            AND INITCAP(TRANSLATE(LOWER(p.categoria), 'áéíóúâêôãõç', 'aeiouaeoaoc')) = INITCAP(TRANSLATE(LOWER(%s), 'áéíóúâêôãõç', 'aeiouaeoaoc'));
        """, (nome_categoria,))
        lista_campanhas = cursor.fetchall()
        
        if not lista_campanhas:
            flash("Nenhuma campanha ativa nesta categoria.", "warning")
            return redirect(url_for('public.index'))

    return render_template("index.html", produtos=lista_campanhas, categoria_ativa=nome_categoria)

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
        nome_doador = escape((request.form.get("doador") or "").strip().title())

        # Try/except para travar quantidade doações e retornar apenas números > 0 (Improper Input Validation Mitigation)
        try:
            # Tenta converter obrigatoriamente para inteiro numérico
            quantidade_doada = int(quantidade_raw)
            if quantidade_doada <= 0:
                raise ValueError("Quantidade negativa ou zero.")
        except (ValueError, TypeError):
            flash("Ops! A quantidade precisa ser um número positivo.", "danger")
            return redirect(url_for('public.doar', id_campanha=id_campanha))

        if not nome_doador:
            flash("Ops! Você precisa inserir um nome!", "danger")
            return redirect(url_for('public.doar', id_campanha=id_campanha))
        elif len(nome_doador) > 100:
            flash("Ops! Nome do doador não pode ultrapassar 100 caracteres.", "danger")
            return redirect(url_for('public.doar', id_campanha=id_campanha))

        # POST: Registra a promessa de doação no banco de dados com o status inicial 'Pendente'
        with get_db_connection() as conn, conn.cursor() as cursor:
            # Verifica se a campanha existe, está ATIVA, PAUSADA=FALSE e o produto vinculado também está ATIVO antes de aceitar a doação (IDOR Mitigation)
            cursor.execute("""
                SELECT c.ativo, c.pausada 
                FROM campanhas c 
                JOIN produtos p ON c.id_produto = p.id 
                WHERE c.id = %s AND p.ativo = TRUE
            """, (id_campanha,))
            campanha_status = cursor.fetchone()
            
            if not campanha_status or not campanha_status[0] or campanha_status[1]:
                flash("Ops! Esta campanha foi encerrada e não aceita mais doações.", "danger")
                return redirect(url_for('public.index'))

            cursor.execute("""
                INSERT INTO doacoes (id_campanha, quantidade, doador, status) 
                VALUES (%s, %s, %s, 'Pendente')
            """, (id_campanha, quantidade_doada, nome_doador))
            conn.commit()
            
        flash("Promessa registrada! Você tem até 7 dias para fazer a entrega. Agradecemos sua colaboração!", "success")
        return redirect(url_for('public.index'))

    # GET: Apresenta os dados da campanha escolhida em um formulário de intenção.
    with get_db_connection() as conn, conn.cursor() as cursor:
        # Impede carregar a tela se o ativo for FALSE (IDOR Mitigation)
        cursor.execute("""
            SELECT c.id, p.nome, p.categoria, c.arrecadado, c.meta 
            FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE c.id = %s AND c.ativo = TRUE AND c.pausada = FALSE
        """, (id_campanha,))
        campanha = cursor.fetchone()
        
        # Se o atacante tentar forçar o link de uma campanha oculta, ele é barrado aqui
        if not campanha:
            flash("Ops! Campanha não encontrada!", "danger")
            return redirect(url_for('public.index'))
            
    return render_template("doar.html", item=campanha)