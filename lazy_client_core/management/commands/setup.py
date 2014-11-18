from __future__ import division
from django.core.management.base import BaseCommand
import logging
from datetime import timedelta
from lazy_client_core.models import DownloadItem
import datetime
from django.core.management import call_command
from django.core.management.base import CommandError
logger = logging.getLogger(__name__)
from lazy_client_core.utils.common import blue_color, fail_color, green_color
from django.conf import settings
from lazy_client_core.models import Version


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
            pass

        print green_color("Running Migrate")
        call_command('migrate', interactive=True)

        print green_color("Loading menu data")
        call_command('sitetreeload', 'lazy_client_ui/fixtures/lazyui_initialdata.json', mode="replace", interactive=True)

        print green_color("Running Syncdb")
        call_command('collectstatic',  interactive=False)

        try:
            Version.objects.get(id=1)
        except:
            new_ver = Version()
            new_ver.id = 1
            new_ver.version = settings.__VERSION__
            new_ver.save()

        print blue_color("Setup success")