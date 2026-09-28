// Estado do carrinho (C3): Map por lote_id, persistido em sessionStorage
// (sobrevive a F5 no meio da venda). Atualiza só a linha alterada — nunca
// recria a tabela inteira — para preservar o foco do usuário de teclado.
import { anunciar } from '/static/core/js/anunciador.js';

const CHAVE_STORAGE = 'emporio-pdv-carrinho';

const corpo = document.getElementById('carrinho-corpo');
const tabela = document.getElementById('tabela-carrinho');
const estadoVazio = document.getElementById('carrinho-vazio');
const contagem = document.getElementById('carrinho-contagem');
const resumoItens = document.getElementById('resumo-itens');
const resumoTotal = document.getElementById('resumo-total');
const template = document.getElementById('tpl-linha-carrinho');

const formatoBRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

let itens = new Map();

function salvar() {
  sessionStorage.setItem(CHAVE_STORAGE, JSON.stringify(Array.from(itens.values())));
}

function carregar() {
  try {
    const bruto = sessionStorage.getItem(CHAVE_STORAGE);
    if (!bruto) return;
    JSON.parse(bruto).forEach((item) => itens.set(item.lote_id, item));
  } catch {
    itens = new Map();
  }
}

function totalCentavos() {
  let total = 0;
  itens.forEach((item) => {
    total += Math.round(parseFloat(item.preco_unitario) * 100) * item.quantidade;
  });
  return total;
}

function atualizarResumo() {
  const qtdItens = itens.size;
  contagem.textContent = String(qtdItens);
  resumoItens.textContent = String(qtdItens);
  resumoTotal.textContent = formatoBRL.format(totalCentavos() / 100);
  tabela.hidden = qtdItens === 0;
  estadoVazio.hidden = qtdItens !== 0;
}

function subtotalItem(item) {
  return parseFloat(item.preco_unitario) * item.quantidade;
}

function preencherLinha(linha, item) {
  linha.dataset.lote = String(item.lote_id);
  linha.querySelector('.carrinho-nome').textContent = item.nome;

  const botaoDiminuir = linha.querySelector('.carrinho-diminuir');
  const botaoAumentar = linha.querySelector('.carrinho-aumentar');
  const saida = linha.querySelector('.carrinho-qtd-valor');
  const botaoRemover = linha.querySelector('.carrinho-remover');

  botaoDiminuir.setAttribute('aria-label', `Diminuir quantidade de ${item.nome}`);
  botaoAumentar.setAttribute('aria-label', `Aumentar quantidade de ${item.nome}`);
  saida.setAttribute('aria-label', `Quantidade de ${item.nome}`);
  saida.textContent = String(item.quantidade);
  botaoRemover.setAttribute('aria-label', `Remover ${item.nome} do carrinho`);

  const limiteAtingido = item.quantidade >= item.saldo_lote;
  botaoAumentar.setAttribute('aria-disabled', String(limiteAtingido));

  linha.querySelector('.carrinho-preco').textContent = formatoBRL.format(parseFloat(item.preco_unitario));
  linha.querySelector('.carrinho-subtotal').textContent = formatoBRL.format(subtotalItem(item));

  botaoDiminuir.onclick = () => alterarQuantidade(item.lote_id, -1);
  botaoAumentar.onclick = () => {
    if (item.quantidade >= item.saldo_lote) {
      anunciar(`Quantidade máxima do lote atingida (${item.saldo_lote}).`, 'assertive');
      return;
    }
    alterarQuantidade(item.lote_id, 1);
  };
  botaoRemover.onclick = () => removerItem(item.lote_id);
}

function criarLinha(item) {
  const fragmento = template.content.cloneNode(true);
  const linha = fragmento.querySelector('tr');
  preencherLinha(linha, item);
  return linha;
}

function render() {
  corpo.replaceChildren();
  itens.forEach((item) => corpo.appendChild(criarLinha(item)));
  atualizarResumo();
}

function linhaDoLote(loteId) {
  return corpo.querySelector(`tr[data-lote="${loteId}"]`);
}

export function init() {
  carregar();
  render();
}

export function obterItens() {
  return Array.from(itens.values());
}

export function adicionarItem(novoItem) {
  const existente = itens.get(novoItem.lote_id);
  if (existente) {
    const quantidade = Math.min(existente.quantidade + novoItem.quantidade, existente.saldo_lote);
    existente.quantidade = quantidade;
    preencherLinha(linhaDoLote(novoItem.lote_id), existente);
  } else {
    itens.set(novoItem.lote_id, novoItem);
    corpo.appendChild(criarLinha(novoItem));
  }
  atualizarResumo();
  salvar();
  const item = itens.get(novoItem.lote_id);
  anunciar(
    `${item.nome} adicionado, ${item.quantidade} unidade(s). Total ${formatoBRL.format(totalCentavos() / 100)}.`
  );
}

function alterarQuantidade(loteId, delta) {
  const item = itens.get(loteId);
  if (!item) return;
  const nova = Math.max(1, Math.min(item.quantidade + delta, item.saldo_lote));
  if (nova === item.quantidade) return;
  item.quantidade = nova;
  preencherLinha(linhaDoLote(loteId), item);
  atualizarResumo();
  salvar();
  anunciar(`${item.nome}: ${item.quantidade} unidade(s). Total ${formatoBRL.format(totalCentavos() / 100)}.`);
}

function removerItem(loteId) {
  const item = itens.get(loteId);
  if (!item) return;
  const linha = linhaDoLote(loteId);
  const proxima = linha.nextElementSibling;
  const anterior = linha.previousElementSibling;
  itens.delete(loteId);
  linha.remove();
  atualizarResumo();
  salvar();
  anunciar(`${item.nome} removido. Total ${formatoBRL.format(totalCentavos() / 100)}.`);

  const focoAlvo = proxima || anterior;
  if (focoAlvo) {
    focoAlvo.querySelector('.carrinho-remover')?.focus();
  } else {
    document.getElementById('busca-produto')?.focus();
  }
}

export function marcarConflito(loteId, disponivel) {
  const item = itens.get(loteId);
  const linha = linhaDoLote(loteId);
  if (!item || !linha) return;
  item.saldo_lote = disponivel;
  linha.classList.add('carrinho-linha-erro');
  const celula = linha.querySelector('.carrinho-subtotal');
  const aviso = document.createElement('p');
  aviso.className = 'campo-erro';
  aviso.textContent = `Disponível: ${disponivel}`;
  celula.appendChild(aviso);
  linha.querySelector('.carrinho-diminuir')?.focus();
}

export function limpar() {
  itens.clear();
  corpo.replaceChildren();
  sessionStorage.removeItem(CHAVE_STORAGE);
  atualizarResumo();
}
