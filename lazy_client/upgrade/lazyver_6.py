__author__ = 'steve'
import os
from PIL import Image
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from lazy_client_core.models import Tvdbcache, Imdbcache
import logging

logger = logging.getLogger(__name__)


def upgrade():
    for tvdb_obj in Tvdbcache.objects.all():
        if tvdb_obj.posterimg:
            try:
                img_file = str(tvdb_obj.posterimg.file)
                img_temp = NamedTemporaryFile(delete=True)

                size = 214, 317

                if os.path.getsize(img_file) > 0:
                    im = Image.open(img_file)
                    im = im.resize(size, Image.ANTIALIAS)
                    im.save(img_temp, "JPEG", quality=70)

                    tvdb_obj.posterimg.save(str(tvdb_obj.id) + '-tvdb.jpg', File(img_temp))

                logger.info("Resized TVDB: %s" % img_file)
            except IOError as e:
                logger.info(e)
                print "cannot create thumbnail for '%s'" % img_file


    for imdb_obj in Imdbcache.objects.all():
        if imdb_obj.posterimg:
            try:
                img_file = str(imdb_obj.posterimg.file)
                img_temp = NamedTemporaryFile(delete=True)

                size = 214, 317

                im = Image.open(img_file)
                im = im.resize(size, Image.ANTIALIAS)
                im.save(img_temp, "JPEG", quality=70)
                imdb_obj.posterimg.save(str(imdb_obj.id) + '-imdb.jpg', File(img_temp))

                logger.info("Resized IMDB: %s" % img_file)
            except IOError as e:
                logger.info(e)
                print "cannot create thumbnail for '%s'" % img_file