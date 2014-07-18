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
from lazy_common import requests

class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Perform daily tasks"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list

    def handle(self, *app_labels, **options):
        requests.get("http://www.thetvdb.org")
        requests.get("http://www.imdb.com")
