from __future__ import division
import logging
import os
import re
from django.conf import settings
from djcelery_transactions import task
import pycurl
import time
from threading import Timer
from datetime import datetime
from celery import current_task
from lazycore import utils
from lazycore.utils import common


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

def timer_fn():
    return

def signal_term_handler(signal, frame):

    import inspect

    mod = inspect.getmodule(frame)

    caller = mod.__name__
    line = inspect.currentframe().f_back.f_lineno

    print "Working on line numner %s %s" % (caller, line)

    for key, value in frame.f_locals.items():

        try:
            if key == "self":

                for c in value.m.handles:
                    print "Effective url %s:" % c.getinfo(pycurl.EFFECTIVE_URL)
                    print "CURLINFO_TOTAL_TIME:%s" % c.getinfo(pycurl.TOTAL_TIME)
                    print "CURLINFO_CONNECT_TIME:%s" % c.getinfo(pycurl.CONNECT_TIME)
                    print "CURLINFO_STARTTRANSFER_TIME:%s" % c.getinfo(pycurl.STARTTRANSFER_TIME)
                    print "CURLINFO_SIZE_DOWNLOAD:%s" % c.getinfo(pycurl.SIZE_DOWNLOAD)
                    print "CURLINFO_SPEED_DOWNLOAD:%s" % c.getinfo(pycurl.SPEED_DOWNLOAD)
                    print "CURLINFO_CONTENT_LENGTH_DOWNLOAD:%s" % c.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD)

        except Exception as e:
            logger.exception(e)

        print "key: %s | val %s" % (key, value)

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

        self.debug("Got bytes: %s" % got_bytes)

        xfer_rate_human = common.bytes2human(xfer_rate, "%(value).1f %(symbol)s/sec")
        self.debug("XFER RATE: %s" % xfer_rate_human)

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

        if seconds_last_check > settings.FTP_TIMEOUT_TRANSFER:
            self.debug("Running check on data rate to make sure it has not died! seconds %s" % (seconds_last_check))
            self.debug("DLTotal: %s  dlnow: %s    downloaded: %s  " % (dltotal, dlnow, self.downloaded))

            self.last_check = time.time()

            if None is self.downloaded:
                self.downloaded = dlnow
                self.debug("First time check, skipping")
                return

            xfer_rate = self.get_rate(self.downloaded, dlnow, seconds_last_check)

            self.downloaded = dlnow

            if xfer_rate < settings.FTP_TIMEOUT_MIN_SPEED:
                self.debug("NO DATA RECEIVED LETS KILL IT")
                #hmm, lets kill it!
                self.killed = True
                return 2


class FTPMirror:

    def __init__(self):
        # We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
        # the libcurl tutorial for more info.

        import signal
        SIGUSR1 = 10

        signal.signal(SIGUSR1, signal_term_handler)
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)


    @task(bind=True)
    def mirror_ftp_folder(self, urls, dlitem):

        update_interval = 3 #seconds

        if not utils.queuemanager.QueueManager.queue_running():
            logger.debug("Queue is stopped, exiting")
            return

        savepath = dlitem.localpath

        current_task.update_state(state='RUNNING', meta={'updated': time.mktime(datetime.now().timetuple()), 'speed': 0, 'last_error': ""})

        dlitem.log("Starting Download")

        self.timer = Timer(update_interval, timer_fn)
        self.timer.start()

        self.m = pycurl.CurlMulti()

        # Make a queue with (url, filename) tuples
        queue = []
        priority = []

        for url in urls:
            size = url[1]
            urlpath = url[0].strip()

            ftpurl = "ftp://%s:%s@%s:%s/%s" % (settings.FTP_USER, settings.FTP_PASS, settings.FTP_IP, settings.FTP_PORT, urlpath.lstrip("/"))

            ftpurl = ftpurl.encode("UTF-8")

            basepath = ""

            i = 0

            urlpath_split = urlpath.split(os.sep)

            if len(urlpath_split) == 3:
                pass
            else:
                for path in urlpath_split:
                    if i > 2:
                        basepath = os.path.join(basepath, path)
                    i += 1

            urlsavepath = os.path.join(savepath, basepath).rstrip("/")

            if os.path.isfile(urlsavepath):
                #compare sizes
                local_size = os.path.getsize(urlsavepath)

                if local_size > 0 and local_size == size:
                    #skip
                    continue

            #make local folders if they dont exist
            try:
                os.makedirs(os.path.split(urlsavepath)[0])
            except:
                pass

            if re.match(".+\.sfv$", urlpath):
                #download first
                priority.append((ftpurl, urlsavepath, size, 0))
            else:
                #add it to the queue
                queue.append((ftpurl, urlsavepath, size, 0))

        queue = priority + queue

        # Pre-allocate a list of curl objects
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
            #c.setopt(pycurl.LOW_SPEED_LIMIT, settings.FTP_TIMEOUT_MIN_SPEED)
            #c.setopt(pycurl.LOW_SPEED_TIME, settings.FTP_TIMEOUT_WAIT_DOWNLOAD)
            #c.setopt(pycurl.TIMEOUT, 3600)

            c.checker = FTPChecker(c.thread_num)

            c.setopt(c.NOPROGRESS, 0)
            c.setopt(c.PROGRESSFUNCTION, c.checker.progress_check)
            #PRET SUPPORT
            c.setopt(188, 1)
            self.m.handles.append(c)

        num_urls = len(queue)

        failed_list = {}

        # Main loop
        freelist = self.m.handles[:]
        num_processed = 0

        last_err = ""

        while num_processed < num_urls:
            # If there is an url to process and a free curl object, add to multi stack
            while queue and freelist:
                #lets find the next one we want to process
                pop_key = None

                now = datetime.now()

                for idx, queue_item in enumerate(queue):
                    if queue_item[3] == 0:
                        pop_key = idx
                        break
                    else:
                        seconds = (now-queue_item[3]).total_seconds()

                        if seconds > 30:
                            #lets use this one
                            pop_key = idx
                            break

                if None is pop_key:
                    #didn't find any to process.. are we still downloading an item??
                    logger.debug("breaking")
                    if len(freelist) == settings.THREADS_PER_DOWNLOAD:
                        logger.debug("Sleeping 1 second")
                        time.sleep(1)
                    break

                url, filename, remote_size, ___ = queue.pop(pop_key)
                c = freelist.pop()


                c.checker.reset()
                logger.debug("CREATE NEW Thread %s  sec: %s      OTHER: %s" % (c.checker.thread_num, c.checker.last_check, c.checker))

                dlitem.log("Remote file %s size: %s" % (filename, remote_size))

                short_filename = os.path.basename(filename)

                local_size = 0
                f = None

                if os.path.isfile(filename):
                    #compare sizes
                    local_size = os.path.getsize(filename)

                    if local_size == 0:
                        #try again
                        dlitem.log("Will download %s (%s bytes)" % (short_filename, remote_size))
                        f = common.open_file(filename, "wb")

                    if local_size > remote_size:
                        dlitem.log("Strange, local size was bigger then remote, re-downloading %s" % short_filename)
                        f = common.open_file(filename, "wb")
                    else:
                        #lets resume
                        dlitem.log("Partial download %s (%s bytes), lets resume from %s bytes" % (short_filename, local_size, local_size))
                        f = common.open_file(filename, "ab")

                else:
                    dlitem.log("Will download %s (%s bytes)" % (short_filename, remote_size))
                    f = common.open_file(filename, "wb")

                c.setopt(pycurl.RESUME_FROM, local_size)
                c.fp = f

                c.setopt(pycurl.URL, url)
                c.setopt(pycurl.WRITEDATA, c.fp)
                self.m.add_handle(c)

                # store some info
                c.filename = filename
                c.remote_size = remote_size
                c.url = url

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
                        time.sleep(3)

                    if success:
                        dlitem.log("CURL Thread: %s Success:%s" % (c.thread_num, os.path.basename(c.filename)))
                    else:
                        failed_list[c.filename] = 1
                        queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                        num_processed -= 1
                        dlitem.log("CURL Thread: %s  Failure: %s as it Didnt download properly, the local (%s) size does not match the remote size (%s), lets retry" % (c.thread_num, os.path.basename(c.filename), local_size, c.remote_size))

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
                            errmsg = "No data received for %s seconds" % settings.FTP_TIMEOUT_TRANSFER

                        msg = "CURL Thread %s: Unlimited retrying: %s %s %s" % (c.thread_num, os.path.basename(c.filename), errno, errmsg)
                        queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                        num_processed -= 1

                    else:
                        if c.filename in failed_list:
                            #what count are we at
                            count = failed_list.get(c.filename)

                            if count >= 3:
                                msg = "CURL Thread %s: Failed: %s %s %s" % (c.thread_num, os.path.basename(c.filename), errno, errmsg)
                                last_err = errmsg
                            else:
                                failed_list[c.filename] += 1

                                #retry
                                queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                                msg = "CURL Thread %s: Retrying: %s %s %s" % (c.thread_num, os.path.basename(c.filename), errno, errmsg)
                                num_processed -= 1

                        else:
                            #lets retry
                            failed_list[c.filename] = 1
                            queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                            msg = "CURL Thread %s: Retrying: %s %s %s" % (c.thread_num, os.path.basename(c.filename), errno, errmsg)
                            num_processed -= 1

                    dlitem.log(msg)
                    freelist.append(c)

                num_processed = num_processed + len(ok_list) + len(err_list)

                if num_q == 0:
                    break

            #should we update?
            if not self.timer.isAlive():
                #Lets get speed
                speed = 0

                for handle in self.m.handles:
                    try:
                        speed = speed + handle.getinfo(pycurl.SPEED_DOWNLOAD)
                    except Exception as e:
                        dlitem.log("error getting speed %s" % e.message)

                current_task.update_state(state='RUNNING', meta={'updated': time.mktime(datetime.now().timetuple()), 'speed': speed, 'last_error': last_err})

                self.timer = Timer(update_interval, timer_fn)
                self.timer.start()

            # Currently no more I/O is pending, could do something in the meantime
            # (display a progress bar, etc.).
            # We just call select() to sleep until some more data is available.
            self.m.select(1.0)

        # Cleanup
        for c in self.m.handles:
            if c.fp is not None:
                common.close_file(c.fp)
                c.fp = None
            c.close()
        self.m.close()

        from lazycore.management.commands.queue import Command
        cmd = Command()
        cmd.handle.delay(seconds=5)
