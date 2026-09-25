# Planejamento de Views — Migração Flask → Django

**Projeto:** Gestão de Estoque na Adega — Empório BR
**Origem:** `estoque_app/` (Flask 3 + SQLAlchemy + SQLite)
**Destino:** `novo_app/` (Django ≥ 5.2 + PostgreSQL)
**Modelos:** ver [`novo_app/models.py`](../novo_app/models.py) (validado com `manage.py check` e `makemigrations` no Django 6.1)

---

## 1. Visão geral da arquitetura alvo

| Flask (hoje) | Django (alvo) |
|---|---|
| App factory `create_app()` + 7 blueprints | Um app `novo_app` com `urls.py` dividido por módulos (`urls/produtos.py`, …) incluídos com `namespace` |
| Flask-Login (`login_required`, `current_user`) | `django.contrib.auth` — `LoginRequiredMixin` / `@login_required`, `request.user` |
| `requer_admin` (utils.py), `requer_admin` duplicado em relatorios.py, `_somente_admin()` em usuarios.py | **Um só** `AdminRequiredMixin` / `@admin_required` que retorna 403 (hoje usuários redireciona com flash e os outros dão 403 — comportamento inconsistente) |
| Flask-WTF `CSRFProtect` | `CsrfViewMiddleware` (nativo). Fetch envia header `X-CSRFToken` |
| `flash(msg, 'danger')` | `messages.error(...)` + `MESSAGE_TAGS = {messages.ERROR: 'danger'}` para manter as classes do Bootstrap |
| Validação manual (`_produto_do_form`, `_validar_entrada`) | `ModelForm` / `Form` — erros ligados a cada campo (ajuda também na acessibilidade) |
| `query.paginate()` / paginação manual | `Paginator` / `ListView.paginate_by` |
| Regras de negócio espalhadas nas rotas | Camada `novo_app/servicos.py` (entrada, ajuste, venda) — views finas, regras testáveis |

Estrutura sugerida:

```
novo_app/
├── models.py          # já entregue
├── hashers.py         # WerkzeugScryptHasher (seção 6)
├── servicos.py        # registrar_entrada, ajustar_lote, registrar_venda
├── forms.py
├── permissoes.py      # AdminRequiredMixin, admin_required
├── views/
│   ├── auth.py  painel.py  produtos.py  estoque.py
│   ├── vendas.py  api.py  relatorios.py  usuarios.py
├── urls.py
├── templates/novo_app/…
└── static/novo_app/js/pdv.js   # JS do PDV sai do template
```

---

## 2. Inventário completo das rotas Flask (31 endpoints)

Legenda de permissão: 🔓 público · 👤 logado · 🔑 admin

### 2.1 `auth_bp` — `routes/auth.py`

| # | Rota Flask | Métodos | Perm. | Django — URL / name | View Django | Observações |
|---|---|---|---|---|---|---|
| 1 | `/login` | GET, POST | 🔓 | `login/` · `login` | `LoginView` (auth nativo) com `template_name` e `redirect_authenticated_user=True` | **Corrige open-redirect**: o Flask usa `request.args.get('next')` sem validar; o `LoginView` valida com `url_has_allowed_host_and_scheme`. |
| 2 | `/logout` | GET | 👤 | `logout/` · `logout` | `LogoutView` | Django 5+ exige **POST**. O link "Sair" do topbar vira `<form method="post">` com botão. |

### 2.2 `main_bp` — `routes/main.py`

| # | Rota Flask | Métodos | Perm. | Django | View Django | Observações |
|---|---|---|---|---|---|---|
| 3 | `/` e `/dashboard` | GET | 👤 | `''` → `RedirectView` para `painel`; `painel/` · `painel` | `TemplateView` (`get_context_data`) | Usar `Produto.objects.ativos().abaixo_do_minimo()` e `Lote.objects.vencendo_em(30)` — 2 queries em vez de N+1. **Bug de fuso:** o Flask calcula "vendas de hoje" a partir da meia-noite **UTC** (= 21h em Santos); vendas entre 21h e 23h59 caem no dia seguinte. Usar `timezone.localdate()` com `TIME_ZONE='America/Sao_Paulo'`. |

### 2.3 `produtos_bp` — `routes/produtos.py`

| # | Rota Flask | Métodos | Perm. | Django | View Django | Observações |
|---|---|---|---|---|---|---|
| 4 | `/categorias` | GET | 👤 | `categorias/` · `categoria_lista` | `ListView` | Anotar `num_produtos=Count('produtos', filter=Q(produtos__ativo=True))` — hoje o template faz uma query por linha. |
| 5 | `/categoria/nova` | GET, POST | 🔑 | `categorias/nova/` · `categoria_criar` | `CreateView` (`CategoriaForm`) | Unicidade case-insensitive já garantida no modelo. |
| 6 | `/categoria/<id>/editar` | POST | 🔑 | `categorias/<int:pk>/editar/` · `categoria_editar` | `UpdateView` (só POST) **ou** endpoint JSON via Fetch para o modal | O template atual injeta o nome em `onclick="abrirEditar(1, '{{ cat.nome }}')"` — um nome com apóstrofo quebra o JS. Passar via `data-*` + `json_script`. |
| 7 | `/categoria/<id>/toggle` | POST | 🔑 | `categorias/<int:pk>/alternar/` · `categoria_alternar` | `View` com `post()` | Redirect + `messages.info`. |
| 8 | `/produtos` | GET | 👤 | `produtos/` · `produto_lista` | `ListView` (`paginate_by=15`) + `FiltroProdutoForm` (GET) | `Produto.objects.com_estoque().select_related('categoria').buscar(q)`. |
| 9 | `/produto/novo` | GET, POST | 🔑 | `produtos/novo/` · `produto_criar` | `CreateView` (`ProdutoForm`) | `preco_venda` é calculado no `save()` do modelo; o form não expõe o campo. |
| 10 | `/produto/<id>/editar` | GET, POST | 🔑 | `produtos/<int:pk>/editar/` · `produto_editar` | `UpdateView` | Validar `estoque_maximo >= estoque_minimo` no `clean()` do form (constraint no banco é a segunda barreira). |
| 11 | `/produto/<id>/toggle` | POST | 🔑 | `produtos/<int:pk>/alternar/` · `produto_alternar` | `View` com `post()` | Mesma injeção em `confirm('... "{{ p.nome }}"')` — trocar por `<dialog>` de confirmação. |

### 2.4 `estoque_bp` — `routes/estoque.py`

| # | Rota Flask | Métodos | Perm. | Django | View Django | Observações |
|---|---|---|---|---|---|---|
| 12 | `/estoque` | GET | 👤 | `estoque/` · `estoque_visao_geral` | `ListView` (`paginate_by=20`) | Hoje filtra **em Python** e pagina manualmente (carrega todos os produtos). Com `com_estoque()` o filtro vira `estoque_total=0` / `estoque_total__gt=0, estoque_total__lte=F('estoque_minimo')` no banco. Anotar também `num_lotes=Count('lotes')`. |
| 13 | `/estoque/entrada` | GET, POST | 👤 | `estoque/entrada/` · `estoque_entrada` | `FormView` (`EntradaForm`) → `servicos.registrar_entrada()` | `?produto_id=` pré-seleciona via `get_initial()`. Lote + Movimentacao em `transaction.atomic()`. |
| 14 | `/estoque/ajuste` | GET, POST | 🔑 | `estoque/ajuste/` · `estoque_ajuste` | `FormView` (`AjusteForm`) → `servicos.ajustar_lote()` | Seleção de lote continua via Fetch (rota 17). Usar `select_for_update()` no lote para não perder uma venda simultânea. |
| 15 | `/estoque/lote/<id>/validade` | GET, POST | 🔑 | `estoque/lotes/<int:pk>/validade/` · `lote_validade` | `UpdateView` (`ValidadeForm`, campos `data_validade` + `motivo`) | Gera Movimentacao `ajuste` com quantidade 0 (manter). |
| 16 | `/movimentacoes` | GET | 👤 | `estoque/movimentacoes/` · `movimentacao_lista` | `ListView` + `FiltroMovimentacaoForm` | `select_related('produto', 'lote', 'usuario')`. Datas de filtro interpretadas no fuso local (`make_aware`). |
| 17 | `/estoque/lotes/<produto_id>` | GET → JSON | 👤 | `api/produtos/<int:pk>/lotes/` · `api_lotes_produto` | Função → `JsonResponse` | `Lote.objects.filter(produto_id=pk).vendaveis()`. Devolver data ISO (`2026-10-01`) **e** formatada — o front hoje recebe só `dd/mm/aaaa`. |

### 2.5 `vendas_bp` — `routes/vendas.py`

| # | Rota Flask | Métodos | Perm. | Django | View Django | Observações |
|---|---|---|---|---|---|---|
| 18 | `/venda/nova` | GET | 👤 | `vendas/pdv/` · `pdv` | `TemplateView` | Só renderiza a tela; toda interação é Fetch (seção 3). |
| 18b | `/venda/nova` | POST (form + `itens_json`) | 👤 | `api/vendas/` · `api_venda_criar` | Função `POST` → `JsonResponse` (201 / 400 / 409) | **Substitui o POST de formulário.** Ver seção 3.3. |
| 19 | `/venda/<id>/recibo` | GET | 👤 | `vendas/<int:pk>/recibo/` · `venda_recibo` | `DetailView` | `prefetch_related('itens__produto', 'itens__lote')`. O agrupamento de itens feito no Jinja (`{% set itens_agrupados = {} %}`) vai para a view (`values('produto').annotate(...)`), pois o DTL não permite esse tipo de lógica. Também servir como fragmento (`?parcial=1`) para o PDV. |
| 20 | `/vendas` | GET | 👤 | `vendas/` · `venda_lista` | `ListView` (`paginate_by=20`) + filtro de datas | `select_related('usuario')`, `annotate(num_itens=Count('itens'))`. |
| 21 | `/venda/buscar-produto` | GET → JSON | 👤 | `api/produtos/busca/` · `api_busca_produto` | Função → `JsonResponse` | `Produto.objects.ativos().com_estoque().buscar(q)[:10]`. Adicionar `match_exato` quando `q == codigo_barras` (leitor de código de barras). |

### 2.6 `relatorios_bp` — `routes/relatorios.py`

| # | Rota Flask | Métodos | Perm. | Django | View Django | Observações |
|---|---|---|---|---|---|---|
| 22 | `/relatorios/estoque` | GET | 👤 | `relatorios/estoque/` · `rel_estoque` | `ListView` | Valor total no banco: `Sum(F('estoque_total') * F('preco_custo'))` via `aggregate` sobre o queryset anotado. |
| 23 | `/relatorios/reposicao` | GET | 👤 | `relatorios/reposicao/` · `rel_reposicao` | `ListView` | `Produto.objects.ativos().abaixo_do_minimo()` + anotar `qtd_compra = Greatest(F('estoque_maximo') - F('estoque_total'), 0)`. |
| 24 | `/relatorios/mais-vendidos/pdf` | GET → PDF | 👤 | `relatorios/reposicao/pdf/` · `rel_reposicao_pdf` | Função → `FileResponse(buffer, as_attachment=True, filename=...)` | **Nome errado no Flask:** a rota se chama "mais-vendidos/pdf", mas gera a *Lista de Reposição*. Renomear. Reaproveitar o queryset da rota 23; código ReportLab pode ser copiado quase sem mudanças. |
| 25 | `/relatorios/mais-vendidos` | GET | 🔑 | `relatorios/mais-vendidos/` · `rel_mais_vendidos` | `ListView` (`paginate_by=30`) | `ItemVenda.objects.filter(periodo).values('produto__id', 'produto__nome', 'produto__fabricante').annotate(qtd=Sum('quantidade'), receita=Sum('subtotal')).order_by('-qtd')`. O Flask executa a query duas vezes (`.all()` + `.paginate()`); calcular os totais com um `aggregate` separado e barato. |
| 26 | `/relatorios/lucro` | GET | 🔑 | `relatorios/lucro/` · `rel_lucro` | `ListView` | **Correção de regra:** o Flask calcula custo com `Produto.preco_custo` **atual**, então mudar o custo de um produto reescreve o lucro de vendas antigas. Usar `ItemVenda.custo_unitario` (novo campo congelado na venda): `custo=Sum(F('quantidade') * F('custo_unitario'))`. |
| 27 | `/relatorios/movimentacoes` | GET | 🔑 | `relatorios/movimentacoes/` · `rel_movimentacoes` | `ListView` (`paginate_by=30`) | Praticamente igual à rota 16 — herdar da mesma classe e trocar template/permissão. |

### 2.7 `usuarios_bp` — `routes/usuarios.py`

| # | Rota Flask | Métodos | Perm. | Django | View Django | Observações |
|---|---|---|---|---|---|---|
| 28 | `/usuarios` | GET | 🔑 | `usuarios/` · `usuario_lista` | `ListView` | |
| 29 | `/usuarios/novo` | GET, POST | 🔑 | `usuarios/novo/` · `usuario_criar` | `CreateView` (`UsuarioCriarForm`) | Senha com `validate_password` (mín. 6 hoje → configurar `MinimumLengthValidator(min_length=6)` ou subir). |
| 30 | `/usuarios/<id>/editar` | GET, POST | 🔑 | `usuarios/<int:pk>/editar/` · `usuario_editar` | `UpdateView` (`UsuarioEditarForm`, senha opcional) | Manter a regra "admin não remove o próprio perfil de admin" no `clean()`. |
| 31 | `/usuarios/<id>/toggle-ativo` | POST | 🔑 | `usuarios/<int:pk>/alternar/` · `usuario_alternar` | `View` com `post()` | Manter a regra "não desativar a própria conta". |

---

## 3. PDV sem recarregar a tela (Vanilla JS + Fetch API)

### 3.1 Problema atual

O PDV já busca produtos e lotes com `fetch`, mas **finaliza a venda com um `<form method="POST">` comum**. Consequências:

1. **Se qualquer validação falhar** (lote vencido, estoque insuficiente porque outro caixa vendeu), a rota faz `redirect` → a página recarrega e **o carrinho inteiro, que só existe em um array JS, é perdido**. O operador precisa bipar tudo de novo.
2. A tela pisca e sai do PDV para o recibo a cada venda, quebrando o fluxo de caixa.
3. O resultado de busca é montado com `innerHTML` e `${p.nome}` sem escape — um produto cadastrado com `<img onerror=...>` no nome executa script (XSS armazenado).

### 3.2 Fluxo alvo

```
[busca digitada] ──debounce 250ms + AbortController──► GET  /api/produtos/busca/?q=
[produto escolhido] ─────────────────────────────────► GET  /api/produtos/<id>/lotes/
[carrinho]  estado só no cliente (array), renderizado com <template> + textContent
[Finalizar] ────── JSON + X-CSRFToken ───────────────► POST /api/vendas/
      ├─ 201 → limpa carrinho, mostra recibo no painel lateral (GET /vendas/<id>/recibo/?parcial=1),
      │        anuncia "Venda #N registrada" em região aria-live, foco volta à busca
      ├─ 409 → mantém carrinho, destaca o item do erro (item_index), atualiza saldo do lote
      └─ 400 → mantém carrinho, mostra mensagem
```

**Onde usar Fetch (e onde não):**

| Tela | Fetch? | Motivo |
|---|---|---|
| PDV — busca, lotes, finalizar, recibo | **Sim** | Operação contínua de caixa; o estado do carrinho não pode se perder. |
| Ajuste de estoque — lista de lotes | Sim (já usa) | Select dependente. |
| Categorias — modal de edição | Opcional | Ganho pequeno; um POST normal com redirect é aceitável. |
| CRUDs, relatórios, filtros | **Não** | Formulários comuns: funcionam sem JS, histórico do navegador e URLs compartilháveis. |

### 3.3 Contrato da API de venda

**Request** — `POST /api/vendas/`

```json
{ "itens": [ { "lote_id": 12, "quantidade": 2 }, { "lote_id": 7, "quantidade": 1 } ] }
```

O cliente **não** envia preço nem `produto_id`: o produto sai do lote e o preço, do banco. (No Flask o `produto_id` vem do cliente e só é conferido contra o lote.)

**Respostas**

| Status | Corpo | Quando |
|---|---|---|
| `201` | `{"id": 57, "total": "43.80", "recibo_url": "/vendas/57/recibo/"}` | Sucesso |
| `400` | `{"erro": "Carrinho vazio."}` | JSON malformado, lista vazia, quantidade ≤ 0 |
| `409` | `{"erro": "Estoque insuficiente no lote #12 (disponível: 1).", "item_index": 0, "lote_id": 12, "disponivel": 1}` | Conflito de estoque / lote vencido / produto inativo |

### 3.4 Serviço transacional (substitui o bloco `try` de `nova_venda`)

```python
# novo_app/servicos.py
from collections import Counter
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import ItemVenda, Lote, Movimentacao, Venda


class ConflitoEstoque(Exception):
    def __init__(self, mensagem, lote_id, disponivel=0):
        super().__init__(mensagem)
        self.lote_id, self.disponivel = lote_id, disponivel


@transaction.atomic
def registrar_venda(usuario, itens):
    # Soma itens repetidos do mesmo lote ANTES de validar (com F() o saldo
    # em memória não diminui a cada item, como acontecia na sessão SQLAlchemy).
    pedido = Counter()
    for item in itens:
        pedido[int(item['lote_id'])] += int(item['quantidade'])

    # Trava as linhas dos lotes até o commit: dois caixas não vendem a mesma unidade.
    # order_by('id') evita deadlock entre transações concorrentes.
    lotes = {
        l.id: l for l in
        Lote.objects.select_for_update().select_related('produto')
        .filter(id__in=pedido).order_by('id')
    }

    venda = Venda.objects.create(usuario=usuario)
    for lote_id, qtd in pedido.items():
        lote = lotes.get(lote_id)
        if lote is None or not lote.produto.ativo:
            raise ConflitoEstoque('Lote ou produto indisponível.', lote_id)
        if lote.vencido:
            raise ConflitoEstoque(f'Lote #{lote_id} de "{lote.produto}" está vencido.', lote_id)
        if qtd > lote.quantidade:
            raise ConflitoEstoque(
                f'Estoque insuficiente no lote #{lote_id} de "{lote.produto}" '
                f'(disponível: {lote.quantidade}).', lote_id, lote.quantidade)

        Lote.objects.filter(pk=lote_id).update(quantidade=F('quantidade') - qtd)
        ItemVenda.objects.create(
            venda=venda, produto=lote.produto, lote=lote, quantidade=qtd,
            preco_unitario=lote.produto.preco_venda,
            custo_unitario=lote.produto.preco_custo,
        )
        Movimentacao.objects.create(
            produto=lote.produto, lote=lote, venda=venda, tipo=Movimentacao.Tipo.SAIDA,
            quantidade=qtd, usuario=usuario, motivo=f'Venda #{venda.pk}',
        )

    venda.recalcular_total()
    venda.save(update_fields=['total'])
    return venda
```

```python
# novo_app/views/api.py
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from ..servicos import ConflitoEstoque, registrar_venda


@login_required
@require_POST
def api_venda_criar(request):
    try:
        itens = json.loads(request.body).get('itens') or []
        assert all(int(i['quantidade']) > 0 for i in itens)
    except (ValueError, KeyError, TypeError, AttributeError, AssertionError):
        return JsonResponse({'erro': 'Dados do carrinho inválidos.'}, status=400)
    if not itens:
        return JsonResponse({'erro': 'Adicione pelo menos um produto à venda.'}, status=400)

    try:
        venda = registrar_venda(request.user, itens)
    except ConflitoEstoque as e:
        indice = next((n for n, i in enumerate(itens) if int(i['lote_id']) == e.lote_id), None)
        return JsonResponse({'erro': str(e), 'lote_id': e.lote_id, 'disponivel': e.disponivel,
                             'item_index': indice}, status=409)

    return JsonResponse({'id': venda.pk, 'total': str(venda.total),
                         'recibo_url': reverse('venda_recibo', args=[venda.pk])}, status=201)
```

> `@login_required` em uma API devolve **302 para o login**, que o `fetch` segue silenciosamente e recebe HTML. No front, tratar `resp.redirected` / `resp.headers.get('content-type')` e redirecionar para o login com aviso de sessão expirada — ou criar um decorator `login_required_json` que responde `401`.

### 3.5 Front-end (`static/novo_app/js/pdv.js`)

```js
const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
let buscaAtual;   // AbortController da busca em andamento

async function buscarProdutos(q) {
  buscaAtual?.abort();                          // descarta resposta atrasada de busca anterior
  buscaAtual = new AbortController();
  const resp = await fetch(`/api/produtos/busca/?q=${encodeURIComponent(q)}`,
                           { signal: buscaAtual.signal, headers: { Accept: 'application/json' } });
  return resp.json();
}

async function finalizarVenda() {
  btnFinalizar.disabled = true;
  btnFinalizar.setAttribute('aria-busy', 'true');
  try {
    const resp = await fetch('/api/vendas/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ itens: cart.map(i => ({ lote_id: i.lote_id, quantidade: i.quantidade })) }),
    });
    const dados = await resp.json();
    if (resp.status === 201) {
      cart.length = 0; renderCart();
      await mostrarRecibo(dados.recibo_url);            // injeta fragmento no painel lateral
      anunciar(`Venda ${dados.id} registrada. Total R$ ${fmt(Number(dados.total))}.`);
      searchInput.focus();
    } else {
      marcarItemComErro(dados.item_index, dados.disponivel);   // carrinho preservado
      anunciar(dados.erro, 'assertive');
    }
  } catch {
    anunciar('Falha de conexão. O carrinho foi mantido; tente novamente.', 'assertive');
  } finally {
    btnFinalizar.removeAttribute('aria-busy');
    btnFinalizar.disabled = cart.length === 0;
  }
}
```

Regras de implementação:

- **Nunca** montar HTML com dados do banco via `innerHTML` + template string. Usar `<template>` no HTML e preencher com `textContent`.
- Formatação monetária: `new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })` — hoje `form.html` mostra `R$ 12.50` (ponto) enquanto o PDV mostra `R$ 12,50`.
- Persistir o carrinho em `sessionStorage` a cada alteração: se a aba recarregar por acidente, a venda em andamento volta.
- Leitor de código de barras: o leitor "digita" o código e envia `Enter`. Se a API retornar `match_exato` com um único lote vendável, adicionar direto ao carrinho sem abrir o modal.
- Acessibilidade do PDV (combobox, `<dialog>`, `aria-live`): ver `melhorias_acessibilidade.md`, seção 5.

---

## 4. Permissões

```python
# novo_app/permissoes.py
from functools import wraps
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_admin


def admin_required(view):
    @wraps(view)
    def _view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not request.user.is_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return _view
```

Recomenda-se ativar `LoginRequiredMiddleware` (Django 5.1+) e marcar apenas o login com `@login_not_required`, em vez de decorar cada view.

---

## 5. Configurações relevantes (`settings.py`)

```python
AUTH_USER_MODEL = 'novo_app.Usuario'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'painel'
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_TZ = True
USE_THOUSAND_SEPARATOR = True        # {{ valor|floatformat:2 }} → 1.234,56

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',   # padrão para senhas novas
    'novo_app.hashers.WerkzeugScryptHasher',               # só para verificar as importadas
]

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {messages.ERROR: 'danger'}

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': env('DB_NAME'), 'USER': env('DB_USER'), 'PASSWORD': env('DB_PASSWORD'),
    'HOST': env('DB_HOST', default='localhost'), 'PORT': env('DB_PORT', default='5432'),
    'CONN_MAX_AGE': 60,
}}
```

O filtro manual `"%.2f"|format() → replace(".", ",")` do Jinja deixa de ser necessário: `{% load l10n %}` + `floatformat` respeitam `pt-br`.

---

## 6. Migração dos dados (SQLite → PostgreSQL)

1. `python manage.py migrate` no PostgreSQL vazio.
2. Script `manage.py importar_flask --sqlite estoque_app/instance/database.db` (management command) lendo com `sqlite3` e inserindo **na ordem das FKs**: usuarios → categorias → produtos → lotes → vendas → itens_venda → movimentacoes. Mantendo os `id`s originais.
3. Conversões durante a carga:
   - `Float` → `Decimal(str(valor)).quantize(Decimal('0.01'))`.
   - `fabricante/volume/peso/numero_lote` `NULL` → `''`; `codigo_barras` `''` → `NULL`.
   - Datas sem fuso gravadas pelo SQLite → `timezone.make_aware(dt, timezone.utc)` (o Flask grava em UTC).
   - `usuarios.senha_hash` → `password = 'werkzeug_scrypt$' + senha_hash`.
   - `itens_venda.custo_unitario` ← `produtos.preco_custo` atual (melhor aproximação; não há histórico).
   - `movimentacoes.venda_id` ← extrair de `motivo LIKE 'Venda #%'`.
   - `itens_venda.subtotal` **não** é inserido (coluna gerada).
4. Reajustar as sequences: `python manage.py sqlsequencereset novo_app | python manage.py dbshell`.
5. Conferência: contagem por tabela, `SUM(quantidade)` de lotes por produto e `SUM(total)` de vendas iguais nos dois bancos.

Volume atual (para dimensionar o teste): 2 usuários, 5 categorias, 3 produtos, 5 lotes, 6 vendas, 7 itens, 14 movimentações.

**Hasher das senhas** — testado: a senha correta valida, a errada é rejeitada e, no primeiro login, o Django regrava o hash como `pbkdf2_sha256`.

```python
# novo_app/hashers.py
import hashlib
import hmac

from django.contrib.auth.hashers import BasePasswordHasher


class WerkzeugScryptHasher(BasePasswordHasher):
    """Verifica hashes 'scrypt:N:r:p$salt$hex' gerados pelo Werkzeug (Flask).

    Os hashes importados recebem o prefixo 'werkzeug_scrypt$'. No primeiro login
    bem-sucedido o Django regrava a senha com o hasher padrão (PBKDF2).
    """
    algorithm = 'werkzeug_scrypt'

    def verify(self, password, encoded):
        _, metodo, salt, hash_hex = encoded.split('$', 3)
        _, n, r, p = (int(x) if x.isdigit() else x for x in metodo.split(':'))
        calculado = hashlib.scrypt(
            password.encode(), salt=salt.encode(), n=n, r=r, p=p,
            maxmem=132 * n * r * p, dklen=64,
        )
        return hmac.compare_digest(calculado.hex(), hash_hex)

    def safe_summary(self, encoded):
        return {'algorithm': self.algorithm}

    def must_update(self, encoded):
        return True
```

---

## 7. Problemas encontrados no Flask que a migração deve corrigir

| # | Onde | Problema | Correção no Django |
|---|---|---|---|
| 1 | `vendas.py:14-88` | Erro na venda recarrega a página e perde o carrinho | API JSON + Fetch (seção 3) |
| 2 | `vendas.py:43-56` | Sem trava de linha: dois caixas podem vender a última unidade do mesmo lote | `select_for_update()` + `F()` |
| 3 | `nova_venda.html:207-228, 278-288` | XSS: nomes de produto inseridos com `innerHTML` sem escape | `<template>` + `textContent` |
| 4 | `categorias.html:89`, `lista.html:119`, `usuarios/lista.html:67` | Nome dentro de string JS em `onclick`/`confirm` — apóstrofo quebra o script | `data-*` / `json_script` + `<dialog>` |
| 5 | `auth.py:21-22` | Open redirect no parâmetro `next` | `LoginView` valida o host |
| 6 | `auth.py:29` | Logout por GET (pode ser disparado por uma `<img>` de outro site) | `LogoutView` via POST |
| 7 | `main.py:16` | "Vendas hoje" usa meia-noite UTC | `TIME_ZONE` + `timezone.localdate()` |
| 8 | `relatorios.py:273-274` | Lucro calculado com o custo atual do produto | `ItemVenda.custo_unitario` |
| 9 | `models.py` (Float) | Valores monetários em ponto flutuante | `DecimalField` |
| 10 | `relatorios.py:97` | Rota `mais-vendidos/pdf` gera o PDF de reposição | Renomear para `relatorios/reposicao/pdf/` |
| 11 | `relatorios.py:8-14`, `usuarios.py:9-13`, `utils.py` | Três implementações diferentes de "somente admin" | `AdminRequiredMixin` único |
| 12 | `estoque.py:26-38`, `main.py:21-22`, `relatorios.py:39` | `estoque_atual` percorre os lotes em Python para cada produto (N+1) | `ProdutoQuerySet.com_estoque()` |
| 13 | `Produto.estoque_atual` | Soma **inclusive lotes vencidos**: o painel pode dizer "estoque OK" com todo o saldo vencido | Decidir a regra com o cliente; sugestão: anotar também `estoque_vendavel` (só lotes válidos) e usá-lo nos alertas |
| 14 | `estoque.py:30` vs `main.py:22` | "Estoque baixo" exclui zerados na tela de Estoque (`0 < est`) mas inclui no painel | Uma só definição no `QuerySet` |
