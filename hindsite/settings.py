"""
Django settings for hindsite project.

Generated by 'django-admin startproject' using Django 1.10.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
import boto3
from botocore.client import Config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ON_HEROKU = os.environ.get('ON_HEROKU')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'xf0#m+=ghvllbpj_q570cj!xe(z=kj^-kr8_0ke=8m0&qj4$gz'

# SECURITY WARNING: don't run with debug turned on in production!
if ON_HEROKU:
    DEBUG = False
    ALLOWED_HOSTS = ['*']
else:
    DEBUG = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'history.apps.HistoryConfig',
    'analytics',
    'authentication',
    'search',
    'corsheaders',
    'django_extensions',
    'pytz',
    'djcelery',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    )
}

CORS_ORIGIN_WHITELIST = [
    'chrome-extension://ocpchccceiphbojcehihihigmoppoflg',
]

ROOT_URLCONF = 'hindsite.urls'

WSGI_APPLICATION = 'hindsite.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the %s environment variable" % var_name
        raise ImproperlyConfigured(error_msg)


if ON_HEROKU:
    import dj_database_url
    db_from_env = dj_database_url.config(conn_max_age=500)
    DATABASES = {'default': db_from_env}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': get_env_variable('DATABASE_NAME'),
            'USER': get_env_variable('DATABASE_USER'),
            'PASSWORD': get_env_variable('DATABASE_PASSWORD'),
            'HOST': '',
            'PORT': '',
        }
    }

# Search

if ON_HEROKU:
    SEARCH_BASE_URI = 'http://ec2-54-211-219-100.compute-1.amazonaws.com:9200/'
else:
    SEARCH_BASE_URI = 'http://127.0.0.1:9200/'


# S3

AWS_ACCESS_KEY_ID = get_env_variable('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = get_env_variable('AWS_SECRET_ACCESS_KEY')

if ON_HEROKU:
    AWS_STORAGE_BUCKET_NAME = 'hindsite-production'
    AWS_BUCKET_URL = 'https://s3.us-east-2.amazonaws.com/hindsite-production/'
else:
    AWS_STORAGE_BUCKET_NAME = 'hindsite-local'
    AWS_BUCKET_URL = 'https://s3.us-east-2.amazonaws.com/hindsite-local/'

S3_CLIENT = boto3.client('s3', 'us-east-1', aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        config=Config(signature_version='s3v4'))


# Celery

if ON_HEROKU:
    BROKER_URL = get_env_variable('CLOUDAMQP_URL')
    BROKER_POOL_LIMIT = 1
    BROKER_HEARTBEAT = None # We're using TCP keep-alive instead
    BROKER_CONNECTION_TIMEOUT = 30 # May require a long timeout due to Linux DNS timeouts etc
    CELERY_RESULT_BACKEND = None # AMQP is not recommended as result backend as it creates thousands of queues
    CELERY_SEND_EVENTS = False # Will not create celeryev.* queues
    CELERY_EVENT_QUEUE_EXPIRES = 60 # Will delete all celeryev. queues without consumers after 1 minute.
else:
    BROKER_URL = "amqp://hindsite:hindsite@localhost:5672/myvhost"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'


AUTH_USER_MODEL = 'authentication.CustomUser'


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

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

if ON_HEROKU:
    RQ_QUEUES = {
        'default': {
            'URL': os.getenv('REDISTOGO_URL', 'redis://localhost:6379/0'), # If you're on Heroku
            'DEFAULT_TIMEOUT': 500,
        }
    }
else:
    RQ_QUEUES = {
        'default': {
            'HOST': 'localhost',
            'PORT': 6379,
            'DB': 0,
            'PASSWORD': '',
            'DEFAULT_TIMEOUT': 360,
        },
        'high': {
            'URL': os.getenv('REDISTOGO_URL', 'redis://localhost:6379/0'), # If you're on Heroku
            'DEFAULT_TIMEOUT': 500,
        },
        'low': {
            'HOST': 'localhost',
            'PORT': 6379,
            'DB': 0,
        }
    }


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_ROOT, "templates")],
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

EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'admin@hindsitehistory.com'
EMAIL_HOST = 'smtp.zoho.com'
EMAIL_HOST_USER = 'admin@hindsitehistory.com'
EMAIL_HOST_PASSWORD = get_env_variable('EMAIL_PASSWORD')
EMAIL_PORT = 587
