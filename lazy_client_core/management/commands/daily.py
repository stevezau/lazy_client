from __future__ import division
from django.core.management.base import BaseCommand
from celery.task.base import periodic_task, task
import logging
from datetime import timedelta
from lazy_client_core.models import DownloadItem
import datetime
from django.conf import settings
import os
logger = logging.getLogger(__name__)
from lazy_client_core.utils import common
from lazy_client_core.models import TVShow
from lazy_common.tvdb_api import Tvdb
from lazy_common.tvdb_api.tvdb_exceptions import tvdb_error

class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Perform daily tasks"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list

    def handle(self, *app_labels, **options):
        #Task 1 - Cleanup downloaditem logs
        time_threshold = datetime.datetime.now() - datetime.timedelta(days=60)
        dl_items = DownloadItem.objects.all().filter(dlstart__lt=time_threshold)

        for dlitem in dl_items:
            dlitem.clear_log()

        #Task 2 - Truncate celeryd logs as it does not support log rotate
        max_bytes = 31457280

        celeryd_log = os.path.join(settings.BASE_DIR, "logs/celeryd.log")
        if os.path.getsize(celeryd_log) > max_bytes:
            common.truncate_file(celeryd_log, max_bytes)

        celerybeat_log = os.path.join(settings.BASE_DIR, "logs/celery_beat.log")
        if os.path.getsize(celerybeat_log) > max_bytes:
            common.truncate_file(celerybeat_log, max_bytes)

        #Task 3- Lets set the favs
        TVShow.update_favs()

        #Task 4 - Update tvshow objects older then 2 weeks
        time_threshold = datetime.datetime.now() - datetime.timedelta(days=14)
        tvshows = TVShow.objects.all().filter(updated__lt=time_threshold)

        tvdb = Tvdb()

        for tvshow in tvshows:
            #First lets make sure we can get the object on thetvdb, it could of been deleted
            if tvshow.get_tvdb_obj() is None:
                try:
                    tvdb[int(tvshow.id)]
                except tvdb_error as e:
                    if "HTTP Error 404" in str(e):
                        tvshow.delete()
                        continue
                except KeyError:
                    tvshow.delete()
                    continue
                except IndexError:
                    tvshow.delete()
                    continue
            else:
                tvshow.update_from_tvdb()

            if "Duplicate of" in tvshow.title:
                tvshow.delete()
                continue

            if tvshow.title is None or tvshow.title == "" or tvshow.title == " " or len(tvshow.title) == 0:
                tvshow.delete()
                continue
