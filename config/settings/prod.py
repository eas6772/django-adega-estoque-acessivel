from .base import *  # noqa: F401,F403
from .base import DATABASES, MIDDLEWARE, env

DEBUG = False

# Hosts: ALLOWED_HOSTS (lista separada por vírgula) + o domínio que o Render injeta sozinho
# em RENDER_EXTERNAL_HOSTNAME (ex.: emporio-br-django.onrender.com).
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
_host_render = env('RENDER_EXTERNAL_HOSTNAME', default='')
if _host_render:
    ALLOWED_HOSTS.append(_host_render)
    CSRF_TRUSTED_ORIGINS.append(f'https://{_host_render}')

# Banco gerenciado (Supabase): conexão sempre com TLS.
DATABASES['default'].setdefault('OPTIONS', {}).setdefault('sslmode', 'require')

# Arquivos estáticos servidos pelo próprio app via WhiteNoise (logo após o SecurityMiddleware,
# antes do LoginRequiredMiddleware: o CSS da tela de login precisa carregar sem sessão).
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
