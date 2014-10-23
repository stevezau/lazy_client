__author__ = 'steve'
import os
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from lazy_client_core.models import TVShow, Movie
import logging
from django.conf import settings
from lazy_common import utils

logger = logging.getLogger(__name__)


def upgrade():
    for tvdb_obj in TVShow.objects.all():
        if tvdb_obj.posterimg:
            try:
                img_file = str(tvdb_obj.posterimg.file)
                img_temp = NamedTemporaryFile(delete=True)

                utils.resize_img(img_file, img_temp.name, 180, 270, convert=settings.CONVERT_PATH, quality=60)
                tvdb_obj.posterimg.save(str(tvdb_obj.id) + '-tvdb.jpg', File(img_temp))

                img_file.close()
                img_temp.close()

                logger.info("Resized TVDB: %s" % img_file)
            except IOError as e:
                logger.info(e)
                print "cannot create thumbnail for '%s'" % img_file


    for imdb_obj in Movie.objects.all():
        if imdb_obj.posterimg:
            try:
                img_file = str(imdb_obj.posterimg.file)
                img_temp = NamedTemporaryFile(delete=True)

                utils.resize_img(img_file, img_temp.name, 180, 270, convert=settings.CONVERT_PATH, quality=60)
                imdb_obj.posterimg.save(str(imdb_obj.id) + '-imdb.jpg', File(img_temp))

                img_file.close()
                img_temp.close()

                logger.info("Resized IMDB: %s" % img_file)
            except IOError as e:
                logger.info(e)
                print "cannot create thumbnail for '%s'" % img_file