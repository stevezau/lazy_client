from decimal import Decimal
from time import sleep, time
from lazy_common.utils import delete, get_size
from django.db.models import Q

import os
from datetime import datetime
from datetime import timedelta
from threading import Thread
from Queue import Queue
from django.conf import settings
import logging
from lazy_client_core.models import DownloadItem
import ftplib
from lazy_common import ftpmanager
from lazy_common import utils
from lazy_common.exceptions import FTPException
from lazy_client_core.utils import renamer
from lazy_client_core.exceptions import *
from lazy_client_core.utils import extractor
from lazy_client_core.utils.mirror import FTPMirror
from django.core.cache import cache
from lazy_client_core.utils import common
from django.db import connection
from django.db import OperationalError

logger = logging.getLogger(__name__)

queue_manager = None

## THREAD SAFE QUERIES for sqlite ###
def get_attr(id, attr):
    dlitem = DownloadItem.objects.get(id=id)
    return getattr(dlitem, attr)

def update_dlitem(id, **kwargs):
    dlitem = DownloadItem.objects.get(id=id)

    for key, value in kwargs.iteritems():

        if key == "failed":
            dlitem.retries += value
        elif key =="message":
            dlitem.message = value
            dlitem.log(value)
        else:
            setattr(dlitem, key, value)

    dlitem.save()
        
#######################
#### Queue Manager ####
#######################

class QueueManager(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.download_threads = []  # thread list
        self.extractor_thread = None
        self.createThreads()
        self.exit = False
        self.paused = False
        self.last_check = None

        #create a extractor thread
        thread = Extractor()
        self.extractor_thread = thread

        #maintenance
        self.maintenance_thread = Maintenance()

        self.start()

    def queue_running(self):
        self.last_check = datetime.now()

        errors = common.get_lazy_errors()

        if len(errors) > 0:
            #lets stop the queue due to errors
            self.pause(errors=True)
            return False
        else:
            #No errors, lets check if stop_queue_errors was set which means the errors was fixed
            queue_stopped_errors = cache.get('stop_queue_errors')

            if queue_stopped_errors == 'true':
                #lets delete it
                cache.delete("stop_queue_errors")

                if None is cache.get('stop_queue'):
                    #Lets start the queue
                    self.resume()

        queue_stopped = cache.get('stop_queue')

        if None is queue_stopped:
            return True

        if queue_stopped == 'true':
            return False

        return False

    def abort_dlitem(self, id):
        thread = self.get_dlitem_thread(id)

        if thread:
            #lets try kill it
            thread.abort_download = True

    def createThreads(self):
        #create a download thread
        for i in range(settings.MAX_SIM_DOWNLOAD_JOBS):
            thread = Downloader()
            self.download_threads.append(thread)

    def dlitem_running(self, id):
        for t in self.download_threads:
            if t.active and t.active == id:
                #Already running
                return True
        return False

    def get_dlitem_thread(self, id):
        for t in self.download_threads:
            if t.active and t.active == id:
                    return t
        return False

    def get_speed(self, id):
        speed = 0
        thread = self.get_dlitem_thread(id)

        if thread and thread.mirror_thread:
            speed = thread.mirror_thread.speed

        return speed

    def assign_download(self):
        free = [x for x in self.download_threads if not x.active]

        if len(free) == 0:
            return

        for dlitem in DownloadItem.objects.filter(status=DownloadItem.QUEUE, retries__lte=settings.DOWNLOAD_RETRY_COUNT).order_by("priority", "dateadded"):
            #Check if its already running
            if not self.dlitem_running(dlitem.id):
                #Check if this was just tried..
                if dlitem.dlstart:
                    cur_time = datetime.now()
                    diff = cur_time - dlitem.dlstart
                    minutes = diff.total_seconds() / 60

                    if minutes < settings.DOWNLOAD_RETRY_DELAY:
                        continue

                #Check if we should mark it as failed
                if dlitem.retries > settings.DOWNLOAD_RETRY_COUNT:
                    dlitem.log("Job hit too many retires, setting to failed")
                    dlitem.retries += 1
                    dlitem.save()
                    continue

                logger.info('Starting download %s' % dlitem.title)
                free[0].put(dlitem.id)

                #sleep to allow the thread to run
                sleep(2)
                return

    def extract(self):
        if self.extractor_thread and not self.extractor_thread.active:
            for dlitem in DownloadItem.objects.filter(Q(status=DownloadItem.EXTRACT) | Q(status=DownloadItem.RENAME),  retries__lte=settings.DOWNLOAD_RETRY_COUNT):
                if dlitem.dlstart:
                    cur_time = datetime.now()
                    diff = cur_time - dlitem.dlstart
                    minutes = diff.total_seconds() / 60

                    if minutes < settings.DOWNLOAD_RETRY_DELAY:
                        continue

                self.extractor_thread.put(dlitem.id)

    def check_finished(self):
        for dlitem in DownloadItem.objects.filter(status=DownloadItem.DOWNLOADING, retries__lte=settings.DOWNLOAD_RETRY_COUNT):

            if self.dlitem_running(dlitem.id):
                continue

            logger.info('Checking download finished properly %s' % dlitem.title)
            try:
                localsize = utils.get_size(dlitem.localpath)
            except:
                localsize = 0

            dlitem.log('Local size of folder is: %s' % localsize)

            localsize = localsize / 1024 / 1024
            remotesize = dlitem.remotesize / 1024 / 1024

            if localsize == 0 and remotesize == 0:
                percent = 0
            else:
                percent = Decimal(100 * float(localsize)/float(remotesize))

            if percent > 99.3:
                #Change status to extract
                dlitem.log("Job actually finished, moving release to extract status")
                dlitem.status = DownloadItem.EXTRACT
                dlitem.retries = 0
                dlitem.message = None
                dlitem.save()

            else:
                #Didnt finish properly
                if not dlitem.message or len(dlitem.message) == 0:
                    dlitem.message = "didn't download properly"
                dlitem.log(dlitem.message)

                if dlitem.retries >= settings.DOWNLOAD_RETRY_COUNT:
                    #Failed download
                    dlitem.retries += 1
                else:
                    #Didnt download properly, put it back in the queue and let others try download first.
                    dlitem.retries += 1
                    dlitem.status = DownloadItem.QUEUE
            dlitem.save()

    def pause(self, errors=False):
        #Stop the queue
        if errors:
            cache.set("stop_queue_errors", "true", None)
        else:
            cache.set("stop_queue", "true", None)

        self.paused = True

        #Abort download
        for t in self.download_threads:
            t.abort_download = True
            t.put("abort")

        for t in self.download_threads:
            print "Waiting for thread to abort %s " % t
            t.join()

        self.download_threads = []

    def resume(self):
        cache.delete("stop_queue")
        cache.delete("stop_queue_errors")
        self.paused = False
        self.createThreads()

    def sleep(self):
        sleep(2)

    def quit(self):
        self.pause()
        self.exit = True

    def run(self):
        while True:
            try:
                if self.exit:
                    return
                if self.paused:
                    self.sleep()
                    continue

                if not self.last_check:
                    if not self.queue_running():
                        self.sleep()
                        continue
                else:
                    diff = datetime.now() - self.last_check
                    if diff.total_seconds() > 30:
                        if not self.queue_running():
                            self.sleep()
                            continue

                self.assign_download()
                self.check_finished()
                self.extract()
            except Exception as e:
                logger.exception("Some error in main thread %s" % str(e))

            self.sleep()


####################
#### Downloader ####
####################

class Downloader(Thread):

    retry_errors = [
        111,
    ]

    def __init__(self):
        Thread.__init__(self)
        self.queue = Queue()
        self.mirror_thread = None
        self.abort_download = False
        self.active = False
        self.start()

    def sleep(self):
        sleep(0.5)

    def abort_mirror(self):
        try:
            if self.mirror_thread:
                self.mirror_thread.abort = True
                self.mirror_thread.join()
        except:
            pass


    def download(self, id):
        update_dlitem(id, message="", dlstart=datetime.now())

        onlyget = get_attr(id, "onlyget")
        ftppath = get_attr(id, "ftppath")
        requested = get_attr(id, "requested")

        #Get files and folders for download
        try:
            if onlyget:
                #we dont want to get everything.. lets figure this out
                files, remotesize = ftpmanager.get_required_folders_for_multi(ftppath, onlyget)
            else:
                files, remotesize = ftpmanager.get_files_for_download(ftppath)
        except ftplib.error_perm as e:
            resp = e.args[0]

            #It does not exist?
            if "FileNotFound" in resp or "file not found" in resp and requested:
                logger.info("Unable to get size and files for %s" % ftppath)
                update_dlitem(id, message='Waiting for item to download on server')
                return
            else:
                update_dlitem(id, message=str(e), failed=1)
                return
        except FTPException as e:
            if e.errno and e.errno in self.retry_errors:
                update_dlitem(id, message=e.message, failed=1)
            else:
                logger.exception("Exception getting files and folders for download" % str(e))
                update_dlitem(id, message=str(e), failed=1)
            return

        if remotesize > 0 and len(files) > 0:
            update_dlitem(id, remotesize=remotesize)
        else:
            update_dlitem(id, message="Unable to get size and files on the FTP", failed=1)
            return

        #Time to start the downloading
        update_dlitem(id, status=DownloadItem.DOWNLOADING)
        self.mirror_thread = FTPMirror(id, files)

        try:
            while True:
                sleep(1)

                try:
                    if self.abort_download:
                        self.abort_mirror()
                        update_dlitem(id, status=DownloadItem.QUEUE)
                        return
                except:
                    return

                if not self.mirror_thread.isAlive():
                    return

        except Exception as e:
            logger.exception(e)
            self.abort_mirror()
            update_dlitem(id, status=DownloadItem.QUEUE, message=str(e))

    def run(self):

        while True:
            self.active = False
            self.mirror_thread = None
            self.abort_download = False
            self.active = self.queue.get()

            if self.active == "abort":
                print "Aborting download"
                return

            if not self.active:
                self.sleep()
                continue

            if isinstance(self.active, long) or isinstance(self.active, int):
                try:
                    id = self.active
                    self.download(id)
                except Extractor as e:
                    logger.exception("Some error while downloading %s" % str(e))

            self.sleep()

    def put(self, job):
        """passing job to thread"""
        self.queue.put(job)


    def stop(self):
        """stops the thread"""
        self.put("abort_download")


####################
#### Extractor# ####
####################

class Extractor(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.queue = Queue()
        self.active = False
        self.start()

    def _fail_dlitem(self, id, backto=None, error=None):
        dlitem = DownloadItem.objects.get(id=id)

        if None is not backto:
            dlitem.status = backto
        if None is not error:
            logger.info(error)
            dlitem.message = error

        dlitem.retries += 1
        dlitem.save()

    def sleep(self):
        sleep(2)

    def extract(self, id):

        status = get_attr(id, "status")
        localpath = get_attr(id, "localpath")
        retries = get_attr(id, "retries")
        title = get_attr(id, "title")

        if status == DownloadItem.EXTRACT:
            logger.info("Extracting Download Item: %s" % localpath)
            update_dlitem(id, dlstart=datetime.now())

            if retries >= settings.DOWNLOAD_RETRY_COUNT:
                logger.info("Tried to extract %s times already but failed.. will skip: %s" % (retries, title))
                self._fail_dlitem(id)
                return

            if not os.path.exists(localpath):
                self._fail_dlitem(id, error="Local download folder does not exist", backto=DownloadItem.QUEUE)

            #Only need to extract folders, not files
            if os.path.isdir(localpath):
                try:
                    extractor.extract(localpath)
                except ExtractException as e:
                    self._fail_dlitem(id, error=str(e), backto=DownloadItem.QUEUE)
                    DownloadItem.objects.get(id=id).reset()
                except ExtractCRCException as e:
                    self._fail_dlitem(id, error=str(e), backto=DownloadItem.QUEUE)
                    DownloadItem.objects.get(id=id).reset()
                    return

            logger.info("Extraction passed")
            update_dlitem(status=DownloadItem.RENAME)

        if status == DownloadItem.RENAME:
            logger.info("Renaming download item")
            update_dlitem(dlstart=datetime.now())

            try:
                renamer.rename(localpath, id=id)
                logger.info("Renaming done")

                update_dlitem(status=DownloadItem.COMPLETE, retries=0)

                logger.info("Deleting temp folder")
                delete(localpath)

            except NoMediaFilesFoundException as e:
                self._fail_dlitem(id, error=str(e))
                return
            except RenameException as e:
                self._fail_dlitem(id, error=str(e))
                return
            except ManuallyFixException as e:
                msg = "Unable to auto rename the below files, please manually fix"

                update_dlitem(video_files=None)

                for f in e.fix_files:
                    msg += "\n File: %s Error: %s" % (f['file'], f['error'])

                    video_files = get_attr(id, "video_files")

                    if video_files:
                        already_there = False

                        for video_file in video_files:
                            if video_file['file'] == f['file']:
                                already_there = True

                        if not already_there:
                            video_files.append(f)
                            update_dlitem(id, video_files=video_files)

                    else:
                        video_files = [f]
                        update_dlitem(id, video_files=video_files)

                self._fail_dlitem(id, error=msg)
            except Exception as e:
                self._fail_dlitem(id, error=str(e))
                return

    def run(self):
        while True:

            try:
                self.active = False
                self.active = self.queue.get()

                if self.active == "abort":
                    print "Aborting Extractor"
                    return

                if not self.active:
                    self.sleep()
                    continue

                if isinstance(self.active, int) or isinstance(self.active, long):
                    self.extract(id)
                else:
                    self.sleep()
                    continue

            except Exception as e:
                logger.exception("Some error occured in exctractor %s " % str(e))

    def put(self, job):
        """passing job to thread"""
        self.queue.put(job)


    def stop(self):
        """stops the thread"""
        self.put("abort_download")


#####################
#### Maintenance ####
#####################
from lazy_common.tvdb_api import Tvdb

class Maintenance(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.start()
        self.tvdb = Tvdb()

    def sleep(self):
        sleep(60)

    def update_tvshow(self, tvshow):
        try:
            if tvshow.get_tvdb_obj() is None:
                self.tvdb[int(tvshow.id)]
            else:
                tvshow.update_from_tvdb()
                tvshow.save()

            if "Duplicate of" in tvshow.title:
                tvshow.delete()
                return

            if tvshow.title is None or tvshow.title == "" or tvshow.title == " " or len(tvshow.title) == 0:
                tvshow.delete()
                return
        except:
            pass

    def do_maintenance(self):
        logger.info("Task 1 - Cleanup downloaditem logs")
        time_threshold = datetime.now() - timedelta(days=60)
        dl_items = DownloadItem.objects.all().filter(dlstart__lt=time_threshold)

        for dlitem in dl_items:
            dlitem.clear_log()

        logger.info("Task 2 - Lets set the favs")
        try:
            from lazy_client_core.models.tvshow import update_show_favs
            update_show_favs()
        except:
            pass

        logger.info("Task 3 - Update tvshow objects older then 2 weeks")
        time_threshold = datetime.now() - timedelta(days=14)
        from lazy_client_core.models import TVShow

        tvshows = TVShow.objects.all().filter(updated__lt=time_threshold)

        for tvshow in tvshows:
            self.update_tvshow(tvshow)

        logger.info("Task 3.1 - Update tvshow objects with no title")
        tvshows = TVShow.objects.filter(Q(title__isnull=True) | Q(title__exact=''))
        for tvshow in tvshows:
            self.update_tvshow(tvshow)

        logger.info("Task 4: Clean library from xbmc")
        if os.path.exists(settings.TV_PATH) and os.path.exists(settings.MOVIE_PATH):
            from lazy_client_core.utils import xbmc
            try:
                xbmc.clean_library()
            except Exception as e:
                pass

        logger.info("Task 5: clean fix threads")
        from lazy_client_core.models import tvshow
        for t in tvshow.fix_threads[:]:
            #Lets check if its still running
            if not t.isAlive():
                #remove the job
                tvshow.fix_threads.remove(t)

        cache.set("maintenance_run", datetime.now(), None)

    def run(self):

        while True:
            last_run = cache.get("maintenance_run")

            if None is last_run:
                self.do_maintenance()
                continue

            now = datetime.now()
            diff = now - last_run
            hours = diff.total_seconds() / 60 / 60

            if hours >= 24:
                try:
                    self.do_maintenance()
                except Exception as e:
                    logger.exception("Error in extractor thread %s" % str(e))

            self.sleep()

