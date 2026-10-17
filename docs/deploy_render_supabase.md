# Deploy: app no Render, banco no Supabase

O serviço web roda no **Render** (plano grátis) e o PostgreSQL fica no **Supabase**.
Tudo que o Render precisa está versionado: `render.yaml` (blueprint), `build.sh` (build) e
`config/settings/prod.py` (WhiteNoise, hosts e TLS). Os segredos ficam só nos painéis.

## 1. Supabase (banco)

1. Crie o projeto (região **South America — São Paulo**) e guarde a senha do banco.
2. Em **Connect** → **Session pooler**, copie a string de conexão (porta **5432** do host
   `...pooler.supabase.com`, usuário `postgres.<id-do-projeto>`).
   - Use o **Session pooler**: é IPv4 e mantém a conexão, o que o sistema precisa
     (`select_for_update` dentro de transações e `CONN_MAX_AGE`).
   - Evite o *Transaction pooler* (porta 6543) e a conexão direta (somente IPv6).
3. Monte a `DATABASE_URL`:
   `postgresql://postgres.<id>:<SENHA>@<host-do-pooler>:5432/postgres`
   (se a senha tiver `@`, `:` ou `/`, codifique em URL). O `sslmode=require` já é aplicado pelo
   `prod.py`.

## 2. Render (aplicação)

1. No painel: **New → Blueprint** e escolha este repositório (branch `develop`).
2. O Render lê o `render.yaml`. Preencha o único segredo pedido: **DATABASE_URL** (item 1.3).
3. `SECRET_KEY`, `DEMO_ADMIN_SENHA` e `DEMO_CAIXA_SENHA` são gerados pelo próprio Render.
   Veja-os em **Environment** do serviço.
4. Aguarde o build. Ele instala as dependências, junta os estáticos, aplica as migrações e
   carrega os dados de demonstração (`SEED_DEMO=true`).
5. Acesse `https://emporio-br.onrender.com` (o nome pode variar). Entre com `admin` e a senha
   de `DEMO_ADMIN_SENHA`; o usuário `caixa` usa `DEMO_CAIXA_SENHA`.

`ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` já incluem o domínio `*.onrender.com`
(variável `RENDER_EXTERNAL_HOSTNAME`, injetada pelo Render). Para um domínio próprio,
acrescente `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` em **Environment**.

## 3. Limitações do plano grátis

- O serviço **dorme após ~15 min sem acesso**; a primeira requisição leva alguns segundos.
- O Supabase grátis **pausa o projeto após ~7 dias sem atividade** (reative no painel) e não faz
  backup diário.
- Os dados de demonstração têm senhas conhecidas por quem vê o painel. Para uso real, defina
  `SEED_DEMO=false` depois da primeira carga e troque as senhas.
- A região mais próxima do Supabase em São Paulo é a **Virgínia** (o Render não tem região no
  Brasil).

## 4. Variáveis de ambiente

| Variável | Origem | Uso |
|---|---|---|
| `DATABASE_URL` | você (painel) | Postgres do Supabase |
| `SECRET_KEY` | gerada pelo Render | chave do Django |
| `DJANGO_SETTINGS_MODULE` | `render.yaml` | `config.settings.prod` |
| `SEED_DEMO` | `render.yaml` | `true` carrega os dados de demonstração |
| `DEMO_ADMIN_SENHA` / `DEMO_CAIXA_SENHA` | geradas pelo Render | senhas dos usuários de demonstração |
| `PYTHON_VERSION` | `render.yaml` | versão do Python no build |
| `RENDER_EXTERNAL_HOSTNAME` | injetada pelo Render | domínio liberado em hosts e CSRF |

## 5. Testar localmente com as configurações de produção

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
export DATABASE_URL='postgresql://...?sslmode=disable'   # Postgres local não tem TLS
export SECRET_KEY=... ALLOWED_HOSTS=localhost
./build.sh                       # ou: collectstatic, migrate, seed_demo
gunicorn config.wsgi:application
```

Dados de demonstração à mão: `python manage.py seed_demo --senha-admin ... --senha-caixa ...`
(idempotente; `--forcar` recarrega o catálogo).
