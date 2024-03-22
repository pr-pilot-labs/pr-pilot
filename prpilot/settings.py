"""
Django settings for prpilot project.

Generated by 'django-admin startproject' using Django 4.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
import os
from pathlib import Path

import sentry_sdk

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-lhats43v$iksb*slj3q#@&l(nnp6+cf*1!atj^_elt8^innjrr'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'accounts',
    'webhooks',
    'engine',
    'django_tables2',
    'dashboard'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'

ROOT_URLCONF = 'prpilot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'prpilot.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'postgres',  # Default is 'postgres'
            'USER': 'postgres',
            'PASSWORD': os.getenv('POSTGRES_PASSWORD'),  # Use the password obtained above
            'HOST': 'pr-pilot-db-postgresql.default.svc.cluster.local',  # Use your PostgreSQL service name
            'PORT': '5432',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'nginx' / 'static'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

GITHUB_CLIENT_ID = os.getenv('GITHUB_APP_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_APP_SECRET')
GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET')
GITHUB_APP_ID = os.getenv('GITHUB_APP_ID')

# Add at the end of the file
LOGIN_REDIRECT_URL = '/dashboard/tasks/'  # Redirect to home after login
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_ALLOW_REGISTRATION = False
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        # 'VERIFIED_EMAIL': True,
        # 'EMAIL_AUTHENTICATION': True,
        # 'EMAIL_AUTHENTICATION_AUTO_CONNECT': True,
        'SCOPE': [
            'read:user',
        ],
        'APP': {
            'client_id': GITHUB_CLIENT_ID,
            'secret': GITHUB_CLIENT_SECRET,
        }
    }
}

AUTH_USER_MODEL = 'accounts.PilotUser'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

SOCIAL_AUTH_URL_NAMESPACE = 'social'
PRIVATE_KEY_PATH = os.getenv('GITHUB_APP_PRIVATE_KEY_PATH', os.path.join(BASE_DIR, 'github_app_private_key.pem'))
TASK_ID = os.getenv('TASK_ID')
REPO_DIR = os.getenv('REPO_DIR', '/repo')
MAX_FILE_LINES = 600
MAX_FILE_SEARCH_RESULTS = 50
MAX_READ_FILES = 5
IGNORE_FILE_PATH = Path(os.getcwd()) / ".pilotignore"
CREDIT_MULTIPLIER = 2

APPEND_SLASH = True  # Default is True

if not DEBUG:
    sentry_sdk.init(
        dsn="https://ada4f090ac744c5c947d9d9363d75a29@o4506900506279936.ingest.us.sentry.io/4506900507262976",
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
        debug=False
    )

STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
MILVIUS_HOST = os.getenv('MILVIUS_HOST')
MILVIUS_PORT = os.getenv('MILVIUS_PORT')
MEMORY_SEARCH_THRESHOLD = 0.55