// =========================================================================
// 1. POLLING DE NOVAS DOAÇÕES (Notificação em Tempo Real)
// =========================================================================
document.addEventListener("DOMContentLoaded", function () {
  // Captura a quantidade inicial de pendências armazenada em um input oculto no HTML
  let qtdAtual = parseInt(document.getElementById("qtd_pendencias_atual").value);
  const toastElement = document.getElementById("toastNovaDoacao");
  const toast = new bootstrap.Toast(toastElement, { autohide: false });

  // Executa uma checagem assíncrona a cada 8 segundos (8000ms)
  setInterval(function () {
    fetch("/admin/api/novas_pendencias")
      .then(response => response.json())
      .then(data => {
        // Se o contador do banco for maior que o exibido na tela, dispara a notificação Toast
        if (data.count > qtdAtual) {
          toast.show();
          qtdAtual = data.count; // Atualiza a variável local para sincronizar o estado
        }
      })
      .catch(erro => console.error("Erro ao checar pendências:", erro));
  }, 8000);
});

// =========================================================================
// 2. CHART.JS - RENDERIZAÇÃO DO GRÁFICO
// =========================================================================
document.addEventListener("DOMContentLoaded", function () {
  let graficoRenderizado = false;
  const abaRelatorios = document.getElementById("relatorios-tab");

  // Técnica de Lazy Loading: O gráfico só é renderizado quando o usuário clica na aba de Relatórios
  abaRelatorios.addEventListener("shown.bs.tab", function (event) {
    if (graficoRenderizado) return; // Evita recriar o gráfico se ele já foi montado
    try {
      const canvas = document.getElementById("graficoDoacoes");
      const ctx = canvas.getContext("2d");
      
      // Faz o parse dos dados JSON injetados de forma segura pelo Flask no HTML
      const labels = JSON.parse(document.getElementById("dados-nomes").textContent);
      const dataEstoque = JSON.parse(document.getElementById("dados-estoques").textContent);
      const dataMeta = JSON.parse(document.getElementById("dados-metas").textContent);

      // Instancia o gráfico de barras comparativo (Arrecadado vs Meta)
      new Chart(ctx, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            { label: "Estoque Arrecadado", data: dataEstoque, backgroundColor: "rgba(25, 135, 84, 0.7)" },
            { label: "Meta Necessária", data: dataMeta, backgroundColor: "rgba(255, 115, 115, 0.7)" },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { y: { beginAtZero: true } },
          plugins: { legend: { labels: { color: "white" } } },
        },
      });
      graficoRenderizado = true; // Sinaliza que a renderização foi concluída com sucesso
    } catch (erro) {
      console.error("Ocorreu um erro ao gerar o gráfico:", erro);
    }
  });
});

// =========================================================================
// 3. DATATABLES - LÓGICA DE TABELAS, ORDENAÇÃO E CROSS-FILTERING
// =========================================================================
$(document).ready(function() {
  // Configuração de localização global para o idioma Português do Brasil
  const configuracaoIdioma = { url: 'https://cdn.datatables.net/plug-ins/2.0.8/i18n/pt-BR.json' };

  // Extensão personalizada do DataTables para ignorar acentos e tags HTML ao ordenar alfabeticamente
  $.fn.dataTable.ext.type.order['sem-acentos-pre'] = function (dados) {
      if (!dados) return '';
      return dados.replace(/<[^>]*>/g, '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  };

  // --- ABA CAMPANHAS ---
  const tabelaInventario = $('#tabelaInventario').DataTable({
    language: configuracaoIdioma,
    pageLength: 10,
    lengthMenu: [5, 10, 25, 50],
    order: [[2, 'desc']], // Ordena inicialmente pelo status da campanha
    columnDefs: [ { type: 'sem-acentos', targets: 0 }, { orderable: false, targets: 5 } ],
    layout: {
      topStart: {
        buttons: [{
          extend: 'excelHtml5',
          text: '<i class="bi bi-file-earmark-excel-fill"></i> Exportar para Excel',
          className: 'btn btn-outline-success btn-sm fw-bold',
          title: 'Relatorio_Campanhas_AmparoTech',
          exportOptions: { modifier: { search: 'applied' }, columns: [0, 1, 2, 3, 4] } // Exporta apenas colunas de dados
        }]
      },
      topEnd: 'search'
    },
    initComplete: function() {
      // Move os elementos nativos do DataTables para containers HTML customizados no topo do painel
      const $linhaOriginal = $('#tabelaInventario_wrapper').find('.dt-search').closest('.dt-layout-row');
      tabelaInventario.buttons().container().appendTo('#containerExcelCampanhas');
      $('#tabelaInventario_wrapper').find('.dt-search').appendTo('#containerPesquisaCampanhas');
      $linhaOriginal.hide(); // Oculta a linha de layout padrão vazia
      atualizarContadoresCampanhas();
    }
  });

  // Atualiza os badges numéricos das pílulas de filtro de campanhas
  function atualizarContadoresCampanhas() {
    let ativas = 0;
    tabelaInventario.rows().every(function() {
      if (this.data()[2].includes('Ativo')) ativas++;
    });
    $('#countCampanhasTodas').text(tabelaInventario.rows().count());
    $('#countCampanhasAtivas').text(ativas);
  }

  tabelaInventario.on('draw', atualizarContadoresCampanhas);

  // Filtros rápidos via cliques nas pílulas (Todas vs Ativas)
  $('#pillCampanhasTodas').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    tabelaInventario.column(2).search('').draw(); 
  });

  $('#pillCampanhasAtivas').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    tabelaInventario.column(2).search('Ativo').draw(); 
  });
  
  // --- ABA AUDITORIA ---
  // Injeção de lógica customizada de busca global para filtros combinados (Operador + Ação)
  $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
      if (settings.nTable.id !== 'tabelaAuditoria') return true;
      const operadorAtivo = $('#tabelaAuditoria').data('operador-ativo');
      const acaoAtiva = $('#tabelaAuditoria').data('acao-ativa');
      if (!operadorAtivo && !acaoAtiva) return true; // Se nenhum filtro estiver ativo, exibe a linha

      // Extrai o texto limpo removendo marcações HTML das células de Operador e Ação
      const textoOperadorLinha = $('<div>').html(data[1]).text().trim(); 
      const textoAcaoLinha = $('<div>').html(data[2]).text().trim();     
      
      let matchOperador = true;
      let matchAcao = true;

      if (operadorAtivo) matchOperador = (textoOperadorLinha === operadorAtivo);
      if (acaoAtiva) matchAcao = (textoAcaoLinha === acaoAtiva);

      return matchOperador && matchAcao; // Retorna verdadeiro se a linha atender a ambos os critérios
  });

  const tabelaAuditoria = $('#tabelaAuditoria').DataTable({
    language: configuracaoIdioma,
    pageLength: 10, 
    order: [[0, 'desc']], // Ordena logs pelo ID/Data decrescente (mais recentes primeiro)
    columnDefs: [ { type: 'sem-acentos', targets: [1, 2, 3] } ],
    layout: {
      topStart: {
        buttons: [{
          extend: 'excelHtml5',
          text: '<i class="bi bi-file-earmark-excel-fill"></i> Exportar para Excel',
          className: 'btn btn-outline-success btn-sm fw-bold',
          title: 'Relatorio_Auditoria_AmparoTech',
          exportOptions: { modifier: { search: 'applied' }, columns: [0, 1, 2, 3] }
        }]
      },
      topEnd: 'search'
    },
    initComplete: function() {
      const $linhaOriginal = $('#tabelaAuditoria_wrapper').find('.dt-search').closest('.dt-layout-row');
      tabelaAuditoria.buttons().container().appendTo('#containerExcelAuditoria');
      $('#tabelaAuditoria_wrapper').find('.dt-search').appendTo('#containerPesquisaAuditoria');
      $linhaOriginal.hide();
      
      // Reconhece dinamicamente os operadores e ações presentes no banco para alimentar os menus dropdown
      construirDropdownsAuditoriaDinamicamente();
      atualizarContadoresAuditoria();
    }
  });

  // Constrói as opções de Dropdown de Auditoria com base exclusiva nos dados existentes na tabela
  function construirDropdownsAuditoriaDinamicamente() {
    let operadoresUnicos = new Set();
    let acoesUnicas = new Set();
    
    tabelaAuditoria.rows().every(function() {
      let textoOperador = $('<div>').html(this.data()[1]).text().trim();
      let textoAcao = $('<div>').html(this.data()[2]).text().trim();
      if (textoOperador) operadoresUnicos.add(textoOperador);
      if (textoAcao) acoesUnicas.add(textoAcao);
    });

    // Popula o menu dinâmico de Operadores
    let $menuOperador = $('#menuDinamicoOperador');
    $menuOperador.empty(); 
    Array.from(operadoresUnicos).sort((a, b) => a.localeCompare(b, 'pt-BR')).forEach(function(operador) {
      let itemHTML = `<li><a class="dropdown-item dropdown-item-operador py-2 fw-semibold d-flex justify-content-between align-items-center" href="#" data-operador="${operador}">
            <span><i class="bi bi-person-fill text-info me-2"></i> ${operador}</span> 
            <span class="badge rounded-pill hard-color-badge count-op-item" data-op-name="${operador}">0</span>
          </a></li>`;
      $menuOperador.append(itemHTML);
    });

    // Popula o menu dinâmico de Ações de Auditoria
    let $menuAcao = $('#menuDinamicoAuditoria');
    $menuAcao.empty(); 
    Array.from(acoesUnicas).sort((a, b) => a.localeCompare(b, 'pt-BR')).forEach(function(acao) {
      let icone = 'bi-activity'; let cor = 'text-light';
      let itemHTML = `<li><a class="dropdown-item dropdown-item-auditoria py-2 fw-semibold d-flex justify-content-between align-items-center" href="#" data-acao="${acao}">
            <span><i class="bi ${icone} ${cor} me-2"></i> ${acao}</span> 
            <span class="badge rounded-pill hard-color-badge count-aud-item" data-aud-name="${acao}">0</span>
          </a></li>`;
      $menuAcao.append(itemHTML);
    });
  }

  // Ativação do filtro por Operador selecionado no dropdown
  $('#menuDinamicoOperador').on('click', '.dropdown-item-operador', function(e) {
    e.preventDefault();
    const operadorSelecionado = $(this).data('operador');
    const textoLimpoOpcao = $(this).find('span').first().text().trim();

    $('#pillAuditoriaTodos').removeClass('ativa');
    $('#pillAuditoriaOperadorDropdown').addClass('ativa');
    $('#textoAuditoriaOperadorPill').html('<i class="bi bi-funnel-fill text-info me-1"></i> ' + textoLimpoOpcao);
    
    $('#tabelaAuditoria').data('operador-ativo', operadorSelecionado);
    tabelaAuditoria.draw(); 
  });

  // Ativação do filtro por Tipo de Ação selecionado no dropdown
  $('#menuDinamicoAuditoria').on('click', '.dropdown-item-auditoria', function(e) {
    e.preventDefault();
    const acaoSelecionada = $(this).data('acao');
    const textoLimpoOpcao = $(this).find('span').first().text().trim();

    $('#pillAuditoriaTodos').removeClass('ativa');
    $('#pillAuditoriaAcaoDropdown').addClass('ativa');
    $('#textoAuditoriaAcaoPill').html('<i class="bi bi-funnel-fill text-info me-1"></i> ' + textoLimpoOpcao);
    
    $('#tabelaAuditoria').data('acao-ativa', acaoSelecionada);
    tabelaAuditoria.draw(); 
  });

  // Recalcula dinamicamente os quantitativos de cada opção de dropdown considerando os filtros aplicados (Cross-Filtering)
  function atualizarContadoresAuditoria() {
    $('#countAuditoriaTodos').text(tabelaAuditoria.rows().count());
    const opAtivo = $('#tabelaAuditoria').data('operador-ativo');
    const acaoAtiva = $('#tabelaAuditoria').data('acao-ativa');
    let contadoresOp = {}; 
    let contadoresAcao = {}; 
    
    tabelaAuditoria.rows().every(function() {
      let textoOp = $('<div>').html(this.data()[1]).text().trim();
      let textoAc = $('<div>').html(this.data()[2]).text().trim();
      if (textoOp && (!acaoAtiva || textoAc === acaoAtiva)) {
          contadoresOp[textoOp] = (contadoresOp[textoOp] || 0) + 1;
      }
      if (textoAc && (!opAtivo || textoOp === opAtivo)) {
          contadoresAcao[textoAc] = (contadoresAcao[textoAc] || 0) + 1;
      }
    });

    $('.count-op-item').each(function() {
      let nome = $(this).data('op-name');
      $(this).text(contadoresOp[nome] || 0);
    });

    $('.count-aud-item').each(function() {
      let nome = $(this).data('aud-name');
      $(this).text(contadoresAcao[nome] || 0);
    });

    if (opAtivo && contadoresOp[opAtivo]) { 
      $('#countAuditoriaOperadorAtivo').text(contadoresOp[opAtivo]).removeClass('d-none'); 
    } else { 
      $('#countAuditoriaOperadorAtivo').addClass('d-none'); 
    }

    if (acaoAtiva && contadoresAcao[acaoAtiva]) { 
      $('#countAuditoriaAcaoAtiva').text(contadoresAcao[acaoAtiva]).removeClass('d-none'); 
    } else { 
      $('#countAuditoriaAcaoAtiva').addClass('d-none'); 
    }
  }

  tabelaAuditoria.on('draw', atualizarContadoresAuditoria);

  // Reseta completamente todos os filtros de cruzamento da aba de auditoria
  $('#pillAuditoriaTodos').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    $('#pillAuditoriaOperadorDropdown').removeClass('ativa');
    $('#textoAuditoriaOperadorPill').text('Operador'); 
    $('#pillAuditoriaAcaoDropdown').removeClass('ativa');
    $('#textoAuditoriaAcaoPill').text('Ação'); 
    $('#tabelaAuditoria').data('operador-ativo', null);
    $('#tabelaAuditoria').data('acao-ativa', null);
    tabelaAuditoria.draw();
  });

  // --- ABA ESTOQUE ---
  // Injeção de lógica customizada de busca global para filtro por Categorias no Estoque Físico
  $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
      if (settings.nTable.id !== 'tabelaEstoque') return true;
      const categoriaAtiva = $('#tabelaEstoque').data('categoria-ativa');
      if (!categoriaAtiva) return true; 
      const textoCategoriaLinha = $('<div>').html(data[1]).text().trim(); 
      return textoCategoriaLinha === categoriaAtiva;
  });

  const tabelaEstoque = $('#tabelaEstoque').DataTable({
    language: configuracaoIdioma,
    pageLength: 10,
    order: [[2, 'desc']], // Ordena inicialmente pela maior quantidade em estoque físico
    columnDefs: [ { type: 'sem-acentos', targets: 0 }, { orderable: false, targets: 3 } ],
    layout: {
      topStart: {
        buttons: [{
          extend: 'excelHtml5',
          text: '<i class="bi bi-file-earmark-excel-fill"></i> Exportar para Excel',
          className: 'btn btn-outline-success btn-sm fw-bold',
          title: 'Posicao_Estoque_AmparoTech',
          exportOptions: { modifier: { search: 'applied' }, columns: [0, 1, 2] }
        }]
      },
      topEnd: 'search'
    },
    initComplete: function() {
      const $linhaOriginal = $('#tabelaEstoque_wrapper').find('.dt-search').closest('.dt-layout-row');
      tabelaEstoque.buttons().container().appendTo('#containerExcelEstoque');
      $('#tabelaEstoque_wrapper').find('.dt-search').appendTo('#containerPesquisaEstoque');
      $linhaOriginal.hide();
      construirDropdownCategoriaDinamicamente();
      atualizarContadoresEstoque();
    }
  });

  // Monta as opções do dropdown de categoria mapeando a coluna correspondente no estoque
  function construirDropdownCategoriaDinamicamente() {
    let templatesUnicos = new Set();
    tabelaEstoque.rows().every(function() {
      let textoCat = $('<div>').html(this.data()[1]).text().trim();
      if (textoCat) templatesUnicos.add(textoCat);
    });

    let $menu = $('#menuDinamicoCategoriaEstoque');
    $menu.empty(); 
    Array.from(templatesUnicos).sort((a, b) => a.localeCompare(b, 'pt-BR')).forEach(function(categoria) {
      let icone = 'bi-tag-fill'; let cor = 'text-light';
      let itemHTML = `<li><a class="dropdown-item dropdown-item-categoria py-2 fw-semibold d-flex justify-content-between align-items-center" href="#" data-categoria="${categoria}">
            <span><i class="bi ${icone} ${cor} me-2"></i> ${categoria}</span> 
            <span class="badge rounded-pill hard-color-badge count-cat-item" data-cat-name="${categoria}">0</span>
          </a></li>`;
      $menu.append(itemHTML);
    });
  }

  // Executa a filtragem do estoque conforme a categoria escolhida no dropdown
  $('#menuDinamicoCategoriaEstoque').on('click', '.dropdown-item-categoria', function(e) {
    e.preventDefault();
    const categoriaSelecionada = $(this).data('categoria');
    const textoLimpoOpcao = $(this).find('span').first().text().trim();

    const $container = $(this).closest('.pilulas-container');
    $container.find('.btn-pilula').removeClass('ativa');
    $('#pillEstoqueCategoriaDropdown').addClass('ativa');
    $('#textoCategoriaPill').html('<i class="bi bi-funnel-fill text-info me-1"></i> ' + textoLimpoOpcao);
    
    $('#tabelaEstoque').data('categoria-ativa', categoriaSelecionada);
    tabelaEstoque.draw(); 
  });

  // Atualiza os contadores numéricos de produtos vinculados a cada categoria
  function atualizarContadoresEstoque() {
    $('#countEstoqueTodos').text(tabelaEstoque.rows().count());
    let contadores = {}; 
    tabelaEstoque.rows().every(function() {
      let cellContent = this.data()[1]; 
      if (cellContent) {
        let catTexto = $('<div>').html(cellContent).text().trim();
        contadores[catTexto] = (contadores[catTexto] || 0) + 1;
      }
    });

    $('.count-cat-item').each(function() {
      let nome = $(this).data('cat-name');
      $(this).text(contadores[nome] || 0);
    });

    const categoriaAtiva = $('#tabelaEstoque').data('categoria-ativa');
    if (categoriaAtiva && contadores[categoriaAtiva]) {
      $('#countEstoqueCategoriaAtiva').text(contadores[categoriaAtiva]).removeClass('d-none');
    } else {
      $('#countEstoqueCategoriaAtiva').addClass('d-none'); 
    }
  }
  
  tabelaEstoque.on('draw', atualizarContadoresEstoque);

  // Reseta o filtro de categorias da listagem de estoque
  $('#pillEstoqueTodos').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    $('#pillEstoqueCategoriaDropdown').removeClass('ativa');
    $('#textoCategoriaPill').text('Categoria'); 
    $('#tabelaEstoque').data('categoria-ativa', null); 
    tabelaEstoque.draw();
  });

  // --- ABA PENDÊNCIAS ---
  const tabelaPendencias = $('#tabelaPendencias').DataTable({
    language: configuracaoIdioma,
    pageLength: 10,
    lengthMenu: [5, 10, 25, 50],
    order: [], // Mantém a ordenação cronológica definida nativamente no backend (ORDER BY d.data ASC)
    columnDefs: [ { type: 'sem-acentos', targets: [1, 3] }, { orderable: false, targets: 4 } ],
    layout: {
      topStart: {
        buttons: [{
          extend: 'excelHtml5',
          text: '<i class="bi bi-file-earmark-excel-fill"></i> Exportar para Excel',
          className: 'btn btn-outline-success btn-sm fw-bold',
          title: 'Relatorio_Pendencias_AmparoTech',
          exportOptions: { modifier: { search: 'applied' }, columns: [0, 1, 2, 3] }
        }]
      },
      topEnd: 'search'
    },
    initComplete: function() {
      const $linhaOriginal = $('#tabelaPendencias_wrapper').find('.dt-search').closest('.dt-layout-row');
      tabelaPendencias.buttons().container().appendTo('#containerExcelPendencias');
      $('#tabelaPendencias_wrapper').find('.dt-search').appendTo('#containerPesquisaPendencias');
      $linhaOriginal.hide();
      atualizarContadoresPilulas();
    }
  });

  // Contabiliza promessas de doações que estão "No Prazo" versus as que já foram "Expiradas" (+ de 7 dias)
  function atualizarContadoresPilulas() {
    let noPrazo = 0, expirados = 0;
    tabelaPendencias.rows().every(function() {
      let dadosColunaData = this.data()[0]; 
      if (dadosColunaData.includes('No Prazo')) noPrazo++;
      if (dadosColunaData.includes('Expirado')) expirados++;
    });
    $('#countTodos').text(tabelaPendencias.rows().count());
    $('#countNoPrazo').text(noPrazo);
    $('#countExpirados').text(expirados);
  }

  tabelaPendencias.on('draw', atualizarContadoresPilulas);

  // Lógica dos botões de pílula para filtragem rápida de prazos de entregas pendentes
  $('#pillTodos').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    tabelaPendencias.column(0).search('').draw();
  });

  $('#pillNoPrazo').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    tabelaPendencias.column(0).search('No Prazo').draw();
  });

  $('#pillExpirado').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    tabelaPendencias.column(0).search('Expirado').draw();
  });
});