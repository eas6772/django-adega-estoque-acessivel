// Comportamento do layout base: menu lateral no mobile, fechamento automático
// de mensagens de sucesso/info, foco no resumo de erros, e o diálogo de
// confirmação genérico usado pelos botões "alternar ativo" de todo o site.
import { abrir, aoFechar } from '/static/core/js/dialogo.js';

function configurarMenu() {
  const toggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('menu-lateral');
  if (!toggle || !sidebar) return;

  function ehMobile() {
    return window.matchMedia('(max-width: 768px)').matches;
  }

  function definirMenu(aberto) {
    sidebar.classList.toggle('aberto', aberto);
    toggle.setAttribute('aria-expanded', String(aberto));
    toggle.setAttribute('aria-label', aberto ? 'Fechar menu' : 'Abrir menu');
    sidebar.inert = !aberto && ehMobile();
    if (aberto) {
      const primeiroLink = sidebar.querySelector('a');
      if (primeiroLink) primeiroLink.focus();
    }
  }

  toggle.addEventListener('click', () => {
    definirMenu(!sidebar.classList.contains('aberto'));
  });
  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape' && sidebar.classList.contains('aberto')) {
      definirMenu(false);
      toggle.focus();
    }
  });
  sidebar.inert = ehMobile();
}

function configurarMensagens() {
  document.querySelectorAll('.mensagem[data-fecha-automatico]').forEach((mensagem) => {
    let temporizador = window.setTimeout(fechar, 10000);
    function fechar() {
      mensagem.remove();
    }
    function pausar() {
      window.clearTimeout(temporizador);
    }
    mensagem.addEventListener('mouseenter', pausar);
    mensagem.addEventListener('focusin', pausar);
    const botaoFechar = mensagem.querySelector('.mensagem-fechar');
    if (botaoFechar) botaoFechar.addEventListener('click', fechar);
  });
}

function focarResumoErros() {
  const resumo = document.getElementById('resumo-erros');
  if (resumo) resumo.focus();
}

function configurarDialogoConfirmar() {
  const dialogo = document.getElementById('dialogo-confirmar');
  const formAlvo = document.getElementById('form-confirmar-alvo');
  if (!dialogo || !formAlvo) return;

  const mensagem = dialogo.querySelector('#dialogo-confirmar-mensagem');
  const botaoConfirmar = dialogo.querySelector('#dialogo-confirmar-botao');

  document.querySelectorAll('[data-confirmar-url]').forEach((botao) => {
    botao.addEventListener('click', () => {
      mensagem.textContent = botao.dataset.confirmarMensagem || 'Confirma esta ação?';
      botaoConfirmar.textContent = botao.dataset.confirmarTexto || 'Confirmar';
      formAlvo.action = botao.dataset.confirmarUrl;
      abrir(dialogo, botaoConfirmar);
    });
  });

  aoFechar(dialogo, (resultado) => {
    if (resultado === 'confirmar') formAlvo.submit();
  });
}

configurarMenu();
configurarMensagens();
focarResumoErros();
configurarDialogoConfirmar();
