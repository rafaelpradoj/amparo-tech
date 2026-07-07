document.addEventListener("DOMContentLoaded", function () {
  // =========================================================================
  // 1. LÓGICA DOS ALERTAS FLASH (Bootstrap 5 API)
  // =========================================================================
  // Seleciona todas as mensagens de alerta da página para fechá-las automaticamente após 8 segundos
  const alertas = document.querySelectorAll(".alert");
  alertas.forEach(function (alerta) {
    setTimeout(function () {
      // Instancia e executa o encerramento do alerta usando a API nativa do Bootstrap 5
      const bsAlert = new bootstrap.Alert(alerta);
      bsAlert.close();
    }, 8000);
  });

  // =========================================================================
  // 2. LÓGICA GLOBAL ANTI-DUPLO CLIQUE (Submit múltiplo)
  // =========================================================================
  // Captura todos os formulários, ignorando apenas os que possuem a classe de escape ".no-loader"
  const formularios = document.querySelectorAll("form:not(.no-loader)");
  
  formularios.forEach(function(form) {
    form.addEventListener("submit", function() {
      const btnSubmit = form.querySelector('button[type="submit"]');

      if (btnSubmit) {
        // Guarda a largura exata atual do botão em pixels.
        // Isso impede que o botão "encolha" ou mude de tamanho visualmente quando o texto sumir para dar lugar ao spinner.
        const width = btnSubmit.offsetWidth; 
        btnSubmit.style.width = width + 'px';
                
        // Injeta o spinner de carregamento sutil do Bootstrap dentro do botão
        btnSubmit.innerHTML = `
          <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        `;
        
        // Aplica um delay mínimo de 10 milissegundos antes de desativar o botão.
        // Esse atraso é uma boa prática para garantir que o navegador processe e envie a requisição do formulário 
        // antes que o elemento fique desabilitado (o que poderia interromper o envio em alguns navegadores).
        setTimeout(() => {
          btnSubmit.disabled = true;
        }, 10);
      }
    });
  });
});

// =========================================================================
// 3. ALTERNAR VISUALIZAÇÃO DE SENHA NOS INPUTS
// =========================================================================
// Função chamada no clique do botão de "olho" nos formulários de credenciais
function togglePassword(botao) {
  // Localiza o input de texto/senha que está posicionado imediatamente antes do botão no HTML
  const input = botao.previousElementSibling;
  const icone = botao.querySelector("i");

  // Alterna o atributo 'type' do input e substitui as classes do Bootstrap Icons correspondentes
  if (input.type === "password") {
    input.type = "text";
    icone.classList.replace("bi-eye", "bi-eye-slash"); // Muda para o ícone de olho cortado
  } else {
    input.type = "password";
    icone.classList.replace("bi-eye-slash", "bi-eye"); // Retorna para o ícone de olho aberto
  }
}