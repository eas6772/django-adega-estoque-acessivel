# Plano de Acessibilidade (WCAG 2.2 nível AA) — Templates Django

**Projeto:** Empório BR — migração Flask → Django
**Base analisada:** `estoque_app/app/templates/` (24 templates) e `static/css/styles.css`
**Referência:** WCAG 2.2 AA + eMAG 3.1. Os números entre colchetes são os critérios de sucesso, ex.: [2.1.1].

Cada item traz **onde está no Flask** (arquivo:linha), **o problema**, e **como fica no template Django**.

---

## 0. Resumo por prioridade

| Prioridade | Item | Critério | Impacto |
|---|---|---|---|
| 🔴 Bloqueador | Resultados da busca do PDV são `<div>` só com clique → **não dá para vender usando só o teclado** | 2.1.1 | Operador sem mouse (ou com leitor de tela) não consegue usar o PDV |
| 🔴 Bloqueador | Modais (lote do PDV, editar categoria) sem `role="dialog"`, sem foco, sem Esc | 2.1.2, 2.4.3, 4.1.2 | Foco fica atrás do modal; leitor de tela não sabe que ele abriu |
| 🔴 Bloqueador | `--text-muted` com contraste **2,09:1** | 1.4.3 | Placeholders, "Página X de Y" e textos auxiliares ilegíveis para baixa visão |
| 🔴 Bloqueador | `outline: none` nos campos, sem indicador de foco equivalente | 2.4.7 | Usuário de teclado não vê onde está |
| 🟠 Alto | Filtros sem `<label>` (busca, selects, datas) | 1.3.1, 3.3.2, 4.1.2 | Campos anunciados só como "editar texto" |
| 🟠 Alto | Botões só com ícone sem nome acessível | 1.1.1, 4.1.2 | "Botão", "botão", "botão"… |
| 🟠 Alto | Alteração do carrinho/total não é anunciada | 4.1.3 | Leitor de tela não confirma que o item entrou |
| 🟠 Alto | Mensagens somem em 5 s, inclusive erros | 2.2.1 | Erro desaparece antes de ser lido |
| 🟡 Médio | Status indicado só por cor (estoque, dias para vencer) | 1.4.1 | Daltônicos não distinguem crítico/normal |
| 🟡 Médio | Títulos pulam de `h1` para `h5` | 1.3.1, 2.4.6 | Navegação por títulos quebrada |
| 🟡 Médio | Sem link "pular para o conteúdo" | 2.4.1 | 10+ tabs até o conteúdo em toda página |
| 🟡 Médio | Página ativa indicada só por classe CSS | 1.3.1, 4.1.2 | Menu e paginação sem `aria-current` |
| 🟢 Baixo | Tabelas sem `<caption>`/`scope`, colunas de ação sem cabeçalho | 1.3.1 | |
| 🟢 Baixo | Sidebar mobile fechada continua no foco do Tab | 2.4.3 | Foco "some" fora da tela |

---

## 1. Layout base (`base.html` → `templates/novo_app/base.html`)

### 1.1 Link "Pular para o conteúdo" [2.4.1]

**Hoje:** não existe. A cada página o usuário de teclado passa por marca, 6–7 links do menu, botão de menu, ações do topo e logout.

```django
<body>
  <a class="skip-link" href="#conteudo">Pular para o conteúdo</a>
  ...
  <main id="conteudo" class="page-body" tabindex="-1">
    {% block content %}{% endblock %}
  </main>
```

```css
.skip-link { position:absolute; left:-9999px; top:8px; z-index:1000;
             background:var(--accent); color:var(--bg-base); padding:8px 16px; border-radius:var(--radius-sm); }
.skip-link:focus { left:8px; }
```

### 1.2 Menu lateral: rótulo, grupos e página atual [1.3.1, 2.4.6, 4.1.2]

**Hoje (`base.html:23-84`):** os rótulos de seção ("Principal", "Catálogo"…) são `<li class="nav-label">` **dentro** da lista de links, então o leitor anuncia "lista, 12 itens" e lê "Catálogo" como se fosse um item de menu. A página ativa só tem `class="active"`.

```django
<nav class="sidebar-nav" aria-label="Menu principal">
  <h2 class="nav-label" id="nav-operacoes">Operações</h2>
  <ul aria-labelledby="nav-operacoes">
    <li>
      <a href="{% url 'estoque_visao_geral' %}"
         {% if secao_ativa == 'estoque' %}class="active" aria-current="page"{% endif %}>
        <i class="bi bi-archive-fill" aria-hidden="true"></i>
        <span>Estoque</span>
      </a>
    </li>
    ...
  </ul>
</nav>
```

> `request.endpoint.startswith('produtos.')` não existe no Django. Usar `request.resolver_match.url_name` ou definir `secao_ativa` no contexto de cada view (mais explícito).

### 1.3 Botão de abrir/fechar menu [4.1.2, 2.1.1, 2.4.3]

**Hoje (`base.html:95-97` + `main.js:1-15`):** `<button>` só com ícone, sem nome, sem estado. No mobile a sidebar sai da tela com `transform: translateX(-100%)` (`styles.css:932`), mas **os links continuam recebendo foco pelo Tab** — o foco vai para um lugar invisível.

```django
<button class="sidebar-toggle" id="sidebarToggle" type="button"
        aria-controls="sidebar" aria-expanded="false" aria-label="Abrir menu">
  <i class="bi bi-list" aria-hidden="true"></i>
</button>
```

```js
function definirMenu(aberto) {
  sidebar.classList.toggle('open', aberto);
  toggle.setAttribute('aria-expanded', aberto);
  toggle.setAttribute('aria-label', aberto ? 'Fechar menu' : 'Abrir menu');
  sidebar.inert = !aberto && window.matchMedia('(max-width: 768px)').matches;  // tira do Tab
  if (aberto) sidebar.querySelector('a').focus();
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && sidebar.classList.contains('open')) { definirMenu(false); toggle.focus(); }
});
```

### 1.4 Ícones decorativos [1.1.1]

**Hoje:** os 121 `<i class="bi ...">` dos templates ficam expostos (nenhum usa `aria-hidden`). Algumas combinações de leitor/navegador leem o caractere de uso privado da fonte de ícones como "símbolo" ou em branco.

- Ícone **ao lado de texto** → `aria-hidden="true"`.
- Ícone **sozinho em botão/link** → `aria-hidden="true"` no ícone **e** `aria-label` no botão (ver 1.5).

Sugestão: um *include* para padronizar e não esquecer.

```django
{# templates/novo_app/_icone.html #}
<i class="bi bi-{{ nome }}" aria-hidden="true"></i>
```

### 1.5 Botões e links só com ícone [1.1.1, 2.4.4, 4.1.2]

`title` **não** é nome acessível confiável (não aparece no toque nem no teclado, e alguns leitores ignoram).

| Arquivo:linha (Flask) | Elemento | Correção |
|---|---|---|
| `base.html:111` | Logout `<a title="Sair">` | Vira `<form method="post">` (Django 5 exige POST) com `<button aria-label="Sair do sistema">` |
| `produtos/lista.html:113` | Editar produto | `aria-label="Editar {{ p.nome }}"` |
| `produtos/lista.html:121` | Ativar/desativar | `aria-label="Desativar {{ p.nome }}"` |
| `produtos/lista.html:42-44` | Limpar filtros (só `bi-x-lg`) | `aria-label="Limpar filtros"` |
| `produtos/categorias.html:88, 97, 129` | Editar, alternar, fechar modal | `aria-label` com o nome da categoria / "Fechar" |
| `estoque/visao_geral.html:104` | Registrar entrada | `aria-label="Registrar entrada de {{ p.nome }}"` |
| `vendas/historico.html:70` | Ver recibo | `aria-label="Ver recibo da venda {{ v.id }}"` |
| `usuarios/lista.html:60, 70` | Editar, ativar/desativar | idem |
| `vendas/nova_venda.html:115, 216, 218, 223` | Fechar modal, `−`, `+`, remover | ver seção 5 |
| paginação (todas) | `‹` `›` | `aria-label="Página anterior"` / `"Próxima página"` |

Incluir o nome do item no rótulo é importante: numa tabela com 15 linhas, 15 botões "Editar" iguais não dizem **qual** produto será editado [2.4.4].

### 1.6 Mensagens (flash → `django.contrib.messages`) [4.1.3, 2.2.1]

**Hoje (`base.html:119-129` + `main.js:17-23`):**
- Todas as mensagens somem após 5 s, inclusive `danger` → viola 2.2.1 (tempo ajustável).
- O botão fechar (`btn-close`) não tem nome.
- O contêiner não é região viva; mensagens renderizadas no carregamento são lidas só se o usuário chegar até elas.

```django
<div class="flash-container" role="region" aria-label="Mensagens do sistema">
  {% for message in messages %}
    <div class="alert alert-{{ message.tags }} alert-dismissible fade show"
         role="{% if message.level >= DEFAULT_MESSAGE_LEVELS.WARNING %}alert{% else %}status{% endif %}"
         {% if message.level < DEFAULT_MESSAGE_LEVELS.WARNING %}data-auto-fechar{% endif %}>
      {% include "novo_app/_icone.html" with nome=message.extra_tags %}  {# ícone por nível: definir em extra_tags ou num filtro próprio #}
      {{ message }}
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"
              aria-label="Fechar mensagem"></button>
    </div>
  {% endfor %}
</div>
```

```js
// Só sucesso/info fecham sozinhos, com tempo maior e pausa ao passar o mouse ou focar.
document.querySelectorAll('.alert[data-auto-fechar]').forEach(alerta => {
  let t = setTimeout(fechar, 10000);
  function fechar() { bootstrap.Alert.getOrCreateInstance(alerta).close(); }
  ['mouseenter', 'focusin'].forEach(ev => alerta.addEventListener(ev, () => clearTimeout(t)));
});
```

Além disso, o **ícone** hoje é igual para todas as categorias no login (`login.html:53` sempre usa triângulo de alerta) — ajustar.

### 1.7 Hierarquia de títulos [1.3.1, 2.4.6]

**Hoje:** `<h1 class="page-title">` no topo e todos os títulos de seção são `<h5 class="section-title">` (dashboard, PDV, formulários…). O recibo usa `<h3>` sem `<h2>`. No login, `<h2>Empório BR</h2>` aparece **antes** do `<h1>Bem-vindo</h1>`.

Regra para os novos templates: `h1` = título da página (um por página); seções = `h2`; subseções = `h3`. A aparência continua controlada pela classe `.section-title`.

```django
<section class="card-dark" aria-labelledby="titulo-carrinho">
  <div class="section-header">
    <span class="section-dot dot-blue" aria-hidden="true"></span>
    <h2 class="section-title" id="titulo-carrinho">Carrinho</h2>
  </div>
  ...
</section>
```

### 1.8 Título da aba [2.4.2]

Já é bom (`{% block title %}Dashboard — Empório BR{% endblock %}`). Manter e, em páginas com erro de formulário, prefixar: `Erro: Novo Produto — Empório BR`.

---

## 2. Tema escuro — contraste e foco (`styles.css`)

### 2.1 Contraste de cores [1.4.3, 1.4.11]

Valores **calculados** com a fórmula de luminância relativa do WCAG sobre os fundos do tema:

| Token | Cor atual | Sobre `--bg-card` `#1a2236` | Situação | Proposta | Novo contraste (card / hover / input) |
|---|---|---|---|---|---|
| `--text-muted` | `#475569` | **2,09:1** | ❌ falha (mín. 4,5) | `#8a98ad` | 5,41 / 4,73 / 6,09 ✅ |
| `--danger` (texto) | `#ef4444` | **4,21:1** | ❌ falha em texto pequeno | `#f87171` | 5,73 / 5,01 / 6,45 ✅ |
| `--info` (texto) | `#3b82f6` | **4,31:1** | ❌ falha em texto pequeno | `#60a5fa` | 6,23 / 5,45 / 7,01 ✅ |
| `--text-secondary` | `#94a3b8` | 6,18:1 | ✅ | manter | |
| `--warning` | `#f59e0b` | 7,37:1 | ✅ | manter | |
| `--accent` | `#22c55e` | 6,95:1 | ✅ | manter | |
| texto de `.btn-accent` | `#0b1120` sobre `#22c55e` | 8,26:1 | ✅ | manter | |

`--text-muted` é usado em placeholders (`styles.css:426, 593`), `.text-muted-sm` (709, ex.: "Página 1 de 3") e mais 6 regras. Se for preciso manter um tom mais apagado para itens **puramente decorativos**, criar um token separado (`--text-decorativo`) e nunca usá-lo em texto informativo.

Manter os valores de fundo em badges (`.badge-red` etc.) com contraste ≥ 4,5:1 entre texto e fundo do próprio badge — verificar após a troca dos tokens.

### 2.2 Indicador de foco visível [2.4.7, 2.4.11 (AA na 2.2), 2.4.13 (AAA)]

**Hoje:** `outline: none` em `.form-dark input` (`styles.css:415`), `.form-control-login` (584), `.filter-control` (747), `.filter-select` (761). O único sinal de foco é trocar a cor da borda de 1 px — pouco perceptível. Links do menu, abas de relatório, `.btn-icon`, `.btn-outline` e itens de paginação não têm estilo de foco próprio.

```css
:root { --focus-ring: #fbbf24; }   /* amarelo: contraste alto contra o fundo escuro e o verde de destaque */

:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}
/* Remover os "outline: none" das 4 regras citadas; manter a troca de borda como reforço. */
```

### 2.3 Movimento reduzido [2.3.3]

Transições de sidebar/alertas/modais devem respeitar a preferência do sistema:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
```

### 2.4 Zoom e reflow [1.4.4, 1.4.10]

- Testar em 400 % (equivalente a 320 px de largura). As tabelas já estão em `.table-scroll`; ver 4.3 para torná-las roláveis por teclado.
- `pdv-layout` com duas colunas deve empilhar abaixo de 768 px (confirmar após migrar o CSS).
- Remover `style="max-width:480px"` e demais estilos inline dos templates; usar classes (facilita também temas de alto contraste do sistema).

---

## 3. Formulários

### 3.1 Todo campo precisa de `<label>` associado [1.3.1, 3.3.2, 4.1.2]

`placeholder` e `title` não substituem rótulo: o placeholder some ao digitar e tem contraste baixo (item 2.1).

| Arquivo:linha (Flask) | Campo sem rótulo |
|---|---|
| `produtos/lista.html:24` | Busca (só placeholder) |
| `produtos/lista.html:28, 34` | Select de categoria e de status |
| `estoque/visao_geral.html:27` | Busca de produto |
| `estoque/movimentacoes.html:22, 28, 30` | Tipo, data inicial, data final (só `title`) |
| `vendas/historico.html:17, 19` | Datas (só `title`) |
| `relatorios/mais_vendidos.html:12, 16` · `lucro.html:12, 16` · `movimentacoes.html:12, 16, 19` | Datas e tipo |
| `vendas/nova_venda.html:29` | **Busca do PDV** |
| `usuarios/form.html:20, 26, 34` | `<label>` **existe mas sem `for`**, e os inputs não têm `id` — não há associação |

Padrão para barras de filtro (rótulo visualmente oculto quando o design não comporta texto visível):

```django
<form method="get" role="search" aria-label="Filtrar produtos" class="filter-row">
  <div class="filter-input">
    <label for="id_q" class="visually-hidden">Buscar por nome, fabricante ou código de barras</label>
    <i class="bi bi-search filter-search-icon" aria-hidden="true"></i>
    {{ form.q }}
  </div>
  <label for="id_categoria" class="visually-hidden">Categoria</label>
  {{ form.categoria }}
  ...
</form>
```

Para datas, preferir **rótulo visível** ("De" / "Até"): um período sem rótulo é ambíguo até para quem enxerga.

Com Django Forms, `{{ form.campo.label_tag }}` + `{{ form.campo }}` geram `for`/`id` automaticamente — basta usar sempre esse par (ou `{{ form.campo.as_field_group }}` no Django 5+).

### 3.2 Erros de validação ligados ao campo [3.3.1, 3.3.3, 4.1.2]

**Hoje:** toda validação do servidor volta como `flash()` genérico no topo ("O nome do produto é obrigatório."), sem apontar o campo, sem `aria-invalid`, e o foco fica no início da página.

Template de campo reutilizável (`templates/novo_app/_campo.html`):

```django
{% with id=campo.id_for_label erro_id=campo.id_for_label|add:"-erro" dica_id=campo.id_for_label|add:"-dica" %}
<div class="mb-3">
  <label for="{{ id }}">
    {{ campo.label }}
    {% if campo.field.required %}<span class="required-star" aria-hidden="true">*</span>{% endif %}
  </label>
  {{ campo }}  {# widget com attrs: aria-describedby / aria-invalid via form.__init__ ou django-widget-tweaks #}
  {% if campo.help_text %}<p class="field-hint" id="{{ dica_id }}">{{ campo.help_text }}</p>{% endif %}
  {% if campo.errors %}<p class="field-error" id="{{ erro_id }}">{{ campo.errors|join:" " }}</p>{% endif %}
</div>
{% endwith %}
```

```python
# forms.py — mixin para todos os forms
class AcessivelMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            ids = []
            if campo.help_text:
                ids.append(f'id_{nome}-dica')
            if self.is_bound and nome in self.errors:
                campo.widget.attrs['aria-invalid'] = 'true'
                ids.append(f'id_{nome}-erro')
            if ids:
                campo.widget.attrs['aria-describedby'] = ' '.join(ids)
```

Quando o formulário volta com erro: renderizar um **resumo de erros** no topo (`role="alert"`, `tabindex="-1"`, com links `href="#id_campo"` para cada erro) e mover o foco para ele.

### 3.3 Campos obrigatórios [3.3.2, 1.3.1]

**Hoje:** o `*` vermelho é o único indicador visual, é lido pelo leitor como "asterisco", e nem todo campo marcado tem o atributo `required` (ex.: `estoque/ajuste.html:60` `nova_quantidade` é marcado com `*` mas não é `required`).

- `<span class="required-star" aria-hidden="true">*</span>` + atributo `required` no input (o leitor anuncia "obrigatório").
- Uma legenda no início de cada formulário: "Campos marcados com * são obrigatórios."

### 3.4 Agrupamento com `<fieldset>` [1.3.1]

`produtos/form.html` tem três blocos (Informações Básicas, Precificação, Limites de Estoque) feitos com `div` + `h5`. Usar `<fieldset>` + `<legend>` para que o contexto seja anunciado ao entrar no grupo. O mesmo para o par "De / Até" dos filtros de data.

### 3.5 Valores calculados em tempo real [4.1.3]

**Hoje (`produtos/form.html:100-105, 161-166`):** o preço de venda é recalculado em um `<input readonly>` — o leitor não anuncia a mudança, e o formato usa ponto (`R$ 12.50`).

```django
<label for="preco_venda_preview">Preço de venda</label>
<output id="preco_venda_preview" for="id_preco_custo id_margem_lucro" aria-live="polite">R$ 0,00</output>
```

```js
const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
preview.value = brl.format(custo * (1 + margem / 100));
```

### 3.6 Campos que aparecem/desaparecem (Ajuste de Estoque) [4.1.3, 3.2.2]

**Hoje (`estoque/ajuste.html:44-63, 97-139`):** ao escolher o produto, o bloco de lotes aparece (`display:block`) sem aviso; o botão "Confirmar Ajuste" fica `disabled` sem explicação; o link "Editar Validade" surge ao lado do select.

- Envolver a área dinâmica com `aria-live="polite"` **ou** anunciar por uma região de status: "3 lotes disponíveis para Vinho Tinto".
- Enquanto carrega: `aria-busy="true"` no select de lotes.
- Botão desabilitado → preferir **habilitado** e validar no envio com mensagem ligada ao campo; se mantiver desabilitado, associar a dica com `aria-describedby` ("Selecione produto e lote para confirmar").
- `qtdAtualInfo` (quantidade atual no sistema) → `aria-describedby` do campo `nova_quantidade`.

### 3.7 Login (`auth/login.html`) [2.1.1, 4.1.2, 1.3.1]

| Linha | Problema | Correção |
|---|---|---|
| 90 | Botão "mostrar senha" com `tabindex="-1"` → **inacessível por teclado**; sem nome | Remover `tabindex`; `aria-label="Mostrar senha"`, `aria-pressed="false"`, `aria-controls="id_password"`; alternar `aria-pressed` e o rótulo no clique |
| 21 / 46 | `h2` da marca antes do `h1` | Marca vira `<p class="brand-title">`; `h1` = "Entrar no Empório BR" |
| 59 | `novalidate` + erro genérico do servidor | Com o `AuthenticationForm`, renderizar `form.non_field_errors` em `role="alert"` e marcar os dois campos com `aria-invalid` |
| 16-39 | Painel de marca com lista de recursos feita com `div` | `<ul>` com `<li>` (é uma lista) |
| 103 | `{{ 2026 }}` fixo | `{% now "Y" %}` |

`autocomplete="username"` / `"current-password"` já estão corretos [1.3.5] — manter.

### 3.8 Confirmações com `window.confirm()` [2.1.1, 3.3.4]

`produtos/lista.html:119`, `categorias.html:95`, `usuarios/lista.html:67` usam `onsubmit="return confirm(...)"` com o nome inserido em string JS. O `confirm()` nativo é acessível, mas o nome com apóstrofo quebra o script (ver `planejamento_views.md`, item 4). Substituir por um `<dialog>` de confirmação reaproveitável (mesmo componente da seção 5.2), com o nome inserido via `textContent`.

---

## 4. Tabelas, listas e paginação

### 4.1 Estrutura das tabelas [1.3.1]

Aplicar em todas as `table-dark-custom` (dashboard, produtos, categorias, estoque, movimentações, vendas, recibo, 5 relatórios):

```django
<table class="table-dark-custom">
  <caption class="visually-hidden">Produtos com estoque abaixo do mínimo</caption>
  <thead>
    <tr>
      <th scope="col">Produto</th>
      ...
      <th scope="col"><span class="visually-hidden">Ações</span></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">{{ p.nome }} <span class="product-brand">{{ p.fabricante }}</span></th>
      ...
```

Colunas de ação com `<th></th>` vazio hoje: `produtos/lista.html:73`, `categorias.html:65`, `estoque/visao_geral.html:66`, `vendas/historico.html:51`, `relatorios/reposicao.html:48`, `nova_venda.html:61`.

### 4.2 Informação transmitida só por cor [1.4.1]

| Arquivo:linha | Hoje | Correção |
|---|---|---|
| `estoque/visao_geral.html:79-85` | Número verde/amarelo/vermelho (`value-ok`/`value-warning`/`value-danger`) | A coluna "Status" ao lado já tem texto — ok; mas no **dashboard** (`dashboard.html:125`) não há coluna de texto equivalente para o número. Adicionar `<span class="visually-hidden">(crítico)</span>` ou ícone com texto |
| `dashboard.html:185-191` | Dias para vencer: `7d` vermelho, `15d` amarelo, `30d` azul | Texto completo: "7 dias — urgente" (a cor reforça, não informa) |
| `produtos/lista.html:94-101` | Badge de estoque só com número colorido | Incluir rótulo visualmente oculto: "12 (baixo)" |
| `dashboard.html:34, 53` | Borda do card KPI colorida (`kpi-alert`/`kpi-warn`) | O texto do `kpi-sub` já descreve — ok |
| `base.html:106` | Perfil "Operador" em azul vs "Admin" em verde | Texto já diferencia — ok; remover o `style` inline |
| `section-dot` (bolinhas coloridas nos títulos) | Decorativas | `aria-hidden="true"` |

### 4.3 Tabelas com rolagem horizontal [2.1.1]

`.table-scroll` rola horizontalmente em telas pequenas, mas uma `div` rolável sem conteúdo focável não é alcançável pelo teclado.

```django
<div class="table-scroll" role="region" aria-labelledby="titulo-estoque" tabindex="0">
```

### 4.4 Paginação [1.3.1, 2.4.4, 4.1.2]

**Hoje (`produtos/lista.html:137-170`, `estoque/visao_geral.html:116-143` e demais):** `<ul>` sem contexto; página atual só com `class="active"`; setas só com ícone; em `produtos/lista.html:140-145` o link "anterior" desabilitado continua sendo um `<a href>` clicável que aponta para `pagina=None`.

Criar `templates/novo_app/_paginacao.html` usado por todas as `ListView`:

```django
{% if page_obj.paginator.num_pages > 1 %}
<nav class="pagination-wrap" aria-label="Paginação">
  <ul class="pagination-dark">
    <li class="page-item">
      {% if page_obj.has_previous %}
        <a class="page-link" href="?{% querystring page=page_obj.previous_page_number %}" aria-label="Página anterior">
          <i class="bi bi-chevron-left" aria-hidden="true"></i></a>
      {% else %}
        <span class="page-link" aria-disabled="true"><i class="bi bi-chevron-left" aria-hidden="true"></i>
          <span class="visually-hidden">Página anterior</span></span>
      {% endif %}
    </li>
    {% for n in page_obj.paginator.get_elided_page_range %}
      <li class="page-item">
        {% if n == page_obj.number %}
          <a class="page-link active" aria-current="page" href="?{% querystring page=n %}">
            <span class="visually-hidden">Página </span>{{ n }}</a>
        {% elif n == page_obj.paginator.ELLIPSIS %}
          <span class="page-link" aria-hidden="true">…</span>
        {% else %}
          <a class="page-link" href="?{% querystring page=n %}"><span class="visually-hidden">Página </span>{{ n }}</a>
        {% endif %}
      </li>
    {% endfor %}
    ...
  </ul>
  <p class="pagination-info">{{ page_obj.paginator.count }} resultados · página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}</p>
</nav>
{% endif %}
```

> `{% querystring %}` (Django 5.1+) preserva os filtros atuais (`q`, `categoria`, datas) — no Flask cada template repete a lista de parâmetros à mão.

### 4.5 Abas de relatórios (`relatorios/_tabs.html`) [1.3.1, 4.1.2]

São **links para páginas diferentes**, não abas ARIA — não usar `role="tablist"` (exigiria navegação por setas e painéis na mesma página).

```django
<nav class="report-tabs mb-4" aria-label="Relatórios">
  <ul>
    <li><a href="{% url 'rel_estoque' %}" class="report-tab {% if ativo == 'estoque' %}active{% endif %}"
           {% if ativo == 'estoque' %}aria-current="page"{% endif %}>
      <i class="bi bi-archive-fill" aria-hidden="true"></i> Inventário</a></li>
    ...
```

O mesmo vale para os filtros "Todos / Estoque Baixo / Zerado" de `estoque/visao_geral.html:30-37`: são links; marcar o ativo com `aria-current="true"` e agrupar com `role="group" aria-label="Filtrar por situação"`.

---

## 5. PDV — `vendas/nova_venda.html` (prioridade máxima)

O PDV é a tela mais usada e hoje **não pode ser operada só pelo teclado**. Como na migração ela passa a funcionar via Fetch (ver `planejamento_views.md`, seção 3), é o momento de refazer a marcação.

### 5.1 Busca de produtos → padrão *combobox* com *listbox* [2.1.1, 4.1.2, 1.3.1]

**Hoje (`nova_venda.html:26-33, 270-300`):**
- Resultados são `<div class="search-result-item">` com `addEventListener('click')` apenas — **sem Tab, sem Enter, sem setas**.
- Nada informa ao leitor que há resultados, quantos, ou qual está destacado.
- Produtos esgotados só ficam com estilo diferente (cor).
- Busca sem `<label>`.

Marcação alvo (padrão ARIA APG "Combobox with Listbox Popup"):

```django
<div class="search-wrapper">
  <label for="busca-produto">Adicionar produto</label>
  <p id="busca-dica" class="field-hint">Digite 2 letras do nome, fabricante ou leia o código de barras. Use ↑ ↓ para escolher e Enter para selecionar.</p>
  <input id="busca-produto" type="text" role="combobox" autocomplete="off"
         aria-autocomplete="list" aria-expanded="false" aria-controls="resultados-busca"
         aria-describedby="busca-dica" aria-keyshortcuts="F2">
  <ul id="resultados-busca" role="listbox" aria-label="Produtos encontrados" hidden></ul>
  <p id="busca-status" class="visually-hidden" role="status" aria-live="polite"></p>
</div>

<template id="tpl-resultado">
  <li role="option" class="search-result-item" aria-selected="false">
    <span class="product-name"></span>
    <span class="product-brand"></span>
    <span class="search-result-meta"><span class="preco"></span> · <span class="estoque"></span></span>
  </li>
</template>
```

Comportamento de teclado:

| Tecla | Ação |
|---|---|
| ↓ / ↑ | Move o destaque; atualiza `aria-activedescendant` no input e `aria-selected` na opção (o foco **permanece** no input) |
| Enter | Seleciona a opção destacada → abre o diálogo de lote. Se houver match exato de código de barras, seleciona direto |
| Esc | Fecha a lista (`hidden`, `aria-expanded="false"`); segundo Esc limpa o campo |
| Home / End | Primeira / última opção |

- Produto esgotado: `aria-disabled="true"` + texto "Esgotado" visível (não só cor); a seta pula esse item ou Enter anuncia "Produto esgotado".
- Ao receber resultados: `busca-status.textContent = '5 produtos encontrados'` ou `'Nenhum produto encontrado'`.
- Cada `<li>` precisa de `id` único para o `aria-activedescendant`.
- Preenchimento com `textContent` a partir do `<template>` (corrige também o XSS atual).

### 5.2 Diálogo de seleção de lote → `<dialog>` nativo [2.1.2, 2.4.3, 4.1.2]

**Hoje (`nova_venda.html:107-144, 316-399`):** `div.modal-overlay` exibida com `style.display='flex'`:
- sem `role="dialog"`, `aria-modal` ou nome;
- o foco **não entra** no modal (continua no campo de busca atrás dele) e pode sair com Tab para a página de fundo;
- **Esc não fecha**;
- ao fechar, o foco não volta de forma consistente (só no "Adicionar", via `searchInput.focus()`);
- "Carregando lotes..." não é anunciado.

`<dialog>` + `showModal()` resolve quase tudo nativamente (foco preso, Esc, fundo inerte, papel de diálogo):

```django
<dialog id="dialogo-lote" class="modal-card" aria-labelledby="dialogo-lote-titulo" aria-describedby="dialogo-lote-desc">
  <form method="dialog" class="form-dark">
    <div class="section-header">
      <h2 class="section-title" id="dialogo-lote-titulo">Selecionar lote</h2>
      <button type="submit" value="cancelar" class="btn-icon" aria-label="Fechar">
        <i class="bi bi-x-lg" aria-hidden="true"></i></button>
    </div>
    <p id="dialogo-lote-desc"><span id="dialogo-lote-produto"></span></p>

    <label for="lote-select">Lote <span class="required-star" aria-hidden="true">*</span></label>
    <select id="lote-select" required aria-describedby="lote-info" aria-busy="true">
      <option value="">Carregando lotes…</option>
    </select>
    <p class="field-hint" id="lote-info" aria-live="polite"></p>

    <label for="lote-qtd">Quantidade <span class="required-star" aria-hidden="true">*</span></label>
    <input id="lote-qtd" type="number" min="1" value="1" inputmode="numeric" required aria-describedby="lote-qtd-info">
    <p class="field-hint" id="lote-qtd-info"></p>

    <div class="form-actions">
      <button type="submit" value="cancelar" class="btn-outline" formnovalidate>Cancelar</button>
      <button type="submit" value="adicionar" class="btn-accent">
        <i class="bi bi-cart-plus-fill" aria-hidden="true"></i> Adicionar ao carrinho</button>
    </div>
  </form>
</dialog>
```

```js
function abrirDialogoLote(produto) {
  origemFoco = document.activeElement;
  dialogo.showModal();
  loteSelect.focus();                       // foco no primeiro campo útil
}
dialogo.addEventListener('close', () => {
  if (dialogo.returnValue === 'adicionar') adicionarAoCarrinho(...);
  (origemFoco ?? buscaInput).focus();       // devolve o foco
});
```

- Com **um único lote vendável**, pré-selecioná-lo e focar direto na quantidade (fluxo mais rápido para todos).
- A validação do máximo (`min`/`max`) deve gerar mensagem ligada ao campo, não "corrigir" o valor silenciosamente como hoje (`nova_venda.html:371-375` troca o número digitado sem avisar) [3.3.1].
- Usar o **mesmo componente** para o modal de edição de categoria (`categorias.html:122-150`) e para as confirmações da seção 3.8.

### 5.3 Carrinho [4.1.2, 4.1.3, 2.4.3]

**Hoje (`nova_venda.html:184-246`):** a tabela inteira é recriada com `innerHTML` a cada alteração → o foco no botão clicado é **destruído** (volta ao `<body>`); os botões `−` / `+` / lixeira não têm nome; a quantidade muda sem anúncio.

- Botões com nome que inclui o produto:
  ```html
  <button type="button" class="qty-btn" aria-label="Diminuir quantidade de Vinho Tinto Seco">−</button>
  <output class="qty-value" aria-label="Quantidade de Vinho Tinto Seco">2</output>
  <button type="button" class="qty-btn" aria-label="Aumentar quantidade de Vinho Tinto Seco">+</button>
  <button type="button" class="btn-icon btn-icon-danger" aria-label="Remover Vinho Tinto Seco do carrinho">…</button>
  ```
- Atualizar **apenas a linha alterada** (ou re-renderizar e restaurar o foco pelo `data-chave` do item).
- Após **remover** um item: foco na próxima linha; se o carrinho ficou vazio, foco no campo de busca.
- Botão `+` no limite do lote: `aria-disabled="true"` + anúncio "Quantidade máxima do lote atingida (5)".
- Região de anúncios única da página:
  ```html
  <div id="anuncios-pdv" class="visually-hidden" role="status" aria-live="polite" aria-atomic="true"></div>
  ```
  Mensagens: "Vinho Tinto adicionado, 2 unidades. Total R$ 45,80." / "Item removido. Total R$ 22,90."
- Resumo da venda: `<dl>` (termo/definição) em vez de `div.summary-row` com `span` + `strong`.
- Coluna "Produto / Lote": `<th scope="row">` por linha (4.1).

### 5.4 Finalização da venda (via Fetch) [4.1.3, 3.3.1, 2.4.3]

- Durante o envio: `aria-busy="true"` e texto do botão "Registrando venda…".
- **Sucesso:** anunciar "Venda 57 registrada. Total R$ 43,80." e mover o foco para o título do recibo exibido no painel (ou de volta à busca, se o recibo abrir em outra área) — nunca deixar o foco "no nada" depois de limpar o carrinho.
- **Erro 409:** o carrinho é mantido; o item com problema recebe destaque visual **e** texto ("Disponível: 1"); mensagem em `role="alert"`; foco no controle de quantidade daquele item.
- O botão "Finalizar" hoje fica `disabled` com carrinho vazio sem explicação → manter habilitado e anunciar "Adicione pelo menos um produto" ao acionar, ou associar uma dica via `aria-describedby`.

### 5.5 Atalhos de teclado do caixa [2.1.1, 2.1.4]

Atalhos agilizam o caixa para todos, mas precisam ser **documentados** e **não conflitar** com leitores de tela (evitar teclas únicas sem modificador).

| Atalho | Ação |
|---|---|
| `F2` | Foco na busca de produtos |
| `F9` | Finalizar venda |
| `Esc` | Fechar lista / diálogo |

Declarar com `aria-keyshortcuts` e listar os atalhos numa linha de ajuda visível no PDV.

---

## 6. Demais telas

### 6.1 Dashboard (`main/dashboard.html`)

- KPIs: cada card é um par rótulo/valor → `<dl>` ou `<section aria-labelledby>` com o rótulo como título. Hoje são dois `<p>` soltos [1.3.1].
- Data do topo: `<time datetime="{{ hoje|date:'Y-m-d' }}">{{ hoje|date:'d/m/Y' }}</time>`.
- "7d" → "7 dias" (abreviação sem expansão) [3.1.4 AAA, mas barato de corrigir].

### 6.2 Recibo (`vendas/recibo.html`)

- `h3 "Empório BR"` → hierarquia correta (`h1` = "Recibo da venda #57").
- Metadados (Venda, Data, Operador) → `<dl>`.
- Data com `<time>`.
- Botão "Imprimir" (`window.print()`) com CSS `@media print` que oculta sidebar/topbar — útil no balcão.

### 6.3 Usuários (`usuarios/form.html`)

- Associar `label`/`input` (hoje sem `for`/`id`, linhas 20-39).
- A dica "(deixe em branco para não alterar)" está **dentro** do `<label>` com 11 px e cor apagada → mover para `<p class="field-hint">` ligado por `aria-describedby`.
- Senha: `autocomplete="new-password"` já correto; adicionar a exigência ("mínimo 6 caracteres") como dica visível, não só `placeholder`.

### 6.4 Idioma

`<html lang="pt-BR">` já está correto [3.1.1]. No Django: `<html lang="{{ LANGUAGE_CODE }}">` com `LANGUAGE_CODE = 'pt-br'`.

---

## 7. Utilitário CSS obrigatório

O Bootstrap 5 já traz `.visually-hidden` e `.visually-hidden-focusable`. Usar essas classes (não criar `sr-only` próprio) e **nunca** `display:none` para texto destinado a leitores de tela.

---

## 8. Como verificar

| Ferramenta | Uso |
|---|---|
| **Teclado apenas** | Fazer uma venda completa (buscar → lote → quantidade → finalizar) sem tocar no mouse. É o teste de aceite do PDV |
| **NVDA** (Windows, gratuito) + Firefox / **Orca** (Linux) | Percorrer PDV, cadastro de produto com erro e relatórios |
| **axe DevTools** / **Lighthouse** | Varredura automática por página (pega ~30–40 % dos problemas) |
| **pa11y-ci** ou **@axe-core/playwright** no CI | Rodar axe nas URLs principais a cada PR, logado como admin |
| **WebAIM Contrast Checker** | Conferir qualquer cor nova do tema |
| Zoom 200 % e 400 % | Reflow sem rolagem horizontal fora das tabelas |

### Checklist de aceite por template Django

- [ ] Um `h1`; seções com `h2`; sem pular níveis
- [ ] Todo `input`/`select` com `<label for>` (visível ou `.visually-hidden`)
- [ ] Ícones com `aria-hidden="true"`; botões só com ícone têm `aria-label` com o nome do item
- [ ] Foco visível em todos os elementos interativos
- [ ] Nenhuma informação só por cor
- [ ] Tabelas com `caption`, `scope` e cabeçalho na coluna de ações
- [ ] Erros de formulário ligados ao campo (`aria-invalid` + `aria-describedby`)
- [ ] Conteúdo dinâmico anunciado (`role="status"` / `aria-live`)
- [ ] Modais com `<dialog>` + `showModal()`, foco entra e volta
- [ ] Sem `onclick`/`onsubmit` inline nem `style` inline
