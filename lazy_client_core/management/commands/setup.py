from __future__ import division
from django.core.management.base import BaseCommand
from celery.task.base import periodic_task, task
import logging
from datetime import timedelta
from lazy_client_core.models import DownloadItem
import datetime
from django.core.management import call_command
from django.core.management.base import CommandError
logger = logging.getLogger(__name__)
from lazy_client_core.utils.common import blue_color, fail_color, green_color
from django.conf import settings


class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Initial setup"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list

    def handle(self, *app_labels, **options):
        base_dir = settings.BASE_DIR
        print green_color("Running Syncdb")
        call_command('syncdb', interactive=True)

        print green_color("Create Cache db")
        try:
            call_command('createcachetable', 'lazy_cache', interactive=True)
        except CommandError as e:
            if 'already exists' in str(e):
                pass
            else:
                raise e

        print green_color("Running Migrate")
        call_command('migrate', interactive=True)

        print green_color("Loading menu data")
        call_command('sitetreeload', 'lazy_client_ui/fixtures/lazyui_initialdata.json', mode="replace", interactive=True)

        print green_color("Running Syncdb")
        call_command('collectstatic',  interactive=False)

        print blue_color("Setup success")