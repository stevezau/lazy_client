#!/usr/bin/python
import re
import logging
import os
import shutil
import unicodedata
import sys
import zlib
import glob

from flexget.utils.titles import SeriesParser, MovieParser
from flexget.utils.titles.parser import ParseWarning

from lazy.includes.exceptions import LazyError
from lazy.includes.docoParser import DocoParser
import manager
import difflib
from flexget.plugins.metainfo.series import MetainfoSeries

logger = logging.getLogger('Fucntions')

def extract_id(url):
    """Return IMDb ID of the given URL. Return None if not valid or if URL is not a string."""
    if not isinstance(url, basestring):
        return
    m = re.search(r'((?:nm|tt)[\d]{7})', url)
    if m:
        return m.group(1)


def compareTorrent2Show(show, torrent):

    torrent = torrent.replace(' ', '.')
    #are we dealing with a season pack here
    pack = re.search('(?i).+\.S[0-9]+\..+|.+\.S[0-9]+-S[0-9]+\..+|.+\.S[0-9]+-[0-9]+\..+', torrent)

    if pack:
        #we have a season pack , lets fake the ep id so we can get a title return
        torrent = re.sub('(?i)\.S[0-9]+\.|\.S[0-9]+-[0-9]+\.|\.S[0-9]+-S[0-9]+\.', '.S01E01.', torrent)

    parser = getSeriesInfo(torrent)

    if parser:
        torSeriesName = parser.name

        #now compare them
        return howSimilar(torSeriesName.lower(), show.lower())
    else:
        return 0

def howSimilar(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def checkRunning(action):

    lazyPath = manager.config.get('general', 'lazy_home')

    actionFile = "%s.run" % action
    pidfile = os.path.join(lazyPath, actionFile)
    
    #Check if pid file exists
    if os.path.exists(pidfile):
        #Is it actually still running tho
        logger.info("Found existing pid file, checking if the program is actually running")
        pid = open(pidfile, 'r').read()
        procPid = "/proc/%s" % pid
        
        if os.path.exists(procPid):
            #Its running so exit
            logger.error("Already running on pid %s , Exiting" % pid)
            sys.exit(1)
        else:
            logger.info("Program was not running, resetting pid file")
    
    myfile = open(pidfile, "w+")
    myfile.write(str(os.getpid()))
    myfile.close


def getEpSeason(title):
    eps = []
    season = 00

    multi = re.search("(?i)S([0-9]+)(E[0-9]+[E0-9]+).+", title, re.IGNORECASE)

    if multi:
        #multi eps found
        epList = re.split("(?i)E", multi.group(2))
        season = multi.group(1)

        for epNum in epList:
            if epNum != '':
                eps.append(int(epNum))

        return season, eps

    normal = re.search("(?i)S([0-9]+)E([0-9]+)", title, re.IGNORECASE)

    if normal:
            try:
                eps.append(int(normal.group(2)))
                season = int(normal.group(1))

                return season, eps
            except:
                eps = [00]
                season = 00
    else:
        eps = [00]
        season = 00

    return season, eps

def getSeason(title):

    multi = re.search('(?i)S([0-9]+)-S([0-9]+)[\. ]', title)
    multi2 = re.search('(?i)S([0-9]+)-([0-9]+)[\. ]', title)


    if multi:
        #found a multi match
        startSeason = int(multi.group(1))
        endSeason = int(multi.group(2))

        seasons = []
        for seasonNo in range(startSeason, endSeason + 1):
            seasons.append(int(seasonNo))

        return seasons
    elif multi2:
        #found a multi match
        startSeason = int(multi2.group(1))
        endSeason = int(multi2.group(2))

        seasons = []
        for seasonNo in range(startSeason, endSeason + 1):
            seasons.append(int(seasonNo))

        return seasons
    else:
        match = re.search('(?i)S([0-9][0-9])', title)

        seasons = []
        if match:
            seasons.append(int(match.group(1)))

            return seasons

    return False

def removePidFile(action):

    lazyPath = manager.config.get('general', 'lazy_home')

    actionFile = "%s.run" % action
    pidfile = os.path.join(lazyPath, actionFile)

    if os.path.exists(pidfile):
        os.remove(pidfile)

def validSection(section):
    
    path = manager.config.get('sections', section)
    
    if path:
        return True
    else:
        return False

def delete(file):
    if os.path.isdir(file):
        shutil.rmtree(file)
    else:
        os.remove(file)


def getRegex(string, regex, group):
    search = re.search(regex, string, re.IGNORECASE)
 
    if search:
        return search.group(1)
    
def error_handler(reason):
    logger.error(reason)
    raise LazyError(reason)

def raiseError(logObj, reason, id = 0):
    logObj.exception(reason)
    raise LazyError(reason, id)

def removeIllegalChars(name):
    name = re.sub('[():\"*?<>|]+', "", name)
    return name

def create_path(path):

    paths_to_create = []
    
    while not os.path.lexists(path):

        paths_to_create.insert(0, path)
        head,tail = os.path.split(path)
        if len(tail.strip())==0: # Just incase path ends with a / or \
            path = head
            head,tail = os.path.split(path)
        
        path = head

    for path in paths_to_create:
        os.mkdir(path)


def remove_accents(str):
    nkfd_form = unicodedata.normalize('NFKD', unicode(str))
    only_ascii = nkfd_form.encode('ASCII', 'ignore')
    return only_ascii
        
def moveFile(src, dst, checkExisting = False):
    dst = removeIllegalChars(re.sub('[\"*?<>|]+', " ", dst))
    create_path(os.path.abspath(os.path.join(dst, '..')))

    doMove = True

    if checkExisting:
        fileName, fileExtension = os.path.splitext(dst)
        if os.path.isfile(fileName + ".mp4"):
            os.remove(fileName + ".mp4")
        if os.path.isfile(fileName + ".mkv"):
            #skip this as we dont want to replace SD with HD
            if 'proper' in src.lower():
                doMove = True
            else:
                doMove = False

        if os.path.isfile(fileName + ".avi"):
            os.remove(fileName + ".avi")
    if doMove:
        shutil.move(src, dst)
        logger.info('Moving file: ' + os.path.basename(src) + ' to: ' + dst)
    else:
        logger.info('NOT MOVING FILE AS BETTER QUALITY EXISTS file: ' + os.path.basename(src) + ' to: ' + dst)


def getSeriesInfo(title):
    seriesInfo = MetainfoSeries()
    parser = seriesInfo.guess_series(title, allow_seasonless=True)

    return parser

def getMovieInfo(title):
        parser = MovieParser()
        parser.data = title
        parser.parse()
        
        name = parser.name
        year = parser.year
        if name == '':
            logger.critical('Failed to parse name from %s' % title)
            return None
        logger.debug('smart_match name=%s year=%s' % (name, str(year)))
        return name, year
    
def getDocoInfo(title):
        parser = DocoParser()
        parser.data = title
        parser.parse()
        name = parser.name
        year = parser.year
        if name == '':
            logger.critical('Failed to parse name from %s' % title)
            return None
        logger.debug('smart_match name=%s year=%s' % (name, str(year)))
        return name, year

def moveFiles(srcFiles, checkExisting = False):
    
    if not srcFiles:
        error_handler('No files to move', 1)
        
    for file in srcFiles:
        moveFile(file['src'], file['dst'], checkExisting)

def getCDNumber(fileName):
     
    byCD = getRegex(os.path.basename(os.path.dirname(fileName)), "^CD([0-9]+)$", 1)
    byNum = getRegex(os.path.basename(fileName), "(?i)CD([0-9])", 1)
    byLetter =  getRegex(os.path.basename(fileName), "-([A-Za-z])\.(avi|iso|mkv)$", 1)
    
    if byCD:
        return byCD
    elif byNum:
        return byNum
    elif byLetter:
        return [ord(char) - 96 for char in byLetter.lower()][0]
    else:
        return

def setupDstFiles(srcFiles, dstFolder, title):
    # Setup file dest
    if srcFiles.__len__() > 1:
        for file in srcFiles: 
            
            cd = getCDNumber(file['src'])
            
            if cd:
                __, ext = os.path.splitext(file['src'])
                file['dst'] = os.path.abspath(dstFolder + "/" + title + " CD" + str(cd) + ext)
            else:
                error_handler('Multiple files but could not locate CD numbering')
    elif srcFiles.__len__() == 1:
        __, ext = os.path.splitext(srcFiles[0]['src'])
        srcFiles[0]['dst'] = os.path.abspath(dstFolder + "/" + title + ext)
    else:
        error_handler('No files to move')  
        
    return srcFiles

def getVidFiles(srcFolder):
    
    srcFiles = []
    
    for root, __, files in os.walk(srcFolder):
        for file in files:
            name, ext = os.path.splitext(file)
            if re.match('(?i)\.(mkv|iso|avi|m4v|mpg|mp4)', ext):
                #check if it's a sample.
                if re.match('(?i).*-sample', name):
                    continue
                if re.match('(?i).*_sample', name):
                    continue
                if re.match('(?i).*(sample)', name):
                    continue
                if re.match('(?i).*sample', name):
                    continue
                if re.match('(?i)sample', name):
                    continue
                
                path = os.path.join(root,file)
                folder = os.path.basename(os.path.dirname(path))
                
                logger.debug('path: ' + path)
                logger.debug('folder: ' + folder)
                
                if re.match('(?i)sample', folder):
                    continue

                file = {'src': path, 'dst': None}
                srcFiles.append(file)
                
    return srcFiles

def unrar(path):
    from easy_extract.archive_finder import ArchiveFinder
    from lazy.includes.rar import RarArchive
    
    logger.info("Unraring folder %s" % path)
    archive_finder = ArchiveFinder(path, recursive=True, archive_classes=[RarArchive,])
    errCode = 0
    
    for archive in archive_finder.archives:
        errCode = archive.extract()

    logger.debug("Extract return code was %s" % str(errCode))
    return errCode

def checkSFVPath(path):
    logger.debug("Checking SFV in path %s" % path)

    os.chdir(path)

    foundSFV = False

    for sfvFile in glob.glob("*.sfv"):
        foundSFV = True
        #DO SFV CHECK
        s = open(sfvFile)

        if os.path.getsize(sfvFile) == 0:
            logger.debug('empty sfv file')
            return False

        names_list = []
        sfv_list = []

        ##loop thru all lines of sfv, removes all unnecessary /r /n chars, split each line to two values,creates two distinct arrays
        for line in s.readlines():
            if line.startswith(';'):
                continue
            m=line.rstrip('\r\n')
            m=m.split(' ')
            names_list.append(m[0])
            sfv_list.append(m[1])

        i = 0
        no_errors = True

        while(len(names_list)>i):
            print "Checking " + names_list[i]
            calc_sfv_value=crc(names_list[i])


            if sfv_list[i].lstrip('0')==calc_sfv_value:
                pass
            else:
                logger.info("there was a problem with file deleting it " + names_list[i])
                no_errors=False
                try:
                    os.remove(names_list[i])
                except:
                    pass

            i=i+1

        if (no_errors):
		    return True
        else:
            return False

    if not foundSFV:
        logger.debug("No SFV FOUND!")
        return False


def crc(fileName):
    prev=0

    ##for the script to work on any sfv file no matter where it's located , we have to parse the absolute path of each file within sfv
    ##so, we will add the file path to each file name , pretty neat huh ?
    fileName=os.path.join(fileName)

    #print fileName
    if os.path.exists(fileName):
        store=open(fileName, "rb")
        for eachLine in store:
            prev = zlib.crc32(eachLine, prev)
        return "%x"%(prev & 0xFFFFFFFF)
        store.close()