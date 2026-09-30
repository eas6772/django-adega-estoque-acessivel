// Diálogo de seleção de lote e quantidade (C2). Usa <dialog> nativo via
// core/js/dialogo.js (foco preso, Esc, devolução de foco). Erro de
// quantidade fica ligado ao campo — nunca "corrige" o valor silenciosamente.
import { getJSON, SessaoExpirada } from '/static/core/js/api.js';
import { abrir, aoFechar } from '/static/core/js/dialogo.js';
import * as carrinho from './carrinho.js';
import { focar as focarBusca } from './busca.js';

const dialogo = document.getElementById('dialogo-lote');
const produtoDesc = document.getElementById('dialogo-lote-produto');
const select = document.getElementById('lote-select');
const infoLote = document.getElementById('lote-info');
const campoQtd = document.getElementById('lote-qtd');
const erroQtd = document.getElementById('lote-qtd-erro');

let produtoAtual = null;
let lotesAtuais = [];

function limparErroQtd() {
  erroQtd.textContent = '';
  campoQtd.removeAttribute('aria-invalid');
}

function popularSelect(lotes) {
  select.replaceChildren();
  lotes.forEach((lote) => {
    const opcao = document.createElement('option');
    opcao.value = String(lote.id);
    opcao.textContent = `Lote ${lote.numero_lote || lote.id} — vence ${lote.data_validade_fmt} — ${lote.quantidade} un.`;
    select.appendChild(opcao);
  });
  select.removeAttribute('aria-busy');
  infoLote.textContent = `${lotes.length} lote(s) disponível(is).`;
}

async function abrirDialogoParaProduto(produto) {
  produtoAtual = produto;
  produtoDesc.textContent = `${produto.nome}${produto.fabricante ? ' — ' + produto.fabricante : ''}`;
  select.setAttribute('aria-busy', 'true');
  select.replaceChildren();
  const opcaoCarregando = document.createElement('option');
  opcaoCarregando.textContent = 'Carregando lotes…';
  select.appendChild(opcaoCarregando);
  limparErroQtd();
  campoQtd.value = '1';

  let resposta;
  try {
    resposta = await getJSON(`/estoque/api/produtos/${produto.id}/lotes/`);
  } catch (erro) {
    if (erro instanceof SessaoExpirada) {
      window.location.href = erro.loginUrl || '/login/';
      return;
    }
    throw erro;
  }

  lotesAtuais = resposta.dados || [];
  if (lotesAtuais.length === 0) {
    select.replaceChildren();
    const vazio = document.createElement('option');
    vazio.textContent = 'Nenhum lote disponível';
    select.appendChild(vazio);
    select.removeAttribute('aria-busy');
    infoLote.textContent = 'Nenhum lote disponível para este produto.';
    abrir(dialogo, select);
    return;
  }

  // Leitor de código de barras com match exato e um único lote: adiciona
  // direto, sem abrir o diálogo (agiliza o fluxo mais comum do caixa).
  if (produto.match_exato && lotesAtuais.length === 1) {
    adicionarAoCarrinho(lotesAtuais[0], 1);
    focarBusca();
    return;
  }

  popularSelect(lotesAtuais);
  campoQtd.max = String(lotesAtuais[0].quantidade);
  abrir(dialogo, select);
}

function adicionarAoCarrinho(lote, quantidade) {
  carrinho.adicionarItem({
    produto_id: produtoAtual.id,
    lote_id: lote.id,
    nome: produtoAtual.nome,
    fabricante: produtoAtual.fabricante,
    numero_lote: lote.numero_lote,
    preco_unitario: produtoAtual.preco_venda,
    saldo_lote: lote.quantidade,
    quantidade,
  });
}

select.addEventListener('change', () => {
  const lote = lotesAtuais.find((l) => String(l.id) === select.value);
  if (lote) campoQtd.max = String(lote.quantidade);
  limparErroQtd();
});

// Intercepta o submit (method="dialog") ANTES do diálogo fechar: se a
// quantidade for inválida, cancela o fechamento e mostra o erro ligado ao
// campo, em vez de aceitar o valor ou fechar silenciosamente.
dialogo.querySelector('form').addEventListener('submit', (evento) => {
  if (evento.submitter?.value !== 'adicionar') return;
  const lote = lotesAtuais.find((l) => String(l.id) === select.value);
  const quantidade = parseInt(campoQtd.value, 10);
  if (!lote || Number.isNaN(quantidade) || quantidade < 1) {
    evento.preventDefault();
    return;
  }
  if (quantidade > lote.quantidade) {
    evento.preventDefault();
    erroQtd.textContent = `Quantidade maior que o saldo disponível (${lote.quantidade}).`;
    campoQtd.setAttribute('aria-invalid', 'true');
    campoQtd.focus();
  }
});

aoFechar(dialogo, (resultado) => {
  if (resultado !== 'adicionar') return;
  const lote = lotesAtuais.find((l) => String(l.id) === select.value);
  const quantidade = parseInt(campoQtd.value, 10);
  if (!lote || Number.isNaN(quantidade) || quantidade < 1) return;
  adicionarAoCarrinho(lote, quantidade);
  focarBusca();
});

export function init() {
  // nada a inicializar além dos listeners acima; exportado para simetria
  // com os outros módulos do PDV orquestrados por main.js.
}

export { abrirDialogoParaProduto as selecionarProduto };
