from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand
from lazycore.models import DownloadItem
import logging
from lazycore.utils.extractor import DownloadItemExtractor
from celery.task.base import periodic_task
from django.core.cache import cache
from datetime import timedelta
from lazycore.utils.queuemanager import QueueManager

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 20 # Lock expires in 20 minutes

class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Your help message"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list  + (
                        make_option('--myoption', action='store',
                            dest='myoption',
                            default='default',
                            help='Option help message'),
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

        #raise CommandError('Only the default is supported')

        if not QueueManager.queue_running():
            logger.debug("Queue is stopped, exiting")
            return

        lock_id = "%s-lock" % self.__class__.__name__
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.debug("Extract already running, exiting")
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
                try:
                    extractor = DownloadItemExtractor(dlitem)
                    extractor.extract()
                except Exception as e:
                    dlitem.log(e.message)
                    logger.exception("Error extracting %s" % e)
                    dlitem.retries += 1
                    dlitem.save()
        finally:
            release_lock()

