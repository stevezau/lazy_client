__author__ = 'Steve'
from django.conf import settings
import os
from lazyweb.models import Job
from lazyweb.utils.missingscanner.tvshow import TVShowScanner
from celery import task
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MissingScanner:

    @task(bind=True)
    def report_all(self):
        #Store results in db as this report can take a while to run
        job = Job()
        job.title = "Report ALL Shows Missing"
        job.save()

        report = {}

        for dir in os.listdir(settings.TVHD):

            tvshow_path = os.path.join(settings.TVHD, dir)

            try:
                scanner = TVShowScanner(tvshow_path)
                report[dir] = scanner.get_tvshow_missing_report()

            except Exception as e:
                logger.exception(e)
                logger
                error = [e.message]
                report[dir] = {}
                report[dir]['errors'] = error

            job.report = report
            job.save()

        job.finishdate = datetime.now()
        job.report = report
        job.save()


    def show_report(self, tvshow_path):
        report = {}

        try:
            scanner = TVShowScanner(tvshow_path)
            report[os.path.basename(tvshow_path)] = scanner.get_tvshow_missing_report()
        except Exception as e:
            logger.exception(e)
            error = [e.message]
            report[os.path.basename(tvshow_path)] = {}
            report[os.path.basename(tvshow_path)]['errors'] = error

        return report

    @task(bind=True)
    def fix_all(self):
        job = Job()
        job.title = "Fix all shows"
        job.save()

        report = {}

        for dir in os.listdir(settings.TVHD):

            tvshow_path = os.path.join(settings.TVHD, dir)

            try:
                scanner = TVShowScanner(tvshow_path)
                report[dir] = scanner.attempt_fix_report()

            except Exception as e:
                logger.exception(e)
                error = [e.message]
                report[dir] = {}
                report[dir]['errors'] = error

            job.report = report
            job.save()

        job.finishdate = datetime.now()
        job.report = report
        job.save()

    @task(bind=True)
    def fix_show(self, tvshow_path, seasons=[]):
        job = Job()
        job.title = "%s Fix seasons %s" % (os.path.basename(tvshow_path), seasons)
        job.save()

        report = {}

        try:
            scanner = TVShowScanner(tvshow_path)
            report[os.path.basename(tvshow_path)] = scanner.attempt_fix_report(check_seasons=seasons)
        except Exception as e:
            logger.exception(e)
            error = [e.message]
            report[os.path.basename(tvshow_path)] = {}
            report[os.path.basename(tvshow_path)]['errors'] = error

        job.report = report
        job.finishdate = datetime.now()
        job.save()