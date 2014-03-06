from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from lazyweb.models import DownloadItem, Tvdbcache
import logging, os
from lazyweb.utils.ftpmanager import FTPManager
from decimal import Decimal
from datetime import datetime
import ftplib
from django.conf import settings
from django.db.models import Q
from lazyweb.utils.tvdb_api import Tvdb
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
        logger.info('Finding duplicate shows')

        tvdbapi = Tvdb()


        for dir in os.listdir(settings.TVHD):
            path = os.path.join(settings.TVHD, dir)

            #lets see if it already belongs to a tvshow

            tvobjs = Tvdbcache.objects.all().filter(localpath=path)

            if len(tvobjs) > 1:
                logger.info("Duplicate tvdb shows found in db %s" % dir)
            elif len(tvobjs) == 0:

                try:
                    showobj = tvdbapi[dir]

                    tvdbid = int(showobj['id'])

                    tvdbobj = Tvdbcache.objects.get(id=int(showobj['id']))

                    if tvdbobj:
                        logger.error("%s: Found a duplicate entry %s:%s" % (dir, tvdbobj.title, tvdbobj.id))
                        continue

                        logger.info("%s was not found on tvdb.com" % dir)

                except Exception as e:
                    logger.error("DIR: %s Failed while searching via tvdb.com %s" % (path, e.message))