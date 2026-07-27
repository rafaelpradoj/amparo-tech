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
  const configuracaoIdioma = { url: '/static/js/pt-BR.json' };

  // Extensão personalizada do DataTables para ignorar acentos e tags HTML ao ordenar alfabeticamente
  $.fn.dataTable.ext.type.order['sem-acentos-pre'] = function (dados) {
      if (!dados) return '';
      return dados.replace(/<[^>]*>/g, '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  };

  // Função auxiliar para normalizar categorias (ignora acentos e letras maiúsculas)
  const normalizarCategoria = (str) => str ? String(str).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim() : "";

  // --- ABA CAMPANHAS ---
  // Injeção de lógica customizada de busca global para filtros combinados (Status + Categoria) na aba Campanhas
  $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
      if (settings.nTable.id !== 'tabelaInventario') return true;
      
      const statusAtivo = $('#tabelaInventario').data('status-ativo');
      const categoriaAtiva = $('#tabelaInventario').data('categoria-ativa');
      if (!statusAtivo && !categoriaAtiva) return true; 

      const textoCategoriaLinha = $('<div>').html(data[1]).text().trim(); 
      const textoStatusLinha = $('<div>').html(data[2]).text().trim();     
      
      let matchStatus = true;
      let matchCategoria = true;

      if (statusAtivo) matchStatus = textoStatusLinha.includes(statusAtivo);
      if (categoriaAtiva) matchCategoria = (normalizarCategoria(textoCategoriaLinha) === normalizarCategoria(categoriaAtiva));

      return matchStatus && matchCategoria;
  });

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
          title: 'Relatorio de Campanhas',
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
      construirDropdownCategoriaCampanhasDinamicamente();
      atualizarContadoresCampanhas();
    }
  });

  // Monta as opções do dropdown AGRUPANDO categorias existentes na tabela de campanhas
  function construirDropdownCategoriaCampanhasDinamicamente() {
    let categoriasMap = new Map();

    tabelaInventario.rows().every(function() {
      let textoCat = $('<div>').html(this.data()[1]).text().trim();
      if (textoCat) {
        let normalizado = normalizarCategoria(textoCat);
        if (!categoriasMap.has(normalizado)) {
          categoriasMap.set(normalizado, textoCat);
        }
      }
    });

    let $menu = $('#menuDinamicoCategoriaCampanhas');
    $menu.empty(); 
    
    let categoriasUnicas = Array.from(categoriasMap.values()).sort((a, b) => a.localeCompare(b, 'pt-BR'));

    categoriasUnicas.forEach(function(categoria) {
      let icone = 'bi-tag-fill'; let cor = 'text-light';
      let $li = $('<li>');
      
      let $a = $('<a>')
          .addClass('dropdown-item dropdown-item-categoria-campanha py-2 fw-semibold d-flex justify-content-between align-items-center')
          .attr('href', '#')
          .attr('data-categoria', categoria);
      
      let $spanIcone = $('<span>')
          .html('<i class="bi ' + icone + ' ' + cor + ' me-2"></i> ')
          .append(document.createTextNode(categoria)); 
          
      let $spanBadge = $('<span>')
          .addClass('badge rounded-pill hard-color-badge count-cat-campanha-item')
          .attr('data-cat-name', categoria)
          .text('0');
      
      $a.append($spanIcone).append($spanBadge);
      $li.append($a);
      $menu.append($li);
    });
  }

  // Executa a filtragem de campanhas conforme a categoria selecionada
  $('#menuDinamicoCategoriaCampanhas').on('click', '.dropdown-item-categoria-campanha', function(e) {
    e.preventDefault();
    const categoriaSelecionada = $(this).data('categoria');
    const textoLimpoOpcao = $(this).find('span').first().text().trim();

    $('#pillCampanhasCategoriaDropdown').addClass('ativa');
    $('#textoCampanhasCategoriaPill').html('<i class="bi bi-funnel-fill text-info me-1"></i> ' + textoLimpoOpcao);
    
    $('#tabelaInventario').data('categoria-ativa', categoriaSelecionada);
    tabelaInventario.draw();
  });

  // Recalcula dinamicamente os quantitativos e badges considerando os filtros aplicados (Cross-Filtering)
  function atualizarContadoresCampanhas() {
    $('#countCampanhasTodas').text(tabelaInventario.rows().count());
    
    const statusAtivo = $('#tabelaInventario').data('status-ativo');
    const categoriaAtiva = $('#tabelaInventario').data('categoria-ativa');

    let ativasCount = 0;
    let contadoresCat = {};

    tabelaInventario.rows().every(function() {
      let cellCategoria = this.data()[1];
      let cellStatus = this.data()[2];

      let textoCat = cellCategoria ? $('<div>').html(cellCategoria).text().trim() : '';
      let textoStatus = cellStatus ? $('<div>').html(cellStatus).text().trim() : '';
      let catNorm = normalizarCategoria(textoCat);

      if (textoStatus.includes('Ativo') && (!categoriaAtiva || catNorm === normalizarCategoria(categoriaAtiva))) {
        ativasCount++;
      }

      if (textoCat && (!statusAtivo || textoStatus.includes(statusAtivo))) {
        contadoresCat[catNorm] = (contadoresCat[catNorm] || 0) + 1;
      }
    });

    $('#countCampanhasAtivas').text(ativasCount);

    $('.count-cat-campanha-item').each(function() {
      let nome = $(this).data('cat-name');
      let catNorm = normalizarCategoria(nome);
      $(this).text(contadoresCat[catNorm] || 0);
    });

    if (categoriaAtiva) {
      let catNormAtiva = normalizarCategoria(categoriaAtiva);
      if (contadoresCat[catNormAtiva]) {
        $('#countCampanhasCategoriaAtiva').text(contadoresCat[catNormAtiva]).removeClass('d-none');
      } else {
        $('#countCampanhasCategoriaAtiva').addClass('d-none');
      }
    } else {
      $('#countCampanhasCategoriaAtiva').addClass('d-none');
    }
  }

  tabelaInventario.on('draw', atualizarContadoresCampanhas);

  // Filtros rápidos via cliques nas pílulas (Todas vs Ativas)
  $('#pillCampanhasTodas').on('click', function() {
    $('#pillCampanhasAtivas').removeClass('ativa');
    $(this).addClass('ativa');
    $('#pillCampanhasCategoriaDropdown').removeClass('ativa');
    $('#textoCampanhasCategoriaPill').text('Categoria');
    $('#tabelaInventario').data('status-ativo', null);
    $('#tabelaInventario').data('categoria-ativa', null);
    tabelaInventario.draw();
  });

  $('#pillCampanhasAtivas').on('click', function() {
    $('#pillCampanhasTodas').removeClass('ativa');
    $(this).addClass('ativa');
    $('#tabelaInventario').data('status-ativo', 'Ativo');
    tabelaInventario.draw();
  });

  // --- ABA AUDITORIA ---
  // Injeção de lógica customizada de busca global para filtros combinados (Operador + Ação)
  $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {
      if (settings.nTable.id !== 'tabelaAuditoria') return true;
      
      const operadorAtivo = $('#tabelaAuditoria').data('operador-ativo');
      const acaoAtiva = $('#tabelaAuditoria').data('acao-ativa');
      if (!operadorAtivo && !acaoAtiva) return true; 

      const textoOperadorLinha = $('<div>').html(data[1]).text().trim(); 
      const textoAcaoLinha = $('<div>').html(data[2]).text().trim();     
      
      const padronizar = (str) => str ? String(str).normalize("NFC").trim() : "";
      
      let matchOperador = true;
      let matchAcao = true;

      if (operadorAtivo) matchOperador = (padronizar(textoOperadorLinha) === padronizar(operadorAtivo));
      if (acaoAtiva) matchAcao = (padronizar(textoAcaoLinha) === padronizar(acaoAtiva));

      return matchOperador && matchAcao;
  });

  const tabelaAuditoria = $('#tabelaAuditoria').DataTable({
    language: configuracaoIdioma,
    pageLength: 10, 
    order: [], // Ficou vazio para respeitar a ordem imutável de IDs do backend
    columnDefs: [ { type: 'sem-acentos', targets: [1, 2, 3] } ],
    layout: {
      topStart: {
        buttons: [{
          extend: 'excelHtml5',
          text: '<i class="bi bi-file-earmark-excel-fill"></i> Exportar para Excel',
          className: 'btn btn-outline-success btn-sm fw-bold',
          title: 'Relatorio de Auditoria',
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

    let $menuOperador = $('#menuDinamicoOperador');
    $menuOperador.empty(); 
    Array.from(operadoresUnicos).sort((a, b) => a.localeCompare(b, 'pt-BR')).forEach(function(operador) {
      let $li = $('<li>');
      
      let $a = $('<a>')
          .addClass('dropdown-item dropdown-item-operador py-2 fw-semibold d-flex justify-content-between align-items-center')
          .attr('href', '#')
          .attr('data-operador', operador);
      
      let $spanIcone = $('<span>')
          .html('<i class="bi bi-person-fill text-info me-2"></i> ')
          .append(document.createTextNode(operador));
          
      let $spanBadge = $('<span>')
          .addClass('badge rounded-pill hard-color-badge count-op-item')
          .attr('data-op-name', operador)
          .text('0');

      $a.append($spanIcone).append($spanBadge);
      $li.append($a);
      $menuOperador.append($li);
    });

    let $menuAcao = $('#menuDinamicoAuditoria');
    $menuAcao.empty(); 
    Array.from(acoesUnicas).sort((a, b) => a.localeCompare(b, 'pt-BR')).forEach(function(acao) {
      let icone = 'bi-activity'; let cor = 'text-light';
      
      let $li = $('<li>');
      
      let $a = $('<a>')
          .addClass('dropdown-item dropdown-item-auditoria py-2 fw-semibold d-flex justify-content-between align-items-center')
          .attr('href', '#')
          .attr('data-acao', acao);
      
      let $spanIcone = $('<span>')
          .html('<i class="bi ' + icone + ' ' + cor + ' me-2"></i> ')
          .append(document.createTextNode(acao));
          
      let $spanBadge = $('<span>')
          .addClass('badge rounded-pill hard-color-badge count-aud-item')
          .attr('data-aud-name', acao)
          .text('0');

      $a.append($spanIcone).append($spanBadge);
      $li.append($a);
      $menuAcao.append($li);
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
      
      // Compara a linha e a pílula clicada após remover acentos de ambas
      return normalizarCategoria(textoCategoriaLinha) === normalizarCategoria(categoriaAtiva);
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
          title: 'Estoque Atual',
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

  // Monta as opções do dropdown AGRUPANDO categorias que diferem apenas por acento/case
  function construirDropdownCategoriaDinamicamente() {
    let categoriasMap = new Map(); // Mapa para guardar: nome_normalizado -> Nome Original

    tabelaEstoque.rows().every(function() {
      let textoCat = $('<div>').html(this.data()[1]).text().trim();
      if (textoCat) {
        let normalizado = normalizarCategoria(textoCat);
        // Guarda apenas a primeira variação encontrada. Ex: se já tem "Construção", ignora "construcao" no menu
        if (!categoriasMap.has(normalizado)) {
          categoriasMap.set(normalizado, textoCat);
        }
      }
    });

    let $menu = $('#menuDinamicoCategoriaEstoque');
    $menu.empty(); 
    
    let categoriasUnicas = Array.from(categoriasMap.values()).sort((a, b) => a.localeCompare(b, 'pt-BR'));

    categoriasUnicas.forEach(function(categoria) {
      let icone = 'bi-tag-fill'; let cor = 'text-light';
      let $li = $('<li>');
      
      let $a = $('<a>')
          .addClass('dropdown-item dropdown-item-categoria py-2 fw-semibold d-flex justify-content-between align-items-center')
          .attr('href', '#')
          .attr('data-categoria', categoria);
      
      let $spanIcone = $('<span>')
          .html('<i class="bi ' + icone + ' ' + cor + ' me-2"></i> ')
          .append(document.createTextNode(categoria)); 
          
      let $spanBadge = $('<span>')
          .addClass('badge rounded-pill hard-color-badge count-cat-item')
          .attr('data-cat-name', categoria) // Guarda o nome original para o contador
          .text('0');
      
      $a.append($spanIcone).append($spanBadge);
      $li.append($a);
      $menu.append($li);
    });
  }

  // Executa a filtragem do estoque conforme a categoria agrupada
  $('#menuDinamicoCategoriaEstoque').on('click', '.dropdown-item-categoria', function(e) {
    e.preventDefault();
    const categoriaSelecionada = $(this).data('categoria');
    const textoLimpoOpcao = $(this).find('span').first().text().trim();

    const $container = $(this).closest('.pilulas-container');
    $container.find('.btn-pilula').removeClass('ativa');
    $('#pillEstoqueCategoriaDropdown').addClass('ativa');
    $('#textoCategoriaPill').html('<i class="bi bi-funnel-fill text-info me-1"></i> ' + textoLimpoOpcao);
    
    $('#tabelaEstoque').data('categoria-ativa', categoriaSelecionada);
    tabelaEstoque.draw(); // Aciona o filtro global e redesenha a tabela
  });

  // Atualiza os contadores numéricos AGRUPANDO os acentos na contagem
  function atualizarContadoresEstoque() {
    $('#countEstoqueTodos').text(tabelaEstoque.rows().count());
    
    let contadores = {}; 
    tabelaEstoque.rows().every(function() {
      let cellContent = this.data()[1]; 
      if (cellContent) {
        let catTexto = $('<div>').html(cellContent).text().trim();
        let normalizado = normalizarCategoria(catTexto);
        contadores[normalizado] = (contadores[normalizado] || 0) + 1;
      }
    });

    $('.count-cat-item').each(function() {
      let nome = $(this).data('cat-name');
      let normalizado = normalizarCategoria(nome);
      $(this).text(contadores[normalizado] || 0); // Soma os itens normais com os itens sem acento
    });

    const categoriaAtiva = $('#tabelaEstoque').data('categoria-ativa');
    if (categoriaAtiva) {
      let ativaNormalizada = normalizarCategoria(categoriaAtiva);
      if (contadores[ativaNormalizada]) {
        $('#countEstoqueCategoriaAtiva').text(contadores[ativaNormalizada]).removeClass('d-none');
      } else {
        $('#countEstoqueCategoriaAtiva').addClass('d-none'); 
      }
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
    pageLength: 5,
    lengthMenu: [5, 10, 25, 50],
    order: [], // Mantém a ordenação cronológica definida nativamente no backend (ORDER BY d.data ASC)
    columnDefs: [ { type: 'sem-acentos', targets: [2, 4] }, { orderable: false, targets: 5 } ],
    layout: {
      topStart: {
        buttons: [{
          extend: 'excelHtml5',
          text: '<i class="bi bi-file-earmark-excel-fill"></i> Exportar para Excel',
          className: 'btn btn-outline-success btn-sm fw-bold',
          title: 'Relatorio de Pendencias',
          exportOptions: { modifier: { search: 'applied' }, columns: [0, 1, 2, 3, 4] }
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
      // Agora o Status está no índice 1 da tabela
      let dadosColunaStatus = this.data()[1]; 
      if (dadosColunaStatus.includes('No Prazo')) noPrazo++;
      if (dadosColunaStatus.includes('Expirado')) expirados++;
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
    tabelaPendencias.column(1).search('').draw();
  });

  $('#pillNoPrazo').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    tabelaPendencias.column(1).search('No Prazo').draw();
  });

  $('#pillExpirado').on('click', function() {
    $(this).closest('.pilulas-container').find('.btn-pilula').removeClass('ativa');
    $(this).addClass('ativa');
    tabelaPendencias.column(1).search('Expirado').draw();
  });
});