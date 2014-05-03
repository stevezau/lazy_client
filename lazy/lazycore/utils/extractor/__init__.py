from __future__ import division
from lazycore.models import DownloadItem
import logging, os
import re, shutil
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from lazycore.utils.common import match_str_regex
from lazycore.utils.extractor.movie import MovieRenamer
from lazycore.utils.extractor.tvshow import TVRenamer
from django.core.cache import cache
from lazycore.exceptions import ExtractException, ExtractCRCException
from lazycore.utils import common
from datetime import datetime
from lazycore.exceptions import *
from lazycore.utils.metaparser import MetaParser

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes


class Extractor(object):

    type = MetaParser.TYPE_UNKNOWN
    path = None

    def __init__(self, path, type=MetaParser.TYPE_UNKNOWN):
        self.type = type
        self.path = path

    def do_extract(self):

        if os.path.isdir(self.path):
            #First lets try extract everything
            self.extract_files()

        #now lets do the renaming and moving
        if os.path.isfile(self.path):
            #check if its a video file
            if common.is_video_file(self.path):
                self.renamer.rename([self.path])
            else:
                raise InvalidFileException("Is not a valid video file %s" % self.path)
        else:
            #Get a list of media files
            media_files = common.get_video_files(self.path)

            if len(media_files) == 0:
                raise NoMediaFilesFoundException("No media files found")

            logger.debug("Found media files %s" % media_files)

            #offload the processing to the extractor type
            self.renamer.rename(media_files)

    def extract(self):
        #Check files and folders exist
        lock_id = "extract-%s-lock" % self.path
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.delete(lock_id)


        if not acquire_lock():
            logger.debug("Already extracting %s , exiting" % self.path)
            return

        try:
            if not os.path.exists(self.path):
                logger.error('Source file or folder does not exist for. Skipping')
                raise ObjectDoesNotExist("Source file or folder does not exist %s" % self.path)

            #Check what type of download item we are dealing with
            self.parser = MetaParser(os.path.basename(self.path), self.type)

            if self.parser.type == MetaParser.TYPE_UNKNOWN:
                raise ObjectDoesNotExist("Unable to figure out if this is a movie or tvshow")

            if self.parser.type == MetaParser.TYPE_MOVIE:
                self.renamer = MovieRenamer()

            if self.parser.type == MetaParser.TYPE_TVSHOW:
                self.renamer = TVRenamer()

            #now we have our extractor, lets do the extracting!
            self.do_extract()

            if common.get_size(self.path) < 5000:
                logger.info("deleting %s" % self.path)
                common.delete(self.path)


        finally:
            release_lock()


    def extract_files(self):

        #First lets try extract everything.
        archives = common.find_archives(self.path)

        for archive in archives:
            archive_path = os.path.join(archive.path, archive.name)
            logger.info("Extracting %s" % archive_path)
            code = archive.extract()

            if code == 0:
                continue
            else:
                logger.info("Extract failed on %s with error code %s, will now do CRC check on all archives" % (archive_path, code))

                bad_archives = archive.crc_check()

                if len(bad_archives) > 0:
                    raise ExtractException("Failed due to CRC errors in files")


class DownloadItemExtractor(object):

    download_item = None

    def __init__(self, download_item):
        self.download_item = download_item

    def do_extract(self):

        if os.path.isdir(self.download_item.localpath):
            #First lets try extract everything
            self.extract_files()

        #now lets do the renaming and moving
        if os.path.isfile(self.download_item.localpath):
            #check if its a video file
            if common.is_video_file(self.download_item.localpath):
                self.renamer.rename([self.download_item.localpath])
            else:
                raise InvalidFileException("Is not a valid video file %s" % self.download_item.localpath)
        else:
            #Get a list of media files
            media_files = common.get_video_files(self.download_item.localpath)

            if len(media_files) == 0:
                raise NoMediaFilesFoundException("No media files found")

            logger.debug("Found media files %s" % media_files)

            #offload the processing to the extractor type
            self.renamer.rename(media_files)

    def extract(self):
        #Check files and folders exist
        lock_id = "extract-%s-lock" % self.download_item.title
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.debug("Already extracting %s , exiting" % self.download_item.title)
            return

        try:
            if not os.path.exists(self.download_item.localpath):
                logger.error('Source file or folder does not exist for. Skipping')
                raise ObjectDoesNotExist("Source file or folder does not exist %s" % self.download_item.localpath)

            #Check what type of download item we are dealing with
            self.parser = self.download_item.metaparser()

            if self.parser.type == MetaParser.TYPE_UNKNOWN:
                raise ObjectDoesNotExist("Unable to figure out if this is a movie or tvshow")

            if self.parser.type == MetaParser.TYPE_MOVIE:
                self.renamer = MovieRenamer(dlitem=self.download_item)

            if self.parser.type == MetaParser.TYPE_TVSHOW:
                self.renamer = TVRenamer(dlitem=self.download_item)

            #now we have our extractor, lets do the extracting!
            self.do_extract()
            self.log("Extraction passed")
            self.download_item.status = DownloadItem.COMPLETE
            self.download_item.msg = None
            self.download_item.taskid = None
            self.download_item.dlstart = datetime.now()
            self.download_item.save()

            try:
                pass
                common.delete(self.download_item.localpath)
            except:
                pass
        except ManuallyFixException as e:
            logger.error("Error extracting %s" % e)
            self.log("Error extracting %s" % e)
            self.download_item.message = e
            self.download_item.status = DownloadItem.ERROR
            self.download_item.save()
        except ExtractCRCException as e:
            logger.error("Error extracting %s" % e)
            self.log("Error extracting %s" % e)
            self.download_item.message = e
            self.download_item.retries += 1
            self.download_item.status = DownloadItem.QUEUE
            self.download_item.save()
        except Exception as e:
            self.download_item.log(e.message)
            logger.exception("Error extracting %s" % e)
            self.download_item.message = e
            self.download_item.retries += 1
            self.download_item.save()

        finally:
            release_lock()

    def extract_files(self):

        #First lets try extract everything.
        archives = common.find_archives(self.download_item.localpath)

        found_bad_archives = False

        for archive in archives:
            archive_path = os.path.join(archive.path, archive.name)
            self.log("Extracting %s" % archive_path)
            code = archive.extract()

            if code == 0:
                continue
            else:
                self.log("Extract failed on %s with error code %s, will now do CRC check on all archives" % (archive_path, code))

                bad_archives = archive.crc_check()

                for bad_archive in bad_archives:
                    found_bad_archives = True
                    try:
                        self.log("Deleting bad archive %s" % bad_archive)
                        common.delete(bad_archive)
                    except:
                        pass

        if found_bad_archives:
            raise ExtractCRCException("Failed due to CRC errors in files, will try download again")

    def log(self, msg):
        if self.download_item:
            self.download_item.log(msg)
