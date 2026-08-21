"""
Django settings for skyconnect project
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Charger .env
load_dotenv(BASE_DIR / '.env', encoding='utf-8')

# Helper pour parser les booléens
def str_to_bool(value):
    return str(value).lower() in ('true', '1', 'yes')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY doit être défini.')
DEBUG = str_to_bool(os.environ.get('DEBUG', 'False'))

# contrôle si les prix des produits doivent être cachés partout sur le site
# (forfaits et tickets ne sont pas concernés)
HIDE_PRODUCT_PRICES = str_to_bool(os.environ.get('HIDE_PRODUCT_PRICES', 'False'))

ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', '').split(',') if host.strip()]
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS doit être défini lorsque DEBUG=False.')

# If Django is running behind a proxy doing SSL termination (e.g. external nginx)
# we need to tell it which header indicates the original request scheme.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = BASE_DIR / 'media'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'django_cleanup',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Public login removed: authentication disabled for public site
ROOT_URLCONF = 'skyconnect.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.logo_context',
                'core.context_processors.panier_count',
                'core.context_processors.menu_categories',
                'core.context_processors.site_settings',
                # Google OAuth context removed
            ],
        },
    },
]

WSGI_APPLICATION = 'skyconnect.wsgi.application'

DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3')
if 'sqlite' in DB_ENGINE.lower():
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        },
    }
    if os.environ.get('RADIUS_DB_HOST'):
        DATABASES['radius'] = {
            'ENGINE': os.environ.get('RADIUS_DB_ENGINE', 'django.db.backends.mysql'),
            'NAME': os.environ.get('RADIUS_DB_NAME', 'radius'),
            'USER': os.environ.get('RADIUS_DB_USER'),
            'PASSWORD': os.environ.get('RADIUS_DB_PASSWORD'),
            'HOST': os.environ['RADIUS_DB_HOST'],
            'PORT': os.environ.get('RADIUS_DB_PORT', '3306'),
        }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-FR'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
            
STATIC_URL = os.environ.get('STATIC_URL', '/static/')
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Configuration (from .env)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = str_to_bool(os.environ.get('EMAIL_USE_TLS', 'True'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY', '')
RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '')

# Security (from .env)
SECURE_SSL_REDIRECT = str_to_bool(os.environ.get('SECURE_SSL_REDIRECT', 'False'))
SESSION_COOKIE_SECURE = str_to_bool(os.environ.get('SESSION_COOKIE_SECURE', 'False'))
CSRF_COOKIE_SECURE = str_to_bool(os.environ.get('CSRF_COOKIE_SECURE', 'False'))
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0

# A single Gunicorn worker is used by default. Replace this cache with Redis
# before scaling the application to multiple processes or hosts.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'skyconnect-production',
    }
}

# CSRF Trusted Origins (from .env)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
