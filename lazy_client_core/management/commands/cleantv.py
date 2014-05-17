from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand
from lazy_client_core.models import Tvdbcache
import logging
import os
from django.conf import settings
from lazy_client_core.utils.tvdb_api import Tvdb
from django.core.exceptions import ObjectDoesNotExist
from lazy_client_core.utils import common
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Your help message"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list  + (
                        make_option('--all', action='store_true',
                            dest='all',
                            default=False,
                            help='Run all fixes'),
                        make_option('--updatetvdb', action='store_true',
                            dest='updatecache',
                            default=False,
                            help='Update TVDB cache'),
                        make_option('--removedups', action='store_true',
                            dest='removedups',
                            default=False,
                            help='Remove duplicate movies'),
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

        tvdbapi = Tvdb()

        if options['all'] or options['updatecache']:
            logger.info('Performing tvdb update')

            for tvdb_obj in Tvdbcache.objects.all():

                logger.info("%s: Updating" % tvdb_obj.title)

                #Step 1 - Lets remove all tvdbcache objects with path that does not exist
                if not os.path.exists(str(tvdb_obj.localpath)):
                    logger.info("%s: folder does not exist anymore" % tvdb_obj.title)
                    tvdb_obj.localpath = None

                #Step 2 - Lets remove all imdbcache objects with path is zero size
                if os.path.exists(str(tvdb_obj.localpath)):
                    size = common.get_size(tvdb_obj.localpath)
                    if size < 204800:
                        logger.info("%s: empty folder, deleteing" % tvdb_obj.localpath)
                        common.delete(tvdb_obj.localpath)
                        tvdb_obj.localpath = None

                #Step 3 - Get the latest info
                try:
                    #Do we need to update it
                    curTime = datetime.now()
                    tvdb_date = tvdb_obj.updated

                    if tvdb_date:
                            diff = curTime - tvdb_obj.updated.replace(tzinfo=None)
                            hours = diff.seconds / 60 / 60
                            if hours > 168:
                                tvdb_obj.update_from_tvdb()
                    else:
                        tvdb_obj.update_from_tvdb()
                except Exception as e:
                    logger.info("%s: failed getting latest data from tvdb.com %s" % (tvdb_obj.title, e.message))
                    pass

                tvdb_obj.save()


        if options['updatecache'] or options['all']:

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



        if options['all'] or options['removedups']:
            logger.info('Finding duplicate shows')

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