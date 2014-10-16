from __future__ import division
from lazy_client_core.models import DownloadItem
from django.core.cache import cache
import logging
from lazy_client_core.exceptions import DownloadException
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from django.db.models import Q
import ftplib
from djcelery.app import current_app
from celery.app.control import Control
import time
from lazy_client_core.utils import common
from lazy_common.utils import get_size


LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes

logger = logging.getLogger(__name__)


class QueueManager():

    @staticmethod
    def stop_jobs():
        #reset all downloading
        dlitems = DownloadItem.objects.all().filter(status=DownloadItem.DOWNLOADING)

        for dlitem in dlitems:
            dlitem.reset(force=True)

        #now purge the queue
        control = Control(app=current_app)
        try:
            control.discard_all()
        except:
            pass

    @staticmethod
    def start_queue():
        #Start the queue and trigger a queue process job
        cache.delete("stop_queue")
        cache.delete("stop_queue_errors")

        from lazy_client_core.tasks import queue
        queue.delay()

    @staticmethod
    def stop_queue(errors=False):

        #Stop the queue
        if errors:
            cache.set("stop_queue_errors", "true", None)
        else:
            cache.set("stop_queue", "true", None)

        QueueManager.stop_jobs()

    @staticmethod
    def queue_running():

        errors = common.get_lazy_errors()

        if len(errors) > 0:
            #lets stop the queue
            QueueManager.stop_queue(errors=True)
            return False
        else:
            #No errors, lets check if stop_queue_errors was set
            queue_stopped_errors = cache.get('stop_queue_errors')

            if queue_stopped_errors == 'true':
                #lets delete it
                cache.delete("stop_queue_errors")

                if None is cache.get('stop_queue'):
                    #Lets start the queue
                    QueueManager.start_queue()


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
            for dlItem in DownloadItem.objects.all().filter(status=DownloadItem.DOWNLOADING, retries__lte=settings.DOWNLOAD_RETRY_COUNT):
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
                    result = dlItem.task_result()
                    dlItem.log("Strange the job is set to pending.. will reset  result %s" % result)
                    logger.error("Strange the job is set to pending.. will reset")
                    dlItem.reset()
                    dlItem.retries += 1
                    dlItem.save()

                if status == DownloadItem.JOB_FINISHED:
                    localsize = get_size(dlItem.localpath)
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
                        dlItem.log("Job actually finished, moving release to extract status")
                        dlItem.status = DownloadItem.EXTRACT
                        dlItem.taskid = None
                        dlItem.retries = 0
                        dlItem.message = None
                        dlItem.save()

                    else:
                        #Didnt finish properly
                        if dlItem.retries >= settings.DOWNLOAD_RETRY_COUNT:
                            #Failed download
                            msg = "didn't download properly after %s retries" % settings.DOWNLOAD_RETRY_COUNT
                            dlItem.log(msg)
                            dlItem.taskid = None
                            dlItem.retries += 1
                            dlItem.message = str(msg)
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
                items = DownloadItem.objects.all().filter(status=DownloadItem.QUEUE, retries__lte=settings.DOWNLOAD_RETRY_COUNT).order_by("priority", "dateadded")

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
                            dlItem.retries += 1
                            dlItem.save()

                        try:
                            dlItem.download()

                        except ftplib.error_perm as e:
                            resp = e.args[0]

                            #It does not exist?
                            if "FileNotFound" in resp or "file not found" in resp:
                                if dlItem.requested:
                                    logger.debug("Unable to get size and files for %s" % dlItem.ftppath)
                                    dlItem.message = 'Waiting for item to download on server'
                                    dlItem.save()
                                    continue

                            logger.info(e.message)
                            dlItem.message = e.message
                            dlItem.log(e.message)
                            dlItem.retries += 1
                            dlItem.save()
                            continue

                        except DownloadException as e:
                            logger.exception(e)

                            if dlItem.requested and str(e) == "Unable to get size and files on the FTP":
                                logger.debug(e)
                                dlItem.rmessage = 'Waiting for item to download on server'
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
                            continue

                        dlItem.save()
                        count += 1
                    else:
                        break
        finally:
            release_lock()