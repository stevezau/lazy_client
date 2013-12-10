'''
Created on 06/04/2012

@author: Steve
'''
import logging
import os
import subprocess
import re
import signal
from ftplib import FTP_TLS

from lazy.includes import manager
from lazy.includes.exceptions import FTPError
from lazy.includes import functions


logger = logging.getLogger('FTPManager')

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class FTPManager():
    __metaclass__ = Singleton

    ftpUser = ''
    ftpPass = ''
    ftpIP = ''
    ftpPort = ''
    ftpSimDownloads = ''
    lftpBin = ''


    def __init__(self):
        self.setup()

        try:
            self.connect()
        except Exception as e:
            #lets try again
            try:
                logger.info("failed connecting to ftp, trying again.")
                self.connect()
            except Exception as e:
                raise e


    def connect(self):
        self.ftps = FTP_TLS()
        self.ftps.set_debuglevel(0)
        self.ftps.connect(self.ftpIP, self.ftpPort, timeout=60)
        self.ftps.login(self.ftpUser, self.ftpPass)


    def setup(self):

        # Check FTP address is an IP
        logger.info('running check config')

        configSection = 'ftp'
        import socket
        try:
            self.ftpIP = manager.config.get(configSection, 'ftp_ip')
            socket.inet_aton(self.ftpIP)
        except socket.error:
            functions.raiseError(logger, 'ftp_ip is not a valid IP address %s' % self.ftpIP)

        # Check the port is an integer between 0 and 65536
        try:
            self.ftpPort = int(manager.config.get(configSection, 'ftp_port'))
            if 0 > self.ftpPort or self.ftpPort > 65536:
                functions.raiseError(logger, 'ftp_port should be between 0 and 65536 (not %s)' % self.ftpPort)
        except TypeError:
            functions.raiseError(logger, 'ftp_port is not a valid port number %s' % self.ftpPort)

        # If the username isn't set, then make it anonymous
        self.ftpUser = manager.config.get(configSection, 'ftp_user')
        if not self.ftpUser:
            self.ftpUser = 'anonymous'

        # If the username isn't anonymous, make sure there's a password
        self.ftpPass = manager.config.get(configSection, 'ftp_pass')
        if self.ftpUser.lower() != 'anonymous' and not self.ftpPass:
            functions.raiseError(logger, 'ftp1: ftp_pass must be set if the user is not anonymous')

        # Check the temp folder is writable. We need somewhere to put the lftp instruction file
        self.tmpFolder = manager.config.get('general', 'tempfolder')

        if not self.tmpFolder:
            self.tmpFolder = '/tmp'
        try:
            if not os.access(self.tmpFolder, os.W_OK):
                functions.raiseError(logger, 'Temporary folder not writable %s' % self.tmpFolder)
        except Exception as e:
            functions.raiseError(logger, 'Error with the temporary folder under General - tempfolder in the config.. ' + e.message)

        self.lftpBin = manager.config.get('general', 'lftp')

        self.ftpSimDownloads = manager.config.get('ftp', 'max_sim')


    def getFolderListing(self, folder, onlyDir = False):
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
                isDir = fileValues[0]

                if isDir == 'type=dir':
                    eps.append((fileValues[-1].strip()))
            else:
                eps.append((fileValues[-1].strip()))

        # If we get here, then the output has finished and we received no match
        return eps

    def getEpFolder(self, season, ep, directoryListing):

        for folder in directoryListing:
            fileName, fileExtension = os.path.splitext(folder)

            if fileExtension == 'nfo':
                continue

            epSeason, epsList = functions.getEpSeason(folder)

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
            folderSeasons = functions.getSeason(seasonFolder)

            if int(season) in folderSeasons:
                logger.debug("we found the folder %s" % seasonFolder)
                return seasonFolder

        return False

    def getRequiredDownloadFolders(self, title, basePath, getEps):
        #first lets check if its a multiseason or not
        folders = []

        seasons = functions.getSeason(title)

        baseDirectoryListing = self.getFolderListing(basePath, onlyDir=True)


        if seasons > 1:
            #milti season
            #ok lets troll through
            logger.debug("Multi season download detected.")

            for season in getEps:
                seasonObj = getEps[season]

                logger.debug("Sorting out what parts to download for season %s" % season)

                seasonFolder = self.getSeasonFolder(season, baseDirectoryListing)

                if not seasonFolder:
                    raise Exception('Unable to find season %s folder in path %s' % (season, basePath))

                if 'getAll' in seasonObj and seasonObj['getAll'] == True:
                    logger.debug("Looks like we want to download the entire season %s" % season)
                    folders.append("%s/%s" % (basePath, seasonFolder))
                else:
                    #lets get the invidiual eps

                    epDirectoryListing = self.getFolderListing(basePath + "/" + seasonFolder)

                    for epNo in seasonObj['eps']:
                        #now find each folder
                        epFolder = self.getEpFolder(season, epNo, epDirectoryListing)

                        if epFolder and epFolder != '':
                            folders.append('%s/%s/%s' % (str(basePath), str(seasonFolder), str(epFolder)))
                        else:
                            error = 'Unable to find ep %s in path %s/%s' % (str(epNo), str(basePath), str(seasonFolder))
                            raise Exception()


        else:
            #single season
            logger.debug("Single season detected")

            for season in getEps:
                seasonObj = getEps[season]

                if 'getAll' in seasonObj and seasonObj['getAll'] == True:
                    #get everything..
                    folders.append(basePath)



        return folders

    def getRemoteSizeMulti(self, folders):
        remotesize = False
        #lets gets get the size in total
        for folder in folders:
            folderSize = self.getRemoteSize(folder)

            remotesize = remotesize + folderSize

        return remotesize

    def getRemoteSize(self, remote):
        ftpCMD = 'cd %s' % remote

        size = self.ftps.size(remote)

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


    def removeScript(self, jobid):
        path = '{0}/{1}'.format(self.tmpFolder, jobid)
        path2 = '{0}/{1}'.format(self.tmpFolder, jobid + ".log")

        if os.path.exists(path):
            try:
                os.remove(path)
                os.remove(path2)
            except:
                logger.info(logger, 'Error removing lftp script at %s' % path)
                return False
        else:
            logger.info('The lftp script for %s was not found when tidying up')
            return False
        return True

    def mirrorMulti(self, localBase, remoteFolders, jobid = 0):

        jobid = 'ftp-%s' % jobid

        scriptCMDs = []

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
                #Build the lftp script for the job
                cmd = 'get -c "%s" -o "%s"' % (remoteFolder, local.strip())
                scriptCMDs.append(cmd)

            else:
                cmd = 'mirror -vvv -c --parallel=%s "%s" "%s"' % (self.ftpSimDownloads, remoteFolder, local.strip())
                scriptCMDs.append(cmd)

        tmpFile = "%s/%s" % (self.tmpFolder, jobid)

        with open(tmpFile, 'w') as script:
            scriptCMDs.append("exit")
            scriptCMDs.append('set xfer:log-file "/tmp/%s.log"' % jobid)
            scriptCMDs.append('set xfer:log true')
            openCmd = 'open -u "%s,%s" ftp://%s:%s\n' % (self.ftpUser, self.ftpPass, self.ftpIP, self.ftpPort)
            script.write(openCmd)
            script.write(os.linesep.join(scriptCMDs))

            log = "--log=/tmp/" + jobid + "-c.log"
            # mirror
            cmd = [self.lftpBin, '-d', '-f', script.name, log]
            logger.info('starting lftp with script %s' % script.name)
            sync = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info('lftp started under PID: {0}'.format(sync.pid))
            #TODO DOES LFTP CRASH IF WE remove the script
            return sync.pid

        if jobid == 0:
            self.removeScript(0)


    def mirror(self, local, remote, jobid = 0):
        local = local.strip()
        logger.info("Starting mirroring of %s to %s" % (remote,local))
        local, remote = os.path.normpath(local), os.path.normpath(remote)
        jobid = 'ftp-%s' % jobid

        m = re.match(".*\.(mkv|avi|mp4)$", remote)

        if m:
            #we have a file
            #Build the lftp script for the job
            with open('{0}/{1}'.format(self.tmpFolder, jobid), 'w') as script:
                lines = ('open -u "{0},{1}" ftp://{2}:{3}'.format(self.ftpUser, self.ftpPass, self.ftpIP, self.ftpPort),
                         'get -c {0} -o {1}'.format("'" + remote + "'", "'" + local + "'"),
                         'exit')
                script.write(os.linesep.join(lines))

                # mirror
                cmd = [self.lftpBin, '-d', '-f', script.name]
                logger.info('starting lftp with script %s' % script.name)
                sync = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info('lftp started under PID: {0}'.format(sync.pid))
                #TODO DOES LFTP CRASH IF WE remove the script
                #removeScript(jobid)
                return sync.pid
        else:

            parallel = ' --parallel={0}'.format(self.ftpSimDownloads) if self.ftpSimDownloads else ''
            scp_args = ('-vvv -c ' + parallel)

            #Build the lftp script for the job
            with open('{0}/{1}'.format(self.tmpFolder, jobid), 'w') as script:
                lines = ('open -u "{0},{1}" ftp://{2}:{3}'.format(self.ftpUser, self.ftpPass, self.ftpIP, self.ftpPort),
                         'set xfer:log-file "/tmp/{0}.log"'.format(jobid),
                         'set xfer:log true',
                         'mirror {0} {1} {2}'.format(scp_args, "'" + remote + "'", "'" + local + "'"),
                         'exit')
                script.write(os.linesep.join(lines))

                # mirror
                log = "--log=/tmp/" + jobid + "-c.log"
                cmd = [self.lftpBin, '-d', '-f', script.name, log]
                logger.info('starting lftp with script %s' % script.name)
                sync = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info('lftp started under PID: {0}'.format(sync.pid))
                #TODO DOES LFTP CRASH IF WE remove the script
                return sync.pid

        if jobid == 0:
            removeScript(0)

    def stopJob(self, pid):
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            logger.info(logger, "error killing the process")



    def jobFinished(self, pid):
        if os.path.exists('/proc/{0}'.format(pid)):
            return False
        else:
            return True

    def sendcmd(self, cmd):

        #first attempt
        try:
            return self.ftps.sendcmd(cmd)
        except Exception as e:
            ## it failed.. lets try again
            self.connect()

        return self.ftps.sendcmd(cmd)


    def getTVTorrents(self, site, show, season, ep):

        show = show.replace("!", "")

        logger.info("Searching %s torrents for   %s S%s E%s" % (site, show, str(season).zfill(2), str(ep).zfill(2)))

        cmdremote = "%s S%s E%s" % (show, str(season).zfill(2), str(ep).zfill(2))
        cmd = "site torrent search %s %s" % (site, cmdremote)

        out = self.sendcmd(cmd)

        logger.debug(out)

        torrents = []

        for line in iter(out.splitlines()):
            line = line.lower()

            #do fuzzy match
            match = re.search("(?i)200- (.+s([0-9][0-9])e([0-9][0-9]).+)\ [0-9]", line.strip())

            if match:
                #found a torrent..
                torrent = match.group(1).strip()

                ratio = functions.compareTorrent2Show(show, torrent)

                if ratio >= 0.93:
                    logger.info("Potential found match %s" % match.group(1))

                    torSeason, torEps = functions.getEpSeason(match.group(1))

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

        return torrents, []



    def getTVTorrentsSeason(self, site, show, season = 0):

        season = int(season)

        show = show.replace("!", "")

        logger.info("Searching %s torrents for   %s S%s" % (site, show, str(season).zfill(2)))

        if season == 0:
            cmdremote = show
        else:
            cmdremote = "%s S%s" % (show, str(season).zfill(2))
        cmd = "site torrent search %s %s" % (site, cmdremote)

        out = self.sendcmd(cmd)

        logger.debug(out)

        torrents = []

        for line in iter(out.splitlines()):

            #do fuzzy match
            match = re.search("200- ((.+)S([0-9][0-9])[-0-9\ .].+)\ [0-9]", line.strip())

            if match:
                #found a torrent..
                torrent = match.group(1).strip()

                ratio = functions.compareTorrent2Show(show, torrent)

                if ratio >= 0.93:
                    logger.info("Found potential match for this show")
                    #its for this show..

                    try:

                        if season == 0:
                            logger.info("Found match %s" % torrent)
                            #we want to return it all!!
                            torrents.append(torrent)
                        else:
                            torSeasons = functions.getSeason(line.strip())

                            if season in torSeasons:
                                logger.info("Found match %s" % torrent)
                                torrents.append(torrent)

                    except:
                        logger.error("Error converting season and ep to int %s" % line)
                        continue

        return torrents

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


