from __future__ import division
from django.core.management.base import BaseCommand
from celery.task.base import periodic_task, task
import logging
from datetime import timedelta
from lazy_client_core.models import DownloadItem
import datetime

logger = logging.getLogger(__name__)



class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Perform daily tasks"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list

    def handle(self, *app_labels, **options):
        #Task 1 - Cleanup downloaditem logs
        time_threshold = datetime.datetime.now() - datetime.timedelta(days=14)
        dl_items = DownloadItem.objects.all().filter(dlstart__lt=time_threshold)

        for dlitem in dl_items:
            print dlitem.title
            dlitem.clear_log()

