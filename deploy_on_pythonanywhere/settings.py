import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the .env file at the project root
load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR / 'deploy_on_pythonanywhere' / '.env')


# Security settings
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-q5-62e7=nr6e^#t0ixhzt%3(-z+=f9da#mbv%v1)wdh9bpz$+u-'
)

DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')
    if host.strip()
]


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app_suivi',
    'widget_tweaks',
    'captcha', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'deploy_on_pythonanywhere.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'app_suivi' / 'templates',   
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'app_suivi.context_processors.pending_requests',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'deploy_on_pythonanywhere.wsgi.application'


# Database: PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'suivi-projet'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator'
        ),
    },
]


# =========================================================
# INTERNATIONALISATION
# =========================================================
from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = 'ar'               

LANGUAGES = [
    ('ar', _('العربية')),
    ('fr', _('Français')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',            
]

TIME_ZONE = 'Africa/Tunis'

USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']        


# Authentication
LOGIN_URL = '/login/'                            
LOGIN_REDIRECT_URL = '/'                         
LOGOUT_REDIRECT_URL = '/login/'                  


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'