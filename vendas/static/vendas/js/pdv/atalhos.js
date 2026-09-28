// Atalhos de teclado do caixa (C8): F2 foca a busca, F9 finaliza a venda.
// Nenhuma tecla única sem modificador — não conflita com leitores de tela.
import { focar as focarBusca } from './busca.js';
import { finalizarVenda } from './finalizar.js';

export function init() {
  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'F2') {
      evento.preventDefault();
      focarBusca();
    } else if (evento.key === 'F9') {
      const dialogoAberto = document.querySelector('dialog[open]');
      if (dialogoAberto) return;
      evento.preventDefault();
      finalizarVenda();
    }
  });
}
