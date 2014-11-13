from __future__ import division
import logging
import os
import re
import pycurl
import time
from threading import Timer
from datetime import datetime
from threading import Thread
from lazy_client_core.utils import common
from django.conf import settings
from lazy_common import ftpmanager
from lazy_common.utils import bytes2human
from lazy_client_core.models import DownloadLog, DownloadItem

logger = logging.getLogger(__name__)

retry_on_errors = [
    13,  #CURLE_FTP_WEIRD_PASV_REPLY (13) libcurl failed to get a sensible result back from the server as a response to either a PASV or a EPSV command. The server is flawed.
    14,  #CURLE_FTP_WEIRD_227_FORMAT
    35,
    42, #Callback aborted (timed out)
    7,  #Connection refused
    12,  #CURLE_FTP_ACCEPT_TIMEOUT (12) During an active FTP session while waiting for the server to connect, the CURLOPT_ACCEPTTIMOUT_MS (or the internal default) timeout expired.
    23,  #CURLE_WRITE_ERROR (23) An error occurred when writing received data to a local file, or an error was returned to libcurl from a write callback.
    28,  #CURLE_OPERATION_TIMEDOUT (28) Operation timeout. The specified time-out period was reached according to the conditions.
]

def dummy_timer_fn():
    return



class FTPChecker:

    last_check = time.time()
    downloaded = None
    killed = False

    def __init__(self, thread_num):
        self.thread_num = thread_num

    def debug(self, msg):
        logger.debug("CURL Thread %s %s:  " %(self.thread_num, msg))

    def get_rate(self, dlprevious, dlnow, interval):
        #lets figure out the transfer rate over the last interval
        if dlprevious == 0:
            got_bytes = dlnow
        else:
            got_bytes = dlnow - dlprevious

        xfer_rate = round(got_bytes / interval)

        #self.debug("Got bytes: %s" % got_bytes)

        xfer_rate_human = bytes2human(xfer_rate, "%(value).1f %(symbol)s/sec")
        #self.debug("XFER RATE: %s" % xfer_rate_human)

        return xfer_rate

    def reset(self):
        self.downloaded = None
        self.last_check = time.time()
        self.killed = False

    def progress_check(self, dltotal, dlnow, ultotal, ulnow):
        if self.killed:
            self.debug("Job was already killed, exiting")
            return 2

        #seconds since last check
        now = time.time()
        seconds_last_check = now - self.last_check

        if seconds_last_check > ftpmanager.FTP_TIMEOUT_TRANSFER:
            self.last_check = time.time()

            if None is self.downloaded:
                self.downloaded = dlnow
                #self.debug("First time check, skipping")
                return

            xfer_rate = self.get_rate(self.downloaded, dlnow, seconds_last_check)

            self.downloaded = dlnow

            if xfer_rate < ftpmanager.FTP_TIMEOUT_MIN_SPEED:
                self.debug("NO DATA RECEIVED LETS KILL IT")
                #hmm, lets kill it!
                self.killed = True
                return 2


class FTPMirror(Thread):

    def __init__(self, id, urls):
        Thread.__init__(self)
        self.abort = False
        self.urls = urls
        self.id = id
        self.speed = 0

        self.start()

    def log(self, msg):
        logger.debug(msg)
        log = DownloadLog(download_id_id=self.id, message=msg)
        log.save()

    def cleanup(self):
        # Cleanup
        for c in self.m.handles:
            if c.fp is not None:
                common.close_file(c.fp)
                c.fp = None
            c.close()
        self.m.close()

    def add_url_queue(self, url):
        size = url[1]
        urlpath = url[0].strip().rstrip("/")

        ftpurl = "ftp://%s:%s@%s:%s/%s" % (ftpmanager.FTP_USER, ftpmanager.FTP_PASS, ftpmanager.FTP_IP, ftpmanager.FTP_PORT, urlpath)
        ftpurl = ftpurl.encode("UTF-8")

        basepath = ""

        for part in urlpath.split(os.sep)[3:]:
            basepath = os.path.join(basepath, part)

        url_savepath = os.path.join(self.savepath, basepath).rstrip("/")

        if os.path.isfile(url_savepath):
            #compare sizes
            local_size = os.path.getsize(url_savepath)

            if local_size > 0 and local_size == size:
                #Already downloaded, skip
                return

        #make local folders if they dont exist
        try:
            os.makedirs(os.path.split(url_savepath)[0])
        except OSError as e:
            if e.errno == 17:
                pass
            else:
                raise(e)

        if re.match(".+\.sfv$", urlpath):
            #download first
            self.priority.append((ftpurl, url_savepath, size, 0))
        else:
            #add it to the queue
            self.queue.append((ftpurl, url_savepath, size, 0))

    def create_curls(self):
        self.m.handles = []

        for i in range(settings.THREADS_PER_DOWNLOAD):
            c = pycurl.Curl()
            c.fp = None
            c.thread_num = i
            c.setopt(pycurl.FOLLOWLOCATION, 1)
            c.setopt(pycurl.MAXREDIRS, 5)
            c.setopt(pycurl.NOSIGNAL, 1)
            #c.setopt(pycurl.VERBOSE, 1)
            c.setopt(pycurl.FTP_SSL, pycurl.FTPSSL_ALL)
            c.setopt(pycurl.SSL_VERIFYPEER, 0)
            c.setopt(pycurl.SSL_VERIFYHOST, 0)

            #TIMER FUNCTIONS
            #c.setopt(pycurl.LOW_SPEED_LIMIT, ftpmanager.FTP_TIMEOUT_MIN_SPEED)
            #c.setopt(pycurl.LOW_SPEED_TIME, ftpmanager.FTP_TIMEOUT_WAIT_DOWNLOAD)
            #c.setopt(pycurl.TIMEOUT, 3600)

            c.checker = FTPChecker(c.thread_num)

            c.setopt(c.NOPROGRESS, 0)
            c.setopt(c.PROGRESSFUNCTION, c.checker.progress_check)
            #PRET SUPPORT
            c.setopt(188, 1)
            self.m.handles.append(c)

    def get_next_queue(self):
        #lets find the next one we want to process
        pop_key = None
        now = datetime.now()

        for idx, queue_item in enumerate(self.queue):
            if queue_item[3] == 0:
                pop_key = idx
                break
            else:
                seconds = (now-queue_item[3]).total_seconds()
                if seconds > 30:
                    #lets use this one
                    pop_key = idx
                    break

        return pop_key

    def add_file_curl(self, curl, url, filename, remote_size):
        curl.checker.reset()
        self.log("Remote file %s size: %s" % (filename, remote_size))

        short_filename = os.path.basename(filename)
        local_size = 0

        f = None

        if os.path.isfile(filename):
            #compare sizes
            local_size = os.path.getsize(filename)

            if local_size == 0:
                #try again
                self.log("Will download %s (%s bytes)" % (short_filename, remote_size))
                f = common.open_file(filename, "wb")

            if local_size > remote_size:

                f = common.open_file(filename, "wb")

                #lets retry
                if filename in self.failed_list:
                    #what count are we at
                    count = self.failed_list.get(curl.filename)

                    if count >= 2:
                        self.log("Local size was bigger then remote, max reties reached, setting to failed %s" % short_filename)
                        return
                    else:
                        self.failed_list[filename] += 1
                else:
                    self.failed_list[filename] = 1

                self.log("Strange, local size was bigger then remote, re-downloading %s" % short_filename)
                f = common.open_file(filename, "wb")
            else:
                #lets resume
                self.log("Partial download %s (%s bytes), lets resume from %s bytes" % (short_filename, local_size, local_size))
                f = common.open_file(filename, "ab")

        else:
            self.log("Will download %s (%s bytes)" % (short_filename, remote_size))
            f = common.open_file(filename, "wb")

        curl.setopt(pycurl.RESUME_FROM, local_size)
        curl.fp = f

        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.WRITEDATA, curl.fp)
        self.m.add_handle(curl)

        # store some info
        curl.filename = filename
        curl.remote_size = remote_size
        curl.url = url

    def get_save_path(self):
        dlitem = DownloadItem.objects.get(id=self.id)
        return dlitem.localpath

    def update_dlitem(self, id, message=None, failed=False):
        try:
            dlitem = DownloadItem.objects.get(id=id)
            if message:
                logger.info(message)
                dlitem.message = message
                dlitem.log(message)

            if failed:
                dlitem.retries += 1

            dlitem.save()
        except:
            pass

    def run(self):
        try:
            max_speed_kb = settings.MAX_SPEED_PER_DOWNLOAD
            speed_delay = 0

            self.savepath = self.get_save_path()

            self.log("Starting Download")

            update_interval = 1

            self.timer = Timer(update_interval, dummy_timer_fn)
            self.timer.start()

            self.m = pycurl.CurlMulti()

            # Make a queue with (url, filename) tuples
            self.queue = []
            self.priority = []

            try:
                for url in self.urls:
                    self.add_url_queue(url)
            except Exception as e:
                logger.exception(e)
                self.log("Error: %s" % str(e))
                self.update_dlitem(self.id, message=str(e))
                return

            self.queue = self.priority + self.queue

            # Pre-allocate a list of curl objects
            self.create_curls()

            num_urls = len(self.queue)
            self.failed_list = {}

            # Main loop
            freelist = self.m.handles[:]
            num_processed = 0
            while num_processed < num_urls:
                # If there is an url to process and a free curl object, add to multi stack
                while self.queue and freelist:
                    key = self.get_next_queue()

                    if None is key:
                        #didn't find any to process.. are we still downloading an item??
                        if len(freelist) == settings.THREADS_PER_DOWNLOAD:
                            logger.debug("Sleeping 0.5 secs")
                            time.sleep(0.5)
                        break

                    url, filename, remote_size, ___ = self.queue.pop(key)
                    try:
                        self.add_file_curl(freelist.pop(), url, filename, remote_size)
                    except Exception as e:
                        logger.exception(e)
                        self.log(str(e))
                        self.update_dlitem(self.id, message=str(e))
                        self.cleanup()
                        return

                # Run the internal curl state machine for the multi stack
                while 1:
                    ret, num_handles = self.m.perform()
                    if ret != pycurl.E_CALL_MULTI_PERFORM:
                        break

                # Check for curl objects which have terminated, and add them to the freelist
                while 1:
                    num_q, ok_list, err_list = self.m.info_read()
                    for c in ok_list:
                        logger.debug("Closing file %s" % c.fp)

                        common.close_file(c.fp)

                        #Did we download the file properly???
                        success = False

                        for x in range(0, 4):
                            local_size = os.path.getsize(c.filename)

                            if local_size == c.remote_size:
                                success = True
                                break
                                logger.debug("sleeping 3 seconds")
                            time.sleep(3)

                        if success:
                            self.log("CURL Thread: %s Success:%s" % (c.thread_num, os.path.basename(c.filename)))
                        else:
                            self.failed_list[c.filename] = 1
                            self.queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                            num_processed -= 1
                            self.log("CURL Thread: %s  Failure: %s as it Didnt download properly, the local (%s) size does not match the remote size (%s), lets retry" % (c.thread_num, os.path.basename(c.filename), local_size, c.remote_size))

                        c.fp = None
                        freelist.append(c)
                        self.m.remove_handle(c)

                    for c, errno, errmsg in err_list:

                        common.close_file(c.fp)
                        c.fp = None
                        self.m.remove_handle(c)

                        #should we retry?
                        if errno in retry_on_errors:

                            if errmsg == "Callback aborted":
                                errmsg = "No data received for %s seconds" % ftpmanager.FTP_TIMEOUT_TRANSFER

                            msg = "CURL Thread %s: Unlimited retrying: %s %s %s" % (c.thread_num, os.path.basename(c.filename), errno, errmsg)
                            self.queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                            num_processed -= 1

                        else:
                            if c.filename in self.failed_list:
                                #what count are we at
                                count = self.failed_list.get(c.filename)

                                if count >= 3:
                                    msg = "CURL Thread %s: Failed: %s %s %s" % (c.thread_num, os.path.basename(c.filename), errno, errmsg)
                                    last_err = errmsg
                                else:
                                    self.failed_list[c.filename] += 1

                                    #retry
                                    self.queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                                    msg = "CURL Thread %s: Retrying: %s %s %s" % (c.thread_num, os.path.basename(c.filename), errno, errmsg)
                                    num_processed -= 1

                            else:
                                #lets retry
                                self.failed_list[c.filename] = 1
                                self.queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                                msg = "CURL Thread %s: Retrying: %s %s %s" % (c.thread_num, os.path.basename(c.filename), errno, errmsg)
                                num_processed -= 1

                        self.log(msg)
                        freelist.append(c)

                    num_processed = num_processed + len(ok_list) + len(err_list)

                    if num_q == 0:
                        break

                #lets do checks
                if not self.timer.isAlive():

                    if self.abort:
                        self.cleanup()
                        return

                    #Lets get speed
                    self.speed = 0

                    for handle in self.m.handles:
                        try:
                            self.speed = self.speed + handle.getinfo(pycurl.SPEED_DOWNLOAD)
                        except:
                            pass

                    current_speed_kb = self.speed / 1024

                    #Do we need to throttle the speed?
                    if max_speed_kb > 0:

                        #Are we over our limit??
                        if current_speed_kb > max_speed_kb:
                            #Throttle down
                            over_by = current_speed_kb - max_speed_kb

                            if over_by > 5:
                                delay_by = over_by / 2000

                                speed_delay += delay_by

                        #Are we under the limit
                        if current_speed_kb < max_speed_kb:

                            if speed_delay > 0:
                                #Throttle up
                                under_by = max_speed_kb - current_speed_kb
                                delay_by = under_by / 2000

                                if under_by > 5:
                                    speed_delay -= delay_by

                                    if speed_delay < 0:
                                        speed_delay = 0

                    #Lets restart the timer for updates..
                    self.timer = Timer(update_interval, dummy_timer_fn)
                    self.timer.start()

                # We just call select() to sleep until some more data is available.
                if speed_delay > 0:
                    time.sleep(speed_delay)
                self.m.select(1.0)
        except Exception as e:
            logger.exception(e)
            self.update_dlitem(self.id, message=str(e))

        finally:
            # Cleanup
            self.cleanup()
