// Único ponto de contato com o backend via Fetch (D4 do plano da Etapa 3):
// lê o token CSRF, define os headers padrão e converte 401 na exceção
// SessaoExpirada. Nenhum outro módulo deve chamar fetch() diretamente.

export class SessaoExpirada extends Error {
  constructor(loginUrl) {
    super('Sessão expirada.');
    this.loginUrl = loginUrl;
  }
}

function tokenCsrf() {
  const campo = document.querySelector('[name=csrfmiddlewaretoken]');
  return campo ? campo.value : '';
}

async function tratarResposta(resposta) {
  if (resposta.status === 401) {
    const dados = await resposta.json().catch(() => ({}));
    throw new SessaoExpirada(dados.login_url);
  }
  const dados = await resposta.json().catch(() => null);
  return { status: resposta.status, dados };
}

export async function getJSON(url, { signal } = {}) {
  const resposta = await fetch(url, {
    headers: { Accept: 'application/json' },
    signal,
  });
  return tratarResposta(resposta);
}

export async function postJSON(url, corpo) {
  const resposta = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': tokenCsrf(),
    },
    body: JSON.stringify(corpo),
  });
  return tratarResposta(resposta);
}
