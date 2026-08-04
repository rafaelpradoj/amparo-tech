from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash
from markupsafe import escape
import unicodedata
from utils.db import get_db_connection
from utils.decorators import login_required, master_required

# Inicialização do Blueprint para as rotas de administração
admin_bp = Blueprint('admin', __name__)

def normalizar_nome(nome):
    """
    Padroniza o nome para comparação e armazenamento:
    - Remove acentos
    - Minúsculas
    - Remove espaços em volta
    - Colapsa múltiplos espaços internos em um único
    """
    if not nome:
        return ""
    nfkd = unicodedata.normalize('NFKD', nome)
    sem_acentos = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ' '.join(sem_acentos.lower().strip().split())

@admin_bp.route("/admin")
@login_required
def painel():
    """
    Rota principal do painel administrativo.
    Busca e renderiza todas as informações necessárias para gerenciar o sistema:
    doações pendentes, relatórios, operadores, campanhas, produtos, logs de auditoria e categorias.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        # 1. Busca doações pendentes com cálculo de expiração (mais de 7 dias atrás) e conversão de fuso horário
        cursor.execute("""
            SELECT d.id, p.nome, d.quantidade, 
                   d.data AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo',
                   d.doador,
                   (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') > (d.data + INTERVAL '7 days') AS expirado
            FROM doacoes d
            JOIN campanhas c ON d.id_campanha = c.id
            JOIN produtos p ON c.id_produto = p.id
            WHERE d.status = 'Pendente'
            ORDER BY d.data DESC;
        """)
        doacoes_pendentes = cursor.fetchall()
        
        # 2. Dados para o relatório de progresso das campanhas ativas
        cursor.execute("""
            SELECT p.nome, c.arrecadado, c.meta 
            FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE c.ativo = TRUE 
            ORDER BY c.arrecadado DESC;
        """)
        dados_relatorio = cursor.fetchall()

        # 3. Lista de operadores do sistema que estão ativos
        cursor.execute("SELECT id, login, is_master FROM operadores WHERE ativo = TRUE ORDER BY id ASC;")
        lista_operadores = cursor.fetchall()

        # 4. Lista geral de campanhas (ativas e inativas) para o gerenciador
        cursor.execute("""
            SELECT c.id, p.nome, p.categoria, c.arrecadado, c.meta, c.ativo, c.pausada 
            FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            ORDER BY c.ativo DESC, p.nome ASC, c.arrecadado DESC;
        """)
        lista_campanhas = cursor.fetchall()

        # 5. Lista de produtos cadastrados no estoque físico (internos)
        cursor.execute("""
            SELECT 
                p.id, 
                p.nome, 
                p.categoria, 
                p.estoque_fisico, 
                0, 
                p.ativo,
                CASE 
                    WHEN c.id IS NULL THEN 'sem'
                    WHEN c.pausada = TRUE THEN 'pausada'
                    ELSE 'ativa' 
                END as status_campanha
            FROM produtos p
            LEFT JOIN campanhas c ON c.id_produto = p.id AND c.ativo = TRUE
            ORDER BY p.nome ASC, p.estoque_fisico DESC;
        """)
        lista_produtos = cursor.fetchall()

        # 6. Histórico de auditoria de ações realizadas pelos operadores
        cursor.execute("""
            SELECT a.id, 
                   a.data AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo', 
                   o.login, 
                   a.acao, 
                   a.descricao 
            FROM auditoria a
            JOIN operadores o ON a.id_operador = o.id
            ORDER BY a.data DESC;
        """)
        lista_auditoria = cursor.fetchall()

        # 7. Lista de categorias disponíveis para ordenação alfabética
        cursor.execute("SELECT id, nome FROM categorias ORDER BY nome ASC;")
        lista_categorias = cursor.fetchall()
            
    # Processa os arrays isolados para alimentar os gráficos do relatório no front-end
    nomes_itens = [d[0] for d in dados_relatorio]
    estoques_itens = [d[1] for d in dados_relatorio]
    metas_itens = [d[2] for d in dados_relatorio]
    
    # Renderiza o template injetando todas as variáveis coletadas
    return render_template("admin.html", 
                           pendencias=doacoes_pendentes, 
                           nomes=nomes_itens, 
                           estoques=estoques_itens, 
                           metas=metas_itens, 
                           operadores=lista_operadores,
                           inventario=lista_campanhas, 
                           produtos=lista_produtos,
                           auditoria=lista_auditoria,
                           categorias=lista_categorias)

@admin_bp.route("/admin/aprovar/<int:id_doacao>", methods=["POST"])
@login_required
def aprovar_doacao(id_doacao):
    """
    Aprova uma doação pendente com proteção contra Race Condition (Atomic UPDATE), incrementando o saldo arrecadado da campanha
    e o estoque físico do produto associado. Registra a ação na auditoria.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        # TENTA atualizar o status da doação, apenas se o status atual ainda for 'Pendente'.
        # O banco de dados garante que apenas UMA requisição simultânea conseguirá fazer isso.
        cursor.execute("UPDATE doacoes SET status = 'Aprovado' WHERE id = %s AND status = 'Pendente'", (id_doacao,))
         
        # Se nenhuma linha foi afetada, o ataque (ou duplo clique) foi interceptado!
        if cursor.rowcount == 0:
            flash("Ops! Essa doação já foi processada.", "warning")
            return redirect(url_for('admin.painel'))

        # Se passou da trava acima, temos garantia absoluta de que esta é a única thread processando a aprovação.
        cursor.execute("""
            SELECT d.id_campanha, d.quantidade, p.nome, d.doador, c.id_produto,
                   c.ativo AS campanha_ativa, p.ativo AS produto_ativo, c.pausada AS campanha_pausada
            FROM doacoes d 
            JOIN campanhas c ON d.id_campanha = c.id 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE d.id = %s
        """, (id_doacao,))
        info = cursor.fetchone()
        
        if info:
            id_da_campanha, quantidade_doada, nome_item, doador, id_do_produto, campanha_ativa, produto_ativo, campanha_pausada = info
            
            # Atualiza o estoque físico do produto (produto recebido, mesmo que campanha encerrada)
            cursor.execute("UPDATE produtos SET estoque_fisico = estoque_fisico + %s WHERE id = %s", (quantidade_doada, id_do_produto))
            
            # Atualiza o arrecadado se a campanha ainda estiver ativa (pausada ou não)
            if campanha_ativa:
                cursor.execute("UPDATE campanhas SET arrecadado = arrecadado + %s WHERE id = %s", (quantidade_doada, id_da_campanha))
            
            # Registra o log detalhado da operação na tabela de auditoria
            descricao_legivel = f"Aprovou a entrada de {quantidade_doada}x '{nome_item}' doados por {doador}"
            if not campanha_ativa or not produto_ativo:
                descricao_legivel += " [ALERTA: aprovação realizada com campanha e/ou produto inativo]"
            cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Aprovação', %s, %s)", (descricao_legivel, session['operador_id']))
        conn.commit()
        
    flash("Doação aprovada com sucesso! O estoque foi atualizado.", "success")
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/recusar/<int:id_doacao>", methods=["POST"])
@login_required
def recusar_doacao(id_doacao):
    """
    Recusa uma promessa de doação pendente com proteção contra Race Condition (Atomic UPDATE). Registra a ação na auditoria.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        # Mesma trava atômica aplicada na função de aprovar promessa. TENTA atualizar o status da doação, apenas se o status atual ainda for 'Pendente'.
        # O banco de dados garante que apenas UMA requisição simultânea conseguirá fazer isso.
        cursor.execute("UPDATE doacoes SET status = 'Recusado' WHERE id = %s AND status = 'Pendente'", (id_doacao,))
         
        if cursor.rowcount == 0:
            flash("Ops! Essa doação já foi processada.", "warning")
            return redirect(url_for('admin.painel'))
        
        cursor.execute("""
            SELECT d.quantidade, p.nome, d.doador 
            FROM doacoes d 
            JOIN campanhas c ON d.id_campanha = c.id 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE d.id = %s
        """, (id_doacao,))
        info = cursor.fetchone()
        
        if info:
            qtd, nome_item, doador = info
            descricao_legivel = f"Recusou a promessa de {qtd}x '{nome_item}' de {doador}"
        else:
            descricao_legivel = "Recusou uma promessa de doação"

        # Registra o log detalhado da operação na tabela de auditoria
        cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Exclusão', %s, %s)", (descricao_legivel, session['operador_id']))
        conn.commit()
        
    flash("Doação recusada com sucesso. O estoque não foi alterado.", "success")
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/item/novo", methods=["POST"])
@login_required
def novo_item():
    """
    Cria uma nova campanha de arrecadação para um produto EXISTENTE no estoque.
    O produto é buscado pelo nome normalizado. A categoria é validada contra o produto.
    """
    produto_nome = request.form.get("produto", "").strip()
    categoria = (request.form.get("categoria") or "").strip()
    meta_raw = request.form.get("meta", "")

    try:
        meta = int(meta_raw)
    except (TypeError, ValueError):
        flash("Ops! A meta precisa ser um número positivo.", "danger")
        return redirect(url_for('admin.painel'))

    if meta <= 0:
        flash("Ops! A meta precisa ser maior que zero.", "danger")
        return redirect(url_for('admin.painel'))

    if not categoria:
        flash("Ops! Selecione uma categoria para a campanha.", "danger")
        return redirect(url_for('admin.painel'))
    
    # Valida se a categoria existe no sistema
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM categorias WHERE nome = %s", (categoria,))
        if not cursor.fetchone():
            flash(f"A categoria '{categoria}' não foi encontrada. Cadastre-a antes de continuar.", "danger")
            return redirect(url_for('admin.painel'))

    nome_normalizado = normalizar_nome(produto_nome)

    if len(nome_normalizado) > 150:
        flash(f"O nome do produto ultrapassa o limite de 150 caracteres.", "danger")
        return redirect(url_for('admin.painel'))

    with get_db_connection() as conn, conn.cursor() as cursor:
        # Busca o produto existente pelo nome normalizado
        cursor.execute("SELECT id, nome, categoria FROM produtos WHERE nome = %s AND ativo = TRUE", (nome_normalizado,))
        produto = cursor.fetchone()

        if not produto:
            flash(f"O produto '{produto_nome}' não foi encontrado no estoque.", "danger")
            return redirect(url_for('admin.painel'))

        id_do_produto = produto[0]
        nome_produto = produto[1]
        categoria_produto = produto[2]

        # Validação: categoria informada deve corresponder à do produto
        if categoria != categoria_produto:
            flash(f"A categoria '{categoria}' não corresponde ao produto '{nome_produto}' (categoria correta: {categoria_produto}).", "warning")
            return redirect(url_for('admin.painel'))

        # Impede duplicatas de campanhas ativas (inclui pausadas) para o mesmo produto
        # Campanhas arquivadas (ativo = FALSE) não bloqueiam nova criação
        cursor.execute("SELECT id, ativo, pausada FROM campanhas WHERE id_produto = %s AND ativo = TRUE", (id_do_produto,))
        campanha_existente = cursor.fetchone()
        
        if campanha_existente:
            id_campanha_existente, ativo_existente, pausada_existente = campanha_existente

            if not pausada_existente:
                flash(f"Já existe uma campanha ativa para '{nome_produto}'.", "warning")
            else:
                flash(f"Já existe uma campanha pausada para '{nome_produto}'.", "warning")
                
            return redirect(url_for('admin.painel'))

        # Insere a nova campanha associada ao ID do produto
        cursor.execute("INSERT INTO campanhas (id_produto, meta, arrecadado) VALUES (%s, %s, 0)", (id_do_produto, meta))
        cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', %s, %s)", (f"Cadastrou nova campanha para '{nome_produto}' com meta {meta}", session['operador_id']))
        conn.commit()

    flash(f"Campanha para '{nome_produto}' criada com sucesso! A meta é {meta}.", "success")
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/estoque/novo_produto", methods=["POST"])
@login_required
def novo_produto_estoque():
    """
    Cadastra um produto diretamente no estoque físico (interno)
    """
    produto_base = request.form.get("produto", "").strip()
    categoria = (request.form.get("categoria") or "").strip()

    if not produto_base:
        flash("Ops! O nome do produto é obrigatório.", "danger")
        return redirect(url_for('admin.painel'))

    if not categoria:
        flash("Ops! Selecione uma categoria.", "danger")
        return redirect(url_for('admin.painel'))
     
    # Valida se a categoria existe no sistema
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM categorias WHERE nome = %s", (categoria,))
        if not cursor.fetchone():
            flash(f"A categoria '{categoria}' não foi encontrada no sistema.", "danger")
            return redirect(url_for('admin.painel'))
     
    # O nome já é o texto completo fornecido pelo usuário
    nome_normalizado = normalizar_nome(produto_base)

# Impede estouro do limite VARCHAR(150) do banco de dados (Improper Input Validation Mitigation)
    if len(nome_normalizado) > 150:
        flash(f"O nome do produto ultrapassa o limite de 150 caracteres.", "danger")
        return redirect(url_for('admin.painel'))
         
    with get_db_connection() as conn, conn.cursor() as cursor:
        # Impede o cadastro de produtos com nomes idênticos no estoque
        cursor.execute("SELECT id FROM produtos WHERE nome = %s", (nome_normalizado,))
        if cursor.fetchone():
            flash(f"O produto '{produto_base}' já está cadastrado no estoque.", "warning")
            return redirect(url_for('admin.painel'))
             
        # Registra o novo item
        cursor.execute("INSERT INTO produtos (nome, categoria, estoque_fisico) VALUES (%s, %s, 0)", (nome_normalizado, categoria))
        cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', %s, %s)", (f"Cadastrou '{produto_base}' no estoque interno", session['operador_id']))
        conn.commit()
         
    flash(f"Produto '{produto_base}' adicionado ao estoque com sucesso!", "success")
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/item/editar/<int:id_campanha>", methods=["POST"])
@login_required
def editar_item(id_campanha):
    """
    Edita APENAS a meta de uma campanha.
    A alteração de nome e categoria do produto deve ser feita exclusivamente 
    pela ficha de edição do estoque.
    """
    nova_meta_raw = request.form.get("meta", "")

    try:
        nova_meta = int(nova_meta_raw)
    except (TypeError, ValueError):
        flash("Ops! A meta precisa ser um número positivo.", "danger")
        return redirect(url_for('admin.painel'))

    if nova_meta <= 0:
        flash("Ops! A meta precisa ser maior que zero.", "danger")
        return redirect(url_for('admin.painel'))

    with get_db_connection() as conn, conn.cursor() as cursor:
        # Garante que a campanha existe e está ativa (Bloqueia Soft Delete Bypass)
        cursor.execute("SELECT id_produto FROM campanhas WHERE id = %s AND ativo = TRUE;", (id_campanha,))
        resultado_campanha = cursor.fetchone()

        if not resultado_campanha:
            flash("Ops! Essa campanha não foi encontrada ou já foi arquivada.", "danger")
            return redirect(url_for('admin.painel'))
         
        id_do_produto = resultado_campanha[0]
         
        # Busca nome do produto para descrição de auditoria
        cursor.execute("SELECT nome FROM produtos WHERE id = %s", (id_do_produto,))
        nome_produto_row = cursor.fetchone()
        nome_produto = nome_produto_row[0] if nome_produto_row else "Desconhecido"

        # Atualiza APENAS a meta da campanha
        cursor.execute("UPDATE campanhas SET meta = %s WHERE id = %s", (nova_meta, id_campanha))
         
        descricao_legivel = f"Editou a Meta da campanha '{nome_produto}' para {nova_meta}"
        cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Edição', %s, %s)", (descricao_legivel, session['operador_id']))
         
        flash("A meta da campanha foi atualizada com sucesso!", "success")
        conn.commit()
        
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/estoque/editar/<int:id_produto>", methods=["POST"])
@login_required
def editar_produto(id_produto):
    """
    Edita os dados de um produto do estoque.
    Regra: Não permite alterar nome/categoria se houver campanha ATIVA vinculada.
    """
    produto_base = request.form.get("produto", "").strip()
    categoria = (request.form.get("categoria") or "").strip()

    if not produto_base:
        flash("Ops! O nome do produto é obrigatório.", "danger")
        return redirect(url_for('admin.painel'))

    if not categoria:
        flash("Ops! Selecione uma categoria.", "danger")
        return redirect(url_for('admin.painel'))
    # Valida se a categoria existe no sistema    
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM categorias WHERE nome = %s", (categoria,))
        if not cursor.fetchone():
            flash(f"A categoria '{categoria}' não foi encontrada no sistema.", "danger")
            return redirect(url_for('admin.painel'))

    nome_normalizado = normalizar_nome(produto_base)

    if len(nome_normalizado) > 150:
        flash(f"O nome do produto ultrapassa o limite de 150 caracteres.", "danger")
        return redirect(url_for('admin.painel'))

    with get_db_connection() as conn, conn.cursor() as cursor:
        # Verifica se o produto existe e está ativo
        cursor.execute("SELECT nome, categoria FROM produtos WHERE id = %s AND ativo = TRUE", (id_produto,))
        produto_atual = cursor.fetchone()

        if not produto_atual:
            flash("Ops! Esse produto não foi encontrado.", "danger")
            return redirect(url_for('admin.painel'))

        nome_antigo = produto_atual[0]
        categoria_antiga = produto_atual[1]

        # Verifica se houve alteração real
        if nome_normalizado == nome_antigo and categoria == categoria_antiga:
            flash("Nenhuma alteração foi detectada.", "warning")
            return redirect(url_for('admin.painel'))
        # Trava de campanha ativa: impede alteração de nome/categoria
        cursor.execute("SELECT id FROM campanhas WHERE id_produto = %s AND ativo = TRUE", (id_produto,))
        if cursor.fetchone():
            flash("Ops! Esse produto tem uma campanha ativa e não pode ser alterado.", "danger")
            return redirect(url_for('admin.painel'))
        # Atualiza o produto
        cursor.execute("UPDATE produtos SET nome = %s, categoria = %s WHERE id = %s", (nome_normalizado, categoria, id_produto))

        descricao = f"Editou o produto '{nome_antigo}' para '{nome_normalizado}' (categoria: {categoria_antiga} → {categoria})"
        cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Edição', %s, %s)", (descricao, session['operador_id']))
        conn.commit()

    flash(f"Produto '{produto_base}' atualizado no estoque com sucesso!", "success")
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/item/pausar/<int:id_campanha>", methods=["POST"])
@login_required
def pausar_campanha(id_campanha):
    """
    Pausa ou reativa uma campanha de arrecadação.
    Pausada: oculta do público, preserva dados e contagem.
    Reativada: volta a aparecer na página pública e receber doações.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("""
            SELECT p.nome, c.pausada FROM campanhas c 
            JOIN produtos p ON c.id_produto = p.id 
            WHERE c.id = %s
        """, (id_campanha,))
        resultado = cursor.fetchone()
        
        if not resultado:
            flash("Ops! Essa campanha não foi encontrada.", "danger")
            return redirect(url_for('admin.painel'))
         
        nome_produto, pausada = resultado
         
        if pausada:
            cursor.execute("UPDATE campanhas SET pausada = FALSE WHERE id = %s", (id_campanha,))
            descricao = f"Reativou a campanha '{nome_produto}'"
            acao = "Reativação"
            mensagem = f"A campanha '{nome_produto}' foi reativada com sucesso!"
        else:
            cursor.execute("UPDATE campanhas SET pausada = TRUE WHERE id = %s", (id_campanha,))
            descricao = f"Pausou a campanha '{nome_produto}'"
            acao = "Pausamento"
            mensagem = f"A campanha '{nome_produto}' foi pausada com sucesso!"
        
        cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES (%s, %s, %s)", (acao, descricao, session['operador_id']))
        conn.commit()
        
    flash(mensagem, "success")
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/item/excluir/<int:id_campanha>", methods=["POST"])
@login_required
def excluir_item(id_campanha):
    """
    Realiza a exclusão lógica (soft delete) de uma campanha, mudando a flag 'ativo' para FALSE.
    Isso oculta a campanha para o público mas retém o produto intacto no estoque interno.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("""
            SELECT p.nome FROM campanhas c JOIN produtos p ON c.id_produto = p.id WHERE c.id = %s
        """, (id_campanha,))
        nome_item_row = cursor.fetchone()
        if not nome_item_row:
            flash("Ops! Essa campanha não foi encontrada.", "danger")
            return redirect(url_for('admin.painel'))

        nome_item = nome_item_row[0]

        # Executa o soft delete da campanha
        cursor.execute("UPDATE campanhas SET ativo = FALSE WHERE id = %s", (id_campanha,))
        cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Exclusão', %s, %s)", (f"Arquivou/Ocultou a campanha '{nome_item}'", session['operador_id']))
        conn.commit()
         
    flash("Campanha arquivada! O produto continua disponível no estoque interno.", "success")
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/estoque/ajustar/<int:id_produto>", methods=["POST"])
@login_required
def ajustar_estoque(id_produto):
    """
    Permite ajustes manuais de entrada ou saída diretamente no estoque físico dos produtos.
    Exige obrigatoriamente uma justificativa/motivo por propósitos de auditoria.
    """
    tipo_ajuste = request.form.get("tipo_ajuste")

    # Validação segura da conversão de tipo numérico
    try:
        quantidade = int(request.form.get("quantidade", 0))
    except ValueError:
        flash("Ops! A quantidade informada é inválida.", "danger")
        return redirect(url_for('admin.painel'))
     
    motivo = request.form.get("motivo", "").strip()
     
    # Validações de campos obrigatórios e lógicos
    if not motivo:
        flash("Ops! É necessário informar um motivo para continuar.", "danger")
        return redirect(url_for('admin.painel'))
     
    if quantidade <= 0:
        flash("Ops! A quantidade precisa ser maior que zero.", "danger")
        return redirect(url_for('admin.painel'))

    with get_db_connection() as conn, conn.cursor() as cursor:
        # Busca o produto garantindo estritamente que ele está ativo (Bloqueia Soft Delete Bypass)
        cursor.execute("SELECT nome, estoque_fisico FROM produtos WHERE id = %s AND ativo = TRUE;", (id_produto,))
        item_info = cursor.fetchone()
         
        if not item_info:
            flash("Ops! Esse produto não foi encontrado ou já foi arquivado.", "danger")
            return redirect(url_for('admin.painel'))
             
        nome_item, estoque_atual = item_info

        # Executa acréscimo de estoque (Entrada)
        if tipo_ajuste == "entrada":
            cursor.execute("UPDATE produtos SET estoque_fisico = estoque_fisico + %s WHERE id = %s", (quantidade, id_produto))
            descricao_legivel = f"Adicionou {quantidade}x '{nome_item}' ao estoque. Motivo: {motivo}"
            cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Edição', %s, %s)", (descricao_legivel, session['operador_id']))
            flash(f"Entrada de {quantidade} unidade(s) de {nome_item} registrada com sucesso!", "success")

        # Executa decréscimo de estoque (Saída) com Proteção Atômica contra Race Conditions (TOCTOU)
        elif tipo_ajuste == "saida":
            if quantidade > estoque_atual:
                flash(f"Ops! Não é possível retirar {quantidade} unidade(s). O estoque atual é de {estoque_atual}.", "danger")
                return redirect(url_for('admin.painel'))
                 
            # Tenta atualizar o estoque fisicamente apenas se o saldo atual no banco for suficiente no momento exato do UPDATE
            cursor.execute("""
                UPDATE produtos 
                SET estoque_fisico = estoque_fisico - %s 
                WHERE id = %s AND estoque_fisico >= %s
            """, (quantidade, id_produto, quantidade))
             
            # Se rowcount for 0, significa que entre o nosso SELECT lá em cima e este UPDATE, outra requisição consumiu o estoque!
            if cursor.rowcount == 0:
                flash("Ops! O estoque foi alterado por outra operação neste momento.", "warning")
                return redirect(url_for('admin.painel'))

            descricao_legivel = f"Retirou {quantidade}x '{nome_item}' do estoque. Motivo: {motivo}"
            cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Edição', %s, %s)", (descricao_legivel, session['operador_id']))
            flash(f"Saída de {quantidade} unidade(s) de {nome_item} registrada com sucesso!", "success")
        else:
            flash("Ops! O tipo de ajuste informado é inválido.", "danger")
            return redirect(url_for('admin.painel'))

        conn.commit()

    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/operador/novo", methods=["POST"])
@login_required
@master_required
def novo_operador():
    """
    Cadastra uma nova credencial de operador de sistema comum (is_master = FALSE).
    Gera criptografia hash segura para a senha e para a palavra-chave de recuperação.
    Protegido pelo decorator @master_required.
    """
    novo_login = (request.form.get("login") or "").strip()
    nova_senha = request.form.get("senha")
    confirma_senha = request.form.get("confirma_senha")
    palavra_chave = request.form.get("palavra_chave")

    if not novo_login:
        flash("Ops! O login do operador não pode ficar vazio.", "danger")
        return redirect(url_for('admin.painel'))

    if not palavra_chave:
        flash("Ops! A palavra-chave de recuperação é obrigatória.", "danger")
        return redirect(url_for('admin.painel'))

    # Validação de complexidade mínima de senha
    if not nova_senha or len(nova_senha) < 6:
        flash("Ops! A senha precisa ter pelo menos 6 caracteres.", "danger")
        return redirect(url_for('admin.painel'))

    # Validação de confirmação de senha
    if nova_senha != confirma_senha:
        flash("Ops! As senhas digitadas não coincidem.", "danger")
        return redirect(url_for('admin.painel'))

    # Hasheamento das strings sensíveis usando Werkzeug Security
    senha_hash = generate_password_hash(nova_senha)
    palavra_hash = generate_password_hash(palavra_chave)

    with get_db_connection() as conn, conn.cursor() as cursor:
        # Impede duplicidade de usernames (logins)
        cursor.execute("SELECT id FROM operadores WHERE login = %s", (novo_login,))
        if cursor.fetchone():
            flash(f"O login '{novo_login}' já está em uso por outro operador.", "danger")
            return redirect(url_for('admin.painel'))

        # Insere a nova credencial de operador comum
        cursor.execute("INSERT INTO operadores (login, senha, palavra_recuperacao, is_master) VALUES (%s, %s, %s, FALSE)", (novo_login, senha_hash, palavra_hash))
        cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', %s, %s)", (f"Concedeu acesso de operador para '{novo_login}'", session['operador_id']))
        conn.commit()
         
    flash(f"O operador '{novo_login}' foi cadastrado com sucesso!", "success")
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/operador/excluir/<int:id_op>", methods=["POST"])
@login_required
@master_required
def excluir_operador(id_op):
    """
    Revoga de forma lógica o acesso de um operador configurando 'ativo = FALSE'.
    Trava de segurança: impede estritamente que contas Master do sistema sejam desativadas.
    Protegido pelo decorator @master_required.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT is_master, login FROM operadores WHERE id = %s", (id_op,))
        operador = cursor.fetchone()

        if operador:
            eh_master, login_op = operador
            if eh_master:
                # Bloqueia a auto-exclusão ou a exclusão do administrador raiz
                flash("Ops! A conta Master do sistema não pode ser excluída.", "danger")
            else:
                # Efetua a revogação lógica do operador comum
                cursor.execute("UPDATE operadores SET ativo = FALSE WHERE id = %s", (id_op,))
                cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Exclusão', %s, %s)", (f"Revogou o acesso do operador '{login_op}'", session['operador_id']))
                flash(f"O acesso do operador '{login_op}' foi revogado com sucesso!", "success")
        conn.commit()
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/api/novas_pendencias")
def checar_pendencias():
    """
    Endpoint assíncrono (API) usado para polling via JavaScript no front-end.
    Retorna em tempo real a contagem atual de doações no status 'Pendente'.
    """
    if 'operador_id' not in session:
        return jsonify({"status": "unauthorized"}), 401

    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM doacoes WHERE status = 'Pendente'")
        quantidade_atual_row = cursor.fetchone()
        quantidade_atual = quantidade_atual_row[0] if quantidade_atual_row else 0

    return jsonify({"count": quantidade_atual})

@admin_bp.route("/admin/categoria/nova", methods=["POST"])
@login_required
def nova_categoria():
    """
    Cadastra uma nova categoria de agrupamento de produtos. 
    Aplica formatação Title Case e evita termos duplicados.
    """
    nome_cru = request.form.get("nome", "").strip().title()

    # Remove os acentos da palavra (Ex: 'Construção' vira 'Construcao')
    nome_normalizado = ''.join(c for c in unicodedata.normalize('NFD', nome_cru) if unicodedata.category(c) != 'Mn')

    # Transforma scripts maliciosos em texto puro.
    nome = escape(nome_normalizado)
    
    if not nome:
        flash("Ops! O nome da categoria não pode ficar vazio.", "danger")
        return redirect(url_for('admin.painel'))

    with get_db_connection() as conn, conn.cursor() as cursor:
        # Evita a colisão/duplicação comparando as versões normalizadas sem acento
        cursor.execute("SELECT id FROM categorias WHERE nome = %s", (nome,))
         
        if cursor.fetchone():
            flash(f"A categoria '{nome}' já existe no sistema.", "warning")
        else:
            # Cria a nova categoria e gera o log
            cursor.execute("INSERT INTO categorias (nome) VALUES (%s)", (nome,))
            cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Criação', %s, %s)", (f"Criou a categoria '{nome}'", session['operador_id']))
            conn.commit()
            flash(f"A categoria '{nome}' foi criada com sucesso!", "success")
            
    return redirect(url_for('admin.painel'))

@admin_bp.route("/admin/categoria/excluir/<int:id_cat>", methods=["POST"])
@login_required
def excluir_categoria(id_cat):
    """
    Exclui permanentemente uma categoria de produto da tabela do banco de dados.
    Trava de integridade referencial: Bloqueia a exclusão caso exista algum produto vinculado a ela.
    """
    with get_db_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT nome FROM categorias WHERE id = %s", (id_cat,))
        cat = cursor.fetchone()
        
        if cat:
            nome_categoria = cat[0]
            # Verifica se há restrição de chave por produtos que dependem desta categoria
            cursor.execute("SELECT id FROM produtos WHERE categoria = %s LIMIT 1", (nome_categoria,))
            if cursor.fetchone():
                flash(f"A categoria '{nome_categoria}' não pode ser excluída: há produtos vinculados a ela.", "danger")
            else:
                # Remove definitivamente a categoria livre de dependências
                cursor.execute("DELETE FROM categorias WHERE id = %s", (id_cat,))
                cursor.execute("INSERT INTO auditoria (acao, descricao, id_operador) VALUES ('Exclusão', %s, %s)", (f"Removeu a categoria '{nome_categoria}'", session['operador_id']))
                conn.commit()
                flash(f"A categoria '{nome_categoria}' foi removida com sucesso!", "success")
                
    return redirect(url_for('admin.painel'))