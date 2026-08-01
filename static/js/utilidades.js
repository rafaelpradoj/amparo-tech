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

  // =========================================================================
  // 3. ALTERNAR VISUALIZAÇÃO DE SENHA NOS INPUTS (Event delegation)
  // =========================================================================
  // Usa event delegation para lidar com todos os botões de toggle de senha
  document.addEventListener("click", function(e) {
    const toggleBtn = e.target.closest(".js-toggle-password");
    if (toggleBtn) {
      e.preventDefault();
      togglePassword(toggleBtn);
    }
  });

  // =========================================================================
  // 4. COPIAR CHAVE PIX (Event delegation)
  // =========================================================================
  // Usa event delegation para o botão de copiar PIX no footer
  document.addEventListener("click", function(e) {
    const copyBtn = e.target.closest(".js-copy-pix");
    if (copyBtn) {
      e.preventDefault();
      const pixValue = copyBtn.querySelector("code")?.textContent; // Uso de Optional Chaining (?.) para evitar erro de runtime caso a tag code não exista
      if (!pixValue) return;

      navigator.clipboard.writeText(pixValue);
      const status = copyBtn.querySelector(".copy-status");
      if (status) {
        status.innerHTML = '<span class="small px-1">Copiado!</span>';
        setTimeout(() => {
          status.innerHTML = '<i class="bi bi-clipboard px-1"></i>';
        }, 2000);
      }
    }
  });

  // =========================================================================
  // 5. BOTÃO "VOLTAR AO TOPO" (Scroll to Top)
  // =========================================================================
  const btnTopo = document.getElementById("btnVoltarAoTopo");
  if (btnTopo) {
    window.addEventListener("scroll", function() {
      if (window.scrollY > 200) {
        btnTopo.classList.add("mostrar");
      } else {
        btnTopo.classList.remove("mostrar");
      }
    });

    btnTopo.addEventListener("click", function() {
      window.scrollTo({
        top: 0,
        behavior: "smooth"
      });
    });
  }
});

// =========================================================================
// 6. ALTERNAR VISUALIZAÇÃO DE SENHA (Função utilitária)
// =========================================================================
function togglePassword(botao) {
  const input = botao.previousElementSibling;
  const icone = botao.querySelector("i");

  if (input.type === "password") {
    input.type = "text";
    icone.classList.replace("bi-eye", "bi-eye-slash");
  } else {
    input.type = "password";
    icone.classList.replace("bi-eye-slash", "bi-eye");
  }
}