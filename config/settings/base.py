"""
Configurações comuns do Empório BR — compartilhadas por dev.py e prod.py.

Ver docs/projeto_django_spec.md §1.3 (fonte de verdade destas configurações).
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'core',
    'catalogo',
    'estoque',
    'vendas',
    'relatorios',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.LoginRequiredMiddleware',  # tudo exige login por padrão
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Banco de dados — DATABASE_URL no formato postgres://usuario:senha@host:5432/emporio
DATABASES = {'default': env.db('DATABASE_URL')}
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['ATOMIC_REQUESTS'] = False  # transações explícitas nos serviços (vendas/servicos.py)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Autenticação
AUTH_USER_MODEL = 'core.Usuario'
LOGIN_URL = 'core:login'
LOGIN_REDIRECT_URL = 'core:painel'
LOGOUT_REDIRECT_URL = 'core:login'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'core.hashers.WerkzeugScryptHasher',
]
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6},
    },
]

# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

# Mensagens
from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {messages.ERROR: 'danger'}

# Segurança / sessão
CSRF_COOKIE_HTTPONLY = True  # o JS lê o token do <input name="csrfmiddlewaretoken">, não do cookie
SESSION_COOKIE_AGE = 60 * 60 * 10  # um turno de caixa

# Arquivos estáticos — cada app expõe os seus em <app>/static/<app>/ (AppDirectoriesFinder)
STATIC_URL = 'static/'
