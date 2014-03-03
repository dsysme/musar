"""
Django settings for musar project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'v8g!bqfl3swprhwjg5^=+_j4ckn8m)a-ynfwlgrknz85szaomf'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

AUTH_PROFILE_MODULE = 'payments.UserProfile'


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'payments',
    'django_tables2',
    'floppyforms',
)

MIDDLEWARE_CLASSES = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)
TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.request",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages"
)
ROOT_URLCONF = 'musar.urls'

WSGI_APPLICATION = 'musar.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'he'

LOCALE_PATHS = ('c:\Hackita\MusarP\locale',
)

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

INTERNAL_IPS = ('127.0.0.1',)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

LOGIN_URL = "/login/"
# LOGIN_REDIRECT_URL = "home"

TEMPLATE_STRING_IF_INVALID = "Opps"


# Overide global with local settings
# TODO FIXME Is it right to just print the error and continue as nothing happened here?
try:  # Build paths inside the project like this: os.path.join(BASE_DIR, ...)
    import local_settings
    BASE_DIR = local_settings.BASE_DIR
    DEBUG = local_settings.DEBUG
    EMAIL_BACKEND = local_settings.EMAIL_BACKEND
    DATABASES = local_settings.DATABASES
    SECRET_KEY = local_settings.SECRET_KEY
    ALLOWED_HOSTS = local_settings.ALLOWED_HOSTS
    STATIC_ROOT = local_settings.STATIC_ROOT
    STATICFILES_DIRS = local_settings.STATICFILES_DIRS
    INSTALLED_APPS = local_settings.INSTALLED_APPS + INSTALLED_APPS
    LOCALE_PATHS = local_settings.LOCALE_PATHS
    
except ImportError as e:
    print e
