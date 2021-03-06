"""
Django settings for LazyApp project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

###################
###Lazy settings###
###################

__VERSION__ = 10

QUEUE = "rabbitmq"
DB_TYPE = "mysql"

# MYSQL Details
MYSQL_USER = 'root'
MYSQL_PASS = 'password'
MYSQL_IP = 'localhost'
MYSQL_PORT = '3389'

TMPFOLDER = "/tmp"
TVDB_ACCOUNTID = "XXXXXXXXX"

MAX_SIM_DOWNLOAD_JOBS = 1
THREADS_PER_DOWNLOAD = 3
MAX_SPEED_PER_DOWNLOAD = 0

# Where is your data path
DATA_PATH = "/data/Videos"
INCOMING_PATH = os.path.join(DATA_PATH, "_incoming")

# Folders, shouldnt need to edit this

TV_PATH_TEMP = os.path.join(INCOMING_PATH, "TVShows")
MOVIE_PATH_TEMP = os.path.join(INCOMING_PATH, "Movies")
REQUESTS_PATH_TEMP = os.path.join(INCOMING_PATH, "Requests")

TV_PATH = os.path.join(DATA_PATH, "TVShows")
MOVIE_PATH = os.path.join(DATA_PATH, "Movies")

# Shouldnt need to change these
MEDIA_ROOT = os.path.join(BASE_DIR, "static/media")
MEDIA_URL = "/media/"

FLEXGET_APPROVED = "/home/media/.flexget/approve.yml"


XBMC_API_URLS = 'http://localhost:8080/jsonrpc'

FREE_SPACE = 30 #GB

ALLOWED_IPS = [
    '192.168.0.1/24'
]

#############################################
#### !!!!DO NOT CHANGE ANYTHING BELOW!!!! ###
#############################################

WEBSERVER_IP = "0.0.0.0"
WEBSERVER_PORT = 8000
WEBSERVER_ERROR_LOG = os.path.join(BASE_DIR, "logs/lazy_access.log")
WEBSERVER_ACCESS_LOG = os.path.join(BASE_DIR, "logs/lazy_error.log")
WEBSERVER_PIDFILE = os.path.join(BASE_DIR, "lazy.pid")


DOWNLOAD_RETRY_COUNT = 3
DOWNLOAD_RETRY_DELAY = 15 #minutes

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

VIDEO_FILE_EXTS = (
    'mkv',
    'avi',
    'mp4',
    'iso',
    'avi',
    'm4v',
    'mpg',
)

TVSHOW_AUTOFIX_REPLACEMENTS = {
    "Australia": "AU",
    "'": "",
    "(": "",
    ")": "",
    ":": "",
    "-": " ",
    "!": "",
    ",": " ",
    ".": " ",
    "?": "",
}

ILLEGAL_CHARS_REGEX = '[:\"*?<>|]+'

#Image processor
CONVERT_PATH = None

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'afizuu0e=b50x8!eu7n3-7e+0yv*u$mpxrdoi%@9f9^h)!q3)c'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = False
TEMPLATE_DIRS = [
    os.path.join(BASE_DIR, 'templates'),
    os.path.join(BASE_DIR, "lazy_client_ui", 'templates'),
    ]

#ALLOWED_HOSTS = []


PAGINATION_SETTINGS = {
    'PAGE_RANGE_DISPLAYED': 3,
    'MARGIN_PAGES_DISPLAYED': 1,
}

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',
    'rest_framework',
    'sitetree',
    'south',
    'jquery',
    'jquery_ui',
    'django_mobile',
    'crispy_forms',
    'lazy_client_core',
    'lazy_client_api',
    'lazy_client_ui',
    'lazy_common',
    'pure_pagination',
)


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'lazy_cache',
    }

}

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'htmlmin.middleware.HtmlMinifyMiddleware',
    'django.middleware.common.CommonMiddleware',
    'htmlmin.middleware.MarkRequestMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_mobile.middleware.MobileDetectionMiddleware',
    'django_mobile.middleware.SetFlavourMiddleware',
    'lazy_client_ui.middleware.LoginRequiredMiddleware',
)


LOGIN_EXEMPT_URLS = (
    'login/',
    'lazy/api',
    'api'
)

LOGIN_URL = "/login"

ROOT_URLCONF = 'lazy_client.urls'

WSGI_APPLICATION = 'lazy_client.wsgi.application'


CRISPY_TEMPLATE_PACK = 'bootstrap3'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_L10N = True
USE_TZ = True

INTERNAL_IPS = (
    '192.168.0.200',
    '115.64.6.2',
    '127.0.0.1',
)

PWD_PROTECT = True

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
    'lazy_client_ui.context_processors.errors',
)


TEMPLATE_LOADERS = (
    'django_mobile.loader.Loader',
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'lazy_client_api.utils.custom_exception_handler'
}
# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

ALLOWED_HOSTS = ['*']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'logfile'],
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'logfile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR + "/logs/lazy.log",
            'maxBytes': 1000000,
            'backupCount': 8,
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
            'handlers':['console', 'logfile'],
            'propagate': True,
            'level':'DEBUG',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'guessit': {
            'handlers':['console'],
            'propagate': True,
            'level':'ERROR',
        },
        'GuessMovieTitleFromPosition': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'GuessYear': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'GuessLanguage': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'GuessProperties': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'GuessReleaseGroup': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'GuessEpisodesRexps': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'GuessEpisodeInfoFromPosition': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'GuessFiletype': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'south': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'stevedore.extension': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'tvdb_api': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
        '': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },
    }
}


import lazysettings
from lazysettings import *

if DEBUG:
    INSTALLED_APPS = INSTALLED_APPS + ("debug_toolbar",)

if DB_TYPE == "mysql":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'lazy',                      # Or path to database file if using sqlite3.
            'USER': lazysettings.MYSQL_USER,                      # Not used with sqlite3.
            'PASSWORD': lazysettings.MYSQL_PASS,                  # Not used with sqlite3.
            'HOST': lazysettings.MYSQL_IP,                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': lazysettings.MYSQL_PORT,                      # Set to empty string for default. Not used with sqlite3.
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'lazy.db',
            'OPTIONS': {
                "timeout": 10,
            }
        }
    }

from lazy_common import utils

# FTP Details
from lazy_common import ftpmanager
ftpmanager.FTP_IP = lazysettings.FTP_IP
ftpmanager.FTP_PORT = lazysettings.FTP_PORT
ftpmanager.FTP_USER = lazysettings.FTP_USER
ftpmanager.FTP_PASS = lazysettings.FTP_PASS

LAZY_USER = lazysettings.LAZY_USER
LAZY_PWD = lazysettings.LAZY_PWD

#########################
### CHECK LAZY PATHTS ###
#########################

if not os.path.isfile(FLEXGET_APPROVED):
    #Lets create it
    approved_file = open(FLEXGET_APPROVED, 'a')
    approved_file.write("regexp:\n")
    approved_file.write("  from: title\n")
    approved_file.write("  accept:\n")
    approved_file.write("    - national.geographic\n")
    approved_file.write("    - discovery.channel\n")
    approved_file.write("    - history.channel\n")
    approved_file.close()

if not os.path.exists(MEDIA_ROOT):
    #create it

    utils.mkdir(MEDIA_ROOT)

if not os.path.exists(os.path.join(BASE_DIR, "logs")):
    utils.mkdir(os.path.join(BASE_DIR, "logs"))