# Especificação Técnica — Empório BR em Django

| | |
|---|---|
| **Sistema** | Gestão de Estoque na Adega — Empório BR (Santos-SP) |
| **Origem** | `estoque_app/` — Flask 3 + SQLAlchemy + SQLite |
| **Destino** | Django ≥ 5.2 (validado em 6.1) + PostgreSQL ≥ 14 (DDL gerado para 16) + psycopg 3 |
| **Front-end** | Django Templates + Bootstrap 5.3 + Vanilla JS (ES modules, Fetch API) — sem framework JS |
| **Acessibilidade** | WCAG 2.2 nível AA |
| **Documentos consolidados** | `novo_app/models.py`, `novo_app/hashers.py`, `planejamento_views.md`, `melhorias_acessibilidade.md` |

Este documento é a referência de implementação. Justificativas, bugs do sistema Flask e o passo a passo da migração de dados continuam em `planejamento_views.md`; o detalhamento de cada problema de acessibilidade continua em `melhorias_acessibilidade.md`.

---

## 1. Arquitetura de pastas

### 1.1 Divisão em apps

`novo_app/models.py` é dividido em cinco apps por domínio. Os nomes de tabela (`db_table`) não mudam, então o esquema da seção 2 vale igual.

| App | Responsabilidade | Modelos | Equivalente Flask |
|---|---|---|---|
| `core` | Autenticação, usuários, painel, layout base, permissões, componentes compartilhados | `Usuario` | `auth_bp`, `main_bp`, `usuarios_bp`, `utils.py` |
| `catalogo` | Categorias e produtos | `Categoria`, `Produto` | `produtos_bp` |
| `estoque` | Lotes, entradas, ajustes, validade, histórico | `Lote`, `Movimentacao` | `estoque_bp` |
| `vendas` | PDV, API do caixa, recibo, histórico de vendas | `Venda`, `ItemVenda` | `vendas_bp` |
| `relatorios` | 5 relatórios + PDF (sem modelos próprios) | — | `relatorios_bp` |

**Dependências entre apps:**

```
core ◄── catalogo ◄── estoque ◄──► vendas
  ▲                      ▲           ▲
  └──────── relatorios ──┴───────────┘   (somente leitura)
```

`estoque` ↔ `vendas` é circular no nível de FK (`Movimentacao.venda → Venda` e `ItemVenda.lote → Lote`). As FKs usam referência por string (`'vendas.Venda'`, `'estoque.Lote'`), e o `makemigrations` resolve isso sozinho, gerando `estoque/0001_initial` + `estoque/0002_initial` (adiciona `venda_id` depois de `vendas/0001`). **Testado:** `check`, `makemigrations` e `migrate` sem erros. No código Python, `vendas/servicos.py` importa de `estoque.models`, e `estoque` **nunca** importa de `vendas` em nível de módulo.

### 1.2 Árvore do projeto

```
emporio/                                  # raiz do repositório Django
├── manage.py
├── pyproject.toml                        # dependências (django, psycopg[binary], reportlab, django-environ)
├── .env.example                          # SECRET_KEY, DATABASE_URL, DEBUG, ALLOWED_HOSTS
│
├── config/                               # projeto Django (substitui config.py + app factory)
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py                       # apps, middleware, auth, i18n, static, messages
│   │   ├── dev.py                        # DEBUG=True, debug-toolbar opcional
│   │   └── prod.py                       # segurança HTTPS, logging, CONN_MAX_AGE
│   ├── urls.py                           # include() de cada app com namespace
│   ├── wsgi.py
│   └── asgi.py
│
├── core/
│   ├── models.py                         # Usuario, UsuarioManager
│   ├── hashers.py                        # WerkzeugScryptHasher (senhas importadas do Flask)
│   ├── permissoes.py                     # AdminRequiredMixin, @admin_required, @login_required_json
│   ├── forms.py                          # AcessivelMixin, UsuarioCriarForm, UsuarioEditarForm
│   ├── views.py                          # PainelView, Usuario*View
│   ├── urls.py                           # app_name = 'core'
│   ├── context_processors.py             # secao_ativa (menu com aria-current)
│   ├── templatetags/
│   │   └── ui.py                         # {% icone %}, |brl (moeda pt-BR), |icone_mensagem
│   ├── management/commands/
│   │   └── importar_flask.py             # carga SQLite → PostgreSQL
│   ├── templates/
│   │   ├── base.html                     # skip link, <nav>, topbar, região de mensagens, <main>
│   │   ├── registration/login.html
│   │   └── core/
│   │       ├── painel.html
│   │       ├── usuario_lista.html
│   │       ├── usuario_form.html
│   │       └── componentes/              # includes reutilizáveis e acessíveis
│   │           ├── _campo.html           # label + input + dica + erro (aria-describedby/invalid)
│   │           ├── _resumo_erros.html    # role="alert", links para os campos
│   │           ├── _paginacao.html       # <nav aria-label="Paginação">, aria-current
│   │           ├── _tabela_vazia.html    # .empty-state
│   │           ├── _dialogo_confirmar.html  # <dialog> de confirmação
│   │           └── _icone.html           # <i class="bi …" aria-hidden="true">
│   ├── static/core/
│   │   ├── css/styles.css                # tema escuro com tokens corrigidos (seção 3.5)
│   │   └── js/
│   │       ├── base.js                   # menu lateral (aria-expanded, inert), mensagens
│   │       ├── api.js                    # wrapper do fetch: CSRF, JSON, sessão expirada
│   │       ├── anunciador.js             # escreve nas regiões aria-live
│   │       └── dialogo.js                # abre/fecha <dialog>, devolve o foco
│   └── tests/
│
├── catalogo/
│   ├── models.py                         # Categoria, Produto, ProdutoQuerySet
│   ├── forms.py                          # CategoriaForm, ProdutoForm, FiltroProdutoForm
│   ├── views.py
│   ├── urls.py                           # app_name = 'catalogo'
│   ├── admin.py
│   ├── templates/catalogo/
│   │   ├── categoria_lista.html
│   │   ├── produto_lista.html
│   │   └── produto_form.html             # <fieldset>/<legend>, <output> do preço de venda
│   ├── static/catalogo/js/preco.js       # cálculo ao vivo do preço (Intl.NumberFormat)
│   └── tests/
│
├── estoque/
│   ├── models.py                         # Lote, LoteQuerySet, Movimentacao
│   ├── servicos.py                       # registrar_entrada, ajustar_lote, alterar_validade
│   ├── forms.py                          # EntradaForm, AjusteForm, ValidadeForm, FiltroMovimentacaoForm
│   ├── views.py
│   ├── api.py                            # JSON: lotes vendáveis de um produto
│   ├── urls.py                           # app_name = 'estoque'
│   ├── templates/estoque/
│   │   ├── visao_geral.html
│   │   ├── entrada_form.html
│   │   ├── ajuste_form.html
│   │   ├── validade_form.html
│   │   └── movimentacao_lista.html
│   ├── static/estoque/js/ajuste.js       # select dependente produto → lote (Fetch)
│   └── tests/
│
├── vendas/
│   ├── models.py                         # Venda, ItemVenda
│   ├── servicos.py                       # registrar_venda (atomic + select_for_update), ConflitoEstoque
│   ├── views.py                          # PdvView, ReciboView, VendaListaView
│   ├── api.py                            # JSON: busca de produto, criar venda
│   ├── urls.py                           # app_name = 'vendas'
│   ├── templates/vendas/
│   │   ├── pdv.html                      # frente de caixa (seção 3.4)
│   │   ├── recibo.html                   # página completa (estende base.html)
│   │   ├── _recibo.html                  # fragmento usado no painel do PDV
│   │   └── venda_lista.html
│   ├── static/vendas/js/pdv/
│   │   ├── main.js                       # orquestra os módulos abaixo
│   │   ├── busca.js                      # combobox + listbox
│   │   ├── dialogo-lote.js               # <dialog> de lote e quantidade
│   │   ├── carrinho.js                   # estado, render por linha, sessionStorage
│   │   ├── finalizar.js                  # POST /api/vendas/, tratamento 201/400/409
│   │   └── atalhos.js                    # F2, F9, Esc
│   └── tests/
│       ├── test_servicos.py              # concorrência, rollback, itens repetidos
│       └── test_api.py
│
├── relatorios/
│   ├── consultas.py                      # querysets anotados reutilizados por HTML e PDF
│   ├── pdf.py                            # ReportLab (lista de reposição)
│   ├── views.py
│   ├── urls.py                           # app_name = 'relatorios'
│   ├── templates/relatorios/
│   │   ├── _abas.html                    # <nav aria-label="Relatórios"> + aria-current
│   │   ├── _filtro_periodo.html          # <fieldset> De/Até com labels visíveis
│   │   ├── estoque.html
│   │   ├── reposicao.html
│   │   ├── mais_vendidos.html
│   │   ├── lucro.html
│   │   └── movimentacoes.html
│   └── tests/
│
└── e2e/                                  # Playwright + @axe-core/playwright
    ├── test_pdv_teclado.py               # venda completa sem mouse (critério de aceite)
    └── test_axe_paginas.py               # varredura axe nas URLs principais
```

### 1.3 Configurações obrigatórias (`config/settings/base.py`)

```python
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'django.contrib.humanize',
    'core', 'catalogo', 'estoque', 'vendas', 'relatorios',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.LoginRequiredMiddleware',   # tudo exige login por padrão
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTH_USER_MODEL = 'core.Usuario'
LOGIN_URL = 'core:login'
LOGIN_REDIRECT_URL = 'core:painel'
LOGOUT_REDIRECT_URL = 'core:login'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'core.hashers.WerkzeugScryptHasher',
]
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

DATABASES = {'default': env.db('DATABASE_URL')}       # postgres://usuario:senha@host:5432/emporio
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['ATOMIC_REQUESTS'] = False       # transações explícitas nos serviços

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {messages.ERROR: 'danger'}

CSRF_COOKIE_HTTPONLY = True    # o JS lê o token do <input name="csrfmiddlewaretoken">, não do cookie
SESSION_COOKIE_AGE = 60 * 60 * 10                     # um turno de caixa
```

### 1.4 Convenções

| Tema | Regra |
|---|---|
| Idioma do código | Português (modelos, campos, views, mensagens), como no projeto Flask |
| Views | CBV genéricas para CRUD/listas; funções para endpoints JSON |
| Regras de negócio | Somente em `servicos.py` / `QuerySet`; views apenas orquestram |
| URLs | Sempre com namespace: `{% url 'vendas:pdv' %}` |
| Templates | `{% extends 'base.html' %}`; nenhum `style=""` nem `onclick=""` inline |
| JS | ES modules (`<script type="module">`), um arquivo por componente, sem `innerHTML` com dados do servidor |
| Dinheiro | `Decimal` no Python, `numeric` no banco, `Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'})` no JS, filtro `|brl` no template |
| Datas | Armazenadas em UTC (`timestamptz`), exibidas no fuso `America/Sao_Paulo`; datas "de hoje" com `timezone.localdate()` |
| Commits | Português, imperativo (ex.: "Adicionar API de venda do PDV") |

---

## 2. Esquema do banco de dados (PostgreSQL)

Gerado a partir de `novo_app/models.py` pelo schema editor do Django 6.1 com o backend PostgreSQL (DDL completo em 2.9).

**Convenções do esquema:**
- Chaves primárias: `bigint GENERATED BY DEFAULT AS IDENTITY` (`DEFAULT_AUTO_FIELD = BigAutoField`).
- FKs: `DEFERRABLE INITIALLY DEFERRED` e índice automático em cada coluna de FK.
- `on_delete` (PROTECT/CASCADE) é aplicado **pelo Django**. No banco a FK fica com `NO ACTION`, o que também impede apagar uma linha referenciada.
- `DEFAULT`s são aplicados pelo Django ao criar o objeto, não no DDL. As colunas marcadas com † são as que o script de importação deve preencher explicitamente.
- Textos opcionais usam `''` (NOT NULL), exceto `codigo_barras` (ver 2.3).

### 2.1 Diagrama de relacionamentos

```
usuarios ──1:N──► vendas ──1:N──► itens_venda ◄──N:1── lotes ◄──N:1── produtos ◄──N:1── categorias
    │                │                  │                  ▲                ▲
    │                │                  └──────N:1─────────┼────────────────┘
    │                └──1:N──► movimentacoes ──N:1─────────┘ (lote, opcional)
    └──────────1:N───────────► movimentacoes ──N:1──► produtos
```

| FK | De → Para | Nulo | `on_delete` | `related_name` |
|---|---|---|---|---|
| `produtos.categoria_id` | Produto → Categoria | não | PROTECT | `produtos` |
| `lotes.produto_id` | Lote → Produto | não | PROTECT | `lotes` |
| `movimentacoes.produto_id` | Movimentacao → Produto | não | PROTECT | `movimentacoes` |
| `movimentacoes.lote_id` | Movimentacao → Lote | sim | PROTECT | `movimentacoes` |
| `movimentacoes.usuario_id` | Movimentacao → Usuario | não | PROTECT | `movimentacoes` |
| `movimentacoes.venda_id` | Movimentacao → Venda | sim | PROTECT | `movimentacoes` |
| `vendas.usuario_id` | Venda → Usuario | não | PROTECT | `vendas` |
| `itens_venda.venda_id` | ItemVenda → Venda | não | **CASCADE** | `itens` |
| `itens_venda.produto_id` | ItemVenda → Produto | não | PROTECT | `itens_venda` |
| `itens_venda.lote_id` | ItemVenda → Lote | sim | PROTECT | `itens_venda` |

### 2.2 `usuarios` — app `core`, modelo `Usuario(AbstractBaseUser)`

| Coluna | Tipo PostgreSQL | Nulo | Default (Django) | Restrições / índices | Origem Flask | Observação |
|---|---|---|---|---|---|---|
| `id` | `bigint` identity | não | auto | PK | `id integer` | |
| `nome` | `varchar(100)` | não | — | `UNIQUE`; índice `varchar_pattern_ops` | `nome` | `USERNAME_FIELD`. No Flask a unicidade só existia no código |
| `password` | `varchar(255)` | não | — | | `senha_hash` | 255 porque o hash Werkzeug importado tem 178 caracteres; importado como `werkzeug_scrypt$<hash>` e regravado como PBKDF2 no 1º login |
| `perfil` | `varchar(20)` | não | `'operador'` | choices `admin` \| `operador` | `perfil` | |
| `ativo` | `boolean` | não | `true` † | | `ativo` | Exposto como `is_active` (bloqueia login) |
| `last_login` | `timestamptz` | sim | `NULL` | | — | Novo, vem do `AbstractBaseUser` |

Propriedades Python (sem coluna): `is_admin`, `is_active`, `is_staff`.

### 2.3 `categorias` e `produtos` — app `catalogo`

**`categorias` — `Categoria`**

| Coluna | Tipo | Nulo | Default | Restrições / índices | Origem Flask | Observação |
|---|---|---|---|---|---|---|
| `id` | `bigint` identity | não | auto | PK | `id` | |
| `nome` | `varchar(80)` | não | — | `UNIQUE INDEX categoria_nome_unico_ci ON (LOWER(nome))` | `nome UNIQUE` | Unicidade agora ignora maiúsculas/minúsculas |
| `ativo` | `boolean` | não | `true` † | | `ativo` | |

**`produtos` — `Produto`**

| Coluna | Tipo | Nulo | Default | Restrições / índices | Origem Flask | Observação |
|---|---|---|---|---|---|---|
| `id` | `bigint` identity | não | auto | PK | `id` | |
| `nome` | `varchar(150)` | não | — | índice composto `(ativo, nome)` | `nome` | |
| `categoria_id` | `bigint` | não | — | FK → `categorias.id`; índice | `categoria_id` | |
| `fabricante` | `varchar(100)` | não | `''` | | `fabricante NULL` | `NULL` → `''` na importação |
| `volume` | `varchar(30)` | não | `''` | | `volume NULL` | idem |
| `peso` | `varchar(30)` | não | `''` | | `peso NULL` | idem |
| `codigo_barras` | `varchar(50)` | **sim** | `NULL` | `UNIQUE`; índice `varchar_pattern_ops` | `codigo_barras UNIQUE` | Única coluna de texto que aceita `NULL`, para que vários produtos sem código não violem o `UNIQUE`. `''` → `NULL` na importação |
| `margem_lucro` | `numeric(6,2)` | não | `30.00` † | `CHECK (margem_lucro >= 0)` | `margem_lucro FLOAT` | Percentual |
| `preco_custo` | `numeric(10,2)` | não | `0.00` † | `CHECK (preco_custo >= 0)` | `preco_custo FLOAT` | |
| `preco_venda` | `numeric(10,2)` | não | `0.00` | `editable=False` | `preco_venda FLOAT` | Recalculado em todo `save()`: `custo × (1 + margem/100)`, arredondamento `ROUND_HALF_UP` |
| `estoque_minimo` | `integer` | não | `5` † | `CHECK (>= 0)` | `estoque_minimo` | |
| `estoque_maximo` | `integer` | não | `100` † | `CHECK (>= 0)`; `CHECK (estoque_maximo >= estoque_minimo)` | `estoque_maximo` | |
| `ativo` | `boolean` | não | `true` † | | `ativo` | |

Valores calculados (sem coluna), via `ProdutoQuerySet`:

| Método | Anotação | SQL equivalente |
|---|---|---|
| `com_estoque()` | `estoque_total` | `COALESCE(SUM(lotes.quantidade), 0)` |
| `abaixo_do_minimo()` | — | `… HAVING estoque_total <= estoque_minimo` |
| `buscar(termo)` | — | `nome ILIKE %t% OR fabricante ILIKE %t% OR codigo_barras ILIKE %t%` |

### 2.4 `lotes` — app `estoque`, modelo `Lote`

| Coluna | Tipo | Nulo | Default | Restrições / índices | Origem Flask | Observação |
|---|---|---|---|---|---|---|
| `id` | `bigint` identity | não | auto | PK | `id` | |
| `produto_id` | `bigint` | não | — | FK → `produtos.id`; índice; índice composto `(produto_id, data_validade)` | `produto_id` | |
| `numero_lote` | `varchar(60)` | não | `''` | | `numero_lote NULL` | Código impresso pelo fabricante |
| `quantidade` | `integer` | não | `0` † | `CHECK (quantidade >= 0)` | `quantidade` | Saldo atual do lote. O banco impede saldo negativo |
| `data_validade` | `date` | sim | `NULL` | | `data_validade` | `NULL` = produto sem validade |
| `data_entrada` | `timestamptz` | não | `now()` † | | `data_entrada DATETIME` | Importação: data sem fuso tratada como UTC |

`LoteQuerySet.vendaveis()`: `quantidade > 0 AND (data_validade IS NULL OR data_validade >= hoje_local) ORDER BY data_validade ASC NULLS LAST, id` (PEPS).
Propriedades: `vencido`, `proximo_vencimento` (≤ 30 dias).

### 2.5 `movimentacoes` — app `estoque`, modelo `Movimentacao`

| Coluna | Tipo | Nulo | Default | Restrições / índices | Origem Flask | Observação |
|---|---|---|---|---|---|---|
| `id` | `bigint` identity | não | auto | PK | `id` | |
| `produto_id` | `bigint` | não | — | FK → `produtos.id`; índice | `produto_id` | |
| `lote_id` | `bigint` | sim | `NULL` | FK → `lotes.id`; índice | `lote_id` | |
| `tipo` | `varchar(20)` | não | — | choices `entrada` \| `saida` \| `ajuste`; índice `(tipo, data DESC)` | `tipo` | |
| `quantidade` | `integer` | não | — | **sem** `CHECK` de sinal | `quantidade` | Ajuste grava a diferença, que pode ser negativa; ajuste de validade grava `0` |
| `data` | `timestamptz` | não | `now()` † | índice `(data DESC)` | `data` | |
| `usuario_id` | `bigint` | não | — | FK → `usuarios.id`; índice | `usuario_id` | Trilha de auditoria |
| `motivo` | `varchar(200)` | não | `''` | | `motivo NULL` | |
| `venda_id` | `bigint` | sim | `NULL` | FK → `vendas.id`; índice | — | **Novo.** Na importação, extraído de `motivo LIKE 'Venda #%'` |

### 2.6 `vendas` — app `vendas`, modelo `Venda`

| Coluna | Tipo | Nulo | Default | Restrições / índices | Origem Flask | Observação |
|---|---|---|---|---|---|---|
| `id` | `bigint` identity | não | auto | PK | `id` | Número exibido no recibo |
| `data` | `timestamptz` | não | `now()` † | índice `(data DESC)` | `data` | |
| `usuario_id` | `bigint` | não | — | FK → `usuarios.id`; índice | `usuario_id` | Operador do caixa |
| `total` | `numeric(12,2)` | não | `0.00` † | | `total FLOAT` | Gravado por `recalcular_total()` = `SUM(itens_venda.subtotal)`, na mesma transação |

### 2.7 `itens_venda` — app `vendas`, modelo `ItemVenda`

| Coluna | Tipo | Nulo | Default | Restrições / índices | Origem Flask | Observação |
|---|---|---|---|---|---|---|
| `id` | `bigint` identity | não | auto | PK | `id` | |
| `venda_id` | `bigint` | não | — | FK → `vendas.id` (CASCADE); índice | `venda_id` | |
| `produto_id` | `bigint` | não | — | FK → `produtos.id`; índice | `produto_id` | Derivado do lote no servidor, nunca vem do cliente |
| `lote_id` | `bigint` | sim | `NULL` | FK → `lotes.id`; índice | `lote_id` | |
| `quantidade` | `integer` | não | — | `CHECK (quantidade >= 0)`; `CHECK (quantidade > 0)` | `quantidade` | |
| `preco_unitario` | `numeric(10,2)` | não | — | | `preco_unitario FLOAT` | Preço de venda congelado no momento da venda |
| `custo_unitario` | `numeric(10,2)` | não | `0.00` † | | — | **Novo.** Custo congelado; base do relatório de lucro. Importação: `produtos.preco_custo` atual |
| `subtotal` | `numeric(12,2)` | — | — | `GENERATED ALWAYS AS (quantidade * preco_unitario) STORED` | propriedade Python | Coluna gerada pelo banco. **Não** incluir em `INSERT` |

### 2.8 Resumo de índices

| Tabela | Índice | Colunas | Uso |
|---|---|---|---|
| `usuarios` | `UNIQUE` + `_like` | `nome` | login |
| `categorias` | `categoria_nome_unico_ci` (único) | `LOWER(nome)` | unicidade |
| `produtos` | `produtos_ativo_…_idx` | `ativo, nome` | listas e busca do PDV |
| `produtos` | `UNIQUE` + `_like` | `codigo_barras` | leitor de código de barras |
| `lotes` | `lotes_produto_…_idx` | `produto_id, data_validade` | PEPS / lotes vendáveis |
| `movimentacoes` | `…_data_…_idx` | `data DESC` | histórico |
| `movimentacoes` | `…_tipo_…_idx` | `tipo, data DESC` | filtro por tipo |
| `vendas` | `vendas_data_…_idx` | `data DESC` | histórico, painel, relatórios por período |
| todas | automático | cada coluna FK | joins |

### 2.9 DDL completo (PostgreSQL 16)

```sql
CREATE TABLE "usuarios" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "last_login" timestamp with time zone NULL, "nome" varchar(100) NOT NULL UNIQUE, "perfil" varchar(20) NOT NULL, "ativo" boolean NOT NULL, "password" varchar(255) NOT NULL);
CREATE TABLE "categorias" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "nome" varchar(80) NOT NULL, "ativo" boolean NOT NULL);
CREATE TABLE "produtos" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "nome" varchar(150) NOT NULL, "categoria_id" bigint NOT NULL, "fabricante" varchar(100) NOT NULL, "volume" varchar(30) NOT NULL, "peso" varchar(30) NOT NULL, "codigo_barras" varchar(50) NULL UNIQUE, "margem_lucro" numeric(6, 2) NOT NULL, "preco_custo" numeric(10, 2) NOT NULL, "preco_venda" numeric(10, 2) NOT NULL, "estoque_minimo" integer NOT NULL CHECK ("estoque_minimo" >= 0), "estoque_maximo" integer NOT NULL CHECK ("estoque_maximo" >= 0), "ativo" boolean NOT NULL, CONSTRAINT "produto_estoque_max_gte_min" CHECK ("estoque_maximo" >= ("estoque_minimo")), CONSTRAINT "produto_preco_custo_nao_negativo" CHECK ("preco_custo" >= 0), CONSTRAINT "produto_margem_nao_negativa" CHECK ("margem_lucro" >= 0));
CREATE TABLE "lotes" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "produto_id" bigint NOT NULL, "numero_lote" varchar(60) NOT NULL, "quantidade" integer NOT NULL CHECK ("quantidade" >= 0), "data_validade" date NULL, "data_entrada" timestamp with time zone NOT NULL);
CREATE TABLE "movimentacoes" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "produto_id" bigint NOT NULL, "lote_id" bigint NULL, "tipo" varchar(20) NOT NULL, "quantidade" integer NOT NULL, "data" timestamp with time zone NOT NULL, "usuario_id" bigint NOT NULL, "motivo" varchar(200) NOT NULL, "venda_id" bigint NULL);
CREATE TABLE "vendas" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "data" timestamp with time zone NOT NULL, "usuario_id" bigint NOT NULL, "total" numeric(12, 2) NOT NULL);
CREATE TABLE "itens_venda" ("id" bigint NOT NULL PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY, "venda_id" bigint NOT NULL, "produto_id" bigint NOT NULL, "lote_id" bigint NULL, "quantidade" integer NOT NULL CHECK ("quantidade" >= 0), "preco_unitario" numeric(10, 2) NOT NULL, "custo_unitario" numeric(10, 2) NOT NULL, "subtotal" numeric(12, 2) GENERATED ALWAYS AS (("quantidade" * "preco_unitario")) STORED, CONSTRAINT "item_venda_quantidade_positiva" CHECK ("quantidade" > 0));

CREATE INDEX "usuarios_nome_d429eb95_like" ON "usuarios" ("nome" varchar_pattern_ops);
CREATE UNIQUE INDEX "categoria_nome_unico_ci" ON "categorias" ((LOWER("nome")));

ALTER TABLE "produtos" ADD CONSTRAINT "produtos_categoria_id_b7177d63_fk_categorias_id" FOREIGN KEY ("categoria_id") REFERENCES "categorias" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "produtos_categoria_id_b7177d63" ON "produtos" ("categoria_id");
CREATE INDEX "produtos_codigo_barras_0db5584e_like" ON "produtos" ("codigo_barras" varchar_pattern_ops);
CREATE INDEX "produtos_ativo_f9c320_idx" ON "produtos" ("ativo", "nome");

ALTER TABLE "lotes" ADD CONSTRAINT "lotes_produto_id_f88f2530_fk_produtos_id" FOREIGN KEY ("produto_id") REFERENCES "produtos" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "lotes_produto_id_f88f2530" ON "lotes" ("produto_id");
CREATE INDEX "lotes_produto_b9987d_idx" ON "lotes" ("produto_id", "data_validade");

ALTER TABLE "movimentacoes" ADD CONSTRAINT "movimentacoes_produto_id_c60f7344_fk_produtos_id" FOREIGN KEY ("produto_id") REFERENCES "produtos" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "movimentacoes" ADD CONSTRAINT "movimentacoes_lote_id_c9cd6dce_fk_lotes_id" FOREIGN KEY ("lote_id") REFERENCES "lotes" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "movimentacoes" ADD CONSTRAINT "movimentacoes_usuario_id_897a922e_fk_usuarios_id" FOREIGN KEY ("usuario_id") REFERENCES "usuarios" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "movimentacoes" ADD CONSTRAINT "movimentacoes_venda_id_1ff276a4_fk_vendas_id" FOREIGN KEY ("venda_id") REFERENCES "vendas" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "movimentacoes_produto_id_c60f7344" ON "movimentacoes" ("produto_id");
CREATE INDEX "movimentacoes_lote_id_c9cd6dce" ON "movimentacoes" ("lote_id");
CREATE INDEX "movimentacoes_usuario_id_897a922e" ON "movimentacoes" ("usuario_id");
CREATE INDEX "movimentacoes_venda_id_1ff276a4" ON "movimentacoes" ("venda_id");
CREATE INDEX "movimentaco_data_36fd65_idx" ON "movimentacoes" ("data" DESC);
CREATE INDEX "movimentaco_tipo_6a3450_idx" ON "movimentacoes" ("tipo", "data" DESC);

ALTER TABLE "vendas" ADD CONSTRAINT "vendas_usuario_id_950310a9_fk_usuarios_id" FOREIGN KEY ("usuario_id") REFERENCES "usuarios" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "vendas_usuario_id_950310a9" ON "vendas" ("usuario_id");
CREATE INDEX "vendas_data_d90030_idx" ON "vendas" ("data" DESC);

ALTER TABLE "itens_venda" ADD CONSTRAINT "itens_venda_venda_id_2fd7311d_fk_vendas_id" FOREIGN KEY ("venda_id") REFERENCES "vendas" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "itens_venda" ADD CONSTRAINT "itens_venda_produto_id_09810612_fk_produtos_id" FOREIGN KEY ("produto_id") REFERENCES "produtos" ("id") DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE "itens_venda" ADD CONSTRAINT "itens_venda_lote_id_e213dc44_fk_lotes_id" FOREIGN KEY ("lote_id") REFERENCES "lotes" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "itens_venda_venda_id_2fd7311d" ON "itens_venda" ("venda_id");
CREATE INDEX "itens_venda_produto_id_09810612" ON "itens_venda" ("produto_id");
CREATE INDEX "itens_venda_lote_id_e213dc44" ON "itens_venda" ("lote_id");
```

> Os sufixos hexadecimais dos nomes de índice/constraint são gerados pelo Django e podem mudar depois da divisão em apps. Os nomes definidos explicitamente no modelo (`categoria_nome_unico_ci`, `produto_*`, `item_venda_*`) não mudam.

---

## 3. Endpoints, views e interface da frente de caixa

Legenda: 🔓 público · 👤 logado (padrão via `LoginRequiredMiddleware`) · 🔑 admin (`AdminRequiredMixin`, responde 403)

### 3.1 Páginas (HTML)

#### `core` — `config/urls.py` inclui `core.urls` na raiz

| URL | Nome | Métodos | Perm. | View | Template | Flask |
|---|---|---|---|---|---|---|
| `/` | `core:inicio` | GET | 👤 | `RedirectView(pattern_name='core:painel')` | — | `/` |
| `/login/` | `core:login` | GET, POST | 🔓 | `LoginView` (`redirect_authenticated_user=True`, `@login_not_required`) | `registration/login.html` | `/login` |
| `/logout/` | `core:logout` | **POST** | 👤 | `LogoutView` | — | `/logout` (era GET) |
| `/painel/` | `core:painel` | GET | 👤 | `PainelView(TemplateView)` | `core/painel.html` | `/dashboard` |
| `/usuarios/` | `core:usuario_lista` | GET | 🔑 | `UsuarioListView` | `core/usuario_lista.html` | `/usuarios` |
| `/usuarios/novo/` | `core:usuario_criar` | GET, POST | 🔑 | `UsuarioCreateView` | `core/usuario_form.html` | `/usuarios/novo` |
| `/usuarios/<pk>/editar/` | `core:usuario_editar` | GET, POST | 🔑 | `UsuarioUpdateView` | `core/usuario_form.html` | `/usuarios/<id>/editar` |
| `/usuarios/<pk>/alternar/` | `core:usuario_alternar` | POST | 🔑 | `UsuarioAlternarView(View)` | — | `/usuarios/<id>/toggle-ativo` |

#### `catalogo` — prefixo `/catalogo/`

| URL | Nome | Métodos | Perm. | View | Template | Flask |
|---|---|---|---|---|---|---|
| `/catalogo/categorias/` | `catalogo:categoria_lista` | GET | 👤 | `CategoriaListView` (anota `num_produtos`) | `catalogo/categoria_lista.html` | `/categorias` |
| `/catalogo/categorias/nova/` | `catalogo:categoria_criar` | POST | 🔑 | `CategoriaCreateView` | (form inline na lista) | `/categoria/nova` |
| `/catalogo/categorias/<pk>/editar/` | `catalogo:categoria_editar` | POST | 🔑 | `CategoriaUpdateView` | (`<dialog>` na lista) | `/categoria/<id>/editar` |
| `/catalogo/categorias/<pk>/alternar/` | `catalogo:categoria_alternar` | POST | 🔑 | `CategoriaAlternarView` | — | `/categoria/<id>/toggle` |
| `/catalogo/produtos/` | `catalogo:produto_lista` | GET | 👤 | `ProdutoListView` (`paginate_by=15`) | `catalogo/produto_lista.html` | `/produtos` |
| `/catalogo/produtos/novo/` | `catalogo:produto_criar` | GET, POST | 🔑 | `ProdutoCreateView` | `catalogo/produto_form.html` | `/produto/novo` |
| `/catalogo/produtos/<pk>/editar/` | `catalogo:produto_editar` | GET, POST | 🔑 | `ProdutoUpdateView` | `catalogo/produto_form.html` | `/produto/<id>/editar` |
| `/catalogo/produtos/<pk>/alternar/` | `catalogo:produto_alternar` | POST | 🔑 | `ProdutoAlternarView` | — | `/produto/<id>/toggle` |

#### `estoque` — prefixo `/estoque/`

| URL | Nome | Métodos | Perm. | View | Template | Flask |
|---|---|---|---|---|---|---|
| `/estoque/` | `estoque:visao_geral` | GET | 👤 | `VisaoGeralView(ListView)` (`paginate_by=20`, filtro no banco) | `estoque/visao_geral.html` | `/estoque` |
| `/estoque/entrada/` | `estoque:entrada` | GET, POST | 👤 | `EntradaView(FormView)` → `servicos.registrar_entrada` | `estoque/entrada_form.html` | `/estoque/entrada` |
| `/estoque/ajuste/` | `estoque:ajuste` | GET, POST | 🔑 | `AjusteView(FormView)` → `servicos.ajustar_lote` | `estoque/ajuste_form.html` | `/estoque/ajuste` |
| `/estoque/lotes/<pk>/validade/` | `estoque:lote_validade` | GET, POST | 🔑 | `ValidadeView(FormView)` → `servicos.alterar_validade` | `estoque/validade_form.html` | `/estoque/lote/<id>/validade` |
| `/estoque/movimentacoes/` | `estoque:movimentacao_lista` | GET | 👤 | `MovimentacaoListView` (`paginate_by=20`) | `estoque/movimentacao_lista.html` | `/movimentacoes` |

#### `vendas` — prefixo `/vendas/`

| URL | Nome | Métodos | Perm. | View | Template | Flask |
|---|---|---|---|---|---|---|
| `/vendas/pdv/` | `vendas:pdv` | GET | 👤 | `PdvView(TemplateView)` | `vendas/pdv.html` | `/venda/nova` (GET) |
| `/vendas/` | `vendas:venda_lista` | GET | 👤 | `VendaListView` (`paginate_by=20`) | `vendas/venda_lista.html` | `/vendas` |
| `/vendas/<pk>/recibo/` | `vendas:recibo` | GET | 👤 | `ReciboView(DetailView)`; com `?parcial=1` renderiza só `_recibo.html` | `vendas/recibo.html` / `vendas/_recibo.html` | `/venda/<id>/recibo` |

#### `relatorios` — prefixo `/relatorios/`

| URL | Nome | Métodos | Perm. | View | Template | Flask |
|---|---|---|---|---|---|---|
| `/relatorios/estoque/` | `relatorios:estoque` | GET | 👤 | `EstoqueRelView` | `relatorios/estoque.html` | `/relatorios/estoque` |
| `/relatorios/reposicao/` | `relatorios:reposicao` | GET | 👤 | `ReposicaoRelView` | `relatorios/reposicao.html` | `/relatorios/reposicao` |
| `/relatorios/reposicao/pdf/` | `relatorios:reposicao_pdf` | GET | 👤 | `reposicao_pdf` → `FileResponse` | — | `/relatorios/mais-vendidos/pdf` (nome errado no Flask) |
| `/relatorios/mais-vendidos/` | `relatorios:mais_vendidos` | GET | 🔑 | `MaisVendidosRelView` (`paginate_by=30`) | `relatorios/mais_vendidos.html` | `/relatorios/mais-vendidos` |
| `/relatorios/lucro/` | `relatorios:lucro` | GET | 🔑 | `LucroRelView` (usa `custo_unitario`) | `relatorios/lucro.html` | `/relatorios/lucro` |
| `/relatorios/movimentacoes/` | `relatorios:movimentacoes` | GET | 🔑 | `MovimentacoesRelView` (herda de `MovimentacaoListView`) | `relatorios/movimentacoes.html` | `/relatorios/movimentacoes` |

### 3.2 API JSON (Fetch)

Todas exigem sessão. Falta de sessão responde **`401` em JSON** (`@login_required_json`), nunca um redirect 302 para o HTML do login. Os erros seguem o formato `{"erro": "<mensagem em português>", ...}`.

| URL | Nome | Método | Perm. | View | Usada por | Flask |
|---|---|---|---|---|---|---|
| `/vendas/api/produtos/?q=` | `vendas:api_busca_produto` | GET | 👤 | `vendas.api.buscar_produto` | PDV — combobox | `/venda/buscar-produto` |
| `/estoque/api/produtos/<pk>/lotes/` | `estoque:api_lotes_produto` | GET | 👤 | `estoque.api.lotes_produto` | PDV — diálogo de lote; tela de ajuste | `/estoque/lotes/<id>` |
| `/vendas/api/vendas/` | `vendas:api_venda_criar` | POST | 👤 | `vendas.api.criar_venda` → `servicos.registrar_venda` | PDV — finalizar | `/venda/nova` (POST de formulário) |

#### `GET /vendas/api/produtos/?q=vinho`

- `q` com menos de 2 caracteres → `200 []`.
- Até 10 produtos ativos, ordenados por nome.

```json
[
  {
    "id": 3, "nome": "Vinho Tinto Seco 750ml", "fabricante": "Aurora",
    "codigo_barras": "7891234567890", "preco_venda": "39.90",
    "estoque": 17, "match_exato": false
  }
]
```

`preco_venda` vem como **string decimal** (sem perda de precisão). `match_exato` é `true` quando `q` é igual ao `codigo_barras`.

#### `GET /estoque/api/produtos/3/lotes/`

Lotes vendáveis em ordem PEPS (`Lote.objects.filter(produto_id=pk).vendaveis()`).

```json
[
  { "id": 12, "numero_lote": "L2409A", "quantidade": 5,
    "data_validade": "2026-10-15", "data_validade_fmt": "15/10/2026",
    "dias_para_vencer": 21, "data_entrada": "2026-09-01" }
]
```

`data_validade` é `null` para produto sem validade (`data_validade_fmt: "Sem validade"`).

#### `POST /vendas/api/vendas/`

Headers: `Content-Type: application/json`, `X-CSRFToken: <token>`.

```json
{ "itens": [ { "lote_id": 12, "quantidade": 2 }, { "lote_id": 7, "quantidade": 1 } ] }
```

O cliente não envia preço nem produto. Os dois são lidos do banco a partir do lote.

| Status | Corpo | Condição |
|---|---|---|
| `201 Created` | `{"id": 57, "total": "43.80", "recibo_url": "/vendas/57/recibo/"}` | Venda gravada |
| `400 Bad Request` | `{"erro": "Dados do carrinho inválidos."}` | JSON malformado, `itens` vazio, quantidade ≤ 0 |
| `401 Unauthorized` | `{"erro": "Sessão expirada.", "login_url": "/login/?next=/vendas/pdv/"}` | Sem sessão |
| `403 Forbidden` | `{"erro": "Falha de verificação CSRF."}` | Token ausente ou inválido |
| `409 Conflict` | `{"erro": "Estoque insuficiente no lote #12 de \"Vinho Tinto\" (disponível: 1).", "lote_id": 12, "item_index": 0, "disponivel": 1}` | Saldo insuficiente, lote vencido, produto inativo |

Garantias do serviço `registrar_venda` (código em `planejamento_views.md` §3.4, **testado**):
1. `transaction.atomic`: Venda + ItemVenda + Movimentacao + baixa do lote, tudo ou nada.
2. `select_for_update()` nos lotes, em ordem de `id`: dois caixas não vendem a mesma unidade e não entram em deadlock.
3. Itens repetidos do mesmo lote são somados antes da validação.
4. Baixa com `F('quantidade') - qtd`. O `CHECK (quantidade >= 0)` do banco é a última barreira.
5. `preco_unitario` e `custo_unitario` são congelados a partir do produto.

### 3.3 Onde usar Fetch

| Tela | Fetch | Motivo |
|---|---|---|
| PDV (`vendas:pdv`) | **Sim**: busca, lotes, finalizar, recibo parcial | O carrinho existe só no cliente e não pode ser perdido; o caixa trabalha sem recarregar a página |
| Ajuste (`estoque:ajuste`) | Sim: lotes do produto | Select dependente |
| Todas as outras | **Não** | Formulários comuns: funcionam sem JS, mantêm o histórico do navegador e URLs compartilháveis |

### 3.4 Frente de caixa acessível — componentes

Layout de `vendas/pdv.html`:

```
┌──────────────────────── <main id="conteudo"> ─────────────────────────┐
│ <h1>Frente de caixa</h1>          [ajuda de atalhos: F2 · F9 · Esc]  │
│ ┌─ <section aria-labelledby="t-busca"> ─┐  ┌─ <aside aria-labelledby="t-resumo"> ─┐
│ │ h2 Adicionar produto                  │  │ h2 Resumo da venda                   │
│ │ [C1 combobox de busca]                │  │ [C4 <dl> itens / total]               │
│ │ [C1 listbox de resultados]            │  │ [C5 botão Finalizar]                 │
│ └───────────────────────────────────────┘  │ [C7 painel do recibo]                │
│ ┌─ <section aria-labelledby="t-carrinho"> ┐└──────────────────────────────────────┘
│ │ h2 Carrinho (n produtos)                │
│ │ [C3 tabela do carrinho]                 │
│ └─────────────────────────────────────────┘
│ [C2 <dialog> de lote]   [C6 regiões aria-live]
└───────────────────────────────────────────────────────────────────────┘
```

#### C1 — Busca de produto (combobox + listbox) · `busca.js`

| Aspecto | Especificação |
|---|---|
| HTML | `<label for="busca-produto">` visível; `<input id="busca-produto" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="resultados-busca" aria-describedby="busca-dica" aria-keyshortcuts="F2" autocomplete="off">`; `<ul id="resultados-busca" role="listbox" hidden>`; `<template id="tpl-resultado">` com `<li role="option">` |
| Dados | `GET vendas:api_busca_produto`, debounce de 250 ms, `AbortController` cancela a busca anterior |
| Render | Clonar o `<template>` e preencher com `textContent` (nunca `innerHTML`); cada `<li>` com `id="opcao-<produto_id>"` |
| Teclado | ↓/↑ move o destaque (`aria-activedescendant` no input, `aria-selected` na opção; o foco fica no input) · Enter seleciona · Esc fecha; 2º Esc limpa · Home/End |
| Esgotado | `aria-disabled="true"` e o texto "Esgotado" visível; não pode ser selecionado |
| Leitor de código | `match_exato` com um único lote vendável → adiciona 1 unidade direto ao carrinho, sem abrir C2 |
| Anúncio | Em C6: "5 produtos encontrados" / "Nenhum produto encontrado" |
| WCAG | 1.3.1, 2.1.1, 4.1.2, 4.1.3 |

#### C2 — Diálogo de lote e quantidade · `dialogo-lote.js` (usa `core/js/dialogo.js`)

| Aspecto | Especificação |
|---|---|
| HTML | `<dialog id="dialogo-lote" aria-labelledby="dialogo-lote-titulo" aria-describedby="dialogo-lote-produto">` contendo `<form method="dialog">`; `<h2 id="dialogo-lote-titulo">Selecionar lote</h2>`; `<select id="lote-select" required aria-describedby="lote-info">`; `<input id="lote-qtd" type="number" min="1" inputmode="numeric" required aria-describedby="lote-qtd-info lote-qtd-erro">`; botões `value="cancelar"` (com `formnovalidate`) e `value="adicionar"`; botão fechar com `aria-label="Fechar"` |
| Abertura | Guarda `document.activeElement` → `showModal()` → foco no `lote-select` (ou direto na quantidade, se houver um único lote, já pré-selecionado) |
| Dados | `GET estoque:api_lotes_produto`; enquanto carrega, `aria-busy="true"` no select e a opção "Carregando lotes…" |
| Opção de lote | `Lote L2409A — vence 15/10/2026 (21 dias) — 5 un.` |
| Validação | Quantidade maior que o saldo → mensagem em `#lote-qtd-erro` + `aria-invalid="true"`; **não** corrigir o valor silenciosamente |
| Fechamento | Esc, botão Fechar ou Cancelar → evento `close` → foco volta ao elemento guardado. Com "Adicionar" → C3 recebe o item e o foco volta para C1 |
| WCAG | 2.1.2, 2.4.3, 3.3.1, 4.1.2 |

#### C3 — Carrinho · `carrinho.js`

| Aspecto | Especificação |
|---|---|
| Estado | `Map` com chave `lote_id` → `{produto_id, lote_id, nome, fabricante, numero_lote, preco_unitario (string), saldo_lote, quantidade}`; salvo em `sessionStorage` a cada mudança e restaurado ao carregar a página |
| HTML | `<table>` com `<caption class="visually-hidden">Itens do carrinho</caption>`, `<th scope="col">` (inclui `<span class="visually-hidden">Ações</span>`), `<th scope="row">` com o nome do produto |
| Linha | `data-lote="<id>"`; botões `aria-label="Diminuir quantidade de {nome}"` / `"Aumentar quantidade de {nome}"`; `<output aria-label="Quantidade de {nome}">`; remover com `aria-label="Remover {nome} do carrinho"`; ícones com `aria-hidden="true"` |
| Render | Atualiza **só a linha alterada**; nunca recria a tabela inteira (preserva o foco) |
| Foco | Depois de remover: foco no botão remover da próxima linha (ou da anterior); carrinho vazio → foco em C1 |
| Limite | `+` no saldo máximo → `aria-disabled="true"` e anúncio "Quantidade máxima do lote atingida (5)" |
| Vazio | `.empty-state` com texto "Nenhum produto no carrinho"; a tabela recebe `hidden` |
| Cor | Item com erro (409): borda `--danger` **e** texto "Disponível: 1" na linha |
| WCAG | 1.3.1, 1.4.1, 2.4.3, 4.1.2, 4.1.3 |

#### C4 — Resumo da venda

| Aspecto | Especificação |
|---|---|
| HTML | `<dl>`: `<dt>Itens</dt><dd id="resumo-itens">`, `<dt>Total</dt><dd id="resumo-total">` |
| Formato | `Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'})`; soma feita em centavos inteiros para evitar erro de ponto flutuante |
| Anúncio | As mudanças de total **não** usam `aria-live` no próprio `<dd>` (seria verboso); o anúncio consolidado sai em C6 |

#### C5 — Finalizar venda · `finalizar.js` (usa `core/js/api.js`)

| Aspecto | Especificação |
|---|---|
| HTML | `<button type="button" id="btn-finalizar" class="btn-accent" aria-keyshortcuts="F9" aria-describedby="finalizar-dica">`; sempre habilitado. Carrinho vazio → anúncio "Adicione pelo menos um produto" |
| Envio | `aria-busy="true"`, texto "Registrando venda…", bloqueia duplo clique |
| 201 | Limpa C3 e o `sessionStorage` → carrega `recibo_url?parcial=1` em C7 → anúncio "Venda 57 registrada. Total R$ 43,80." → foco no `<h2>` do recibo (`tabindex="-1"`) |
| 409 | Mantém o carrinho → marca a linha `item_index` com o saldo `disponivel` → mensagem em `role="alert"` → foco no controle de quantidade daquela linha |
| 400 / 403 | Mantém o carrinho → mensagem em `role="alert"` |
| 401 | Salva o carrinho no `sessionStorage` → aviso "Sessão expirada" → leva ao `login_url`; o carrinho volta depois do login |
| Falha de rede | Mantém o carrinho → "Falha de conexão. O carrinho foi mantido; tente novamente." |
| WCAG | 3.3.1, 3.3.4, 4.1.3 |

#### C6 — Regiões de anúncio · `core/js/anunciador.js`

```html
<div id="anuncio-status" class="visually-hidden" role="status" aria-live="polite" aria-atomic="true"></div>
<div id="anuncio-alerta" class="visually-hidden" role="alert" aria-live="assertive" aria-atomic="true"></div>
```

As duas regiões ficam **no HTML desde o carregamento** (regiões criadas depois não são anunciadas de forma confiável). `anunciar(texto, 'polite' | 'assertive')` limpa e reescreve o texto.

| Evento | Região | Mensagem |
|---|---|---|
| Resultado da busca | polite | "5 produtos encontrados" |
| Item adicionado | polite | "Vinho Tinto adicionado, 2 unidades. Total R$ 79,80." |
| Quantidade alterada | polite | "Vinho Tinto: 3 unidades. Total R$ 119,70." |
| Item removido | polite | "Vinho Tinto removido. Total R$ 0,00." |
| Venda concluída | polite | "Venda 57 registrada. Total R$ 43,80." |
| Conflito / erro | assertive | mensagem do servidor |

#### C7 — Painel do recibo

| Aspecto | Especificação |
|---|---|
| HTML | `<section id="painel-recibo" aria-labelledby="recibo-titulo" hidden>`; recebe o fragmento `vendas/_recibo.html` |
| Fragmento | `<h2 id="recibo-titulo" tabindex="-1">Recibo da venda #57</h2>`; `<dl>` com Data (`<time datetime>`), Operador; tabela com `caption` e `scope`; botões "Imprimir" (`window.print()`) e "Nova venda" (esconde o painel, foco em C1) |
| Impressão | `@media print` oculta sidebar, topbar e o PDV; mostra só o recibo |

#### C8 — Atalhos de teclado · `atalhos.js`

| Tecla | Ação | Observação |
|---|---|---|
| F2 | Foco em C1 | |
| F9 | Aciona C5 | Ignorado com um `<dialog>` aberto |
| Esc | Fecha a lista de C1 / C2 | Nativo no `<dialog>` |

Sem atalhos de tecla única (não conflitam com a navegação dos leitores de tela). A lista de atalhos fica visível no topo do PDV [2.1.4].

#### Módulos compartilhados (`core/static/core/js/`)

| Arquivo | Exporta | Responsabilidade |
|---|---|---|
| `api.js` | `getJSON(url, {signal})`, `postJSON(url, corpo)` | Lê o CSRF de `[name=csrfmiddlewaretoken]`, define `Accept`/`Content-Type`, converte `401` na exceção `SessaoExpirada` e devolve `{status, dados}` |
| `anunciador.js` | `anunciar(texto, nivel)` | Escreve em C6 |
| `dialogo.js` | `abrir(dialog)`, `aoFechar(dialog, cb)` | `showModal()`, guarda e devolve o foco |
| `base.js` | — | Menu lateral (`aria-expanded`, `inert` no mobile, Esc); fechamento automático só para mensagens de sucesso/info (10 s, pausa com hover/foco) |

#### Carregamento no template

```django
{% block scripts %}
  {% csrf_token %}   {# obrigatório: o PDV não tem <form> POST, e api.js lê o token deste input #}
  {{ lotes_iniciais|json_script:"dados-pdv" }}   {# se houver pré-carga; nunca interpolar dados em JS #}
  <script type="module" src="{% static 'vendas/js/pdv/main.js' %}"></script>
{% endblock %}
```

### 3.5 Requisitos de acessibilidade transversais (todos os templates)

| # | Requisito | Onde é implementado | WCAG |
|---|---|---|---|
| A1 | Link "Pular para o conteúdo" → `<main id="conteudo" tabindex="-1">` | `base.html` | 2.4.1 |
| A2 | `<nav aria-label="Menu principal">`, grupos com `<h2>` + `<ul aria-labelledby>`, `aria-current="page"` | `base.html` + `context_processors.secao_ativa` | 1.3.1, 4.1.2 |
| A3 | Um `h1` por página; seções com `h2` | todos | 1.3.1, 2.4.6 |
| A4 | Ícones com `aria-hidden="true"`; botões só com ícone com `aria-label` que inclui o nome do item | `{% icone %}`, `_icone.html` | 1.1.1, 2.4.4 |
| A5 | Todo campo com `<label for>`; filtros em `<form role="search">`; datas em `<fieldset>` "De/Até" | `_campo.html`, `_filtro_periodo.html` | 1.3.1, 3.3.2 |
| A6 | Erros ligados ao campo (`aria-invalid`, `aria-describedby`) + resumo de erros com foco | `AcessivelMixin`, `_resumo_erros.html` | 3.3.1, 3.3.3 |
| A7 | `*` com `aria-hidden` + atributo `required` + legenda "Campos com * são obrigatórios" | `_campo.html` | 3.3.2 |
| A8 | Tabelas com `caption`, `scope`, cabeçalho "Ações"; wrapper rolável com `role="region" tabindex="0"` | todos os templates de lista | 1.3.1, 2.1.1 |
| A9 | Status nunca só por cor (texto ou `.visually-hidden` junto do badge) | listas de estoque, painel | 1.4.1 |
| A10 | Paginação em `<nav aria-label="Paginação">`, `aria-current="page"`, anterior/próxima com rótulo, desabilitado como `<span aria-disabled>` | `_paginacao.html` | 2.4.4, 4.1.2 |
| A11 | Abas de relatório como `<nav aria-label="Relatórios">` + `aria-current` (não usar `role="tablist"`) | `relatorios/_abas.html` | 1.3.1 |
| A12 | Confirmações e edição inline com `<dialog>` (substitui `confirm()` e os modais em `div`) | `_dialogo_confirmar.html`, `dialogo.js` | 2.1.2, 2.4.3 |
| A13 | Mensagens: erro/aviso em `role="alert"` sem fechar sozinhas; sucesso/info em `role="status"` fechando em 10 s com pausa; botão fechar com `aria-label` | `base.html`, `base.js` | 2.2.1, 4.1.3 |
| A14 | Foco visível: `:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 2px }`; remover os 4 `outline: none` | `styles.css` | 2.4.7, 2.4.11 |
| A15 | Tokens de cor corrigidos: `--text-muted: #8a98ad` (5,41:1), `--danger: #f87171` (5,73:1), `--info: #60a5fa` (6,23:1), `--focus-ring: #fbbf24` | `styles.css` | 1.4.3, 1.4.11 |
| A16 | `prefers-reduced-motion` desativa transições | `styles.css` | 2.3.3 |
| A17 | Login: botão "mostrar senha" alcançável por Tab, com `aria-pressed` e `aria-controls` | `registration/login.html` | 2.1.1, 4.1.2 |
| A18 | Preço de venda calculado em `<output aria-live="polite">` | `catalogo/produto_form.html` | 4.1.3 |
| A19 | Sem `style`/`onclick`/`onsubmit` inline; dados para o JS via `data-*` ou `json_script` | todos | — |

### 3.6 Critérios de aceite da frente de caixa

1. **Somente teclado:** F2 → digitar "vin" → ↓ → Enter → escolher o lote → quantidade 2 → Enter → F9 → recibo exibido. Nenhum clique de mouse.
2. **NVDA + Firefox e Orca:** cada passo acima é anunciado (resultados, diálogo, item adicionado com o total, venda registrada).
3. **Conflito:** com duas abas vendendo o último item do mesmo lote, uma recebe `201`, a outra `409` com o carrinho intacto e o item destacado.
4. **Recarga acidental (F5)** no meio da venda: o carrinho é restaurado do `sessionStorage`.
5. **Sessão expirada:** o `401` leva ao login e, depois de entrar de novo, o carrinho continua lá.
6. **axe-core:** zero violações "serious" ou "critical" em `/vendas/pdv/` com o diálogo aberto e fechado.
7. **XSS:** um produto chamado `<img src=x onerror=alert(1)>` aparece como texto na busca, no carrinho e no recibo.
8. **Zoom 400 %:** o PDV empilha as colunas e continua operável, sem rolagem horizontal fora da tabela.
