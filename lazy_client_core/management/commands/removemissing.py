from __future__ import division
from optparse import make_option
import logging
import ftplib

from django.core.management.base import BaseCommand

from lazy_client_core.models import DownloadItem
from lazy_client_core.utils import ftpmanager


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
        logger.info('Finding duplicate entries')

        for download in DownloadItem.objects.filter(status=DownloadItem.PENDING):
            try:
                ftpmanager.cwd(download.ftppath)
            except ftplib.error_perm as e:
                if "550 FileNotFound" in e.message:
                    print "Remove %s"  % download.title
                    download.delete()




