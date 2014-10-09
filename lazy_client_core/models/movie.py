from __future__ import division

import urllib2
import logging
import os
from datetime import datetime
from requests.exceptions import HTTPError
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.core.exceptions import ObjectDoesNotExist
from flexget.utils.imdb import ImdbSearch, ImdbParser
from PIL import Image

from lazy_client_core.utils.common import OverwriteStorage
from lazy_client_core.utils.jsonfield.fields import JSONField

from django.db import models

logger = logging.getLogger(__name__)


class Movie(models.Model):

    class Meta:
        db_table = 'imdbcache'
        app_label = 'lazy_client_core'

    def __unicode__(self):
        return self.title

    title = models.CharField(max_length=200, db_index=True)
    score = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    votes = models.IntegerField(default=0, blank=True, null=True)
    year = models.IntegerField(default=0, blank=True, null=True)
    genres = models.CharField(max_length=200, blank=True, null=True)
    posterimg = models.ImageField(upload_to=".", storage=OverwriteStorage(), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)
    localpath = models.CharField(max_length=255, blank=True, null=True)
    ignored = models.BooleanField(default=False)

    def get_genres(self):
        genres = []

        if self.genres:
            for genre in self.genres.split("|"):
                genres.append(genre)
        return genres

    def update_from_imdb(self):
        imdbtt = "tt" + str(self.id).zfill(7)

        logger.info("Updating %s %s" % (imdbtt, self.title))

        try:
            imdbobj = ImdbParser()
            imdbobj.parse(imdbtt)

            self.score = imdbobj.score
            self.title = imdbobj.name.encode('ascii', 'ignore')
            self.year = imdbobj.year
            self.votes = imdbobj.votes

            if imdbobj.plot_outline:
                self.description = imdbobj.plot_outline.encode('ascii', 'ignore')

            sGenres = ''

            if imdbobj.genres:
                for genre in imdbobj.genres:
                    sGenres += '|' + genre.encode('ascii', 'ignore')

            self.genres = sGenres.replace('|', '', 1)

            if imdbobj.photo:
                try:
                    img_download = NamedTemporaryFile(delete=True)
                    img_download.write(urllib2.urlopen(imdbobj.photo).read())
                    img_download.flush()

                    size = 214, 317

                    if os.path.getsize(img_download.name) > 0:
                        img_tmp = NamedTemporaryFile(delete=True)
                        im = Image.open(img_download.name)
                        im = im.resize(size, Image.ANTIALIAS)
                        im.save(img_tmp, "JPEG", quality=70)

                        self.posterimg.save(str(self.id) + '-imdb.jpg', File(img_tmp))
                except Exception as e:
                    logger.error("error saving image: %s" % e.message)

            self.save()
            self.updated = datetime.now()
            self.save()
        except HTTPError as e:
            if e.errno == 404:
                logger.error("Error entry was not found in imdn!")
                raise ObjectDoesNotExist()


@receiver(post_save, sender=Movie)
def add_new_imdbitem(sender, created, instance, **kwargs):

    if created:
        logger.info("Adding a new imdbitem, lets make sure its fully up to date")
        instance.update_from_imdb()

