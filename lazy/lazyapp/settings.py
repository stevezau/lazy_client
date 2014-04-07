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

# XBMC Details
QUEUE = "rabbitmq"

XBMC_API = "http://192.168.0.190:8080"

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
MEDIA_ROOT = "/home/media/lazy/static/media"
MEDIA_URL = "/lazy/media/"

FLEXGET_APPROVED = "/home/media/.flexget/approve.yml"
FLEXGET_IGNORE = "/home/media/.flexget/ignore.yml"


XBMC_API_URLS = [
    'http://localhost:8080/jsonrpc'
]

#############################################
#### !!!!DO NOT CHANGE ANYTHING BELOW!!!! ###
#############################################

FTP_TIMEOUT_RETRY_COUNT = 3
FTP_TIMEOUT_RETRY_DELAY = 10  #Seconds
FTP_TIMEOUT_WAIT = 120  #Seconds

DOWNLOAD_RETRY_COUNT = 3
DOWNLOAD_RETRY_DELAY = 15 #minutes

FTP_IGNORE_FILES = (
    '.*-MISSING',
    '^\.$',
    '^\.\.$',
    '.+% Complete.+',
)

VIDEO_FILE_EXTS = (
    '.mkv',
    '.avi',
    '.mp4',
)


TVSHOW_REGEX = (
    '(?i).+\.S[0-9]+E[0-9]+.+',
    '(?i).+\.S[0-9]+\..+',
    '(?i).+\.S[0-9]+-S[0-9]+\..+',
    '(?i).+\.[0-9]+x[0-9]+\..+',
    '(?i).+S[0-9]+E[0-9]+.+',
    '(?i).+Season [0-9]+ Episode [0-9]+',

)

TVSHOW_SEASON_MULTI_PACK_REGEX = (
    '(?i).+S([0-9]+)-S([0-9]+)[\. ].+',
    '(?i).+S([0-9]+)-([0-9]+)[\. ].+',
)

TVSHOW_SPECIALS_REGEX = (
    "(?i).+special.+",
)

TVSHOW_SEASON_PACK_REGEX = (
    "(?i).+\.S[0-9]+\..+",
)

TVSHOW_SEASON_REGEX = (
    "(?i)Season[^0-9]+([0-9]+)",
    "(?i)Season([0-9]+)",
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
    "-": "",
    "!": "",
}

ILLEGAL_CHARS_REGEX = '[:\"*?<>|]+'


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
    'lazycore',
    'lazyapi',
    'lazyui',
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
        'guessit': {
            'handlers':['console'],
            'propagate': True,
            'level':'INFO',
        },
        'GuessMovieTitleFromPosition': {
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
        #'lazycore': {
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
    'lazyui.middleware.LoginRequiredMiddleware',
)

LOGIN_URL = '/lazy/login/'

LOGIN_EXEMPT_URLS = (
    'login/',
    'lazy/api',
    'api'
)

ROOT_URLCONF = 'lazyapp.urls'

WSGI_APPLICATION = 'lazyapp.wsgi.application'


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

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/lazy/static/'
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
    'EXCEPTION_HANDLER': 'lazycore.utils.custom_exception_handler'
}

__VERSION__ = 2


from lazysettings import *


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'lazy',                      # Or path to database file if using sqlite3.
        'USER': MYSQL_USER,                      # Not used with sqlite3.
        'PASSWORD': MYSQL_PASS,                  # Not used with sqlite3.
        'HOST': MYSQL_IP,                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': MYSQL_PORT,                      # Set to empty string for default. Not used with sqlite3.
    }
}

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

for path in [TMPFOLDER,
             MEDIA_ROOT,
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
        raise Exception("Cannot write to folder %s" % path)


##############
### CELERY ###
##############

if QUEUE == "db":
    CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend',
    CELERY_ACKS_LATE = False
    CELERY_TRACK_STARTED = True
    CELERYD_PREFETCH_MULTIPLIER = 1
else:
    BROKER_URL = "amqp://"
    CELERY_RESULT_BACKEND = "amqp://"
    CELERY_ACKS_LATE = False
    CELERY_TRACK_STARTED = True
    CELERYD_PREFETCH_MULTIPLIER = 1