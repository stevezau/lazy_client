from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from lazyweb.models import DownloadItem
import logging, os
from lazyweb.utils.ftpmanager import FTPManager
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from celery.task.base import periodic_task, task
from django.core.cache import cache
from datetime import timedelta

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5 # Lock expires in 5 minutes

class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Your help message"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list  + (
                        make_option('--myoption', action='store',
                            dest='myoption',
                            default='default',
                            help='Option help message'),
                  )

    @periodic_task(bind=True, run_every=timedelta(seconds=120))
    def handle(self, *app_labels, **options):
        """
        app_labels - app labels (eg. myapp in "manage.py reset myapp")
        options - configurable command line options
        """

        # Return a success message to display to the user on success
        # or raise a CommandError as a failure condition
        #if options['myoption'] == 'default':
        #    return 'Success!'

        #raise CommandError('Only the default is supported')

        #Find jobs running and if they are finished or not
        lock_id = "%s-lock" % (self.name)

        # cache.add fails if if the key already exists
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking

        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.debug("Queuerunner already running, exiting")
            return

        logger.info('Performing queue update')

        try:

            ftp_manager = FTPManager()

            for dlItem in DownloadItem.objects.all().filter(status=DownloadItem.DOWNLOADING):

                logger.info('Checking job: %s' % dlItem.title)

                #Now check if its finished
                if ftp_manager.jobFinished(dlItem.pid):

                    #Lets make sure it finished downloading properly
                    logger.info('Job has finished')

                    localsize = -1
                    try:
                        localsize = ftp_manager.getLocalSize(dlItem.localpath)
                        logger.info('Local size of folder is: %s' % localsize)
                    except:
                        logger.info("error getting local size of folder: %s" % dlItem.ftppath)

                    localsize = localsize / 1024 / 1024
                    remotesize = dlItem.remotesize / 1024 / 1024

                    if (localsize == 0) and (remotesize == 0):
                        percent = 100
                    else:
                        percent = Decimal(100 * float(localsize)/float(remotesize))

                    if percent > 99.3:
                        #Change status to extract
                        logger.info("Job actually finished, moving release to move status")
                        ftp_manager.removeScript('ftp-%s' % dlItem.id)
                        dlItem.status = DownloadItem.MOVE
                        dlItem.retries = 0
                        dlItem.message = None
                        dlItem.save()

                    else:
                        #Didnt finish properly
                        if dlItem.retries > 10:
                            #Failed download
                            #TODO: Notify
                            logger.info("%s didn't download properly after 10 retries" % dlItem.ftppath)
                            dlItem.message = "didn't download properly after 10 retries, stopping download"
                            dlItem.status = DownloadItem.ERROR
                            dlItem.save()
                        else:
                            #Didnt download properly, put it back in the queue and let others try download first.
                            logger.info("%s didn't download properly, trying again" % dlItem.ftppath)

                            dlItem.retries += 1
                            dlItem.message = "Failed Download, will try again (Retry Count: %s)" % dlItem.retries
                            dlItem.status = DownloadItem.QUEUE
                            dlItem.dlstart = datetime.now()

                            dlItem.save()
                else:
                    #Lets make sure the job has not been running for over x hours
                    curTime = datetime.now()
                    diff = curTime - dlItem.dlstart.replace(tzinfo=None)
                    hours = diff.seconds / 60 / 60
                    if hours > 5:
                        logger.info("Job as has been running for over 8 hours, killing job and setting to retry: %s" % dlItem.ftppath)
                        dlItem.retries += 1
                        FTPManager.stopJob(dlItem.pid)
                        dlItem.save()

            #Figure out the number of jobs running after the above checks
            count = DownloadItem.objects.all().filter(status=DownloadItem.DOWNLOADING).count()

            if count == 0:
                startnew = settings.MAX_SIM_DOWNLOAD_JOBS
            else:
                startnew = settings.MAX_SIM_DOWNLOAD_JOBS - count

            logger.info("Going to try start %s new jobs" % startnew)

            #If jobs running is smaller then the config then start new jobs
            if (startnew > 0):
                items = DownloadItem.objects.all().filter(status=DownloadItem.QUEUE).order_by("priority", "dateadded")
                countJobs = items.count()

                if countJobs == 0:
                    logger.info("No outstanding jobs found to start")
                    return

                count = 0

                for dlItem in items:

                    if (count < startnew):

                        if dlItem.dlstart:
                            curTime = datetime.now()
                            diff = curTime - dlItem.dlstart.replace(tzinfo=None)
                            minutes = diff.seconds / 60

                            if minutes < 0:
                                logger.info("skipping job as it was just retired: %s" % dlItem.title)
                                continue

                        logger.info("Starting job: %s" % dlItem.ftppath)

                        if (dlItem.retries > 10):
                            logger.info("Job hit too many retires, setting to failed")
                            dlItem.status = DownloadItem.ERROR
                            dlItem.save()

                        remotesize = False

                        if dlItem.onlyget:
                            try:
                                #we dont want to get everything.. lets figure this out
                                get_folders = ftp_manager.getRequiredDownloadFolders(dlItem.title, dlItem.ftppath, dlItem.onlyget)

                                remotesize = ftp_manager.getRemoteSizeMulti(get_folders)
                            except Exception as e:
                                logger.exception(e)
                                remotesize == 0
                        else:
                            try:
                                remotesize = ftp_manager.getRemoteSize(dlItem.ftppath)
                            except Exception as e:
                                logger.exception(e)
                                remotesize = 0

                        if remotesize > 0:
                            dlItem.remotesize = remotesize
                        else:
                            if dlItem.requested == True:
                                logger.info("Unable to get remote size for %s" % dlItem.ftppath)
                                dlItem.message = 'Waiting for item to appear on ftp'
                                dlItem.save()
                            else:
                                logger.info("Unable to get remote size for %s" % dlItem.ftppath)
                                dlItem.message = 'Unable to get remote size on the ftp'
                                dlItem.retries += 1
                                dlItem.save()

                            continue


                        #Time to start a new one!.
                        if dlItem.onlyget:
                            cmd = Command()
                            task = ftp_manager.mirrorMulti.delay(dlItem.localpath, get_folders, dlItem.id)
                            dlItem.pid = task.task_id
                        else:
                            cmd = Command()
                            task = ftp_manager.mirror.delay(dlItem.localpath, dlItem.ftppath, dlItem.id)
                            dlItem.pid = task.task_id

                        dlItem.message = None
                        dlItem.dlstart = datetime.now()
                        dlItem.status = DownloadItem.DOWNLOADING

                        dlItem.save()

                        count += 1
                    else:
                        break
        finally:
            release_lock()


