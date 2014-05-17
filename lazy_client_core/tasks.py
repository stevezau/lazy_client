__author__ = 'Steve'
from celery.task.base import periodic_task
from datetime import timedelta

from lazy_client_core.utils.missingscanner import MissingScanner
from lazy_client_core.management.commands.extract import Command as ExtractCommand
from lazy_client_core.management.commands.queue import Command as QueueCommand

@periodic_task(bind=True, run_every=timedelta(hours=24))
def cleanup_movies():
    from lazy_client_core.management.commands.cleanmovies import Command as clean_movies_command

    options = {'removedups': true}

