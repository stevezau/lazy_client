#!/usr/bin/python2.7
import re
import os
import logging

from lazy.includes import manager
from lazy.includes.manager import Session
from lazy.includes.schemadef import DownloadItem
from lazy.includes import movetv, movemovie
from lazy.includes.exceptions import LazyError
from lazy.includes import functions


logger = logging.getLogger('MoveRelease')
    
class moverls:
    
    __showNameReplacements = None

    def __checkArgs(self, parser):
        group = parser.add_argument_group("MoveRelease")

    def __init__(self, parentParser):
          
        self.__parser = parentParser
        self.__checkArgs(parentParser)
                    
    def execute(self):

        functions.checkRunning('moverls')

        session = Session()
        
        logger.debug('Getting jobs')
        query = session.query(DownloadItem).filter(DownloadItem.status == DownloadItem.DOWNLOAD_MOVE)
        results = query.all()
        
        for dlItem in results:
            
            if dlItem.retries > 3:
                #Failed skip
                #dlItem.status = DownloadItem.DOWNLOAD_FAILED
                #session.commit()
                logger.error("Tried to extract 3 times already but failed.. will skip: %s" % dlItem.title)
                continue
            
            logger.info("Processing: %s" % dlItem.localpath)

            #Check what type of things we are dealing with
            if re.match('(?i)(REQUESTS)', dlItem.section):
                if re.match('(?i)(.+\.[P|H]DTV\..+|.+\.S[0-9]+E[0-9]+.+|.+\.S[0-9]+\..+|.+\.S[0-9]+-S[0-9]+\..+)', dlItem.title):
                    #Prob an ep
                    dlItem.section = 'TVHD'
                    session.commit()
                else:
                    #prob a movie
                    dlItem.section = "HD"
                    session.commit()

            #Check files and folders exist
            if not os.path.exists(dlItem.localpath):
                logger.error('Source file or folder does not exist for. Skipping')
                continue
            try:
                dstFolder = manager.config.get("sections", dlItem.section)
            except:
                logger.error("Cannot find dst folder for section: %s" % dlItem.section)
                continue
                    
        
            if re.match('(?i)(XVID|HD)', dlItem.section):
                try:
                    movemovie.moveMovie(dlItem, dstFolder)
                    dlItem.status = DownloadItem.DOWNLOAD_COMPLETE
                    dlItem.msg = None
                    session.commit()
                except LazyError as e:
                    if e.id == 2:
                        dlItem.status = DownloadItem.DOWNLOAD_NEW
                    dlItem.retries += 1
                    dlItem.message = e.message
                    session.commit()
                    logger.error("error moving %s due to %s" % (dlItem.localpath, e.message))
            elif re.match('(?i)(TV|TVHD)', dlItem.section):
                try:
                    movetv.moveTV(dlItem, dstFolder)
                    dlItem.status = DownloadItem.DOWNLOAD_COMPLETE
                    dlItem.msg = None
                    session.commit()
                except LazyError as e:
                    if e.id == 2:
                        dlItem.status = DownloadItem.DOWNLOAD_NEW
                    dlItem.retries += 1
                    dlItem.message = e.message
                    session.commit()
                    logger.error("error moving %s due to %s" % (dlItem.localpath, e.message))
            else:
                logger.error("Cannot figure out what type of thing this is..")
            
                
