// Select dependente produto → lote (D1 do plano da Etapa 3: única tela de
// estoque que usa Fetch). Busca os lotes vendáveis do produto escolhido e
// repopula o <select> de lote, sempre via textContent (nunca innerHTML).
import { getJSON } from '/static/core/js/api.js';

const form = document.getElementById('form-ajuste');
const campoProduto = document.getElementById('id_produto');
const campoLote = document.getElementById('id_lote');
const infoLote = document.getElementById('lote-info');
const urlBase = form.dataset.urlLotes.replace('0', '');

function limparSelect(mensagem) {
  campoLote.replaceChildren();
  const opcao = document.createElement('option');
  opcao.value = '';
  opcao.textContent = mensagem;
  campoLote.appendChild(opcao);
}

async function carregarLotes(produtoId) {
  if (!produtoId) {
    limparSelect('Selecione um produto primeiro');
    campoLote.removeAttribute('aria-busy');
    return;
  }
  campoLote.setAttribute('aria-busy', 'true');
  limparSelect('Carregando lotes…');
  const { status, dados } = await getJSON(`${urlBase}${produtoId}/lotes/`);
  campoLote.removeAttribute('aria-busy');
  if (status !== 200 || !dados || dados.length === 0) {
    limparSelect('Nenhum lote disponível para este produto');
    infoLote.textContent = '0 lotes disponíveis.';
    return;
  }
  campoLote.replaceChildren();
  dados.forEach((lote) => {
    const opcao = document.createElement('option');
    opcao.value = String(lote.id);
    opcao.textContent = `Lote ${lote.numero_lote || lote.id} — ${lote.data_validade_fmt} — ${lote.quantidade} un.`;
    campoLote.appendChild(opcao);
  });
  infoLote.textContent = `${dados.length} lote(s) disponível(is) para este produto.`;
}

campoProduto.addEventListener('change', () => carregarLotes(campoProduto.value));
carregarLotes(campoProduto.value);
