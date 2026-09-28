// Abertura/fechamento de <dialog> com devolução de foco (C2/A12): guarda o
// elemento com foco antes de abrir e devolve o foco a ele ao fechar —
// showModal() já cuida de prender o foco dentro do diálogo e do Esc nativo.

const focoAnterior = new WeakMap();

export function abrir(dialogo, focoInicial) {
  focoAnterior.set(dialogo, document.activeElement);
  dialogo.showModal();
  if (focoInicial) focoInicial.focus();
}

export function aoFechar(dialogo, callback) {
  dialogo.addEventListener('close', () => {
    callback(dialogo.returnValue);
    const origem = focoAnterior.get(dialogo);
    (origem ?? document.body).focus();
  });
}
