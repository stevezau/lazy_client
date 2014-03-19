from __future__ import division
from lazycore.models import DownloadItem
from django.core.cache import cache
import logging
from lazycore.exceptions import DownloadException
from decimal import Decimal
from datetime import datetime
from django.conf import settings
import ftplib
from djcelery.app import current_app
from celery.app.control import Control
import time
from lazycore.utils import common


LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes

logger = logging.getLogger(__name__)


class QueueManager():

    @staticmethod
    def start_queue():
        #Start the queue and trigger a queue process job
        cache.delete("stop_queue")

        from lazycore.management.commands.queue import Command
        cmd = Command()
        cmd.handle.delay()

    @staticmethod
    def stop_queue():

        #Stop the queue
        cache.set("stop_queue", "true", None)

        #reset all downloading
        dlitems = DownloadItem.objects.all().filter(status=DownloadItem.DOWNLOADING)

        for dlitem in dlitems:
            dlitem.reset(force=True)

        #now purge the queue
        control = Control(app=current_app)
        control.discard_all()

    @staticmethod
    def queue_running():
        queue_stopped = cache.get('stop_queue')

        if None is queue_stopped:
            return True

        if queue_stopped == 'true':
            return False

        return False

    def process(self):

        if not self.queue_running():
            logger.debug("Queue is stopped, exiting")
            return

        lock_id = "%s-lock" % self.__class__.__name__
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.debug("Queuerunner already running, exiting")
            return

        logger.info('Performing queue update')

        try:
            for dlItem in DownloadItem.objects.all().filter(status=DownloadItem.DOWNLOADING):
                status = dlItem.download_status()

                logger.info('Checking job: %s status: %s' % (dlItem.title, status))

                if status == DownloadItem.JOB_RUNNING:
                    #Lets ensure it has not crashed
                    seconds_now = time.mktime(datetime.now().timetuple())

                    result = dlItem.task_result()

                    if dlItem.still_alive():
                        logger.debug("Job is still running")
                    else:
                        dlItem.log("Job appears to of crashed: %s .. lets reset it: %s" % (result, dlItem.ftppath))
                        dlItem.download_retry()
                        dlItem.save()


                if status == DownloadItem.JOB_FAILED:
                    result = dlItem.task_result()
                    dlItem.log("Job marked as failed , will retry (result: %s)" % result)
                    dlItem.message = str("Download failed %s, wil retry (result: %s)" % (dlItem.title, result))
                    dlItem.retries += 1
                    dlItem.reset(force=True)
                    dlItem.save()

                if status == DownloadItem.JOB_PENDING:
                    dlItem.log("Strange the job is set to pending.. will reset")
                    dlItem.reset(force=True)
                    dlItem.retries += 1
                    dlItem.save()

                if status == DownloadItem.JOB_FINISHED:
                    localsize = common.get_size(dlItem.localpath)
                    dlItem.log("Job has finished")
                    dlItem.log('Local size of folder is: %s' % localsize)

                    localsize = localsize / 1024 / 1024
                    remotesize = dlItem.remotesize / 1024 / 1024

                    if localsize == 0 and remotesize == 0:
                        percent = 0
                    else:
                        percent = Decimal(100 * float(localsize)/float(remotesize))

                    if percent > 99.3:
                        #Change status to extract
                        dlItem.log("Job actually finished, moving release to move status")
                        dlItem.status = DownloadItem.MOVE
                        dlItem.retries = 0
                        dlItem.message = None
                        dlItem.save()

                    else:
                        #Didnt finish properly
                        if dlItem.retries > settings.DOWNLOAD_RETRY_COUNT:
                            #Failed download
                            msg = "didn't download properly after %s retries" % settings.DOWNLOAD_RETRY_COUNT
                            dlItem.log(msg)
                            dlItem.message = str(msg)
                            dlItem.status = DownloadItem.ERROR
                            dlItem.save()
                        else:
                            #Didnt download properly, put it back in the queue and let others try download first.
                            msg = "didn't download properly, trying again"
                            dlItem.log(msg)
                            dlItem.retries += 1
                            dlItem.message = str(msg)
                            dlItem.reset(force=True)
                            dlItem.save()
                dlItem.save()

            #Figure out the number of jobs running
            count = DownloadItem.objects.all().filter(status=DownloadItem.DOWNLOADING).count()

            if count == 0:
                startnew = settings.MAX_SIM_DOWNLOAD_JOBS
            else:
                startnew = settings.MAX_SIM_DOWNLOAD_JOBS - count

            logger.info("Going to try start %s new jobs" % startnew)

            #If jobs running is smaller then the config then start new jobs
            if startnew > 0:
                items = DownloadItem.objects.all().filter(status=DownloadItem.QUEUE).order_by("priority", "dateadded")

                if items.count() == 0:
                    logger.info("No outstanding jobs found to start")
                    return

                count = 0

                for dlItem in items:

                    if count < startnew:

                        if dlItem.dlstart:
                            cur_time = datetime.now()
                            diff = cur_time - dlItem.dlstart.replace(tzinfo=None)
                            minutes = diff.seconds / 60

                            if minutes < settings.DOWNLOAD_RETRY_DELAY:
                                logger.info("skipping job as it was just retired: %s (%s)" % (dlItem.title, minutes))
                                continue

                        logger.info("Starting job: %s" % dlItem.ftppath)

                        if dlItem.retries > settings.DOWNLOAD_RETRY_COUNT:
                            dlItem.log("Job hit too many retires, setting to failed")
                            dlItem.status = DownloadItem.ERROR
                            dlItem.save()

                        try:
                            dlItem.download()

                        except ftplib.error_perm as e:
                            #It does not exist?
                            if "FileNotFound" in e.message:
                                if dlItem.requested:
                                    logger.debug("Unable to get size and files for %s" % dlItem.ftppath)
                                    dlItem.message = 'Waiting for item to appear on ftp'
                                    dlItem.save()
                                    continue
                            else:
                                logger.error(e)
                                dlItem.message = e.message
                                dlItem.log(e.message)
                                dlItem.retries += 1
                                dlItem.save()
                                continue

                        except DownloadException as e:
                            if e.message == "Unable to get size and files on the FTP":
                                if dlItem.requested:
                                    logger.debug(e)
                                    dlItem.message = 'Waiting for item to appear on ftp'
                                    dlItem.save()
                            else:
                                dlItem.log(e)
                                dlItem.message = e
                                dlItem.retries += 1
                                dlItem.save()
                            continue
                        except Exception as e:
                            dlItem.log(e.message)
                            logger.exception(e)

                        dlItem.save()
                        count += 1
                    else:
                        break
        finally:
            release_lock()