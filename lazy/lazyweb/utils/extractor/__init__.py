from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from lazyweb.models import DownloadItem
import logging, os
from lazyweb.utils.ftpmanager import FTPManager
from decimal import Decimal
from datetime import datetime
import ftplib
import re, shutil
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from lazyweb.utils.extractor.movie import MovieExtractor
from lazyweb.utils.extractor.tvshow import TVExtractor
from lazyweb import utils

logger = logging.getLogger(__name__)


class DownloadItemExtractor():

    download_item = None

    def __init__ (self, dlitem):
        self.download_item = dlitem

    def extract(self):
        #Check files and folders exist
        if not os.path.exists(self.download_item.localpath):
            logger.error('Source file or folder does not exist for. Skipping')
            raise ObjectDoesNotExist("Source file or folder does not exist %s" % self.download_item.localpath)

        extractor_type = None
        dest_folder = None

        #Check what type of download item we are dealing with
        if self.download_item.section == "REQUESTS":
            is_tv_show = False

            if utils.match_str_regex(settings.TVSHOW_REGEX, self.download_item.title) or re.search("(?i).+\.[P|H]DTV\..+", self.download_item.title):
                is_tv_show = True

            if is_tv_show:
                extractor_type = TVExtractor()
                dest_folder = settings.TVHD
            else:
                extractor_type = MovieExtractor()
                dest_folder = settings.HD

        if self.download_item.section == "TVHD":
            extractor_type = TVExtractor()
            dest_folder = settings.TVHD

        if self.download_item.section == "HD":
            extractor_type = MovieExtractor()
            dest_folder = settings.HD

        if self.download_item.section == "XVID":
            extractor_type = MovieExtractor()
            dest_folder = settings.XVID

        if extractor_type is None or not extractor_type:
            raise ObjectDoesNotExist("Unable to find extractor type")

        if dest_folder is None or not dest_folder:
            raise Exception("Unable to figure out destination folder")

        #now we have our extractor, lets do the extracting!
        try:
            passed = extractor_type.extract(self.download_item, dest_folder)

            if passed:
                if os.path.isdir(self.download_item.localpath):
                    shutil.rmtree(self.download_item.localpath)
                self.download_item.status = DownloadItem.COMPLETE
                self.download_item.msg = None
                self.download_item.save()

        except Exception as e:
            self.download_item.retries += 1
            self.download_item.message = e.message
            self.download_item.save()
            logger.exception("error moving %s due to %s" % (self.download_item.localpath, e.message))




