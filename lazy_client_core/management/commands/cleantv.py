from __future__ import division
from optparse import make_option
import logging
import os
from datetime import datetime
import time

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from lazy_client_core.models import TVShow
from lazy_common.tvdb_api import Tvdb
from lazy_common import metaparser
from lazy_client_core.utils import common
from lazy_common.utils import delete, get_size


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
                        make_option('--fixpaths', action='store_true',
                            dest='fixpaths',
                            default=False,
                            help='Update TVDB cache'),
                        make_option('--removedups', action='store_true',
                            dest='removedups',
                            default=False,
                            help='Remove duplicate movies'),
                        make_option('--updateimgs', action='store_true',
                            dest='updateimgs',
                            default=False,
                            help='Remove duplicate movies'),
                        make_option('--fixdocos', action='store_true',
                            dest='fixdocos',
                            default=False,
                            help='Fix doco channels'),
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

        if options['all'] or options['fixdocos']:
            logger.info('Performing doco fix')

            for doco_dict in metaparser.DOCO_REGEX:
                doco_folder = os.path.join(settings.TV_PATH, doco_dict['name'])

                if os.path.exists(doco_folder):

                    #Get all media files
                    for video_file in common.get_video_files(doco_folder):
                        #Lets check for a nfo file
                        video_file_name, ext = os.path.splitext(os.path.basename(video_file))

                        nfo_file = os.path.join(doco_folder, "%s.nfo" % video_file_name)

                        if not os.path.exists(nfo_file):
                            airdate = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(video_file)))

                            nfo_content = "<episodedetails> \n\
                            <title>" + os.path.splitext(video_file_name)[0] + "</title> \n\
                            <season>0</season> \n\
                            <episode>1</episode> \n\
                            <aired>%s</aired> \n\
                            <displayseason>0</displayseason>  <!-- For TV show specials, determines how the episode is sorted in the series  --> \n\
                            <displayepisode>4096</displayepisode> \n\
                            </episodedetails>" % airdate

                            nfof = open(nfo_file, 'w')
                            nfof.write(nfo_content)
                            nfof.close()
                            print 'Wrote NFO file %s' % nfo_file

                else:
                    logger.info("Doco folder does not exist, skipping")

        if options['all'] or options['removedups']:
            logger.info('Finding duplicate shows')

            for dir in os.listdir(settings.TV_PATH):
                path = os.path.join(settings.TV_PATH, dir)

                #lets see if it already belongs to a tvshow
                tvobjs = TVShow.objects.all().filter(localpath=path)

                if len(tvobjs) > 1:
                    logger.info("Duplicate tvdb shows found in db %s" % dir)
                elif len(tvobjs) == 0:

                    try:
                        showobj = tvdbapi[dir]

                        tvdbid = int(showobj['id'])

                        tvdbobj = TVShow.objects.get(id=int(showobj['id']))

                        if tvdbobj:
                            logger.info("%s: Found a duplicate entry %s:%s" % (dir, tvdbobj.title, tvdbobj.id))
                            continue

                            logger.info("%s was not found on tvdb.com" % dir)

                    except Exception as e:
                        logger.error("DIR: %s Failed while searching via tvdb.com %s" % (path, e.message))