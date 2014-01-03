from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from lazyweb.models import DownloadItem
import logging, os
from lazyweb.utils.ftpmanager import FTPManager
from decimal import Decimal
from datetime import datetime
import ftplib
from django.conf import settings
from lazyweb.utils.extractor import DownloadItemExtractor

logger = logging.getLogger(__name__)

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

        #Find jobs running and if they are finished or not
        logger.info('Performing Extraction')

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
                logger.exception("Error extracting %s" % e)
                dlitem.retries += 1
                dlitem.save()

