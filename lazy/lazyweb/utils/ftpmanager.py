'''
Created on 06/04/2012

@author: Steve
'''
from __future__ import division
from django.core.cache import cache
import logging
import os
import subprocess
import re
import signal
from ftplib import FTP_TLS
from django.conf import settings
from lazyweb import utils
from djcelery_transactions import task
from celery.result import AsyncResult
from lazyweb.models import DownloadItem
from cStringIO import StringIO
import pycurl, time
from datetime import datetime
import pprint
from celery import current_task
import ftplib

logger = logging.getLogger(__name__)


def open_file(file, options):

    for x in range(0, 4):
        try:
            return open(file, options, 8192)
        except:
            time.sleep(1)
            pass

    #one last try!
    return open(file, options, 8192)


def close_file(file):

    for x in range(0, 4):
        try:
            file.close()
        except:
            time.sleep(1)
            pass

    #one last try
    file.close()

retry_on_errors = [
    13, #CURLE_FTP_WEIRD_PASV_REPLY (13) libcurl failed to get a sensible result back from the server as a response to either a PASV or a EPSV command. The server is flawed.
    14, #CURLE_FTP_WEIRD_227_FORMAT
    35,
    7, #Connection refused
    12, #CURLE_FTP_ACCEPT_TIMEOUT (12) During an active FTP session while waiting for the server to connect, the CURLOPT_ACCEPTTIMOUT_MS (or the internal default) timeout expired.
    23, #CURLE_WRITE_ERROR (23) An error occurred when writing received data to a local file, or an error was returned to libcurl from a write callback.
    28, #CURLE_OPERATION_TIMEDOUT (28) Operation timeout. The specified time-out period was reached according to the conditions.
    ]

class FTPMirror:

    # We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
    # the libcurl tutorial for more info.

    @task(bind=True)
    def mirror_ftp_folder(self, urls, savepath, dlitem):

        if not utils.queue_running():
            logger.debug("Queue is stopped, exiting")
            return


        current_task.update_state(state='RUNNING', meta={'updated': time.mktime(datetime.now().timetuple()), 'speed': 0})

        dlitem.log("Starting Download")

        last_status_update = datetime.now()

        #Find jobs running and if they are finished or not
        task = dlitem.get_task()

        if None is task:
            pass
        elif task.state == "REVOKED":
            logger.info("%s was revoked. ignore" % dlitem.ftppath)
            return
        elif task.state == "SUCCESS" or task.state == "FAILURE":
            pass
        else:
            dlitem.log("%s already being downloaded" % dlitem.ftppath)
            return

        self.m = pycurl.CurlMulti()

        try:
            import signal
            from signal import SIGPIPE, SIG_IGN
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)
        except ImportError:
            pass


        # Get args
        num_conn = settings.LFTP_THREAD_PER_DOWNLOAD

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

        logger.debug(queue)

        # Pre-allocate a list of curl objects
        self.m.handles = []

        for i in range(num_conn):
            c = pycurl.Curl()
            c.fp = None
            c.setopt(pycurl.FOLLOWLOCATION, 1)
            c.setopt(pycurl.MAXREDIRS, 5)
            c.setopt(pycurl.NOSIGNAL, 1)
            #c.setopt(pycurl.VERBOSE, 1)
            c.setopt(pycurl.FTP_SSL, pycurl.FTPSSL_ALL)
            c.setopt(pycurl.SSL_VERIFYPEER, 0)
            c.setopt(pycurl.SSL_VERIFYHOST, 0)

            #PRET SUPPORT
            c.setopt(188, 1)
            self.m.handles.append(c)

        num_urls = len(queue)

        failed_list = {}

        # Main loop
        freelist = self.m.handles[:]
        num_processed = 0

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

                        if seconds > 120:
                            #lets use this one
                            pop_key = idx
                            break

                if None is pop_key:
                    #didn't find any to process.. lets wait
                    time.sleep(1)
                    break

                url, filename, remote_size, ___ = queue.pop(0)
                c = freelist.pop()

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
                        f = open_file(filename, "wb")

                    if local_size > remote_size:
                        dlitem.log("Strange, local size was bigger then remote, re-downloading %s" % short_filename)
                        f = open_file(filename, "wb")
                    else:
                        #lets resume
                        dlitem.log("Partial download %s (%s bytes), lets resume from %s bytes" % (short_filename, local_size, local_size))
                        f = open_file(filename, "ab")

                else:
                    dlitem.log("Will download %s (%s bytes)" % (short_filename, remote_size))
                    f = open_file(filename, "wb")

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

                    close_file(c.fp)

                    #Did we download the file properly???
                    success = False

                    for x in range(0, 4):
                        local_size = os.path.getsize(c.filename)

                        if local_size == remote_size:
                            success = True
                            break
                        time.sleep(3)

                    if success:
                        dlitem.log("Success:%s" % (os.path.basename(c.filename)))
                    else:
                        failed_list[c.filename] = 1
                        queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                        num_processed -= 1
                        dlitem.log("Failure: %s as it Didnt download properly, the local (%s) size does not match the remote size (%s), lets retry" % (os.path.basename(c.filename), local_size, remote_size))

                    c.fp = None
                    freelist.append(c)
                    self.m.remove_handle(c)

                for c, errno, errmsg in err_list:

                    close_file(c.fp)
                    c.fp = None
                    self.m.remove_handle(c)

                    #should we retry?
                    if errno in retry_on_errors:
                        msg = "Unlimited retrying: %s %s %s" % (os.path.basename(c.filename), errno, errmsg)
                        queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                        num_processed -= 1

                    else:
                        if c.filename in failed_list:
                            #what count are we at
                            count = failed_list.get(c.filename)

                            if count >= 3:
                                msg = "Failed: %s %s %s" % (os.path.basename(c.filename), errno, errmsg)
                            else:
                                failed_list[c.filename] += 1
                                #retry
                                queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                                msg = "Retrying: %s %s %s" % (os.path.basename(c.filename), errno, errmsg)
                                num_processed -= 1

                        else:
                            #lets retry
                            failed_list[c.filename] = 1
                            queue.append((c.url, c.filename, c.remote_size, datetime.now()))
                            msg = "Retrying: %s %s %s" % (os.path.basename(c.filename), errno, errmsg)
                            num_processed -= 1

                    dlitem.log(msg)
                    freelist.append(c)

                num_processed = num_processed + len(ok_list) + len(err_list)

                if num_q == 0:
                    break

            #should we update?
            now = datetime.now()
            seconds = (now-last_status_update).total_seconds()

            if seconds > 3:
                last_status_update = now

                #Lets get speed
                speed = 0

                for handle in self.m.handles:
                    try:
                        speed = speed + handle.getinfo(pycurl.SPEED_DOWNLOAD)
                    except Exception as e:
                        dlitem.log("error getting speed %s" % e.message)

                current_task.update_state(state='RUNNING', meta={'updated': time.mktime(now.timetuple()), 'speed': speed})

            # Currently no more I/O is pending, could do something in the meantime
            # (display a progress bar, etc.).
            # We just call select() to sleep until some more data is available.
            self.m.select(1.0)

        dlitem.log("Queue")
        dlitem.log(queue)
        dlitem.log("Failed list")
        dlitem.log(failed_list)

        # Cleanup
        for c in self.m.handles:
            if c.fp is not None:
                close_file(c.fp)
                c.fp = None
            c.close()
        self.m.close()

        from lazyweb.management.commands.queuerunner import Command
        cmd = Command()
        cmd.handle.delay(seconds=5)


class FTPManager:
    ftps = None

    def __init__(self):
        try:
            self.connect()
        except Exception as e:
            #lets try again
            print "failed connecting to ftp, trying again."
            self.connect()


    def ftpwalk(self, top, topdown=True, onerror=None, cur_depth=0, max_depth=9):
        """
        Generator that yields tuples of (root, dirs, nondirs).
        """
        # Make the FTP object's current directory to the top dir.
        self.ftps.cwd(top)

        # We may not have read permission for top, in which case we can't
        # get a list of the files the directory contains.  os.path.walk
        # always suppressed the exception then, rather than blow up for a
        # minor reason when (say) a thousand readable directories are still
        # left to visit.  That logic is copied here.


        try:
            dirs, nondirs = self._ftp_listdir()
        except os.error, err:
            print "ERROR"
            if onerror is not None:
                onerror(err)
            return

        if cur_depth >= max_depth:
            yield top, dirs, nondirs
            return

        next_depth = cur_depth + 1

        if topdown:
            yield top, dirs, nondirs
        for entry in dirs:
            dname = entry[0]
            path = os.path.join(top, dname)
            for x in self.ftpwalk(path, topdown=topdown, onerror=onerror, cur_depth=next_depth, max_depth=max_depth):
                yield x

        if not topdown:
                yield top, dirs, nondirs

    def _ftp_listdir(self):
        """
        List the contents of the FTP opbject's cwd and return two tuples of

           (filename, size, mtime, mode, link)

        one for subdirectories, and one for non-directories (normal files and other
        stuff).  If the path is a symbolic link, 'link' is set to the target of the
        link (note that both files and directories can be symbolic links).

        Note: we only parse Linux/UNIX style listings; this could easily be
        extended.
        """
        dirs, nondirs = [], []
        listing = []
        self.sendcmd("PRET LIST")
        self.ftps.retrlines('MLSD', listing.append)
        for line in listing:
            # Parse, assuming a UNIX listing
            line_values = line.split(";")

            if len(line_values) < 6:
                logger.info('Warning: Error reading short line')
                continue

            type = line_values[0].strip()
            filename = line_values[-1].lstrip()

            if filename.endswith("-MISSING"):
                continue

            if filename in ('.', '..'):
                continue

            # Get the file size.
            size = int(line_values[1].strip("size="))

            entry = (filename, size)
            if type == "type=dir":
                dirs.append(entry)
            else:
                nondirs.append(entry)

        return dirs, nondirs

    def get_files_for_download(self, folder):
        found_files = []
        size = 0

        if utils.is_video_file(folder):
            #we have a file
            size = self.getRemoteSize(folder)
            file_found = [folder, size]
            found_files.append(file_found)
        else:
            #we have a folder
            for curfolder, dirs, files in self.ftpwalk(folder):
                for file in files:
                    file_found = [str(os.path.join(curfolder, file[0])), file[1]]
                    found_files.append(file_found)
                    size += file[1]

        return found_files, size


    def connect(self):
        self.ftps = FTP_TLS()
        self.ftps.set_debuglevel(0)
        self.ftps.connect(settings.FTP_IP, settings.FTP_PORT, timeout=60)
        self.ftps.login(settings.FTP_USER, settings.FTP_PASS)



    def get_required_folders_for_multi(self, folder, onlyget):

        onlyget_clean_seasons = []
        onlyget_clean_eps = {}

        #sanatise onlyget
        for season, eps in onlyget.items():
            if len(eps) == 0 or 0 in eps:
                #get whole season
                onlyget_clean_seasons.append(int(season))
                continue

            get_eps = []

            for ep in eps:
                try:
                    if int(ep) in get_eps:
                        #duplicate
                        continue
                    else:
                        get_eps.append(int(ep))
                except:
                    pass

            if len(get_eps) > 0:
                onlyget_clean_eps[int(season)] = get_eps

        skippath = []
        size = 0
        urls = []

        logger.debug("Eps: %s" % onlyget_clean_eps)
        logger.debug("Seasons: %s" % onlyget_clean_seasons)


        #lets find them all
        for curdir, dirs, files in self.ftpwalk(folder, max_depth=4):

            if len(onlyget_clean_eps) == 0 and len(onlyget_clean_seasons) == 0:
                break

            for path in skippath:
                if path.startswith(curdir) or path == curdir:
                    continue

            for file in files:
                #first lets check if something we might be interested in

                if utils.is_video_file(file[0]):
                    found_ep_season, found_ep = utils.get_ep_season_from_title(file[0])

                    if found_ep_season in onlyget_clean_eps.keys():
                        eps = onlyget_clean_eps[found_ep_season]

                        if found_ep in eps:
                            onlyget_clean_eps[found_ep_season].remove(ep)

                        if len(found_ep) > 1:
                            #multi ep

                            process = False

                            for ep in found_ep:
                                if ep in eps:
                                    process = True

                            if process:
                                logger.debug("We found a multi ep match, we must download this! %s" % file[0])
                                file_found = [(str(os.path.join(curdir, file[0])), file[1])]
                                size += file[1]
                                urls = urls + file_found

                                for ep in found_ep:
                                    try:
                                        onlyget_clean_eps[found_ep_season].remove(ep)
                                    except:
                                        pass

                        elif len(found_ep) == 1:
                            if found_ep[0] in eps:
                                logger.debug("We found a match, we must download this! %s" % file[0])
                                file_found = [(str(os.path.join(curdir, file[0])), file[1])]
                                size += file[1]
                                urls = urls + file_found
                                onlyget_clean_eps[found_ep_season].remove(found_ep[0])

            #Lets check if required items are in folders
            for dir in dirs:
                dir = dir[0]
                full_dir = os.path.join(curdir, dir)

                #multi season pack
                if utils.match_str_regex(settings.TVSHOW_SEASON_MULTI_PACK_REGEX, dir):
                    logger.debug("Multi Season pack detected %s" % dir)

                    seasons = utils.get_season_from_title(dir)

                    #first do we even want to bother
                    process = False

                    for season in seasons:
                        if season in onlyget_clean_seasons or season in onlyget_clean_eps.keys():
                            #we want to process this
                            process = True

                    if not process:
                        skippath.append(full_dir)
                        continue

                elif utils.match_str_regex(settings.TVSHOW_SEASON_PACK_REGEX, dir):
                    logger.debug("Season pack detected %s" % dir)

                    seasons = utils.get_season_from_title(dir)

                    for season in seasons:
                        if season in onlyget_clean_seasons:
                            onlyget_clean_seasons.remove(season)
                            logger.debug("we must download this one! %s " % dir)
                            skippath.append(full_dir)
                            found_urls, found_size = self.get_files_for_download(full_dir)
                            size += found_size
                            urls = urls + found_urls

                elif utils.match_str_regex(settings.TVSHOW_REGEX, dir):
                    logger.debug("We found an ep %s" % dir)
                    skippath.append(full_dir)

                    #first lets check if something we might be interested in
                    found_ep_season, found_ep = utils.get_ep_season_from_title(dir)

                    if found_ep_season in onlyget_clean_eps.keys():
                        eps = onlyget_clean_eps[found_ep_season]

                        if len(found_ep) > 1:
                            #multi ep

                            process = False

                            for ep in found_ep:
                                if ep in eps:
                                    process = True

                            if process:
                                logger.debug("We found a multi ep match, we must download this! %s" % dir)
                                skippath.append(full_dir)
                                found_urls, found_size = self.get_files_for_download(full_dir)
                                size += found_size
                                urls = urls + found_urls

                                for ep in found_ep:
                                    try:
                                        onlyget_clean_eps[found_ep_season].remove(ep)
                                    except:
                                        pass

                        elif len(found_ep) == 1:
                            if found_ep[0] in eps:
                                logger.debug("We found a match, we must download this! %s" % dir)
                                skippath.append(full_dir)
                                found_urls, found_size = self.get_files_for_download(full_dir)
                                size += found_size
                                urls = urls + found_urls
                                eps.remove(found_ep[0])

        for season, eps in onlyget_clean_eps.copy().iteritems():
            if len(eps) == 0:
                del onlyget_clean_eps[season]

        logger.debug("Left Eps: %s" % onlyget_clean_eps)
        logger.debug("Left Seasons: %s" % onlyget_clean_seasons)

        if len(onlyget_clean_eps) > 0 or len(onlyget_clean_seasons) > 0:
            raise Exception("Unable to find all the required ep's within season pack")

        return urls, size


    def getEpFolder(self, season, ep, directoryListing):

        for folder in directoryListing:
            fileName, fileExtension = os.path.splitext(folder)

            if fileExtension == 'nfo':
                continue

            epSeason, epsList = utils.get_ep_season_from_title(folder)

            #we got the right season?
            if int(season) == int(epSeason):
                #we got the right ep?
                for epNo in epsList:
                    if int(epNo) == int(ep):
                        logger.debug("we found the folder %s" % folder)
                        return folder

        return False

    def getSeasonFolder(self, season, directoryListing):

        for seasonFolder in directoryListing:
            folderSeasons = utils.get_season_from_title(seasonFolder)

            if int(season) in folderSeasons:
                logger.debug("we found the folder %s" % seasonFolder)
                return seasonFolder

        return False

    def getRemoteSize(self, remote):
        ftpCMD = 'cd %s' % remote

        try:
            size = self.ftps.size(remote)
        except:
            return 0

        return size


    def get_size(self, local):
        local = local.strip()
        """Get size of a directory tree or a file in bytes."""
        logger.debug("Getting local size of folder: %s" % local)
        path_size = 0
        for path, directories, files in os.walk(local):
            for filename in files:
                path_size += os.lstat(os.path.join(path, filename)).st_size
            for directory in directories:
                path_size += os.lstat(os.path.join(path, directory)).st_size
        path_size += os.path.getsize(local)
        return path_size


    def downloadTVSeasonTorrent(self, site, torrent):
        logger.info("Downloading torrent on ftp %s" % torrent)

        cmd = "site torrent download %s %s" % (site, torrent)

        out = self.sendcmd(cmd)

        for line in out.splitlines():
            m = re.search('(?i)200- Finished grabbing Torrent file. Now starting the torrent, when completed the files will show up under (.+)', line)

            if m:
                return m.group(1)

            m = re.search('(?i)ERROR: Torrent already downloaded here: (.+)', line)

            if m:
                return m.group(1)

        return False


    def getTVTorrentsPreScan(self, search_names):

        sites = ['scc', 'tl', 'revtt']

        torrents = {}
        torrents['scc'] = []
        torrents['tl'] = []
        torrents['revtt'] = []

        show_name = search_names[-1]

        for site in sites:

            cmdremote = "%s" % (show_name)
            cmd = "site torrent search %s %s" % (site, cmdremote)

            out = self.sendcmd(cmd)

            logger.debug(out)

            for line in iter(out.splitlines()):
                line = line.lower()

                #do fuzzy match
                match = re.search("(?i)200- (.+s([0-9][0-9])e([0-9][0-9]).+)\ [0-9]", line.strip())

                if match:
                    #found a torrent..
                    torrent = match.group(1).strip()

                    ratio = utils.compare_torrent_2_show(show_name, torrent)

                    if ratio >= 0.93:
                        torrents[site].append(torrent)

        return torrents

    def getTVTorrents(self, site, search_names, season, ep):

        logger.info("Searching %s torrents for   %s S%s E%s" % (site, search_names[0], str(season).zfill(2), str(ep).zfill(2)))

        torrents = []
        str_season = str(season).zfill(2)
        str_ep = str(ep).zfill(2)

        for show_name in search_names:

            cmdremote = "%s S%sE%s" % (show_name, str_season, str_ep)
            cmd = "site torrent search %s %s" % (site, cmdremote)

            out = self.sendcmd(cmd)

            logger.debug(out)

            for line in iter(out.splitlines()):
                line = line.lower()

                #do fuzzy match
                match = re.search("(?i)200- (.+s([0-9][0-9])e([0-9][0-9]).+)\ [0-9]", line.strip())

                if match:
                    #found a torrent..
                    torrent = match.group(1).strip()

                    ratio = utils.compare_torrent_2_show(show_name, torrent)

                    if ratio >= 0.93:
                        logger.debug("Potential found match %s" % match.group(1))

                        torSeason, torEps = utils.get_ep_season_from_title(match.group(1))

                        try:
                            if int(torSeason) == season:
                                for torEp in torEps:
                                    logger.info("found match %s %s" % (season,ep))
                                    if int(torEp) == ep:
                                        torrents.append(torrent)
                                        return torrents, torEps

                        except Exception as e:
                            logger.exception(e.message)

        return torrents, []


    def downloadTVTorrent(self, site, torrent):
        logger.info("Downloading torrent on ftp %s" % torrent)

        cmd = "site torrent gettv %s %s" % (site, torrent)

        out = self.sendcmd(cmd)

        for line in out.splitlines():
            m = re.search('(?i)200- Finished grabbing Torrent file. Now starting the torrent, when completed the files will show up under (.+)', line)
            if m:
                logger.info("Downloaded torrent on the ftp as %s" % m.group(1))

                if m.group(1).strip() == "":
                    return False

                return m.group(1)

            m = re.search('(?i)ERROR: Torrent already downloaded here: (.+)', line)
            if m:
                logger.info("Downloaded torrent on the ftp as %s" % m.group(1))
                if m.group(1).strip() == "":
                    return False

                return m.group(1)

        return False

    def getTVTorrentsSeason(self, site, show_names, season=0):

        str_season = str(season).zfill(2)

        logger.info("Searching %s torrents for   %s S%s" % (site, show_names[0], str_season))

        torrents = []

        for show_name in show_names:

            if season == 0:
                cmdremote = show_name
            else:
                cmdremote = "%s S%s" % (show_name, str_season)

            cmd = "site torrent search %s %s" % (site, cmdremote)

            out = self.sendcmd(cmd)

            logger.debug(out)

            for line in iter(out.splitlines()):

                #do fuzzy match
                match = re.search("200- ((.+)S([0-9][0-9])[-0-9\ .].+)\ [0-9]", line.strip())

                if match:
                    #found a torrent..
                    torrent = match.group(1).strip()

                    ratio = utils.compare_torrent_2_show(show_name, torrent)

                    if ratio >= 0.93:
                        #its for this show..

                        if utils.match_str_regex(settings.TVSHOW_SPECIALS_REGEX, torrent):
                            continue

                        try:

                            if season == 0:
                                logger.info("Found match %s" % torrent)
                                #we want to return it all!!
                                torrents.append(torrent)
                            else:
                                torSeasons = utils.get_season_from_title(line.strip())

                                if season in torSeasons:
                                    logger.info("Found match %s" % torrent)
                                    torrents.append(torrent)

                        except:
                            logger.error("Error converting season and ep to int %s" % line)
                            continue

        return torrents


    def sendcmd(self, cmd):

        #first attempt
        try:
            logger.debug("Sending command to ftp %s" % cmd)
            return self.ftps.sendcmd(cmd)
        except Exception as e:
            print "retrying sending command as : %s" % e
            ## it failed.. lets try again
            self.connect()

        return self.ftps.sendcmd(cmd)

    def download_torrent(self, site, torrent):
        ftpresult = self.sendcmd("site torrent download %s %s" % (site, torrent))

        path = None
        error = None
        print ftpresult

        for line in ftpresult.split("\n"):

            path_found = utils.get_regex(line, "200- Finished grabbing Torrent file. Now starting the torrent, when completed the files will show up under (.+)", 1)
            error_found = utils.get_regex(line, "200- ERROR: (.+)", 1)
            already_downloaded_path = utils.get_regex(line, "ERROR: Torrent already downloaded here: (.+)", 1)

            if path_found and path_found != "":
                path = path_found

            if error_found and error_found != "":
                error = error_found

            if already_downloaded_path and already_downloaded_path != "":
                error = None
                path = already_downloaded_path

        if error:
            raise Exception(error)

        if path:
            return path


    def search_torrents(self, search):
        ftpresult = self.sendcmd("site torrent search all %s" % search)

        if ftpresult and ftpresult != '':
            results = {}

            cur_site = {}
            results['global'] = cur_site

            process_tors = False

            for line in ftpresult.split("\n"):
                error = utils.get_regex(line, "[0-9]+- ERROR: (.+)", 1)

                if error:
                    if "errors" in cur_site:
                        cur_site['errors'].append(error)
                    else:
                        cur_site['errors'] = []
                        cur_site['errors'].append(error)

                found_site = utils.get_regex(line, '.+===.+Matches Found on\ ([A-Za-z\-0-9]+)', 1)

                if found_site:
                    #found a new site
                    cur_site = {}
                    results[found_site] = cur_site

                if utils.match_str_regex(['200- TORRENT.+SIZE.+'], line):
                    process_tors = True

                if process_tors:
                    found_torrent = utils.get_regex(line, '200- (.+)\ ([0-9]+\.[0-9]+.[MBGB]+).+', 1)
                    found_size = utils.get_regex(line, '200- (.+)\ ([0-9]+\.[0-9]+.[MBGB]+).+', 2)

                    if found_size:
                        found_size = found_size.strip()

                    if found_torrent:

                        found_torrent = found_torrent.strip()

                        #we found a torrent
                        if 'torrents' in cur_site:
                            cur_site['torrents'][found_torrent] = {}
                            cur_site['torrents'][found_torrent]['name'] = found_torrent
                            cur_site['torrents'][found_torrent]['size'] = found_size
                        else:
                            cur_site['torrents'] = {}
                            cur_site['torrents'][found_torrent] = {}
                            cur_site['torrents'][found_torrent]['name'] = found_torrent
                            cur_site['torrents'][found_torrent]['size'] = found_size

            import pprint
            pprint.pprint(results)
            return results


