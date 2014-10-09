__author__ = 'Steve'
from django.conf import settings
import os
from lazy_client_core.models import Job
from lazy_client_core.utils.missingscanner.tvshow import TVShow
from celery import task
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

#EP STATUS
EP_MISSING = "ep_missing"
DOWNLOADING_EP_FROM_FTP = "downloading_from_ftp"
EP_ALREADY_PROCESSED = "ep_already_processed"
FOUND_EP = "found_ep"
FOUND_EP_TORRENT = "found_ep_torrent"
EP_FAILED = "failed_ep"
DIDNT_FIND_EP = "didnt_find_ep"

#SEASON STATUS
SEASON_MISSING = "missing"
WONT_FIX = "wont_fix"
SEASON_EXISTS = "exists"
DOWNLOADING_SEASON = "downloading_entire_season"

#BOTH
ALREADY_IN_QUEUE = "already_in_queue"

