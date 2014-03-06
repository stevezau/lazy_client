from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand
from lazyweb.models import Tvdbcache
import logging
import os
from django.conf import settings
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
        logger.info('Performing tvdb update')


        for tvdb_obj in Tvdbcache.objects.all():

            logger.info("%s: Updating" % tvdb_obj.title)

            #Step 1 - Lets remove all tvdbcache objects with path that does not exist
            if not os.path.exists(str(tvdb_obj.localpath)):
                logger.info("%s: folder does not exist anymore" % tvdb_obj.title)
                tvdb_obj.localpath = None

            #Step 2 - Get the latest info
            try:
                tvdb_obj.update_from_tvdb()
                logger.info("%s: got latest data from tvdb.com" % tvdb_obj.title)
            except Exception as e:
                logger.info("%s: failed getting latest data from tvdb.com %s" % (tvdb_obj.title, e.message))
                pass

            tvdb_obj.save()


        tvdbapi = Tvdb()

        for dir in os.listdir(settings.TVHD):
            path = os.path.join(settings.TVHD, dir)

            #lets see if it already belongs to a tvshow
            try:
                tvobj = Tvdbcache.objects.get(localpath=path)
            except ObjectDoesNotExist:
                #does not exist
                logger.info("FOLDER: %s is not associated with any tvdb object.. lets try fix" % dir)
                try:
                    showobj = tvdbapi[dir]

                    tvdbid = int(showobj['id'])

                    try:
                        tvdbobj = Tvdbcache.objects.get(id=int(showobj['id']))
                        tvdbobj.localpath = path
                        tvdbobj.save()
                        logger.info("FOLDER: %s was associated with tvdb object id %s" % (dir, tvdbobj.id))
                    except:
                        #does not exist in tvdbcache, lets create it
                        new_tvdbcache = Tvdbcache()
                        new_tvdbcache.id = tvdbid
                        new_tvdbcache.localpath = path
                        logger.info("FOLDER: %s create new tvdb object" % dir)
                        new_tvdbcache.save()

                except Exception as e:
                    logger.error("DIR: %s Failed while searching via tvdb.com %s" % (path, e.message))

                tvdbapi = Tvdb()