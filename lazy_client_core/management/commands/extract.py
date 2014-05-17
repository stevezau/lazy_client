from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand
from lazy_client_core.models import DownloadItem
import logging
from lazy_client_core.utils.extractor import DownloadItemExtractor, Extractor
from celery.task.base import periodic_task
from django.core.cache import cache
from django.conf import settings
from datetime import timedelta
from lazy_client_core.utils.metaparser import MetaParser
from lazy_client_core.utils.queuemanager import QueueManager
import os
from lazy_client_core.utils import common

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 20 # Lock expires in 20 minutes

def extract_others(path, type):
    for f in os.listdir(path):
        #Is this from lazy?

        full_path = os.path.join(path, f)

        try:
            DownloadItem.objects.get(localpath=full_path)
        except:
            logger.debug("Will try rename %s" % full_path)

            try:
                if common.get_size(full_path) == 0:
                    logger.info("Empty folder %s, will delete" % full_path)
                    common.delete(full_path)
                    continue

                extractor = Extractor(full_path, type=type)
                extractor.extract()
            except Exception as e:
                logger.error("Error extracting %s" % e)



class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Your help message"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list + (
                        make_option('--all', action='store_true',
                            dest='extract_all',
                            default=False,
                            help='Try to rename files that lazy didnt download'),
                  )

    @periodic_task(bind=True, run_every=timedelta(seconds=600))
    def handle(self, *app_labels, **options):

        """
        app_labels - app labels (eg. myapp in "manage.py reset myapp")
        options - configurable command line options
        """

        # Return a success message to display to the user on success
        # or raise a CommandError as a failure condition
        #if options['myoption'] == 'default':
        #    return 'Success!'

        if 'extract_all' in options:
            extract_all = options['extract_all']
        else:
            extract_all = False

        #raise CommandError('Only the default is supported')

        if not QueueManager.queue_running():
            logger.info("Queue is stopped, exiting")
            return

        lock_id = "%s-lock" % self.__class__.__name__
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.info("Extract already running, exiting")
            return

        #Find jobs running and if they are finished or not
        logger.info('Performing Extraction')

        try:
            for dlitem in DownloadItem.objects.all().filter(status=DownloadItem.MOVE):

                if dlitem.retries > 3:
                    dlitem.status = DownloadItem.ERROR
                    dlitem.save()
                    logger.error("Tried to extract 3 times already but failed.. will skip: %s" % dlitem.title)
                    continue

                logger.info("Processing: %s" % dlitem.localpath)

                #offload processing to the DownloadItemExtractor
                extractor = DownloadItemExtractor(dlitem)
                extractor.extract()

            #Lets rename stuff that didnt come from lazy
            if extract_all:
                #TVShows
                extract_others(settings.TVHD_TEMP, MetaParser.TYPE_TVSHOW)

                #Movies
                extract_others(settings.HD_TEMP, MetaParser.TYPE_MOVIE)

                #Other
                #self.extract_others(settings.REQUESTS_TEMP, MetaParser.TYPE_UNKNOWN)

        finally:
            release_lock()

