#!/usr/bin/python2.7
import re
import os
import logging
from datetime import datetime, timedelta
import subprocess
import sys
import pprint
import tvdb_api

from lazy.includes.exceptions import LazyError, FTPError
from lazy.includes import manager
from lazy.includes.schemadef import DownloadItem
from lazy.includes.schemadef import Job
from lazy.includes.manager import config
from lazy.includes.exceptions import LazyError
from lazy.includes.ftpmanager import FTPManager
from lazy.includes.manager import Session
from lazy.includes import functions


logger = logging.getLogger('FindMissing')

stderr_log_handler = logging.StreamHandler()
logger.addHandler(stderr_log_handler)

class findmissing:

    __tvFolder = None
    __latestEp = None
    __apiTVDB = None
    __ckShow = None
    __fix = None
    __allSeasons = None
    __type = 1
    __showID = None
    __ckFTP = None
    __showNameReplacements = None
    __seasons = None

    def __checkArgs(self, parser):
        group = parser.add_argument_group("FindMissing")

        group.add_argument('--show', action='store', dest='ckShow', help='List Actions')
        group.add_argument('--showID', action='store', dest='showID', help='List Actions')
        group.add_argument('-s', required=True, action="store", dest='tvFolder', help='tvFolder')
        group.add_argument('-f', action="store_true", dest='fix', help='fix')
        group.add_argument('--ckFTP', action="store_true", dest='ckFTP', help='fix')
        group.add_argument('--allseasons', action="store_true", dest='allseasons', help='fix')
        group.add_argument('--type', action="store", dest='type', help='fix')
        group.add_argument('--seasons', action="store", dest='seasons', help='fix')

        self.__showNameReplacements = {}

        for showName, showID in manager.config.items("TVShowID"):
            self.__showNameReplacements[showName.lower()] = showID

        result = parser.parse_args()
        self.__allSeasons = result.allseasons
        self.__tvFolder = result.tvFolder
        self.__ckShow = result.ckShow
        self.__fix = result.fix
        self.__showID = result.showID
        self.__ckFTP = result.ckFTP
        self.__apiTVDB = tvdb_api.Tvdb()

        if result.seasons is not None:
            self.__seasons = []

            for num in result.seasons.split(','):
                self.__seasons.append(int(num))

        if (result.type.isdigit):
            self.__type = result.type
        else:
            self.__type = 1
        
    def __checkConfig(self):
        pass

    def __init__(self, parentParser):
        global config
        self.__config = config
        
        self.__parser = parentParser
        self.__checkArgs(parentParser)
        self.__checkConfig()

    def getShowID(self, showName):

        if self.__showNameReplacements.get(showName.lower()):
            return self.__showNameReplacements.get(showName.lower())

        logger.debug("looking for tvshow via thetvdb.com: %s" % showName)

        try:
            showObj = self.__apiTVDB[showName]
            return showObj['id']

        except Exception as e:
            functions.raiseError(logger, "Could not find a match for TV Show")
     
    def showEnded(self, showID):
        if showID:
            showObj = self.__apiTVDB[int(showID)]

            status = showObj['status']
            if status == "Ended":
                return 1
            else:
                return 0
        
    def getLatestSeason(self, path):
        latestSeason = 0
        for dir in os.listdir(path):
            tvFolderPath =  os.path.join(path, dir)
                                        
            if os.path.isdir(tvFolderPath):
                m = re.search("(?i)Season([0-9]+)", dir)
                if m:
                    season = int(m.group(1))
                    if season > latestSeason:
                        latestSeason = season
                        
        return latestSeason

    def getLatestTVDBEP(self, showID, showObj, seasonNo):
        now = datetime.now() - timedelta(days=2)

        for ep in reversed(showObj[int(seasonNo)].keys()):
                epObj = showObj[seasonNo][ep]

                airedDate = epObj['firstaired']

                if airedDate is not None:
                    aired_date = datetime.strptime(airedDate, '%Y-%m-%d')

                    if (now > aired_date):
                        #Found the ep and season
                        return ep
                
        return 1
    
        
    def getLatestTVDBSeason(self, showID, showObj):

        now = datetime.now() - timedelta(days=2)

        #loop through each season
        for season in reversed(showObj.keys()):
            #Lets loop through each ep..
            logger.debug("Season %s" % season)

            for ep in reversed(showObj[season].keys()):
                epObj = showObj[season][ep]

                airedDate = epObj['firstaired']

                if airedDate is not None:
                    aired_date = datetime.strptime(airedDate, '%Y-%m-%d')

                    if (now > aired_date):
                        #Found the ep and season
                        return season
        return 1

    def existsFTPSeason(self, ftpPaths, show, season):

        season = int(season)
        
        logger.debug("Checking if season is on the ftp: %s   %s" % (show, season))
        
        for ftpRls in ftpPaths:

            #Check if this is a season pack
            multi = re.search('(?i)S([0-9]+)-S([0-9]+)[\. ]', ftpRls)
            multi2 = re.search('(?i)S([0-9]+)-([0-9]+)[\. ]', ftpRls)

            if not multi or not multi2:
                continue

            ratio = functions.compareTorrent2Show(show, ftpRls)

            if ratio > 0.93:
                ftpSeasonNos = functions.getSeason(ftpRls)

                #multi seasons?
                if ftpSeasonNos:
                    #loop though each of them
                    if season in ftpSeasonNos:
                        return "/REQUESTS/%s" % ftpRls, ftpSeasonNos

        return False, []
                
                
    def existsFTP(self, ftpEps, show, season, ep):
        
        show = show.replace(" ", ".")
        
        logger.debug("Checking if ep is on the ftp: %s   %s x %s" % (show, season, ep))
        
        for ftpEp in ftpEps:

            if ftpEp.lower().startswith(show.lower()):

                ftpSeasonNo, ftpEpNos = functions.getEpSeason(ftpEp)

                if ftpSeasonNo == season:
                    for epNo in ftpEpNos:

                        if epNo == ep:
                            logger.info("FOUND ep on ftp %s" % ftpEp)
                            return "/TVHD/%s" % ftpEp

        
    def existsDB(self, show, season, ep):
        
        session = Session()
        query = session.query(DownloadItem).filter(DownloadItem.status != DownloadItem.DOWNLOAD_COMPLETE)
    
        results = query.all()
    
        for entry in results:
            ratio = functions.compareTorrent2Show(show, entry.title)

            if ratio > 0.93:

                entrySeason, entryEps = functions.getEpSeason(entry.title)

                if entrySeason == season:
                    for epNo in entryEps:
                        if epNo == ep:
                            return True
            
        return False

    def existsDBSeasonCheck(self, season, existingSeasonsDB, showID):
        #lets check if its on the db already
        for torrentName in existingSeasonsDB:
            existingSeasons = existingSeasonsDB[torrentName]['seasons']
            ftpPath = existingSeasonsDB[torrentName]['path']

            for existingSeason in existingSeasons:
                if existingSeason == season:
                    if len(existingSeasons) > 1:
                        logger.debug("Found multi season %s in the queue already on torrent %s.. will make sure this seasnon is downloaded" % (season, torrentName))
                        cmd = [self.__lazyExec, 'addrelease', '--getEps', str(season), '-t', str(showID), '-d', ftpPath]
                        logger.debug("Exec command: " + str(cmd))
                        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    else:
                        logger.debug("Found existing season %s being downloaded in queue already %s" % (season, torrentName))

                    self.write('SEASONINQUEUE: %s' % season)
                    return True
        return False

    def existsDBSeason(self, show):
        #first lets get the series name
        found = {}

        session = Session()
        query = session.query(DownloadItem).filter(DownloadItem.status != DownloadItem.DOWNLOAD_COMPLETE)
    
        results = query.all()
    
        for entry in results:

            similar = functions.compareTorrent2Show(show, entry.title)

            if similar >= 0.93:
                #IS this just a season
                m = re.search('(?i).+\.S[0-9]+\..+|.+\.S[0-9]+-S[0-9]+\..+', entry.title)
                if m:
                    entrySeasons = functions.getSeason(entry.title)

                    foundSeasons = []
                    for entrySeason in entrySeasons:
                        foundSeasons.append(entrySeason)

                    found[entry.title] = {}
                    found[entry.title]['title'] = entry.title
                    found[entry.title]['path'] = entry.path
                    found[entry.title]['seasons'] = foundSeasons

        return found

    def write(self, val):
        self.__reportFile.write("%s\n" % val)
        self.__reportFile.flush()

    def finishJob(self, job, session, status):
        job.status = status
        job.finishDate = datetime.now()
        session.commit()

    def __addToFtpPaths(self, path):
        match = re.search('(?i)/([a-zA-Z]+?)/(.+)', path)

        if match:
            type = match.group(1)
            title = match.group(2)

            if type.lower() == 'requests':
                self.__ftpReqEps.append(title)

            elif type.lower() == 'tvhd':
                self.__ftpEps.append(title)



    def downloadSeason(self, show, season, showID, getEpsList = None):

        if getEpsList is not None:
            getEps = ""
            for ep in getEpsList:
                getEps += str(season) + ":" + str(ep) + ","
            getEps = getEps.rstrip(",")
        else:
            getEps = ''

        #now lets check the ftp for it
        logger.debug("Frist lets check the ftp for season %s" % season)
        ftpPath, gotSeasons = self.existsFTPSeason(self.__ftpReqEps, show, season)

        logger.debug("ftp path is %s" % ftpPath)

        if ftpPath:
            logger.info("MISSING downloading latest SEASON from ftp: %s" % ftpPath)
            self.write("SEASONINQUEUE: %s" % season)

            if len(gotSeasons) == 1:
                #found a single season
                cmd = [self.__lazyExec, 'addrelease', '--getEps', getEps, '-t', showID, '-d', ftpPath.strip()]
            else:
                #found multi season
                if getEps == '':
                    #if we dont have any specific eps to download (ie get whole season) then make sure we only get the 1 season
                    cmd = [self.__lazyExec, 'addrelease', '--getEps', str(season), '-t', showID, '-d', ftpPath.strip()]
                else:
                    #only get the eps we need
                    cmd = [self.__lazyExec, 'addrelease', '--getEps', getEps, '-t', showID, '-d', ftpPath.strip()]
            logger.debug("Exec command: " + str(cmd))
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = proc.communicate()[0]
            logger.debug(output)

            self.__addToFtpPaths(ftpPath.strip())
            return True


        #lets check on on the prescan
        if self.__preScan == None:
            foundOnSCC = self.ftpManager.getTVTorrentsSeason('scc-archive', show, 0)
            foundOnTL = self.ftpManager.getTVTorrentsSeason('tl-packs', show, 0)

            self.__preScan = {'scc': foundOnSCC, 'tl-packs': foundOnTL}

        if self.__preScan is not None:
            for site in self.__preScan:
                logger.debug("looking for season %s in the first primilary scan on site %s" % (season, site))
                torrents = self.__preScan[site]

                #TODO FIND THE BEST MATCH HERE..
                for torrent in torrents:
                    foundSeasons = functions.getSeason(torrent)

                    if season in foundSeasons:
                        logger.debug("looks like we found the season %s in %s" % (season, torrent))

                        seasonPath = self.ftpManager.downloadTVSeasonTorrent(site, torrent)

                        if seasonPath is not False and seasonPath != '':

                            if len(foundSeasons) == 1:
                                #found a single season
                                cmd = [self.__lazyExec, 'addrelease', '--getEps', getEps, '-t', showID, '-r', '-d', seasonPath]
                            else:
                                #found multi season
                                if getEps == '':
                                    #if we dont have any specific eps to download (ie get whole season) then make sure we only get the 1 season
                                    cmd = [self.__lazyExec, 'addrelease', '--getEps', str(season), '-t', showID, '-r', '-d', seasonPath]
                                else:
                                    #only get the eps we need
                                    cmd = [self.__lazyExec, 'addrelease', '--getEps', getEps, '-t', showID, '-r', '-d', seasonPath]

                            logger.debug("addig to the db")
                            self.write("SEASONINQUEUE: %s" % season)
                            logger.debug("Exec command: " + str(cmd))
                            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            output = proc.communicate()[0]
                            logger.debug(output)
                            self.__addToFtpPaths(os.path.basename(seasonPath))
                            return True

        #LEts try find it via torrents
        sites = ['scc-archive', 'revtt', 'tl']

        for site in sites:
            logger.debug("Looking for season pack")

            showTxt = show

            if site == 'scc-archive':
                showTxt = show.replace(" ", ".")

            try:
                torrentSeasons = self.ftpManager.getTVTorrentsSeason(site, showTxt, season)
            except Exception as e:
                logger.info("Error when trying to get torrent listing from site %s... %s" % (site, e.message))
                continue

            if len(torrentSeasons) >= 1:
                #Lets find the best match! we prefer a single season
                bestMatch = ''
                smallestSize = 0

                for torrent in torrentSeasons:
                    seasons = functions.getSeason(torrent)

                    if len(seasons) == 1:
                        bestMatch = torrent
                        break
                    else:
                        if smallestSize > len(seasons):
                            bestMatch = torrent

                if bestMatch == '':
                    bestMatch = torrentSeasons[0]

                try:
                    logger.info("Telling FTP to download from %s in requests %s" % (site, bestMatch))

                    seasonPath = self.ftpManager.downloadTVSeasonTorrent(site, bestMatch)

                    if seasonPath is not False and seasonPath != '':
                        gotSeasons = functions.getSeason(bestMatch)

                        if len(gotSeasons) == 1:
                            #found a single season
                            cmd = [self.__lazyExec, 'addrelease', '--getEps', getEps, '-t', showID, '-r', '-d', seasonPath]
                        else:
                            #found multi season
                            if getEps == '':
                                #if we dont have any specific eps to download (ie get whole season) then make sure we only get the 1 season
                                cmd = [self.__lazyExec, 'addrelease', '--getEps', str(season), '-t', showID, '-r', '-d', seasonPath]
                            else:
                                #only get the eps we need
                                cmd = [self.__lazyExec, 'addrelease', '--getEps', getEps, '-t', showID, '-r', '-d', seasonPath]

                        self.__addToFtpPaths(ftpPath.strip())
                        logger.debug("Exec command: " + str(cmd))
                        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        output = proc.communicate()[0]
                        logger.debug(output)

                        self.write("SEASONINQUEUE: %s" % season)
                        self.__addToFtpPaths(os.path.basename(seasonPath))
                        return True
                    else:
                        return False
                except Exception as e:
                    logger.debug("Error download season pack %s because %s" % (bestMatch, e.message))
                    return False


        return False

    def getMissingSeasons(self, missingEps):

        missingSeasons = []

        missingEpsCheck = missingEps.copy()

        for curSeasonNo in missingEpsCheck:

            curSeason = missingEpsCheck[curSeasonNo]

            if curSeason['exists'] == True and curSeason['percentExists'] < 50:
                missingSeasons.append(curSeasonNo)
                continue

            if curSeason['exists'] == False:
                if self.__allSeasons:
                    missingSeasons.append(curSeasonNo)
                else:
                    logger.debug("Skipping season %s as we are not meant to fix it" % curSeasonNo)
                    del missingEps[curSeasonNo]

        return missingSeasons


    def getMissingEps(self, path, show, showID, showObj, tvdbLatestSeason):

        missing = {}

        for curSeason in range(1, tvdbLatestSeason + 1):

            try:
                #do we want to process this season?
                if self.__seasons:
                    if curSeason not in self.__seasons:
                        continue

                #get latest ep of this season
                tvdbLatestEp = self.getLatestTVDBEP(showID, showObj, curSeason)

                if tvdbLatestEp == 0:
                    tvdbLatestEp = 1

                seasonPath = path + os.path.sep + "Season%s" % curSeason

                missing[curSeason] = {}
                missing[curSeason]['latestEP'] = tvdbLatestEp

                downloadedEps = []

                if not os.path.isdir(seasonPath):
                    missing[curSeason]['exists'] = False
                    missing[curSeason]['percentExists'] = 0

                else:
                    missing[curSeason]['exists'] = True
                    for seasonDir in os.listdir(seasonPath):
                        epFile = os.path.join(seasonPath, seasonDir)

                        m = re.search("(?i).+?- (S[0-9]+E[0-9]+.+) -.+\.(mkv|avi|mp4)$", epFile)

                        if m:
                            multi = re.search("(?i)S[0-9]+(E[0-9]+E.+)", m.group(1))

                            if multi:
                                #we have a multi ep
                                epList = re.split("(?i)E", multi.group(1))

                                for epNum in epList:
                                    if epNum != '':
                                        downloadedEps.append(int(epNum))
                            else:

                                normal = re.search("(?i)S[0-9]+E([0-9]+)", m.group(1))

                                if normal:
                                    #we have a normal ep
                                    epNum = int(normal.group(1))
                                    downloadedEps.append(epNum)

                ##We now have a list of existing ep's.. now lets check what is missing.
                if len(downloadedEps) == 0:
                    downloadedPercent = 0
                else:
                    downloadedPercent = 100 * len(downloadedEps)/tvdbLatestEp

                missing[curSeason]['percentExists'] = downloadedPercent

                logger.debug("%s percent of season %s exists." % (downloadedPercent, curSeason))

                missing[curSeason]['eps'] = {}
                ##Now check we have them
                for epNo in range(1, tvdbLatestEp + 1):
                    if epNo not in downloadedEps:
                        missing[curSeason]['eps'][epNo] = epNo

            except:
                continue


        return missing


    def execute(self):
        session = Session()
        self.__lazyPath = manager.config.get('general', 'lazy_home')
        self.__lazyExec = manager.config.get('general', 'lazy_exec')

        #Create a new job
        newJob = Job()
        newJob.startDate = datetime.now()
        newJob.type = self.__type

        session.add(newJob)
        session.commit()

        #open report and log files for writing.
        basePath = self.__lazyPath + os.sep + "jobs"
        jobFile = os.path.join(basePath, 'job-' + str(newJob.id) + '.job')
        jobLog = os.path.join(basePath, 'job-' + str(newJob.id) + '.log')
        self.__reportFile = open(jobFile, "wb+")

        file_log_handler = logging.FileHandler(jobLog)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_log_handler)
        ch = logging.StreamHandler()

        if self.__fix:
            try:
                self.ftpManager = FTPManager()
            except Exception as e:
                self.write('FATAL: Unable to connect to FTP %s' % e.message)
                functions.raiseError('FATAL: Unable to connect to FTP %s %s' % (str(e.__class__), e.message))

        print "REPORT ID: %s" % newJob.id

        #Check files and folders exist
        if not os.path.exists(self.__tvFolder):
            self.write('FATAL: Source folder does not exist')
            self.finishJob(newJob, session, Job.FINISHED)
            print "REPORT ID: %s" % newJob.id
            self.__reportFile.close()
            functions.raiseError(logger, 'Source folder does not exist')

        shows = []


        # Create a report title
        # just checking 1 show, make sure it exists and set a title for it.
        if self.__ckShow is not None and self.__ckShow != '':
            if self.__seasons:

                seasonTxt = ''

                for season in self.__seasons:
                    seasonTxt += str(season) + ' '

                newJob.title = "Fix attempt for %s on seasons %s" % (self.__ckShow, seasonTxt)
            else:
                newJob.title = "Missing Report for %s" % self.__ckShow

            showPath = self.__tvFolder + os.sep + self.__ckShow
            if os.path.exists(showPath):
                shows = [self.__ckShow]
            else:
                self.write("FATAL: Cannot find show folder %s" % showPath)
                self.finishJob(newJob, session, Job.FINISHED)
                print "REPORT ID: %s" % newJob.id
                self.__reportFile.close()
                functions.raiseError(logger, "FATAL: Cannot find show folder %s" % showPath)

        else:
            #set the report title, not show specific
            if self.__fix:
                newJob.title = "Fix all shows report"
            else:
                newJob.title = "Missing report for ALL Shows"

            shows = os.listdir(self.__tvFolder)

        session.commit()

        #lets get all releases on the ftp, this way we can check if it exists on the ftp already
        if self.__fix:
            try:
                self.__ftpEps = self.ftpManager.getFolderListing("/TVHD")
                self.__ftpReqEps = self.ftpManager.getFolderListing("/REQUESTS")

                if not self.__ftpEps or len(self.__ftpEps) == 0:
                    self.write("FATAL: Unable to get listing from FTP.. exiting")
                    self.finishJob(newJob, session, Job.FINISHED)
                    print "REPORT ID: %s" % newJob.id
                    self.__reportFile.close()
                    functions.raiseError(logger, "FATAL: Unable to get listing from FTP.. exiting")

            except Exception as e:
                self.write("FATAL: eroor getting directory listing on FTP %s %s" % (e.__class__, e.message))
                self.finishJob(newJob, session, Job.FINISHED)
                print "REPORT ID: %s" % newJob.id
                self.__reportFile.close()
                functions.raiseError(logger, e.message)

        self.write('REPORTTYPE: %s' % newJob.type)
        self.write('JOBID: %s' % newJob.id)

        total = len(shows)
        self.write("CKTOTAL: %s" % str(total))

        #Now loop through each show we need to check
        for dir in shows:

            path = os.path.join(self.__tvFolder, dir)
            if os.path.isdir(path):

                try:
                    show = dir.replace("'", "").replace("&", "and").replace("(", "").replace(")" , "").replace(",", "")

                    logger.info("Checking show: %s" % dir)
                    self.write('CHECKSHOW: %s' % dir)

                    if (self.__showID):
                        showID = self.__showID
                    else:
                        showID = self.getShowID(dir)

                    if (showID):
                        showObj = self.__apiTVDB[int(showID)]

                        #Get latest season and ep number
                        tvdbLatestSeason = self.getLatestTVDBSeason(showID, showObj)

                        try:
                            tvdbLatestSeason = int(tvdbLatestSeason)
                        except:
                            logger.error("ERROR getting season info # %s   ID: %s" % (show, showID))
                            self.write('CHECKSHOW: %s' % dir)
                            self.write("SHOWERROR: ERROR getting season info # %s   ID: %s" % (show, showID))
                            continue

                        allExists = False

                        #Now lets figure out all the missing epsiodes/seasons
                        missingEps = self.getMissingEps(path, show, showID, showObj, tvdbLatestSeason)

                        if not self.__fix:
                            #we are not fixing anyting so lets just report the missing stuff
                            for curSeasonNo in missingEps:
                                curSeason = missingEps[curSeasonNo]

                                if curSeason['exists'] == False:
                                    self.write('DOESNOTEXIST: %s' % curSeasonNo)
                                elif curSeason['percentExists'] >= 100:
                                    #all exists
                                    self.write('ALLEXISTS: %s' % curSeasonNo)
                                else:
                                    #loop through each ep
                                    for epNo in curSeason['eps']:
                                        self.write("MISSINGEP: %s:%s" % (curSeasonNo, epNo))
                            continue


                        #Look like we are trying to fix the missing eps..First lets sort out the whole missing seasons
                        missingWholeSeasons = self.getMissingSeasons(missingEps)

                        #fix missing season folders
                        existingSeasonsDB = self.existsDBSeason(show)

                        self.__preScan = None

                        #lets check if the season is already being downloaded.. in that case then add the required seasons
                        for season in missingWholeSeasons:
                            if self.existsDBSeasonCheck(season, existingSeasonsDB, showID):
                                del missingEps[season]

                        #Now we have to find the rest of the missing seasons on torrent sites
                        missingWholeSeasons = self.getMissingSeasons(missingEps)

                        for season in missingWholeSeasons:
                            if self.downloadSeason(show, season, showID):
                                del missingEps[season]


                        # All the seasons are now sorted out.. lets try sort out the inviduial eps.
                        checkMissingEps = missingEps.copy()

                        for curSeasonNo in checkMissingEps:
                            curSeason = checkMissingEps[curSeasonNo]

                            #If it already all exists then ignore
                            if curSeason['percentExists'] >= 100:
                                #all exists
                                logger.debug("The whole season %s exists, skipping" % curSeasonNo)
                                self.write('ALLEXISTS: %s' % curSeasonNo)
                                continue

                            #lets try sort out the inviduial eps.
                            logger.debug("Sorting out individual eps on season %s" % curSeasonNo)

                            alreadyProcessed = []
                            found = []

                            for epNo in curSeason['eps'].copy():

                                if epNo in alreadyProcessed:
                                    logger.info("Skipping ep %s as it was found previously" % epNo)
                                    self.write("FOUNDEP: %s:%s" % (curSeasonNo, epNo))
                                    del missingEps[curSeasonNo]['eps'][epNo]
                                    continue

                                #first check if its on the ftp already
                                if self.existsDB(show, curSeasonNo, epNo):
                                    logger.debug("Already in the download queue skipping! %s  %s x %s" % (show, curSeasonNo, epNo))
                                    self.write("EPEXISTONFTP: %s:%s" % (curSeasonNo, epNo))
                                    del missingEps[curSeasonNo]['eps'][epNo]
                                    continue

                                #second lets check the ftp for it
                                ftpPath = self.existsFTP(self.__ftpEps, show, curSeasonNo, epNo)

                                if ftpPath:
                                    logger.info("Already exists on the ftp.. will download from there %s x %s" % (curSeasonNo, epNo))
                                    epDetail = {'ftpPath': ftpPath, 'ep': int(epNo)}
                                    found.append(epDetail)
                                    del missingEps[curSeasonNo]['eps'][epNo]
                                    continue

                                logger.debug("Not on ftp.. lets try find it")

                                sites = ['scc', 'tl', 'revtt']

                                doContinue = False

                                for site in sites:
                                    try:
                                        showName = show

                                        if site == 'scc':
                                            showName = show.replace(" ", ".")

                                        torrentEps, foundEps = self.ftpManager.getTVTorrents(site, showName, curSeasonNo, epNo)

                                        if foundEps:
                                            for foundEp in foundEps:
                                                alreadyProcessed.append(int(foundEp))

                                        if len(torrentEps) >= 1:
                                            epDetail = {'site': site, 'torrent': torrentEps[0], 'ep': int(epNo)}
                                            found.append(epDetail)
                                            del missingEps[curSeasonNo]['eps'][epNo]
                                            doContinue = True
                                            break
                                    except Exception as e:
                                        epInfo = str(curSeasonNo) + 'x' + str(epNo)
                                        logger.exception("Error searching for ep %s on site site %s because %s" % (epInfo , site, e.message))
                                        self.write("SHOWERROR: problem getting info for ep %s on site site %s because %s" % (epInfo ,site, e.message))
                                        continue

                                if doContinue:
                                    continue
                                else:
                                    logger.info("CANNOT FIND %s  %s x %s  " % (show, curSeasonNo, epNo))

                            checkMissingEps = missingEps.copy()

                            #First lets deal with the ones we didnt find
                            if len(checkMissingEps[curSeasonNo]['eps']) > 0:
                                logger.info("Hmm we didnt find them all.. lets try get season pack instead..")
                                try:
                                    getEps = []

                                    #add the missing eps to the get list
                                    for epNo in checkMissingEps[curSeasonNo]['eps']:
                                        getEps.append(epNo)

                                    #add the already found eps to the get list
                                    for item in found:
                                        getEps.append(item['ep'])

                                    if self.downloadSeason(show, season, showID, getEpsList=getEps):
                                        continue
                                    else:
                                        logger.info("didnt get season pack, lets spit out what we didnt find")
                                        for ep in checkMissingEps[curSeasonNo]['eps']:
                                            self.write("MISSINGEP: %s:%s" % (curSeasonNo, ep))
                                except Exception as e:
                                    logger.info("Problem searching for season season pack, lets download what we have")


                            if found > 0:
                                for item in found:
                                    try:
                                        if 'ftpPath' in item:
                                            cmd = [self.__lazyExec, 'addrelease', '-t', showID, '-d', ftpPath.strip()]
                                            logger.debug("Exec command: " + str(cmd))
                                            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                            logger.info("MISSING downloading latest EP from ftp: %s" % ftpPath)
                                            self.write("FOUNDEP: %s:%s" % (curSeasonNo, item['ep']))
                                        else:
                                            path = self.ftpManager.downloadTVTorrent(item['site'], item['torrent'])
                                            if path and path != '':
                                                logger.debug("Adding ep to db %s" % path)
                                                self.write("FOUNDEP: %s:%s" % (curSeasonNo, item['ep']))
                                                cmd = [self.__lazyExec, 'addrelease', '-t', showID, '-r', '-d', path.strip()]

                                                logger.debug("Exec command: " + str(cmd))
                                                subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                            else:
                                                self.write("FAILEDEP: %s:%s" % (curSeasonNo, item['ep']))
                                    except Exception as e:
                                        self.write("SHOWERROR: failed downloading %s cause: %s" % (item['torrent'], e.message))
                                        logger.debug("SHOWERROR: failed downloading %s cause: %s" % (item['torrent'], e.message))

                    else:
                        #show not found.. log the error
                        logger.error("SHOWERROR Show not found on THETVDB: %s" % show)
                        self.write("SHOWERROR: NOT FOUND on THETVDB.COM")




                except Exception, e:
                    self.write('CHECKSHOW: %s' % dir)
                    self.write("SHOWERROR: %s" % e.message)
                    self.finishJob(newJob, session, Job.ERROR)
                    logging.exception(e)


        #finish off
        self.finishJob(newJob, session, Job.FINISHED)
        print "REPORT ID: %s" % newJob.id
        self.__reportFile.close()