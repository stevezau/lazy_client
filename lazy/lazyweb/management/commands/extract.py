from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from lazyweb.models import DownloadItem
import logging
from lazyweb.utils.extractor import DownloadItemExtractor
from celery.task.base import periodic_task
from django.core.cache import cache
from datetime import timedelta

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5 # Lock expires in 5 minutes

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

        lock_id = "%s-lock" % (self.name)

        # cache.add fails if if the key already exists
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking

        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.debug("Extractor already running, exiting")
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
                    dlitem.log(__name__, e.message)
                    logger.exception("Error extracting %s" % e)
                    dlitem.retries += 1
                    dlitem.save()
        finally:
            release_lock()

