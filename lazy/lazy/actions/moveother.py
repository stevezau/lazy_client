#!/usr/bin/python2.7
import os
import logging
import re

from lazy.includes.exceptions import LazyError
from lazy.includes import movetv
from lazy.includes.schemadef import DownloadItem
from lazy.includes import manager
from lazy.includes.manager import Session
from lazy.includes.easytvdb import EasyTVDB
from lazy.fuzzywuzzy import fuzz
from lazy.includes import functions


logger = logging.getLogger('MoveOther')
    
class moveother:
    
    __srcFolder = None
    __type = None
    __clean = None
    
    def __checkArgs(self, parser):
        group = parser.add_argument_group("Move Multi TV Releases")

        group.add_argument('-s', required=True, action="store", dest='srcFolder', help='Source file')
        group.add_argument('-t', required=True, action="store", dest='type', help='type')

        result = parser.parse_args()
        
        self.__srcFolder = os.path.normpath(result.srcFolder)
        self.__type = result.type.lower()
        
    def __init__(self, parentParser):
        self.__checkArgs(parentParser)
        self.__parser = parentParser
        
    def execute(self):
        
        apiID = manager.config.get('MoveTV', 'TheTVDB_api')
        
        if apiID:
            easyTV = EasyTVDB(apiID)
        else:
            functions.raiseError(logger, 'TheTVDB api id is not set')
    
        #Check files and folders exist
        if not os.path.exists(self.__srcFolder):
            functions.raiseError(logger, 'Source folder does not exist')
        if not os.path.isdir(self.__srcFolder):
            functions.raiseError(logger, 'Source is not a folder')
            
        #Lets get all the folders and files
        files = os.listdir(self.__srcFolder)
        
        if not files or len(files) == 0:
            functions.raiseError(logger, 'No folders or files in path ' + self.__srcFolder)
        
        for file in os.listdir(self.__srcFolder):
            filePath = os.path.join(self.__srcFolder + os.sep + file)            
            if os.path.exists(filePath):
                
                #Create fake dlItem
                dlItem = DownloadItem()
                __, dlItem.title = os.path.split(filePath)
                dlItem.localpath = filePath
                
                if self.__type == "tv":
                    dlItem.section = "TVHD"
                if self.__type == "movie":    
                    dlItem.section = "HD"
                
                #Lets see if its in the database, if so ignore
                session = Session()
        
                logger.debug('Check if its in the db: %s' % dlItem.title)
                query = session.query(DownloadItem).filter(DownloadItem.title == dlItem.title)
                results = query.all()
                
                if results:
                    logger.info("skipping as its in the database: %s" % dlItem.title)
                    continue
                   
                try:
                    dstFolder = manager.config.get("sections", dlItem.section)
                except:
                    logger.error("Cannot find dst folder for section: %s" % dlItem.section)
                    continue
                               
                #Do we need to rename any of them??
                if re.match('(?i)(.+S00E[0-9][0-9].+)', dlItem.title):
                    ## No season info lets rename
                    logger.debug("finding series info")
                    series = manager.config.items("TVShowID")

                    title = dlItem.title.lower()

                    for tvshow in series:
                        
                        if title.startswith(tvshow[0]):
                            showTitle = tvshow[0]
                            showID = tvshow[1]
                            break
                            
                    if showTitle and showID :
                        epName = title.replace(showTitle, "").strip()

                        #Ok lets get the right season info etc
                        seriesInfo = easyTV.tvshowToDict(showID)
                        eps = seriesInfo.get(tvshow[1]).get("Episodes")
                        
                        match = [0, "", ""]
                        
                        for ep in eps:
                            epID = ep
                            epData = eps.get(epID)
                            
                            tvdbEpName = epData.get("EpisodeName")
                            
                            if tvdbEpName:
                                percent = fuzz.partial_ratio(tvdbEpName, epName)
                                
                                if percent > match[0]:
                                    match = [percent, ep, tvdbEpName]                               

                        if match[0] > 50:
                            logger.info("Matched (%s): %s to ep title %s" % (match[0], epName, match[2]))
                            
                            dlItem.title = showTitle + " .S" + match[1].replace('x','E') + ". " + match[2]
                        else:
                            continue
       
                #MoveTV
                if re.match('(?i)(TV|TVHD)', dlItem.section):
                    try:
                        movetv.moveTV(dlItem, dstFolder)
                    except LazyError as e:
                        logger.error("error moving %s due to %s" % (dlItem.localpath, e.msg))
                
                #MoveMovies
                if re.match('(?i)(XVID|HD)', dlItem.section):
                    try:
                        movetv.moveTV(dlItem, dstFolder)
                    except LazyError as e:
                        logger.error("error moving %s due to %s" % (dlItem.localpath, e.msg))
                