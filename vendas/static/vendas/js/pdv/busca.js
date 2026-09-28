// Busca de produto — combobox com listbox (C1), padrão ARIA APG. Preenche a
// lista sempre clonando <template id="tpl-resultado"> e usando textContent
// (nunca innerHTML com dado do servidor).
import { getJSON, SessaoExpirada } from '/static/core/js/api.js';
import { anunciar } from '/static/core/js/anunciador.js';

const ATRASO_DEBOUNCE = 250;

const entrada = document.getElementById('busca-produto');
const lista = document.getElementById('resultados-busca');
const template = document.getElementById('tpl-resultado');

let controladorAbort = null;
let temporizador = null;
let indiceDestacado = -1;
let resultadosAtuais = [];
let aoSelecionar = null;

function idOpcao(produtoId) {
  return `opcao-${produtoId}`;
}

function fecharLista() {
  lista.hidden = true;
  entrada.setAttribute('aria-expanded', 'false');
  entrada.removeAttribute('aria-activedescendant');
  indiceDestacado = -1;
}

function destacar(indice) {
  const opcoes = lista.querySelectorAll('[role="option"]');
  opcoes.forEach((opcao) => opcao.setAttribute('aria-selected', 'false'));
  if (indice >= 0 && indice < opcoes.length) {
    opcoes[indice].setAttribute('aria-selected', 'true');
    entrada.setAttribute('aria-activedescendant', opcoes[indice].id);
    opcoes[indice].scrollIntoView({ block: 'nearest' });
  } else {
    entrada.removeAttribute('aria-activedescendant');
  }
  indiceDestacado = indice;
}

function renderizarResultados(produtos) {
  resultadosAtuais = produtos;
  lista.replaceChildren();
  produtos.forEach((produto) => {
    const fragmento = template.content.cloneNode(true);
    const opcao = fragmento.querySelector('[role="option"]');
    opcao.id = idOpcao(produto.id);
    opcao.querySelector('.produto-nome').textContent = produto.nome;
    opcao.querySelector('.produto-fabricante').textContent = produto.fabricante || '';
    opcao.querySelector('.produto-preco').textContent = `R$ ${produto.preco_venda}`;
    if (produto.estoque > 0) {
      opcao.querySelector('.produto-estoque').textContent = `${produto.estoque} em estoque`;
    } else {
      opcao.querySelector('.produto-estoque').textContent = 'Esgotado';
      opcao.setAttribute('aria-disabled', 'true');
    }
    opcao.addEventListener('click', () => selecionar(produto));
    lista.appendChild(opcao);
  });
  lista.hidden = produtos.length === 0;
  entrada.setAttribute('aria-expanded', String(produtos.length > 0));
  anunciar(
    produtos.length > 0
      ? `${produtos.length} produto${produtos.length > 1 ? 's' : ''} encontrado${produtos.length > 1 ? 's' : ''}`
      : 'Nenhum produto encontrado'
  );
}

async function buscar(termo) {
  if (controladorAbort) controladorAbort.abort();
  controladorAbort = new AbortController();
  try {
    const { status, dados } = await getJSON(
      `/vendas/api/produtos/?q=${encodeURIComponent(termo)}`,
      { signal: controladorAbort.signal }
    );
    if (status === 200) renderizarResultados(dados || []);
  } catch (erro) {
    if (erro instanceof SessaoExpirada) {
      window.location.href = erro.loginUrl || '/login/';
      return;
    }
    if (erro.name !== 'AbortError') {
      anunciar('Falha de conexão ao buscar produtos.', 'assertive');
    }
  }
}

function selecionar(produto) {
  fecharLista();
  entrada.value = '';
  if (aoSelecionar) aoSelecionar(produto);
}

entrada.addEventListener('input', () => {
  const termo = entrada.value.trim();
  window.clearTimeout(temporizador);
  if (termo.length < 2) {
    fecharLista();
    return;
  }
  temporizador = window.setTimeout(() => buscar(termo), ATRASO_DEBOUNCE);
});

entrada.addEventListener('keydown', (evento) => {
  const totalOpcoes = resultadosAtuais.length;
  if (lista.hidden && evento.key !== 'Escape') return;

  switch (evento.key) {
    case 'ArrowDown':
      evento.preventDefault();
      destacar(Math.min(indiceDestacado + 1, totalOpcoes - 1));
      break;
    case 'ArrowUp':
      evento.preventDefault();
      destacar(Math.max(indiceDestacado - 1, 0));
      break;
    case 'Home':
      if (!lista.hidden) {
        evento.preventDefault();
        destacar(0);
      }
      break;
    case 'End':
      if (!lista.hidden) {
        evento.preventDefault();
        destacar(totalOpcoes - 1);
      }
      break;
    case 'Enter':
      if (indiceDestacado >= 0 && resultadosAtuais[indiceDestacado]) {
        evento.preventDefault();
        const produto = resultadosAtuais[indiceDestacado];
        if (produto.estoque > 0) selecionar(produto);
      }
      break;
    case 'Escape':
      if (!lista.hidden) {
        fecharLista();
      } else {
        entrada.value = '';
      }
      break;
    default:
      break;
  }
});

document.addEventListener('click', (evento) => {
  if (!lista.hidden && !lista.contains(evento.target) && evento.target !== entrada) {
    fecharLista();
  }
});

export function init(callbackSelecionar) {
  aoSelecionar = callbackSelecionar;
}

export function focar() {
  entrada.focus();
}
