from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand
from lazyweb.models import Imdbcache
import logging
import os
from lazyweb import utils
from flexget.utils.imdb import ImdbSearch, ImdbParser
from django.conf import settings
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

        #Find jobs running and if they are finished or not
        logger.info('Performing imdb update')

        for imdb_obj in Imdbcache.objects.all():

            logger.info("%s: Updating" % imdb_obj.title)

            #Step 1 - Lets remove all imdbcache objects with path that does not exist
            if not os.path.exists(str(imdb_obj.localpath)):
                logger.info("%s: folder does not exist anymore" % imdb_obj.title)
                imdb_obj.localpath = None

            #Step 2 - Get the latest info
            try:
                imdb_obj.update_from_imdb()
                logger.info("%s: got latest data from imdb.com" % imdb_obj.title)
            except Exception as e:
                logger.exception("%s: failed getting latest data from imdb.com %s" % (imdb_obj.title, e.message))
                pass

            imdb_obj.save()

        for dir in os.listdir(settings.HD):
            path = os.path.join(settings.HD, dir)

            #lets see if it already belongs to a movie
            try:
                imdbobj = Imdbcache.objects.get(localpath=path)
            except ObjectDoesNotExist:
                #does not exist
                logger.info("FOLDER: %s is not associated with any imdb object.. lets try fix" % dir)
                try:
                    movie_name, movie_year = utils.get_movie_info(dir)

                    if not movie_name or not movie_year:
                        logger.info("FOLDER: %s unable to figure out year and movie name" % dir)
                        continue

                    imdbS = ImdbSearch()
                    results = imdbS.best_match(movie_name, movie_year)

                    if results and results['match'] > 0.90:
                        movieObj = ImdbParser()

                        movieObj.parse(results['url'])

                        if not movieObj.name:
                            logger.info("FOLDER: %s unable to get movie name from imdb" % dir)
                            continue

                        imdb_id = int(movieObj.imdb_id.lstrip("tt"))

                    try:
                        imdbobj = Imdbcache.objects.get(id=imdb_id)
                        imdbobj.localpath = path
                        imdbobj.save()
                        logger.info("FOLDER: %s was associated with imdb object id %s" % (dir, imdbobj.id))
                    except:
                        #does not exist in imdb, lets create it
                        new_imdbcache = Imdbcache()
                        new_imdbcache.id = imdb_id
                        new_imdbcache.localpath = path
                        logger.info("FOLDER: %s create new imdb object" % dir)
                        new_imdbcache.save()

                except Exception as e:
                    logger.exception("DIR: %s Failed while searching via imdb.com %s" % (path, e.message))