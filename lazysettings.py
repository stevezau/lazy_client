import os

## DATABASE Settings ##

# SQLITE Setup (DEFAULT)
#DB_TYPE = "sqlite3"

# MySQL Setup
DB_TYPE = "mysql"

#MYSQL Details
MYSQL_USER = 'root'
MYSQL_PASS = 'drift990'
MYSQL_IP = 'localhost'
MYSQL_PORT = '3389'

# Account ID on thetvdb.com
TVDB_ACCOUNTID = "289F895955772DE3"

# Your Timezone
TIME_ZONE = "Australia/Sydney"

# Max downloads
MAX_SIM_DOWNLOAD_JOBS = 1

# Threads per download
THREADS_PER_DOWNLOAD = 3

# Speed per download in KBS, 0 for unlimited
MAX_SPEED_PER_DOWNLOAD = 0

# Path to media folder
DATA_PATH = "/data/Videos"

# Where to store incoming downloads
INCOMING_PATH = os.path.join(DATA_PATH, "_incoming")

# Download folders, shouldnt need to edit this
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


# Flexget get files
FLEXGET_APPROVED = "/home/media/.flexget/approve.yml"
FLEXGET_IGNORE = "/home/media/.flexget/ignore.yml"

# XBMC API (Auto library updates)

XBMC_API_URLS = [
    'http://192.168.0.190:8080/jsonrpc'
]

# Default Queue
#QUEUE = "db"
QUEUE = "rabbitmq"
