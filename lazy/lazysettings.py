#DONT THIS THESES IMPORTS
import os

# MYSQL Details

MYSQL_USER = 'root'
MYSQL_PASS = 'xxxx'
MYSQL_IP = 'localhost'
MYSQL_PORT = '3389'

# TMP folder to store temp files
TMPFOLDER = "/tmp"

#Account ID on thetvdb.com
TVDB_ACCOUNTID = "xxxxxxxxxx"


MAX_SIM_DOWNLOAD_JOBS = 2
LFTP_THREAD_PER_DOWNLOAD = 3

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
FTP_IP = "66.90.113.62"
FTP_PORT = 32245
FTP_USER = "xxxx"
FTP_PASS = "xxxx"

LFTP_BIN = "/usr/local/bin/lftp"


# Shouldnt need to change these
MEDIA_ROOT = "/home/media/lazy/static/media"
MEDIA_URL = "/lazy/media/"

FLEXGET_APPROVED = "/home/media/.flexget/approve.yml"
FLEXGET_IGNORE = "/home/media/.flexget/ignore.yml"