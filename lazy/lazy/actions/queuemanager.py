'''
Created on 10/08/2011

@author: jdankbaar
'''
import logging
import os
from decimal import Decimal
from datetime import datetime
import ftplib

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from flexget.utils.imdb import ImdbParser

from lazy.includes.manager import Session
from lazy.includes.schemadef import DownloadItem
from lazy.includes import manager
from lazy.includes.ftpmanager import FTPManager
from lazy.includes.exceptions import FTPError, LazyError
from lazy.includes import functions


logger = logging.getLogger('queueManager')


class queuemanager:
    
    __id = None
    __qaction = None

    __type = None
    __parser = None
    __maxlftp = None
    
    def __init__(self, parentParser):
        
        self.__parser = parentParser
        self.__checkArgs(parentParser)
        self.__checkConfig()
        
    def __checkConfig(self):
        for section, path in manager.config['sections'].items():
            logger.debug("testing permissions to %s " % section)
            if not os.path.exists(path):
                functions.raiseError(logger, "failed %s" % section)
                
        try:
            self.__maxlftp = int(manager.config.get("general", 'max_lftp'))
            if self.__maxlftp < 1 or self.__maxlftp > 10:
                logger.info('Max LFTP was not between 1 and 10, adjusting to 1')
                self.__maxlftp = 1
        except:
                functions.raiseError(logger, "Max FTP not set in the config")
    
    def __checkArgs(self, parser):
        group = parser.add_argument_group("Manage FTP Queue")

        #TODO print out queue actions with help
        group.add_argument('-q',required=True, action="store", dest='qaction', help='queue action')
        group.add_argument('-j', action="store", dest='id', help='Job ID')
        
        result = parser.parse_args()
        self.__id = result.id
        self.__qaction = result.qaction

    def getEps(self, dlItem):
    #create list
        downloadEps = {}

        for ep in str(dlItem.getEps).split(","):
            split = ep.split(":")

            season = split[0]

            seasonObj = {}


            if season not in downloadEps:
                downloadEps[season] = seasonObj
            else:
                seasonObj = downloadEps[season]

            epsObject = []

            if 'eps' not in seasonObj:
                seasonObj['eps'] = epsObject
            else:
                epsObject = seasonObj['eps']

            if len(split) == 2:
                ep = split[1]

                #now add it
                epsObject.append(ep)

            elif len(split) == 1:
                seasonObj['getAll'] = True

        return downloadEps
    
    def execute(self):

        functions.checkRunning('queuemanager')

        session = Session()

        ftpManager = FTPManager()
            
        #So lets find out what we are doing
        if (self.__qaction == "update"):
            #Find jobs running and if they are finished or not
            logger.debug('Performing queue update')
            query = session.query(DownloadItem).filter(DownloadItem.status == DownloadItem.DOWNLOAD_STARTED)
            results = query.all()    
            
            for dlItem in results:
                logger.info('Checking job: %s' % dlItem.path)
                #Now check if its finished
                if ftpManager.jobFinished(dlItem.lftppid):
                    #Lets make sure it finished downloading properly
                    logger.info('Job has finished')
                    localsize = -1
                    try:
                        localsize = ftpManager.getLocalSize(dlItem.localpath)
                        logger.debug('Local size of folder is: %s' % localsize)
                    except:
                        logger.info("error getting local size of folder: %s" % dlItem.path)
                    
                    localsize = localsize / 1024 / 1024
                    remotesize = dlItem.remotesize / 1024 / 1024
                    
                    if (localsize == 0) and (remotesize == 0):
                        percent = 100
                    else:
                        percent = Decimal(100 * float(localsize)/float(remotesize))

                    if percent > 99.3:
                        #Change status to extract
                        logger.info("Job actually finished, moving release to move status")
                        ftpManager.removeScript('ftp-%s' % dlItem.id)
                        dlItem.status = DownloadItem.DOWNLOAD_MOVE
                        dlItem.retries = 0
                        dlItem.message = ''
                        session.commit()
                    else:
                        #Didnt finish properly
                        if dlItem.retries > 10:
                            #Failed download
                            #TODO: Notify
                            logger.info("%s didn't download properly after 10 retries" % dlItem.path)
                            dlItem.message = "didn't download properly after 10 retries, stopping download"
                            dlItem.status = DownloadItem.DOWNLOAD_FAILED
                            session.commit()
                        else:
                            #Didnt download properly, put it back in the queue and let others try download first.
                            logger.info("%s didn't download properly, trying again" % dlItem.path)
                            
                            dlItem.retries += 1
                            dlItem.message = "Failed Download, will try again (Retry Count: %s)" % dlItem.retries
                            dlItem.status = DownloadItem.DOWNLOAD_NEW
                            dlItem.dlstart = datetime.now()

                            session.commit()
                else:
                    #Lets make sure the job has not been running for over x hours
                    curTime = datetime.now()
                    diff = curTime - dlItem.dlstart
                    hours =  diff.seconds / 60 / 60
                    if hours > 8:
                        logger.info("Job as has been running for over 8 hours, killing job and setting to retry: %s" % dlItem.path)
                        dlItem.retries += 1
                        FTPManager.stopJob(dlItem.lftppid)
                        session.commit()
                
                                
            #Figure out the number of jobs running after the above checks
            query = session.query(DownloadItem).filter(DownloadItem.status == DownloadItem.DOWNLOAD_STARTED)
            count = query.count()
            
            startnew = self.__maxlftp - count 
            logger.info("Going to try start %s new jobs" % startnew)
            
            #If jobs running is smaller then the config then start new jobs
            if (startnew > 0):
                query = session.query(DownloadItem).filter(DownloadItem.status == DownloadItem.DOWNLOAD_NEW).order_by(DownloadItem.priority).order_by(DownloadItem.dateadded)
                countJobs = query.count()
                results = query.all()
                
                if countJobs == 0:
                    logger.info("No outstanding jobs found to start")
                    return
            
                count = 0
                                                                
                for dlItem in results:
                    
                    if (count < startnew):

                        if dlItem.dlstart:
                            curTime = datetime.now()
                            diff = curTime - dlItem.dlstart
                            minutes = diff.seconds / 60

                            if minutes < 20:
                                logger.info("skipping job as it was just retired: %s" % dlItem.title)
                                continue

                        logger.info("Starting job: %s" % dlItem.path)

                        if (dlItem.retries > 10):
                            logger.info("Job hit too many retires, setting to failed")
                            dlItem.status = DownloadItem.DOWNLOAD_FAILED
                            session.commit()

                        remotesize = False

                        try:
                            if dlItem.getEps and dlItem.getEps != '':
                                #we dont want to get everything.. lets figure this out
                                downloadEps = self.getEps(dlItem)
                                getFolders = ftpManager.getRequiredDownloadFolders(dlItem.title, dlItem.path, downloadEps)
                                remotesize = ftpManager.getRemoteSizeMulti(getFolders)
                            else:
                                remotesize = ftpManager.getRemoteSize(dlItem.path)
                        except ftplib.error_perm as e:
                            remotesize == 0

                        if remotesize > 0:
                            dlItem.remotesize = remotesize
                        else:
                            if dlItem.requested == 1:
                                logger.info("Unable to get remote size for %s" % dlItem.path)
                                dlItem.message = 'Waiting for item to appear on ftp'
                                session.commit()
                            else:
                                logger.info("Unable to get remote size for %s" % dlItem.path)
                                dlItem.retries += 1
                                session.commit()

                            continue

                        #Time to start a new one!.
                        if dlItem.getEps and dlItem.getEps != '':
                            dlItem.lftppid = ftpManager.mirrorMulti(dlItem.localpath, getFolders, dlItem.id)
                        else:
                            dlItem.lftppid = ftpManager.mirror(dlItem.localpath, dlItem.path, dlItem.id)

                        dlItem.dlstart = datetime.now()
                        dlItem.status = DownloadItem.DOWNLOAD_STARTED
                        
                        session.commit()      

                        count += 1 
                    else:
                        break
                                 
        elif (self.__qaction == "stopall"):
            
            query = session.query(DownloadItem).filter(DownloadItem.status == DownloadItem.DOWNLOAD_STARTED)
            results = query.all()
            
            for dlItem in results:
                ftpManager.stopJob(dlItem.lftppid)
                logger.info("Stopping %s" % dlItem.path)
                                        
        else:
            functions.raiseError(logger, "Invalid queue action")

        
                