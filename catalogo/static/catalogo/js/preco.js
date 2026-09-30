// Recalcula o preço de venda no cliente (só um preview visual — o valor
// definitivo é sempre recalculado no servidor por Produto.save(), nunca
// aceito do formulário). A11: <output aria-live="polite"> anuncia a mudança.
const formatoBRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

const campoCusto = document.getElementById('id_preco_custo');
const campoMargem = document.getElementById('id_margem_lucro');
const saida = document.getElementById('preco-venda-calculado');

function recalcular() {
  const custo = parseFloat(campoCusto.value.replace(',', '.'));
  const margem = parseFloat(campoMargem.value.replace(',', '.'));
  if (Number.isNaN(custo) || Number.isNaN(margem)) return;
  saida.textContent = formatoBRL.format(custo * (1 + margem / 100));
}

if (campoCusto && campoMargem && saida) {
  campoCusto.addEventListener('input', recalcular);
  campoMargem.addEventListener('input', recalcular);
}
