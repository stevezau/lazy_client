from __future__ import division
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from lazyweb.models import DownloadItem
import logging, os
from lazyweb.utils.ftpmanager import FTPManager, FTPMirror
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from celery.task.base import periodic_task, task
from django.core.cache import cache
from datetime import timedelta
import ftplib

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


    @periodic_task(bind=True, run_every=timedelta(seconds=60))
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

                task = dlItem.get_task()

                if task is not None:
                    logger.debug("%s status: %s   result: %s" % (dlItem.title, task.state, task.result))

                if None is task:
                    #No task assigned, it never reached MQ..
                    msg = "no task assigned for some strange reason.. "
                    logger.error(msg)
                    dlItem.status = DownloadItem.QUEUE
                    dlItem.dlstart = None
                    dlItem.log(__name__, msg)
                    dlItem.message = msg
                    dlItem.retries += 1
                    dlItem.save()

                elif task.state == "SUCCESS" or task.state == "FAILURE":
                    #Now check if its finished
                    #Lets make sure it finished downloading properly

                    if task.state == "FAILURE":
                        msg = 'Job has failed, will check if we got everything anyway'
                        dlItem.log(__name__, msg)
                        logger.info(msg)
                    else:
                        msg = 'Job has finished'
                        dlItem.log(__name__, msg)
                        logger.info(msg)

                    localsize = -1

                    try:
                        localsize = ftp_manager.getLocalSize(dlItem.localpath)
                        dlItem.log(__name__, 'Local size of folder is: %s' % localsize)
                    except:
                        dlItem.log(__name__, "error getting local size of folder: %s" % dlItem.ftppath)

                    localsize = localsize / 1024 / 1024
                    remotesize = dlItem.remotesize / 1024 / 1024

                    if (localsize == 0) and (remotesize == 0):
                        percent = 100
                    else:
                        percent = Decimal(100 * float(localsize)/float(remotesize))

                    if percent > 99.3:
                        #Change status to extract
                        dlItem.log(__name__, "Job actually finished, moving release to move status")
                        dlItem.status = DownloadItem.MOVE
                        dlItem.retries = 0
                        dlItem.message = None
                        dlItem.save()

                    else:
                        #get error msg

                        if task.result:
                            errormsg = task.result
                        else:
                            errormsg = ""

                        #Didnt finish properly
                        if dlItem.retries > 3:
                            #Failed download
                            #TODO: Notify
                            msg = "didn't download properly after 3 retries cause %s" % errormsg
                            dlItem.log(__name__, msg)
                            logger.debug(msg)
                            dlItem.message = str(msg)
                            dlItem.status = DownloadItem.ERROR
                            try:
                                dlItem.save()
                            except:
                                #ignore collation lation truncate errors
                                pass
                        else:
                            #Didnt download properly, put it back in the queue and let others try download first.
                            msg = "didn't download properly, trying again cause: %s" % errormsg
                            dlItem.log(__name__, msg)
                            logger.debug(msg)
                            dlItem.retries += 1
                            dlItem.message = str(msg)
                            dlItem.status = DownloadItem.QUEUE
                            dlItem.dlstart = None
                            try:
                                dlItem.save()
                            except:
                                #ignore collation lation truncate errors
                                pass
                else:
                    #Lets make sure the job has not been running for over x hours
                    curTime = datetime.now()
                    diff = curTime - dlItem.dlstart.replace(tzinfo=None)
                    hours = diff.seconds / 60 / 60
                    if hours > 8:
                        dlItem.log(__name__, "Job as has been running for over 8 hours, killing job and setting to retry: %s" % dlItem.ftppath)
                        dlItem.retries += 1
                        dlItem.reset()

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
                            dlItem.log(__name__, "Job hit too many retires, setting to failed")
                            dlItem.status = DownloadItem.ERROR
                            dlItem.save()

                        remotesize = False

                        if dlItem.onlyget:
                            try:
                                #we dont want to get everything.. lets figure this out
                                get_folders = ftp_manager.get_required_folders_for_multi(dlItem.title, dlItem.ftppath, dlItem.onlyget)

                                remotesize = ftp_manager.getRemoteSizeMulti(get_folders)
                            except Exception as e:
                                logger.exception(e)
                                remotesize == 0
                        else:
                            try:
                                files, remotesize = ftp_manager.get_files_for_download(dlItem.ftppath)
                            except ftplib.error_perm, e:
                                if dlItem.requested == True:
                                    pass
                                else:
                                    logger.error(e)
                                    dlItem.message = e.message
                                    dlItem.log(__name__, e.message)
                                    dlItem.retries += 1
                                    dlItem.save()
                                    continue
                            except Exception as e:
                                remotesize = 0

                        if remotesize > 0 and len(files) > 0:
                            dlItem.remotesize = remotesize
                        else:
                            if dlItem.requested == True:
                                logger.debug("Unable to get size and files for %s" % dlItem.ftppath)
                                dlItem.message = 'Waiting for item to appear on ftp'
                                dlItem.save()
                            else:
                                dlItem.log(__name__, "Unable to get size and files for %s" % dlItem.ftppath)
                                logger.info("Unable to get size and files for %s" % dlItem.ftppath)
                                dlItem.message = 'Unable to get size and files'
                                dlItem.retries += 1
                                dlItem.save()
                            continue

                        #Time to start a new one!.
                        if dlItem.onlyget:
                            task = ftp_manager.mirrorMulti.delay(dlItem.localpath, urls, dlItem.id)
                            dlItem.taskid = task.task_id
                        else:
                            mirror = FTPMirror()
                            task = mirror.mirror_ftp_folder.delay(files, dlItem.localpath, dlItem)
                            dlItem.taskid = task.task_id

                        dlItem.message = None
                        dlItem.dlstart = datetime.now()
                        dlItem.status = DownloadItem.DOWNLOADING

                        dlItem.save()

                        count += 1
                    else:
                        break
        finally:
            release_lock()


