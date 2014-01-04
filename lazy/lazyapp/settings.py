"""
Django settings for LazyApp project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
import os

###################
###Lazy settings###
###################
TMPFOLDER = "/tmp"

MEDIA_ROOT = "/home/media/.lazy/imgs"
MEDIA_URL = "/media/"

FLEXGET_APPROVED = "/home/media/.flexget/approve.yml"
FLEXGET_IGNORE = "/home/media/.flexget/ignore.yml"

TVDB_ACCOUNTID = "289F895955772DE3"

LFTP_BIN = "/usr/local/bin/lftp"

MAX_SIM_DOWNLOAD_JOBS = 2
LFTP_THREAD_PER_DOWNLOAD = 3

DATA_PATH = os.sep + "data" + os.sep + "Videos"
INCOMING_PATH = os.path.join(DATA_PATH, "_incoming")

TVHD_TEMP = os.path.join(INCOMING_PATH, "TVShows")
HD_TEMP = os.path.join(INCOMING_PATH, "Movies")
XVID_TEMP = os.path.join(INCOMING_PATH, "Movies")
REQUESTS_TEMP = os.path.join(INCOMING_PATH, "Requests")

TVHD = os.path.join(DATA_PATH, "TVShows")
HD = os.path.join(DATA_PATH, "Movies")
XVID = os.path.join(DATA_PATH, "Movies")

FTP_IP = "66.90.113.62"
FTP_PORT = 32245
FTP_USER = "steve"
FTP_PASS = "site990"

#############################################
#### !!!!DO NOT CHANGE ANYTHING BELOW!!!! ###
#############################################

TVSHOW_REGEX = (
    '(?i).+\.S[0-9]+E[0-9]+.+',
    '(?i).+\.S[0-9]+\..+',
    '(?i).+\.S[0-9]+-S[0-9]+\..+',
    '(?i).+\.[0-9]+x[0-9]+\..+',
    '(?i).+S[0-9]+E[0-9]+.+',
    '(?i).+Season [0-9]+ Episode [0-9]+',
)

TVSHOW_SEASON_MULTI_PACK_REGEX = (
    "(?i).+\.S[0-9]+-[0-9]+\..+",
    "(?i).+\.S[0-9]+-S[0-9]+\..+",
)

TVSHOW_SPECIALS_REGEX = (
    "(?i).+special.+",
)

TVSHOW_SEASON_PACK_REGEX = (
    "(?i).+\.S[0-9]+\..+",
)

MOVIE_PACKS_REGEX = (
    "(?i).+\.(TRiLOGY|PACK|Duology|Pentalogy)\..+",
)

DOCOS_REGEX = (
    "(?i)^(History\.Channel|Discovery\.Channel|National\.Geographic).+",
)

SAMPLES_REGEX = (
    "(?i).*-sample",
    "(?i).*_sample",
    "(?i).*(sample)",
    "(?i).*sample",
    "(?i)sample",
    "(?i)extras",
    "(?i)subpack",
)

QUALITY_REGEX = (
    "360p",
    "368p",
    "480p",
    "576p",
    "hr",
    "720i",
    "720p",
    "1080i",
    "1080p",
)

TVSHOW_AUTOFIX_REPLACEMENTS = {
    "Australia": "AU",
    "'": "",
    "(": "",
    ")": "",
    "!": "",
}

ILLEGAL_CHARS_REGEX = '[():\"*?<>|]+'

#########################
### CHECK LAZY PATHTS ###
#########################

for path in [FLEXGET_APPROVED,
             FLEXGET_IGNORE,
             TMPFOLDER,
             MEDIA_ROOT,
             LFTP_BIN,
             DATA_PATH,
             INCOMING_PATH,
             TVHD,
             TVHD_TEMP,
             XVID,
             XVID_TEMP,
             REQUESTS_TEMP,
             HD,
             HD_TEMP]:
    if not os.path.exists(path):
        raise Exception("Folder dose not exist %s" % path)
    if not os.access(path, os.W_OK):
        raise Exception("Cannot write to folder " % path)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'afizuu0e=b50x8!eu7n3-7e+0yv*u$mpxrdoi%@9f9^h)!q3)c'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True
TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

ALLOWED_HOSTS = []

import djcelery
djcelery.setup_loader()

#CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
BROKER_URL = 'django://'

# Application definition

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'logfile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR + "/logfile",
            'maxBytes': 50000,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        'django': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'south': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        '': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
        #'lazyapi': {
        #    'handlers': ['console', 'logfile'],
        #    'level': 'DEBUG',
        #},
    }
}

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'rest_framework',
    'sitetree',
    'south',
    'jquery',
    'djcelery',
    'kombu.transport.django',
    'jquery_ui',
    'django_mobile',
    'lazyweb',
    'lazyapi',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_mobile.middleware.MobileDetectionMiddleware',
    'django_mobile.middleware.SetFlavourMiddleware',
)

ROOT_URLCONF = 'lazyapp.urls'

WSGI_APPLICATION = 'lazyapp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.default'),
    },
}

#DATABASE_ROUTERS = ['lazyapp.router.LazyRouter']

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'django_mobile.context_processors.flavour',
)

TEMPLATE_LOADERS = (
    'django_mobile.loader.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)


REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'lazyweb.utils.custom_exception_handler'
}


