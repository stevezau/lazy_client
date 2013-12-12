'''
Created on 12/04/2012

@author: Steve
'''
import re
import subprocess
import shutil
import os
import logging
from lazy.includes.manager import Session, config
from urllib2 import HTTPError
import time
import datetime

import tvdb_api

from lazy.includes import manager
from lazy.includes.schemadef import DownloadItem
from lazy.includes.ftpmanager import FTPManager
from lazy.includes.exceptions import LazyError
from lazy.includes import functions


logger = logging.getLogger('MoveTV')

apiTVDB = tvdb_api.Tvdb()

showNameReplacements = {}

for showName, showID in manager.config.items("TVShowID"):
    showNameReplacements[showName.lower()] = showID


def moveDoco(dlItem, seriesName, srcFiles, dstFolder):

    docoFolder = functions.getRegex(seriesName, '(?i)(National Geographic|Discovery Channel|History Channel)', 1)

    if not docoFolder:
        functions.raiseError(logger, 'Unable to figure out the type of doco')            
        
    dstFolder = functions.removeIllegalChars(os.path.abspath(dstFolder + os.sep + docoFolder + ' Docos'))
    functions.create_path(dstFolder)
    seriesName = re.sub("(?i)National Geographic|Discovery Channel|History Channel", "", seriesName).strip()

    logger.debug('Found ' + docoFolder + ' Doco: ' + seriesName)

    airdate = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(srcFiles[0]['src'])))
    
    srcFiles = functions.setupDstFiles(srcFiles, dstFolder, seriesName + ' S00E01')
                            
    nfoFile = os.path.abspath(dstFolder + os.sep + seriesName + " S00E01.nfo")

    nfoContent = "<episodedetails> \n\
    <title>" + seriesName  + "</title> \n\
    <season>0</season> \n\
    <episode>1</episode> \n\
    <aired>%s</aired> \n\
    <displayseason>0</displayseason>  <!-- For TV show specials, determines how the episode is sorted in the series  --> \n\
    <displayepisode>4096</displayepisode> \n\
    </episodedetails>" % airdate

    nfof = open(nfoFile, 'w')
    nfof.write(nfoContent)
    nfof.close()
    logger.debug('Wrote NFO file ' + nfoFile)

    functions.moveFiles(srcFiles, True)
    
    if os.path.exists(dlItem.localpath):
        logger.debug('Deleting  ' + dlItem.localpath)
        functions.delete(dlItem.localpath)

def moveEsp(dlItem, dstFolder, srcFiles, seriesName, seriesSeason, seriesEP, seriesID, epOverride = 0):


    showObj = apiTVDB[int(seriesID)]
    seriesName = functions.removeIllegalChars(showObj['seriesname'].replace(".", " ").strip())

    if epOverride > 0:
        seriesSeason = 0
        seriesEP = int(epOverride)

    epName = showObj[int(seriesSeason)][int(seriesEP)]['episodename']

    if epName is not None and epName != '':
        epTitle = epName
        #epTitle = unicodedata.normalize('NFKD', unicode(epName, errors='ignore')).encode('ascii','ignore')
    else:
        logger.debug('Could not find tvshow (TVDB) ' + seriesSeason + 'x' + seriesEP)
        return False

    # Now lets move the file
    epTitle = functions.removeIllegalChars(epTitle)

    logger.debug('Found episode ' + str(seriesEP) + " title: " + epTitle)

    #IS this a multiep
    multi = re.search("(?i)S([0-9]+)(E[0-9]+[E0-9]+).+", dlItem.title)

    epTxt = 'E' + str(seriesEP)

    if multi:
        #we have a multi
        epList = re.split("(?i)E", multi.group(2))

        epTxt = ''

        for epNum in epList:
            if epNum != '':
                epTxt += "E" + epNum

    seasonFolder = "Season" + str(seriesSeason).lstrip("0")

    dstFolderBase = functions.removeIllegalChars(os.path.abspath(dstFolder + os.sep + seriesName.strip()))
    dstFolder = functions.removeIllegalChars(os.path.abspath(dstFolderBase + os.sep + seasonFolder))

    functions.create_path(dstFolder)
    srcFiles = functions.setupDstFiles(srcFiles, dstFolder, seriesName + ' - ' + 'S' + str(seriesSeason) + epTxt + ' - ' + epTitle)

    functions.moveFiles(srcFiles, True)

    if os.path.exists(dlItem.localpath):
        logger.debug('Deleting  ' + dlItem.localpath)
        functions.delete(dlItem.localpath)

    return True


def doMoveTV(dstFolder, srcFiles, dlItem, seriesName, seriesSeason, seriesEP, proper, seriesID):

    #THETVDB
    logger.debug("Checking via TVDB")
    try:
        if seriesID:
            if dlItem.epOverride > 0:
               if not moveEsp(dlItem, dstFolder, srcFiles, seriesName, seriesSeason, seriesEP, seriesID, dlItem.epOverride):
                functions.raiseError(logger, "Failed moving show for some unknown reason")
            else:
                if not moveEsp(dlItem, dstFolder, srcFiles, seriesName, seriesSeason, seriesEP, seriesID):
                    functions.raiseError(logger, "Failed moving show for some unknown reason")
        else:
                showObj = apiTVDB[seriesName]

                if not moveEsp(dlItem, dstFolder, srcFiles, seriesName, seriesSeason, seriesEP, showObj['id'], dlItem.epOverride):
                    functions.raiseError(logger, "Failed moving show for some unknown reason")
    except Exception as e:
        functions.raiseError(logger, "Could not find show: " + seriesName + " via thetvdb.com " + e.message)



def moveTV(dlItem, dstFolder):

    logger.debug("running on %s" % dlItem.localpath)

    name = os.path.basename(dlItem.localpath)
    if os.path.isdir(dlItem.localpath):
        if name.lower() == "sample":
            logger.info("skipping sample folder")
            return
        if name.lower() == "extras":
            logger.info("skipping sample folder")
            return
        if 'subpack' in name.lower():
            logger.info("skipping sample folder")
            return

        if '.special.' in name.lower():
            if not dlItem.epOverride > 0:

              logger.info("We can't handle specials.. do it manually")
              functions.raiseError(logger, "Appears this is a special, Click above to sort it out")
              return


    if os.path.isdir(dlItem.localpath):

        if re.match('.*\.S[0-9][0-9]-[0-9][0-9]\..*', dlItem.title) or re.match('.*\.S[0-9][0-9]-S[0-9][0-9]\..*', dlItem.title):
            logger.info("Multi Season pack detected")

            #Lets build up the first folder
            files = os.walk(dlItem.localpath).next()[1]

            if not files or len(files) == 0:
                functions.raiseError(logger, 'No folders or files in path ' + dlItem.localpath)

            for file in files:
                filePath = os.path.join(dlItem.localpath + os.sep + file)

                if os.path.isdir(filePath):

                    #Offload rest of processing to the action object
                    try:
                        newDLItem = DownloadItem()

                        newDLItem.title = file
                        newDLItem.localpath = filePath
                        newDLItem.section = dlItem.section
                        newDLItem.path = dlItem.path.strip() + os.sep + os.path.basename(filePath)

                        moveTV(newDLItem, dstFolder)
                    except LazyError as e:
                        functions.raiseError(logger, 'some error ' + e.message)


            if os.path.exists(dlItem.localpath):
                logger.debug('Deleting  ' + dlItem.localpath)
                functions.delete(dlItem.localpath)
                return

        elif re.match('(?i).*\.S[0-9][0-9]\..*', dlItem.title) and '.special.' not in dlItem.title.lower():
            logger.info("Season pack detected")

            #Lets build up the first folder
            files = os.listdir(dlItem.localpath)

            if not files or len(files) == 0:
                functions.raiseError(logger, 'No folders or files in path ' + dlItem.localpath)

            for file in files:
                filePath = os.path.join(dlItem.localpath + os.sep + file)

                if os.path.isdir(filePath):

                    #Offload rest of processing to the action object
                    try:
                        newDLItem = DownloadItem()

                        newDLItem.title = file
                        newDLItem.localpath = filePath
                        newDLItem.path = dlItem.path.strip() + os.sep + os.path.basename(filePath)
                        newDLItem.section = dlItem.section
                        newDLItem.tvdbid = dlItem.tvdbid

                        moveTV(newDLItem, dstFolder)
                    except LazyError as e:
                        functions.raiseError(logger, 'some error ' + e.message)
                else:
                    #If its small its prob an nfo so ignore
                    size = os.path.getsize(filePath)
                    if size < 15120:
                        continue
                    else:
                        newDLItem = DownloadItem()
                        title = os.path.basename(filePath)

                        newDLItem.title = title
                        newDLItem.localpath = filePath
                        newDLItem.section = dlItem.section
                        newDLItem.tvdbid = dlItem.tvdbid

                        moveTV(newDLItem, dstFolder)

            if os.path.exists(dlItem.localpath):
                logger.debug('Deleting  ' + dlItem.localpath)
                functions.delete(dlItem.localpath)
                return

        else:
            code = functions.unrar(dlItem.localpath)

            #Is this part of a season pack?
            parentDir = os.path.basename(os.path.dirname(dlItem.localpath))

            if code == 0:
                srcFiles = functions.getVidFiles(dlItem.localpath)
            else:
                logger.info('failed extract, error %s' % code)
                #failed.. lets do sfv check
                logger.info('failed extract, lets check the sfv')
                sfvck = functions.checkSFVPath(dlItem.localpath)

                logger.info("SFV CHECK " + str(sfvck))

                if sfvck:
                    #SFV passed, lets get vid files.. maybe it was extracted previously
                    srcFiles = functions.getVidFiles(dlItem.localpath)
                else:
                    if re.match('(?i).*\.S[0-9]+[\. ].*|.*\.S[0-9]+-[0-9]+[\. ].*|.*\.S[0-9]+-S[0-9]+[\. ].*', parentDir):
                        logger.debug("SFV check had errors, we cant set this to pending or it will download the whole thing again, it has been added as a seperate download")

                        lazyExec = manager.config.get('general', 'lazy_exec')

                        mvPath = False

                        for section in manager.config.items("sections"):
                            sectionPath = manager.config.get('sections', section[0])

                            if sectionPath in dlItem.localpath:
                                mvPath = sectionPath

                        if mvPath:
                            shutil.move(dlItem.localpath, mvPath)

                            if dlItem.tvdbid:
                                cmd = [lazyExec, 'addrelease', '-d', dlItem.path, '-t', dlItem.tvdbid]
                            else:
                                cmd = [lazyExec, 'addrelease', '-d', dlItem.path]

                            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            return
                        else:
                            functions.raiseError(logger, "Unable to get right section path, call steve: %s" % code)

                    else:
                        functions.raiseError(logger, "CRC Errors in the download, deleted the errors and resetting back to pending: %s" % code, 2)

    elif os.path.isfile(dlItem.localpath):
        __, ext = os.path.splitext(dlItem.localpath)
        if re.match('(?i)\.(mkv|avi|m4v|mpg|mp4)', ext):
            srcFiles = [{'src': dlItem.localpath, 'dst': None}]
        else:
            functions.raiseError(logger, 'Is not a media file')

    if not srcFiles:
        functions.raiseError(logger, 'No media files found')


    #Check if we are dealing with docos
    if re.match('(?i).+S[0-9][0-9].+', dlItem.title) or re.match('(?i).+\.[0-9]+x[0-9]+\..+', dlItem.title):

        title = dlItem.title

        if '.special.' in dlItem.title.lower() and dlItem.epOverride > 0:
            if not re.match('(?i).+S[0-9][0-9]E[0-9][0-9].+', dlItem.title):
                #lets fake the ep
                title = re.sub('\.S[0-9][0-9]\.', '.S01E01.', title)

        if re.match('(?i)^(History\.Channel|Discovery\.Channel|National\.Geographic).+', dlItem.title):
            title = re.sub(r'(History\.Channel|Discovery\.Channel|National\.Geographic\.Wild|National\.Geographic)\.', r'', dlItem.title)
            parser = functions.getSeriesInfo(title)
        else:
            parser = functions.getSeriesInfo(title)

        if parser:
            seriesName = functions.removeIllegalChars(parser.name)
            seriesSeason = str(parser.season).zfill(2)
            seriesEP = str(parser.episode).zfill(2)
            proper = parser.proper
        else:
            functions.raiseError(logger, "Unable to get series info")

        if showNameReplacements.get(seriesName.lower()):
            seriesID = showNameReplacements.get(seriesName.lower())
        else:
            seriesID = None


        doMoveTV(dstFolder, srcFiles, dlItem, seriesName, seriesSeason, seriesEP, proper, seriesID)
    elif re.match('(?i)^(History\.Channel|Discovery\.Channel|National\.Geographic).+', dlItem.title):
        #We have a doco, we treat the title as a movie
        seriesName, __ = functions.getDocoInfo(dlItem.title)
        moveDoco(dlItem, seriesName, srcFiles, dstFolder)