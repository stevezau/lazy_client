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

        #raise CommandError('Only the default is supported')

        #Find jobs running and if they are finished or not
        logger.info('Finding duplicate movies')

        for dir in os.listdir(settings.HD):
            path = os.path.join(settings.HD, dir)

            #lets see if it already belongs to a movie
            try:
                imdbobj = Imdbcache.objects.get(localpath=path)
                continue
            except ObjectDoesNotExist:
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
                        if not movieObj.year or movieObj.year == 0:
                            logger.info("FOLDER: %s unable to get movie year from imdb" % dir)
                            continue

                        movie_name = movieObj.name
                        movie_year = movieObj.year
                        imdb_id = int(movieObj.imdb_id.lstrip("tt"))

                        imdbobj = Imdbcache.objects.get(id=imdb_id)

                        if imdbobj:
                            logger.error("%s: Found a duplicate entry %s:%s" % (dir, imdbobj.title, imdbobj.id))
                            continue

                        logger.info("%s was not found on imdb.com" % dir)

                except Exception as e:
                    logger.error("DIR: %s Failed while searching via tvdb.com %s" % (path, e.message))