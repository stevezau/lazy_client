#DONT THIS THESES IMPORTS
import os

# MYSQL Details
MYSQL_USER = 'root'
MYSQL_PASS = 'drift990'
MYSQL_IP = 'localhost'
MYSQL_PORT = '3389'

# TMP folder to store temp files
TMPFOLDER = "/tmp"

#Account ID on thetvdb.com
TVDB_ACCOUNTID = "289F895955772DE3"

TIME_ZONE = "Australia/Sydney"

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
FTP_IP = "66.90.73.180"
FTP_PORT = 32245
FTP_USER = "steve"
FTP_PASS = "site990"


# Shouldnt need to change these
MEDIA_ROOT = "/home/media/lazy/static/media"
MEDIA_URL = "/lazy/media/"

FLEXGET_APPROVED = "/home/media/.flexget/approve.yml"
FLEXGET_IGNORE = "/home/media/.flexget/ignore.yml"

XBMC_API_URLS = [
    'http://192.168.0.190:8080/jsonrpc'
]

QUEUE = "rabbitmq"
