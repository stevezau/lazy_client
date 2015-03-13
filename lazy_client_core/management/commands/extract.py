from __future__ import division
from optparse import make_option
import logging
import os

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from lazy_client_core.models import DownloadItem
from lazy_client_core.utils import extractor
from lazy_common.utils import delete, get_size
from lazy_client_core.utils import renamer
from lazy_client_core.exceptions import *
from lazy_common import metaparser
from lazy_client_core.utils import common


logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 20 # Lock expires in 20 minutes

class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Your help message"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list + (
                        make_option('--all', action='store_true',
                            dest='extract_all',
                            default=False,
                            help='Try to rename files that lazy didnt download'),
                        make_option('--path', action='store',
                            dest='extract_path',
                            default=False,
                            help='Extract Specific folder'),
                  )

    def _extract_others(self, path, parser_type=metaparser.TYPE_UNKNOWN):
        for f in os.listdir(path):
            full_path = os.path.join(path, f)

            #Is this from lazy?
            try:
                DownloadItem.objects.get(localpath=full_path)
                #we dont want to process so pass
                pass
            except ObjectDoesNotExist:
                try:
                    logger.info("Will try extract %s" % full_path.encode('ascii', 'ignore'))

                    if get_size(full_path) == 0:
                        logger.info("Empty folder %s, will delete" % full_path)
                        delete(full_path)
                        continue

                    try:
                        extractor.extract(full_path)
                    except ExtractException as e:
                        logger.debug("Error extracting %s %s" % (str(e), full_path.encode('ascii', 'ignore')))
                    except ExtractCRCException as e:
                        logger.debug("Error extracting %s %s" % (str(e), full_path.encode('ascii', 'ignore')))


                    logger.info("Will try rename %s" % full_path)

                    try:
                        renamer.rename(full_path, type=parser_type)
                    except RenameException as e:
                        logger.info("Error renaming %s %s" % (full_path.encode('ascii', 'ignore'), str(e)))
                    except ManuallyFixException as e:
                        for f in e.fix_files:
                            logger.info("Unable to rename %s rename, please manually fix" % f)
                    except Exception as e:
                        logger.exception(e)
                        logger.info("Error renaming %s %s" % (full_path.encode('ascii', 'ignore'), str(e)))
                except Exception as e:
                    logger.exception(e)

            if get_size(full_path) < 5000000:
                logger.info("deleting %s" % full_path)
                try:
                    delete(full_path)
                except:
                    pass


    def _process_dlitem(self, dlitem):
        logger.info("Processing Download Item: %s" % dlitem.localpath)

        if dlitem.status == DownloadItem.EXTRACT:
            self._extract_dlitem(dlitem)

        if dlitem.status == DownloadItem.RENAME:
            logger.info("Renaming download item")

            try:
                renamer.rename(dlitem.localpath, id=dlitem.id)
                logger.info("Renaming done")

                dlitem.status = DownloadItem.COMPLETE
                dlitem.retries = 0
                dlitem.save()

                logger.info("Deleting temp folder")
                delete(dlitem.localpath)

            except NoMediaFilesFoundException as e:
                self._fail_dlitem(dlitem, error=str(e))
                return
            except RenameException as e:
                self._fail_dlitem(dlitem, error=str(e))
                return
            except ManuallyFixException as e:
                msg = "Unable to auto rename the below files, please manually fix"

                dlitem.video_files = None

                for f in e.fix_files:
                    msg += "\n File: %s Error: %s" % (f['file'], f['error'])

                    if dlitem.video_files:
                        already_there = False

                        for video_file in dlitem.video_files:
                            if video_file['file'] == f['file']:
                                already_there = True

                        if not already_there:
                            dlitem.video_files.append(f)
                    else:
                        dlitem.video_files = []
                        dlitem.video_files.append(f)


                self._fail_dlitem(dlitem, error=msg)
                dlitem.save()


    def _extract_dlitem(self, dlitem):
        logger.info("Extracting download item")

        if dlitem.retries >= settings.DOWNLOAD_RETRY_COUNT:
            logger.info("Tried to extract %s times already but failed.. will skip: %s" % (dlitem.retries, dlitem.title))
            self._fail_dlitem(dlitem)
            return

        if not os.path.exists(dlitem.localpath):
            #Does not exist??
            self._fail_dlitem(dlitem, error="Local download folder does not exist", backto=DownloadItem.QUEUE)

        #Only need to extract folders, not files
        if os.path.isdir(dlitem.localpath):
            try:
                extractor.extract(dlitem.localpath)
            except ExtractException as e:
                self._fail_dlitem(dlitem, error=str(e), backto=DownloadItem.QUEUE)
                dlitem.reset()
                return
            except ExtractCRCException as e:
                self._fail_dlitem(dlitem, error=str(e), backto=DownloadItem.QUEUE)
                dlitem.reset()
                return

        logger.info("Extraction passed")
        dlitem.status = DownloadItem.RENAME
        dlitem.save()



    def handle(self, *app_labels, **options):

        """
        app_labels - app labels (eg. myapp in "manage.py reset myapp")
        options - configurable command line options
        """

        if 'extract_all' in options:
            extract_all = options['extract_all']
        else:
            extract_all = False

        if 'extract_path' in options:
            extract_path = options['extract_path']
        else:
            extract_path = None

        lock_id = "extract_command-lock"
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.info("Extract already running, exiting")
            return

        #Find jobs running and if they are finished or not
        logger.info('Performing Extraction')

        try:

            if extract_path:
                #Ok, is this part of a downloaditem?
                try:
                    dlitem = DownloadItem.objects.get(localpath=extract_path)
                    self._process_dlitem(dlitem)
                except ObjectDoesNotExist:
                    #Nope its not, lets do manual extract
                    self._extract_others(extract_path)

            else:
                for dlitem in DownloadItem.objects.all().filter(Q(status=DownloadItem.EXTRACT) | Q(status=DownloadItem.RENAME),  retries__lte=settings.DOWNLOAD_RETRY_COUNT):
                    self._process_dlitem(dlitem)

            #Lets rename stuff that didnt come from lazy
            if extract_all:
                #TVShows
                self._extract_others(settings.TV_PATH_TEMP, metaparser.TYPE_TVSHOW)

                #Movies
                self._extract_others(settings.MOVIE_PATH_TEMP, metaparser.TYPE_MOVIE)

        finally:
            release_lock()


    def _fail_dlitem(self, dlitem, backto=None, error=None):

        if None is not backto:
            dlitem.status = backto
        if None is not error:
            logger.info(error)
            dlitem.message = error

        dlitem.retries += 1
        dlitem.save()