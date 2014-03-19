from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand
from lazycore.models import Imdbcache
import logging
import os
from lazycore.utils import common
from flexget.utils.imdb import ImdbSearch, ImdbParser
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import shutil
from datetime import datetime

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

        #Find jobs running and if they are finished or not
        logger.info('Performing imdb update')

        for imdb_obj in Imdbcache.objects.all():

            #logger.info("%s: Updating" % imdb_obj.title)

            #Step 1 - Lets remove all imdbcache objects with path that does not exist
            if None is not imdb_obj.localpath and not os.path.exists(str(imdb_obj.localpath)):
                logger.info("%s: folder does not exist anymore" % imdb_obj.title)
                imdb_obj.localpath = None

            #Step 2 - Lets remove all imdbcache objects with path is zero size
            if os.path.exists(str(imdb_obj.localpath)):
                size = common.get_size(imdb_obj.localpath)
                if size < 204800:
                    logger.info("%s: empty folder, deleteing" % imdb_obj.localpath)
                    shutil.rmtree(imdb_obj.localpath)
                    imdb_obj.localpath = None

            #Step 3 - Get the latest info
            try:
                #Do we need to update it
                curTime = datetime.now()
                imdb_date = imdb_obj.updated

                if imdb_date:
                        diff = curTime - imdb_obj.updated.replace(tzinfo=None)
                        hours = diff.seconds / 60 / 60
                        if hours > 48:
                            pass
                            #imdb_obj.update_from_imdb()
                else:
                    pass
                    #imdb_obj.update_from_imdb()

            except Exception as e:
                logger.exception("%s: failed getting latest data from imdb.com %s" % (imdb_obj.title, e.message))
                pass

            imdb_obj.save()

        for dir in os.listdir(settings.HD):
            path = os.path.join(settings.HD, dir)

            if not os.path.exists(path):
                #was prob deleted, lets continue
                continue

            #First, if its empty then delete it
            size = common.get_size(path)

            if size < 204800:
                logger.info("%s: empty folder, deleteing" % path)
                shutil.rmtree(path)
                continue

            #lets see if it already belongs to a movie
            try:
                imdbobj = Imdbcache.objects.get(localpath=path)
            except ObjectDoesNotExist:
                #does not exist
                logger.info("FOLDER: %s is not associated with any imdb object.. lets try fix" % dir)
                try:
                    parser = MetaParser(dir)


                    movie_name, movie_year = get_movie_info(dir)

                    if not movie_name or not movie_year:
                        logger.error("FOLDER: %s unable to figure out year and movie name" % dir)
                        continue

                    imdbS = ImdbSearch()
                    results = imdbS.best_match(movie_name, movie_year)
                    imdb_id = None

                    if results and results['match'] > 0.94:
                        movieObj = ImdbParser()

                        movieObj.parse(results['url'])

                        if not movieObj.name:
                            logger.error("FOLDER: %s unable to get movie name from imdb" % dir)
                            continue

                        imdb_id = int(movieObj.imdb_id.lstrip("tt"))

                    if None is imdb_id:
                        logger.error("FOLDER: %s unable to find a decent match" % dir)
                        continue

                    try:
                        imdbobj = Imdbcache.objects.get(id=imdb_id)

                        #lets compare the two
                        cur_files = common.get_video_files(path)
                        existing_files = common.get_video_files(imdbobj.localpath)

                        if len(cur_files) > 1 or len(existing_files) > 1:
                            logger.error("cannot handle multiple vid files yet")
                            continue

                        cur_file = cur_files[0]['src']
                        existing_file = existing_files[0]['src']

                        best_file = common.compare_best_vid_file(cur_file, existing_file)

                        if best_file == cur_file:
                            #This one is better then the existing one, lets replace it
                            logger.info("Delete existing %s" % imdbobj.localpath)
                            shutil.rmtree(imdbobj.localpath)

                            logger.info("FOLDER: %s was associated with imdb object id %s" % (dir, imdbobj.id))
                            imdbobj.localpath = path
                        else:
                            #lets delete this one
                            logger.info("Delete current %s" % path)
                            shutil.rmtree(path)

                        imdbobj.save()
                    except:
                        #does not exist in imdb, lets create it
                        new_imdbcache = Imdbcache()
                        new_imdbcache.id = imdb_id
                        new_imdbcache.localpath = path
                        logger.info("FOLDER: %s create new imdb object" % dir)
                        new_imdbcache.save()

                except Exception as e:
                    logger.exception("DIR: %s Failed while searching via imdb.com %s" % (path, e.message))