from .base import *  # noqa
import os
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'abtin-demo-render-secret-key-change-this-in-production-2026')
if len(SECRET_KEY) < 32:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY must be at least 32 characters long.')

DEBUG = False
render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
configured_hosts = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', '').split(',') if host.strip()]
ALLOWED_HOSTS = list(dict.fromkeys(configured_hosts + ([render_host] if render_host else [])))
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must contain explicit production hostnames.')

frontend_url = os.environ.get('FRONTEND_URL', '').strip().rstrip('/')
default_origin = f'https://{render_host}' if render_host else ''
CORS_ALLOWED_ORIGINS = [x for x in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if x.strip()] or ([frontend_url] if frontend_url else [default_origin] if default_origin else [])
CSRF_TRUSTED_ORIGINS = [x for x in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if x.strip()] or ([frontend_url] if frontend_url else [default_origin] if default_origin else [])

# Render terminates TLS at its edge and forwards the original scheme.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Render Postgres can be supplied as a single DATABASE_URL.
# If the service was created manually without a database yet, fall back to
# SQLite so the demo can boot instead of crashing at startup.
database_url = os.environ.get('DATABASE_URL', '').strip()
if database_url:
    parsed = urlparse(database_url)
    if parsed.scheme not in {'postgres', 'postgresql'}:
        raise ImproperlyConfigured('DATABASE_URL must be a PostgreSQL URL.')
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed.path.lstrip('/'),
        'USER': parsed.username or '',
        'PASSWORD': parsed.password or '',
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or 5432),
        'ATOMIC_REQUESTS': False,
        'CONN_MAX_AGE': 60,
        'OPTIONS': {'sslmode': os.environ.get('DB_SSLMODE', 'require')},
    }
else:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'render-demo.sqlite3',
    }

# Redis is optional for the single-service demo.
if not os.environ.get('REDIS_URL'):
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
    }
