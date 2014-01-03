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
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

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
        logger.info('Performing imdb tvdb update')

        ftp_manager = FTPManager()

        for dlItem in DownloadItem.objects.all().filter(Q(status=DownloadItem.QUEUE) | Q(status=DownloadItem.PENDING)):
            try:
                if dlItem.tvdbid:
                    logger.info("Updating tvdb %s" % dlItem.title)
                    dlItem.tvdbid.update_from_tvdb()
            except:
                pass

            try:
                if dlItem.imdbid:
                    logger.info("Updating imdb %s" % dlItem.title)
                    dlItem.imdbid.update_from_imdb()
            except:
                pass
