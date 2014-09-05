from lazy_common import utils

__author__ = 'Steve'
import os
import logging
from lazy_client_core.models import TVShow
from lazy_common.tvdb_api import Tvdb
from datetime import datetime, timedelta
from lazy_client_core.utils import common
from lazy_client_core.exceptions import *
from lazy_client_core.models import DownloadItem
from django.core.exceptions import ObjectDoesNotExist
from lazy_client_core.utils import lazyapi
from lazy_common import metaparser

logger = logging.getLogger(__name__)

class TVShow:

    tvshow_path = None
    tvshow_name = None
    search_names = None





    def get_downloading_season_eps(self, season):
        from lazy_common import metaparser
        items = DownloadItem.objects.all().exclude(status=DownloadItem.COMPLETE)

        eps = []

        for entry in items:
            if entry.get_type() != metaparser.TYPE_TVSHOW:
                continue

            if entry.tvdbid_id and entry.tvdbid_id != self.tvdbcache_obj.id:
                continue

            if entry.tvdbid_id and entry.tvdbid_id == self.tvdbcache_obj.id:
                parser = entry.metaparser()
                entry_season = parser.get_season()

                if entry_season == season:
                    eps += parser.get_eps()
            else:
                highest_match = 0

                for name in self.search_names:
                    similar = utils.compare_torrent_2_show(name, entry.title)

                    if similar > highest_match:
                        highest_match = similar

                if highest_match > 0.93:
                    parser = entry.metaparser()
                    entry_season = parser.get_season()

                    if entry_season == season:
                        eps += parser.get_eps()

        return eps
