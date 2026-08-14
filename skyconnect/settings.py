"""
Django settings for skyconnect project
- Détection automatique de l'environnement (local/production)
- Configuration unique pour les deux environnements
"""

from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Charger .env
load_dotenv(BASE_DIR / '.env', encoding='utf-8')

# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def str_to_bool(value):
    """Convertir une chaîne en booléen"""
    return str(value).lower() in ('true', '1', 'yes', 'on')

def is_docker():
    """Détecter si l'application tourne dans Docker"""
    return os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)

def is_local():
    """Détecter si on est en environnement local"""
    # Si DEBUG est explicitement défini dans .env
    if os.environ.get('DEBUG') is not None:
        return str_to_bool(os.environ.get('DEBUG'))
    
    # Détection automatique
    # - En local : runserver, pas de variable ENVIRONMENT
    # - En production : ENVIRONMENT=production ou variables spécifiques
    if os.environ.get('ENVIRONMENT') == 'production':
        return False
    
    # Détection par le nom du host ou présence de runserver
    import socket
    hostname = socket.gethostname()
    
    # Si c'est un conteneur Docker et que ENVIRONMENT n'est pas défini
    if is_docker() and os.environ.get('ENVIRONMENT') is None:
        return True
    
    # Si c'est localhost
    if hostname in ['localhost', 'MacBook', 'DESKTOP-', 'LAPTOP-']:
        return True
    
    # Par défaut, on considère que c'est le développement
    return True

# ============================================
# ENVIRONNEMENT
# ============================================

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
IS_LOCAL = is_local()
IS_DOCKER = is_docker()
IS_PRODUCTION = ENVIRONMENT == 'production' or not IS_LOCAL

print(f"🚀 Environnement: {'LOCAL' if IS_LOCAL else 'PRODUCTION'}")
print(f"🐳 Docker: {'OUI' if IS_DOCKER else 'NON'}")

# ============================================
# CONFIGURATION DE BASE
# ============================================

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if IS_LOCAL:
        SECRET_KEY = 'django-insecure-local-dev-key-change-me'
    else:
        raise ValueError("DJANGO_SECRET_KEY doit être défini en production")

DEBUG = IS_LOCAL  # DEBUG = True en local, False en production

# Contrôle des prix
HIDE_PRODUCT_PRICES = str_to_bool(os.environ.get('HIDE_PRODUCT_PRICES', 'False'))

# ============================================
# HÔTES AUTORISÉS
# ============================================

if IS_LOCAL:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
    # Si ALLOWED_HOSTS est vide, au moins le domaine de production
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
        ALLOWED_HOSTS = [
            'skyconnect-sa.com',
            'www.skyconnect-sa.com',
            'localhost',
            '127.0.0.1',
        ]

# ============================================
# PROXY SSL
# ============================================

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================
# MÉDIA ET STATIC
# ============================================

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = os.environ.get('STATIC_URL', '/static/')
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ============================================
# APPLICATIONS INSTALLÉES
# ============================================

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

# ============================================
# MIDDLEWARE
# ============================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# En local, on peut désactiver CSRF pour faciliter le développement
# (Décommentez si vous voulez désactiver CSRF en local)
# if IS_LOCAL:
#     MIDDLEWARE = [m for m in MIDDLEWARE if 'csrf' not in m.lower()]

# ============================================
# AUTHENTIFICATION
# ============================================

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# ============================================
# URLS ET TEMPLATES
# ============================================

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
            ],
        },
    },
]

WSGI_APPLICATION = 'skyconnect.wsgi.application'

# ============================================
# BASE DE DONNÉES
# ============================================

DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3')

if 'sqlite' in DB_ENGINE.lower():
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Configuration pour PostgreSQL/MySQL
    DATABASES = {
        'default': {
            'ENGINE': DB_ENGINE,
            'NAME': os.environ.get('DB_NAME', 'skyconnect'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }r

# Base RADIUS (uniquement si configurée)
if os.environ.get('RADIUS_DB_NAME'):
    DATABASES['radius'] = {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('RADIUS_DB_NAME', 'radius'),
        'USER': os.environ.get('RADIUS_DB_USER', 'radius_user'),
        'PASSWORD': os.environ.get('RADIUS_DB_PASSWORD', ''),
        'HOST': os.environ.get('RADIUS_DB_HOST', '192.168.67.17'),
        'PORT': os.environ.get('RADIUS_DB_PORT', '3306'),
    }

# ============================================
# VALIDATEURS DE MOTS DE PASSE
# ============================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================
# INTERNATIONALISATION
# ============================================

LANGUAGE_CODE = 'fr-FR'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# EMAIL
# ============================================

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = str_to_bool(os.environ.get('EMAIL_USE_TLS', 'True'))
EMAIL_USE_SSL = str_to_bool(os.environ.get('EMAIL_USE_SSL', 'False'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# ============================================
# RECAPTCHA
# ============================================

RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY', '')
RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '')

# ============================================
# SÉCURITÉ - Configuration différente selon l'environnement
# ============================================

if IS_LOCAL:
    # Configuration locale (désactivé)
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
else:
    # Configuration production (activé)
    SECURE_SSL_REDIRECT = str_to_bool(os.environ.get('SECURE_SSL_REDIRECT', 'True'))
    SESSION_COOKIE_SECURE = str_to_bool(os.environ.get('SESSION_COOKIE_SECURE', 'True'))
    CSRF_COOKIE_SECURE = str_to_bool(os.environ.get('CSRF_COOKIE_SECURE', 'True'))
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ============================================
# CSRF - Configuration différente selon l'environnement
# ============================================

# Valeurs de base depuis .env
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

if IS_LOCAL:
    # Ajouter automatiquement localhost en développement
    CSRF_TRUSTED_ORIGINS.extend([
        'http://localhost:8000',
        'http://localhost',
        'http://127.0.0.1:8000',
        'http://127.0.0.1',
        'http://0.0.0.0:8000',
        'http://0.0.0.0',
    ])
else:
    # En production, vérifier qu'il y a au moins un domaine
    if not CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS = [
            'https://skyconnect-sa.com',
            'https://www.skyconnect-sa.com',
        ]

# Supprimer les doublons
CSRF_TRUSTED_ORIGINS = list(set(CSRF_TRUSTED_ORIGINS))

# ============================================
# LOGGING - Configuration différente selon l'environnement
# ============================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if IS_LOCAL else 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if IS_LOCAL else ['file'],
            'level': 'DEBUG' if IS_LOCAL else 'INFO',
            'propagate': True,
        },
        'core': {
            'handlers': ['console', 'file'] if IS_LOCAL else ['file'],
            'level': 'DEBUG' if IS_LOCAL else 'INFO',
            'propagate': True,
        },
    },
    'root': {
        'handlers': ['console'] if IS_LOCAL else ['file'],
        'level': 'INFO' if IS_LOCAL else 'WARNING',
    },
}

# Créer le dossier logs
if IS_LOCAL:
    (BASE_DIR / 'logs').mkdir(exist_ok=True)

# ============================================
# AFFICHAGE DES INFORMATIONS DE DEBUG
# ============================================

if IS_LOCAL:
    print("=" * 60)
    print("🔧 ENVIRONNEMENT DE DÉVELOPPEMENT")
    print("=" * 60)
    print(f"📍 Hôte autorisés: {ALLOWED_HOSTS}")
    print(f"🔒 CSRF Trusted Origins: {CSRF_TRUSTED_ORIGINS}")
    print(f"📧 Email Backend: {EMAIL_BACKEND}")
    print(f"🗄️  Base de données: {DB_ENGINE}")
    print("=" * 60)