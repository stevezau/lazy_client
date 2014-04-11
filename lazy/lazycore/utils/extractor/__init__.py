from __future__ import division
from lazycore.models import DownloadItem
import logging, os
import re, shutil
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from lazycore.utils.common import match_str_regex
from lazycore.utils.extractor.movie import MovieExtractor
from lazycore.utils.extractor.tvshow import TVExtractor
from django.core.cache import cache

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes

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

        lock_id = "extract-%s-lock" % self.download_item.title
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.debug("Already extracting %s , exiting" % self.download_item.title)
            return

        try:

            logger.info('Performing queue update')

            #Check what type of download item we are dealing with
            if self.download_item.section == "REQUESTS":
                is_tv_show = False

                if match_str_regex(settings.TVSHOW_REGEX, self.download_item.title) or re.search("(?i).+\.[P|H]DTV\..+", self.download_item.title):
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
                    self.download_item.log("Extraction passed")
                    self.download_item.status = DownloadItem.COMPLETE
                    self.download_item.msg = None
                    self.download_item.save()

                    if os.path.isdir(self.download_item.localpath):
                        shutil.rmtree(self.download_item.localpath)


            except Exception as e:
                logger.exception("error moving %s due to %s" % (self.download_item.localpath, e.message))
                self.download_item.log("Exception during extraction: %s" % e)
                self.download_item.retries += 1
                self.download_item.message = e
                self.download_item.save()

        finally:
            release_lock()

