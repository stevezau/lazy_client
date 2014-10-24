__author__ = 'steve'
from lazy_client_core.models import TVShow, Movie, TVShowMappings
from lazy_client_core.models import DownloadItem
import logging
from django.db.models import Q
from lazy_common.tvdb_api import Tvdb
from lazy_common.tvdb_api.tvdb_exceptions import tvdb_error
from django.conf import settings
from lazy_client_core.models.tvshow import update_show_favs
import shutil
import datetime

logger = logging.getLogger(__name__)

def upgrade():

    #Delete all metaparser cache
    from lazy_common.models import MetaParserCache
    for p in MetaParserCache.objects.all():
        p.delete()

    #Update tvshow objects
    count = TVShow.objects.all().count()
    up_to = 0
    for tvshow in TVShow.objects.all():
        try:
            up_to += 1
            print "### %s / %s" % (up_to, count)
            tvshow.update_from_tvdb()
        except:
            pass
