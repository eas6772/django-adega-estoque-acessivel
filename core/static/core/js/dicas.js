// Dicas (tooltips) para botões e links só de ícone. O texto vem do aria-label (ou de
// data-dica), então o nome acessível e a dica visual nunca divergem. A dica é só visual
// (aria-hidden), para o leitor de tela não anunciar duas vezes.
// WCAG 1.4.13: aparece também no foco do teclado, some com Esc, fica aberta enquanto o
// ponteiro está sobre o botão ou sobre a própria dica, e não some sozinha.
const SELETOR = [
  '.botao-icone[aria-label]',
  '.mensagem-fechar[aria-label]',
  '.celula-acoes [aria-label]',
  '.paginacao a[aria-label]',
  '[data-dica]',
].join(', ');
const ATRASO_MOUSE = 400;
const ATRASO_SAIDA = 120;
const FOLGA = 8;

function textoDaDica(alvo) {
  return alvo.dataset.dica || alvo.getAttribute('aria-label') || '';
}

function configurarDicas() {
  const dica = document.createElement('div');
  dica.className = 'dica';
  dica.setAttribute('aria-hidden', 'true');
  const suportaPopover = typeof dica.showPopover === 'function';
  if (suportaPopover) dica.popover = 'manual';
  document.body.append(dica);

  let alvoAtual = null;
  let temporizadorMostrar = 0;
  let temporizadorSumir = 0;

  function posicionar(alvo) {
    const caixa = alvo.getBoundingClientRect();
    const largura = dica.offsetWidth;
    const altura = dica.offsetHeight;
    let esquerda = caixa.left + caixa.width / 2 - largura / 2;
    esquerda = Math.max(FOLGA, Math.min(esquerda, window.innerWidth - largura - FOLGA));
    let topo = caixa.bottom + FOLGA;
    if (topo + altura > window.innerHeight - FOLGA) topo = Math.max(FOLGA, caixa.top - altura - FOLGA);
    dica.style.left = `${esquerda}px`;
    dica.style.top = `${topo}px`;
  }

  function mostrar(alvo) {
    const texto = textoDaDica(alvo);
    if (!texto || !alvo.isConnected) return;
    window.clearTimeout(temporizadorSumir);
    alvoAtual = alvo;
    dica.textContent = texto;
    if (suportaPopover && !dica.matches(':popover-open')) dica.showPopover();
    dica.classList.add('visivel');
    posicionar(alvo);
  }

  function esconder() {
    window.clearTimeout(temporizadorMostrar);
    window.clearTimeout(temporizadorSumir);
    alvoAtual = null;
    dica.classList.remove('visivel');
    if (suportaPopover && dica.matches(':popover-open')) dica.hidePopover();
  }

  function agendarSaida() {
    window.clearTimeout(temporizadorMostrar);
    window.clearTimeout(temporizadorSumir);
    temporizadorSumir = window.setTimeout(esconder, ATRASO_SAIDA);
  }

  function alvoDe(evento) {
    return evento.target instanceof Element ? evento.target.closest(SELETOR) : null;
  }

  document.addEventListener('pointerover', (evento) => {
    if (evento.pointerType === 'touch') return;
    if (evento.target instanceof Element && dica.contains(evento.target)) {
      window.clearTimeout(temporizadorSumir);
      return;
    }
    const alvo = alvoDe(evento);
    if (!alvo || alvo === alvoAtual) {
      if (alvo) window.clearTimeout(temporizadorSumir);
      return;
    }
    window.clearTimeout(temporizadorMostrar);
    temporizadorMostrar = window.setTimeout(() => mostrar(alvo), alvoAtual ? 0 : ATRASO_MOUSE);
  });

  document.addEventListener('pointerout', (evento) => {
    if (evento.pointerType === 'touch') return;
    const saiu = evento.target instanceof Element
      && (evento.target.closest(SELETOR) || dica.contains(evento.target));
    if (!saiu) return;
    const destino = evento.relatedTarget;
    if (destino instanceof Element && (dica.contains(destino) || destino.closest(SELETOR) === alvoAtual)) return;
    agendarSaida();
  });

  document.addEventListener('focusin', (evento) => {
    const alvo = alvoDe(evento);
    if (alvo && alvo.matches(':focus-visible')) {
      window.clearTimeout(temporizadorMostrar);
      mostrar(alvo);
    } else if (!dica.contains(evento.target)) {
      esconder();
    }
  });
  document.addEventListener('focusout', (evento) => {
    if (alvoDe(evento)) esconder();
  });

  // Esc dispensa a dica sem impedir o que o Esc já fazia (fechar diálogo ou menu).
  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape' && alvoAtual) esconder();
  }, true);
  document.addEventListener('click', esconder, true);
  window.addEventListener('scroll', esconder, true);
  window.addEventListener('resize', esconder);
}

configurarDicas();
