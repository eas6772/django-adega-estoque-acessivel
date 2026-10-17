#!/usr/bin/env bash
# Build do Render: instala dependências, junta os estáticos e aplica as migrações.
set -o errexit

pip install --upgrade pip
pip install .

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Dados de demonstração só quando SEED_DEMO=true (idempotente: não duplica nada).
if [ "${SEED_DEMO:-false}" = "true" ]; then
  python manage.py seed_demo
fi
