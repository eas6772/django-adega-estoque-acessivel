// Escreve nas regiões aria-live fixas do HTML (C6/A13). As regiões nunca são
// criadas dinamicamente — leitores de tela não anunciam região criada depois
// que a página já carregou.

export function anunciar(texto, nivel = 'polite') {
  const id = nivel === 'assertive' ? 'anuncio-alerta' : 'anuncio-status';
  const regiao = document.getElementById(id);
  if (!regiao) return;
  regiao.textContent = '';
  // Força o navegador a tratar como um anúncio novo mesmo se o texto repetir.
  window.requestAnimationFrame(() => {
    regiao.textContent = texto;
  });
}
