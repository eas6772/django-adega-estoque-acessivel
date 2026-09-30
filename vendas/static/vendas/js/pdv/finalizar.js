// Finalização da venda (C5): POST /vendas/api/vendas/ e tratamento de cada
// status da tabela do contrato (docs/projeto_django_spec.md §3.2).
import { postJSON, SessaoExpirada } from '/static/core/js/api.js';
import { anunciar } from '/static/core/js/anunciador.js';
import * as carrinho from './carrinho.js';
import { focar as focarBusca } from './busca.js';

const botao = document.getElementById('btn-finalizar');
const textoOriginal = botao.innerHTML;
const painelRecibo = document.getElementById('painel-recibo');

async function buscarFragmentoRecibo(url) {
  const resposta = await fetch(`${url}?parcial=1`, { headers: { 'X-Requested-With': 'fetch' } });
  return resposta.text();
}

async function finalizarVenda() {
  const itens = carrinho.obterItens();
  if (itens.length === 0) {
    anunciar('Adicione pelo menos um produto ao carrinho.', 'assertive');
    return;
  }

  botao.setAttribute('aria-busy', 'true');
  botao.disabled = true;
  botao.textContent = 'Registrando venda…';

  try {
    const { status, dados } = await postJSON('/vendas/api/vendas/', {
      itens: itens.map((item) => ({ lote_id: item.lote_id, quantidade: item.quantidade })),
    });

    if (status === 201) {
      carrinho.limpar();
      // dados já vem renderizado e escapado pelo Django (fragmento HTML de
      // confiança) — diferente dos endpoints JSON, aqui é seguro atribuir
      // diretamente ao innerHTML.
      const fragmentoHtml = await buscarFragmentoRecibo(dados.recibo_url);
      painelRecibo.innerHTML = fragmentoHtml;
      painelRecibo.hidden = false;
      painelRecibo.querySelector('#botao-imprimir-recibo')?.addEventListener('click', () => window.print());
      painelRecibo.querySelector('#botao-nova-venda')?.addEventListener('click', () => {
        painelRecibo.hidden = true;
        painelRecibo.replaceChildren();
        focarBusca();
      });
      const titulo = painelRecibo.querySelector('#recibo-titulo');
      titulo?.focus();
      anunciar(`Venda ${dados.id} registrada. Total R$ ${dados.total.replace('.', ',')}.`);
      return;
    }

    if (status === 409) {
      anunciar(dados.erro, 'assertive');
      if (dados.lote_id != null) carrinho.marcarConflito(dados.lote_id, dados.disponivel);
      return;
    }

    // 400 / 403: mantém o carrinho, mensagem em role="alert".
    anunciar(dados?.erro || 'Não foi possível registrar a venda.', 'assertive');
  } catch (erro) {
    if (erro instanceof SessaoExpirada) {
      anunciar('Sessão expirada. Redirecionando para o login…', 'assertive');
      window.location.href = erro.loginUrl || '/login/';
      return;
    }
    anunciar('Falha de conexão. O carrinho foi mantido; tente novamente.', 'assertive');
  } finally {
    botao.removeAttribute('aria-busy');
    botao.disabled = false;
    botao.innerHTML = textoOriginal;
  }
}

export function init() {
  botao.addEventListener('click', finalizarVenda);
}

export { finalizarVenda };
