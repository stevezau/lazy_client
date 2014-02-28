from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand
from lazyweb.models import Imdbcache
import logging
import os
from lazyweb import utils
from lazyweb.models import DownloadItem
from flexget.utils.imdb import ImdbSearch, ImdbParser
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

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

        idlist = []

        for download in DownloadItem.objects.all():
            idlist.append(download.id)

        for id in idlist:
            #Does it exist else where?
            try:
                downloaditem = DownloadItem.objects.get(id=id)

                if downloaditem:
                    try:
                        existing = DownloadItem.objects.get(~Q(id=downloaditem.id), title=downloaditem.title)

                        existing.delete()

                    except ObjectDoesNotExist:
                        continue
                    except Exception as e:
                        logger.exception(e)
                        continue
            except ObjectDoesNotExist:
                continue
            except Exception as e:
                continue
                logger.exception(e)



