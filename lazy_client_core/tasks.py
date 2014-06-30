__author__ = 'Steve'
from datetime import timedelta
import logging

from django.core.management import call_command
from celery.task.base import periodic_task
from lazy_client_core.utils.mirror import FTPMirror
from lazy_client_core.utils import missingscanner

logger = logging.getLogger(__name__)

@periodic_task(run_every=timedelta(days=1))
def daily_task():
    call_command('daily', interactive=False)

@periodic_task(run_every=timedelta(seconds=60))
def queue():
    call_command('queue', interactive=False)

@periodic_task(run_every=timedelta(seconds=600))
def extract():
    call_command('extract', interactive=False)

