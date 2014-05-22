from __future__ import division
from django.core.management.base import BaseCommand
import logging
from datetime import timedelta

from lazy_client_core.utils.queuemanager import QueueManager


logger = logging.getLogger(__name__)

class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Process the queue"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list

    def handle(self, *app_labels, **options):
        queue_manager = QueueManager()
        queue_manager.process()



