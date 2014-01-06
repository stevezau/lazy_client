'''
Created on 06/04/2012

@author: Steve
'''
from __future__ import division
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


logger = logging.getLogger(__name__)

#class Singleton(type):
#    _instances = {}
#    def __call__(cls, *args, **kwargs):
#        if cls not in cls._instances:
#           cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
#       return cls._instances[cls]

class FTPMirror():

    def __init__(self):
        m = pycurl.CurlMulti()
        m.setopt(pycurl.URL, r'ftp://ftp.ncbi.nih.gov/refseq/release/')

    def mirror_ftp_folder(self, remotepath, localpath):
        curl = pycurl.CurlMulti()

        urls = [] # list of urls
        # reqs: List of individual requests.
        # Each list element will be a 3-tuple of url (string), response string buffer
        # (cStringIO.StringIO), and request handle (pycurl.Curl object).
        reqs = []

        # Build multi-request object.
        m = pycurl.CurlMulti()
        for url in urls:
            response = StringIO()
            handle = pycurl.Curl()
            handle.setopt(pycurl.URL, url)
            handle.setopt(pycurl.WRITEFUNCTION, response.write)
            req = (url, response, handle)
            # Note that the handle must be added to the multi object
            # by reference to the req tuple (threading?).
            m.add_handle(req[2])
            reqs.append(req)

        # Perform multi-request.
        # This code copied from pycurl docs, modified to explicitly
        # set num_handles before the outer while loop.
        SELECT_TIMEOUT = 1.0
        num_handles = len(reqs)
        while num_handles:
            ret = m.select(SELECT_TIMEOUT)
            if ret == -1:
                continue
            while 1:
                ret, num_handles = m.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break



class FTPManager():
    ftps = None

    def __init__(self):
        try:
            self.connect()
        except Exception as e:
            #lets try again
            print "failed connecting to ftp, trying again."
            self.connect()

    def ftpwalk(self, top, topdown=True, onerror=None):
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
            if onerror is not None:
                onerror(err)
            return

        if topdown:
            yield top, dirs, nondirs
        for entry in dirs:
            dname = entry[0]
            path = os.path.join(top, dname)
            if entry[-1] is None: # not a link
                for x in self.ftpwalk(path, topdown, onerror):
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
        _calmonths = dict( (x, i+1) for i, x in
                   enumerate(('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')) )

        dirs, nondirs = [], []
        listing = []
        self.sendcmd("PRET LIST")
        self.ftps.retrlines('MLSD', listing.append)
        for line in listing:
            # Parse, assuming a UNIX listing
            print "line: " + line
            line_values = line.split(";")

            print len(line_values)
            print line
            words = line.split(None, 8)
            print len(words)
            if len(words) < 6:
                print words
                logger.info('Warning: Error reading short line %s' % line)
                continue

            # Get the filename.
            filename = words[-1].lstrip()
            if filename in ('.', '..'):
                continue

            # Get the link target, if the file is a symlink.
            extra = None
            i = filename.find(" -> ")
            if i >= 0:
                # words[0] had better start with 'l'...
                extra = filename[i+4:]
                filename = filename[:i]

            # Get the file size.
            size = int(words[4])

            # Get the date.
            year = datetime.today().year
            month = _calmonths[words[5]]
            day = int(words[6])
            mo = re.match('(\d+):(\d+)', words[7])
            if mo:
                hour, min = map(int, mo.groups())
            else:
                mo = re.match('(\d\d\d\d)', words[7])
                if mo:
                    year = int(mo.group(1))
                    hour, min = 0, 0
                else:
                    raise ValueError("Could not parse time/year in line: '%s'" % line)
            dt = datetime(year, month, day, hour, min)
            mtime = time.mktime(dt.timetuple())

            # Get the type and mode.
            mode = words[0]

            entry = (filename, size, mtime, mode, extra)
            if mode[0] == 'd':
                dirs.append(entry)
            else:
                nondirs.append(entry)
        return dirs, nondirs

    def connect(self):
        self.ftps = FTP_TLS()
        self.ftps.set_debuglevel(1)
        self.ftps.connect(settings.FTP_IP, settings.FTP_PORT, timeout=60)
        self.ftps.login(settings.FTP_USER, settings.FTP_PASS)

    def getFolderListing(self, folder, onlyDir=False):
        logger.debug("Getting listing of %s" % folder)

        ls = []

        self.ftps.cwd(folder)

        self.sendcmd("PRET LIST")

        cmd = "MLSD"
        self.ftps.retrlines(cmd, ls.append)

        eps = []

        for item in ls:

            fileValues = item.split(";")

            if onlyDir:
                isDir = fileValues[0].strip()

                if isDir == 'type=file':
                    eps.append((fileValues[-1].strip()))
            else:
                eps.append((fileValues[-1].strip()))

        # If we get here, then the output has finished and we received no match
        return eps

    def getRemoteSizeMulti(self, folders):
        remotesize = False
        #lets gets get the size in total
        for folder in folders:
            folderSize = self.getRemoteSize(folder)

            remotesize = remotesize + folderSize

        return remotesize

    def getRequiredDownloadFolders(self, title, basePath, onlyget):
        #first lets check if its a multiseason or not
        folders = []

        seasons = utils.get_season_from_title(title)

        baseDirectoryListing = self.getFolderListing(basePath, onlyDir=True)

        if len(seasons) > 1:
            #milti season
            #ok lets troll through
            logger.debug("Multi season download detected.")

            for season in onlyget:
                get_eps = onlyget[season]

                logger.debug("Sorting out what parts to download for season %s" % season)

                seasonFolder = self.getSeasonFolder(season, baseDirectoryListing)

                #TODO make this into a def so we are not repeating code below
                if not seasonFolder:
                    raise Exception('Unable to find season %s folder in path %s' % (season, basePath))

                if 0 in get_eps:
                    logger.debug("Looks like we want to download the entire season %s" % season)
                    folders.append("%s/%s" % (basePath, seasonFolder))
                else:
                    #lets get the invidiual eps
                    epDirectoryListing = self.getFolderListing(basePath + "/" + seasonFolder)

                    for epNo in get_eps:
                        #now find each folder
                        epFolder = self.getEpFolder(season, epNo, epDirectoryListing)

                        if epFolder and epFolder != '':
                            folders.append('%s/%s/%s' % (str(basePath), str(seasonFolder), str(epFolder)))
                        else:
                            error = 'Unable to find ep %s in path %s/%s' % (str(epNo), str(basePath), str(seasonFolder))
                            raise Exception(error)


        else:
            #single season
            logger.debug("Single season detected")

            for season in onlyget:
                get_eps = onlyget[season]

                if 0 in get_eps:
                    logger.debug("Looks like we want to download the entire season %s" % season)
                    folders.append(basePath)
                else:
                    #TODO make this into a def so we are not repeating code below
                    #lets get the invidiual eps
                    epDirectoryListing = self.getFolderListing(basePath)

                    for epNo in get_eps:
                        #now find each folder
                        epFolder = self.getEpFolder(season, epNo, epDirectoryListing)

                        if epFolder and epFolder != '':
                            folders.append('%s/%s' % (str(basePath), str(epFolder)))
                        else:
                            error = 'Unable to find ep %s in path %s' % (str(epNo), str(basePath))
                            raise Exception(error)

        return folders

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


    def getLocalSize(self, local):
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
                return m.group(1)

            m = re.search('(?i)ERROR: Torrent already downloaded here: (.+)', line)
            if m:
                logger.info("Downloaded torrent on the ftp as %s" % m.group(1))
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


    def removeScript(self, jobid):
        path = os.path.join(settings.TMPFOLDER, jobid)
        path2 = os.path.join(settings.TMPFOLDER, jobid + ".log")

        if os.path.exists(path):
            try:
                os.remove(path)
                os.remove(path2)
            except:
                print logger, 'Error removing lftp script at %s' % path
                return False
        else:
            print 'The lftp script for %s was not found when tidying up'
            return False
        return True


    @task(bind=True)
    def mirror(self, local, remote, jobid=0):

        dlitemid = jobid
        local = local.strip()
        print "Starting mirroring of %s to %s" % (remote,local)
        local, remote = os.path.normpath(local), os.path.normpath(remote)
        jobid = 'ftp-%s' % jobid

        m = re.match(".*\.(mkv|avi|mp4)$", remote)

        script = open(os.path.join(settings.TMPFOLDER, jobid), 'w')

        if m:
            #we have a file
            #Build the lftp script for the job
            lines = ('open -u "{0},{1}" ftp://{2}:{3}'.format(settings.FTP_USER, settings.FTP_PASS, settings.FTP_IP, settings.FTP_PORT),
                         'get -c {0} -o {1}'.format("'" + remote + "'", "'" + local + "'"),
                         'exit')
            script.write(os.linesep.join(lines))
            script.close()

        else:

            parallel = ' --parallel={0}'.format(settings.LFTP_THREAD_PER_DOWNLOAD) if settings.LFTP_THREAD_PER_DOWNLOAD else ''
            scp_args = ('-vvv -c ' + parallel)

            #Build the lftp script for the job
            lines = ('open -u "{0},{1}" ftp://{2}:{3}'.format(settings.FTP_USER, settings.FTP_PASS, settings.FTP_IP, settings.FTP_PORT),
                         'set xfer:log-file "/tmp/{0}.log"'.format(jobid),
                         'set xfer:log true',
                         'mirror {0} {1} {2}'.format(scp_args, "'" + remote + "'", "'" + local + "'"),
                         'exit')
            script.write(os.linesep.join(lines))
            script.close()

        # mirror
        cmd = [settings.LFTP_BIN, '-d', '-f', script.name]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print 'starting lftp with script %s' % script.name
        print 'lftp started under PID: {0}'.format(proc.pid)

        try:
            dlitem = DownloadItem.objects.get(id=dlitemid)
            dlitem.pid = proc.pid
            dlitem.save()
        except Exception as e:
            pass

        proc.wait()

        if jobid == 0:
            self.removeScript(0)

    @task(bind=True)
    def mirrorMulti(self, localBase, remoteFolders, jobid=0):

        jobid = 'ftp-%s' % jobid

        scriptCMDs = []

        dlitemid = jobid
        for remoteFolder in remoteFolders:
            splitRemote = remoteFolder.split("/")

            del splitRemote[0]
            del splitRemote[0]
            del splitRemote[0]

            local = localBase

            for dir in splitRemote:
                local = local + "/" + dir

            logger.info("Starting mirroring of %s to %s" % (remoteFolder, local))

            local, remoteFolder = os.path.normpath(local), os.path.normpath(remoteFolder)

            m = re.match(".*\.(mkv|avi|mp4)$", remoteFolder)

            if m:
                #we have a file
                #make sure the folder is created
                #Build the lftp script for the job
                print os.path.realpath(local)
                os.makedirs(localBase)

                cmd = 'get -c "%s" -o "%s"' % (remoteFolder, local.strip())
                scriptCMDs.append(cmd)

            else:
                cmd = 'mirror -vvv -c --parallel=%s "%s" "%s"' % (settings.LFTP_THREAD_PER_DOWNLOAD, remoteFolder, local.strip())
                scriptCMDs.append(cmd)

        tmpFile = "%s/%s" % (settings.TMPFOLDER, jobid)
        script = open(tmpFile, 'w')

        scriptCMDs.append("exit")
        scriptCMDs.append('set xfer:log-file "/tmp/%s.log"' % jobid)
        scriptCMDs.append('set xfer:log true')
        openCmd = 'open -u "%s,%s" ftp://%s:%s\n' % (settings.FTP_USER, settings.FTP_PASS, settings.FTP_IP, settings.FTP_PORT)
        script.write(openCmd)
        script.write(os.linesep.join(scriptCMDs))
        script.close()

        # mirror
        cmd = [settings.LFTP_BIN, '-d', '-f', script.name]
        sync = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        logger.info('starting lftp with script %s' % script.name)
        logger.info('lftp started under PID: {0}'.format(sync.pid))
        #TODO DOES LFTP CRASH IF WE remove the script
        try:
            dlitem = DownloadItem.objects.get(id=dlitemid)
            dlitem.pid = sync.pid
            dlitem.save()
        except Exception as e:
            pass
        sync.wait()

        if jobid == 0:
            self.removeScript(0)

    def stopJob(self, pid):
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            print logger, "error killing the process"


    def jobFinished(self, taskid):
        if taskid == None or taskid == "":
            return True

        result = AsyncResult(taskid)
        print result
        return result.ready()

    def sendcmd(self, cmd):

        #first attempt
        try:
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


