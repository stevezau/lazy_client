from south.modelsinspector import add_introspection_rules
from django.db import models

add_introspection_rules([], ["^lazy_client_core\.utils\.jsonfield\.fields\.JSONField"])

class Version(models.Model):
    class Meta:
        """ Meta """
        db_table = 'version'

    version = models.IntegerField()

from .downloaditem import DownloadItem
from .tvshow import TVShow
from .tvshow import TVShowMappings
from .tvshow import TVShowNetworks
from .tvshow import TVShowGenres
from .tvshow import GenreNames
from .movie import Movie
from .log import DownloadLog
from .log import Job


__all__ = ["DownloadItem", "TVShow", "TVShowMappings", "Log", "Movie", "DownloadLog", "Job", "TVShowNetworks", "TVShowGenres", "GenreNames", "Version"]