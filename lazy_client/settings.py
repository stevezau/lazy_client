"""
Django settings for LazyApp project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CELERYD_PID_FILE = os.path.join(BASE_DIR, "celeryd.pid")

###################
###Lazy settings###
###################

__VERSION__ = 3

QUEUE = "rabbitmq"

# MYSQL Details
MYSQL_USER = 'root'
MYSQL_PASS = 'password'
MYSQL_IP = 'localhost'
MYSQL_PORT = '3389'

TMPFOLDER = "/tmp"
TVDB_ACCOUNTID = "XXXXXXXXX"

MAX_SIM_DOWNLOAD_JOBS = 1
THREADS_PER_DOWNLOAD = 3

# Where is your data path
DATA_PATH = "/data/Videos"
INCOMING_PATH = os.path.join(DATA_PATH, "_incoming")

# Folders, shouldnt need to edit this

TVHD_TEMP = os.path.join(INCOMING_PATH, "TVShows")
HD_TEMP = os.path.join(INCOMING_PATH, "Movies")
XVID_TEMP = os.path.join(INCOMING_PATH, "Movies")
REQUESTS_TEMP = os.path.join(INCOMING_PATH, "Requests")

TVHD = os.path.join(DATA_PATH, "TVShows")
HD = os.path.join(DATA_PATH, "Movies")
XVID = os.path.join(DATA_PATH, "Movies")

# FTP Details
FTP_IP = "66.90.113.61"
FTP_PORT = 32245
FTP_USER = "XXXXXX"
FTP_PASS = "XXXXX"

# Shouldnt need to change these
MEDIA_ROOT = os.path.join(BASE_DIR, "static/media")
MEDIA_URL = "/media/"

FLEXGET_APPROVED = "/home/media/.flexget/approve.yml"
FLEXGET_IGNORE = "/home/media/.flexget/ignore.yml"


XBMC_API_URLS = [
    'http://localhost:8080/jsonrpc'
]

FREE_SPACE = 30 #GB

ALLOWED_IPS = [
    '192.168.0.1/24'
]

#############################################
#### !!!!DO NOT CHANGE ANYTHING BELOW!!!! ###
#############################################

WEBSERVER_IP = "0.0.0.0"
WEBSERVER_PORT = 8000
WEBSERVER_ERROR_LOG = os.path.join(BASE_DIR, "logs/web_access.log")
WEBSERVER_ACCESS_LOG = os.path.join(BASE_DIR, "logs/web_error.log")
WEBSERVER_PIDFILE = os.path.join(BASE_DIR, "lazy_web_server.pid")

FTP_TIMEOUT_RETRY_COUNT = 3
FTP_TIMEOUT_RETRY_DELAY = 10  #Seconds
FTP_TIMEOUT_CONNECT = 120  #Seconds
FTP_TIMEOUT_TRANSFER = 30  #Seconds
FTP_TIMEOUT_MIN_SPEED = 3096 #bytes

DOWNLOAD_RETRY_COUNT = 3
DOWNLOAD_RETRY_DELAY = 15 #minutes

FTP_IGNORE_FILES = (
    '.*-MISSING',
    '^\.$',
    '^\.\.$',
    '.+% Complete.+',
)

TVSHOW_SEASON_MULTI_PACK_REGEX = (
    '(?i).+S([0-9]+)-S([0-9]+)[\. ].+',
    '(?i).+S([0-9]+)-([0-9]+)[\. ].+',
)


TVSHOW_SEASON_PACK_REGEX = (
    "(?i).+\.S[0-9]+\..+",
)

MOVIE_PACKS_REGEX = (
    "(?i).+\.(TRiLOGY|PACK|Duology|Pentalogy)\..+",
)

DOCO_REGEX = (
    {"regex": "(?i)^(History.Channel).+", "name": "History Channel Docos"},
    {"regex": "(?i)^(Discovery.Channel).+", "name": "Discovery Channel Docos"},
    {"regex": "(?i)^(National.Geographic).(?!Wild)", "name": "National Geographic Docos"},
    {"regex": "(?i)^(National.Geographic.Wild).+", "name": "National Geographic Wild Docos"},
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
    "-": "",
    "!": "",
}

ILLEGAL_CHARS_REGEX = '[:\"*?<>|]+'




# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'afizuu0e=b50x8!eu7n3-7e+0yv*u$mpxrdoi%@9f9^h)!q3)c'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True
TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

#ALLOWED_HOSTS = []

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
    'jquery_ui',
    'django_mobile',
    'lazy_client_core',
    'lazy_client_api',
    'lazy_client_ui',
)

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
            'filename': BASE_DIR + "/logs/web_server.log",
            'maxBytes': 50000,
            'backupCount': 4,
            'formatter': 'standard',
        },
        'console':{
            'level':'INFO',
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
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'stevedore.extension': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        '': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
        },

        #'lazy_client_core': {
        #    'handlers': ['console'],
        #    'level': 'DEBUG',
        #},
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'lazy_cache',
    }

}

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
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

ROOT_URLCONF = 'lazy_client.urls'

WSGI_APPLICATION = 'lazy_client.wsgi.application'


# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_L10N = True
USE_TZ = True

INTERNAL_IPS = (
    '192.168.0.200'
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
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)


REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'lazy_client_api.utils.custom_exception_handler'
}
# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
import lazysettings

try:
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
except:
    pass

from lazysettings import *

#########################
### CHECK LAZY PATHTS ###
#########################

if not os.path.isfile(FLEXGET_IGNORE):
    #Lets create it
    ignore_file = open(FLEXGET_IGNORE, 'a')
    ignore_file.write("regexp:\n")
    ignore_file.write("  from: title\n")
    ignore_file.write("  reject:\n")
    ignore_file.write("    - ^FIRST.IGNORE.DEL.ME.AFTER.YOU.ADD.MORE\n")
    ignore_file.close()

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
    os.mkdir(MEDIA_ROOT)

if not os.path.exists(os.path.join(BASE_DIR, "logs")):
    os.mkdir(os.path.join(BASE_DIR, "logs"))




##############
### CELERY ###
##############
if QUEUE == "db":
    CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend',
    CELERY_ACKS_LATE = False
    CELERY_TRACK_STARTED = True
    CELERYD_PREFETCH_MULTIPLIER = 1
    INSTALLED_APPS = INSTALLED_APPS + ('django.contrib.session')
else:
    BROKER_URL = "amqp://"
    CELERY_RESULT_BACKEND = "amqp://"
    CELERY_ACKS_LATE = False
    CELERY_TRACK_STARTED = True
    CELERYD_PREFETCH_MULTIPLIER = 1

CELERYD_PID_FILE = os.path.join(BASE_DIR, "celeryd.pid")
CELERY_BEAT_PID_FILE = os.path.join(BASE_DIR, "celeryd_beat.pid")