#!/usr/bin/python2.7
import os
import logging

from lazy.includes.manager import config
from lazy.includes.manager import Session
from lazy.includes.schemadef import ImdbCache
from lazy.includes.schemadef import DownloadItem, TVDBCache
from lazy.includes.easytvdb import EasyTVDB
from lazy.includes.easytvdb import EasyTVDB
from lazy.includes import manager
from lazy.includes import functions


logger = logging.getLogger('MoveMovie')

logger = logging.getLogger('MoveTV')

apiID = manager.config.get('MoveTV', 'TheTVDB_api')

if apiID:
    easyTV = EasyTVDB(apiID)
else:
    functions.raiseError(logger, 'TheTVDB api id is not set')

class dailytask:

    __tvFolder = None

    def __checkArgs(self, parser):
        group = parser.add_argument_group("DailyTask")

        group.add_argument('-s', required=True, action="store", dest='tvFolder', help='tvFolder')

        result = parser.parse_args()

        self.__tvFolder = result.tvFolder


    def __checkConfig(self):
        pass

    def __init__(self, parentParser):
        global config
        self.__config = config

        self.__parser = parentParser
        self.__checkArgs(parentParser)
        self.__checkConfig()

    def setupNFOFile(self, nfoFile, seriesID):
        logger.info("writing nfo file %s" % nfoFile)
        f = open(nfoFile,'w')
        f.write('http://thetvdb.com/?tab=series&id=%s&lid=7' % seriesID) # python will convert \n to os.linesep
        f.close()


    def execute(self):

        #First lets ensure all tvshow.nfo exists
        if not os.path.exists(self.__tvFolder):
            functions.raiseError(logger, 'Source folder does not exist')

        session = Session()

        for show in os.listdir(self.__tvFolder):
            tvshowFileName = self.__tvFolder + os.sep + show + os.sep + 'tvshow.nfo'

            if not os.path.exists(tvshowFileName):
                logger.info("Running on %s" % show)
                logger.debug("Checking via TVDB")
                matches = easyTV.findShow(show)

                if matches.__len__() > 1:
                    #Multi matches, do something here
                    logger.debug("Multiple shows found")

                    bestMatch = None

                    for match in matches:
                        #choose best match above 85 percent
                        if match[1] > 89:
                            if not bestMatch:
                                bestMatch = match
                            else:
                                if match[1] > bestMatch[1]:
                                    bestMatch = match

                    if not bestMatch:
                        functions.raiseError(logger, "Could not find a match for TV Show")
                    else:
                        logger.debug("Best match found: " + bestMatch[2]['SeriesName'] + " Percent: " + str(bestMatch[1]))

                    self.setupNFOFile(tvshowFileName, bestMatch[0])


                elif matches.__len__() == 1:
                    self.setupNFOFile(tvshowFileName, matches[0][0])
                else:
                    logger.error(logger, "Could not find show: " + show + " via thetvdb.com")



        #Now lets check tvshows
        """
        easyTV = EasyTVDB('9fbbdb8fb05b90f9b71fed41025f559a47db2c47')
    
        session = Session()
        query = session.query(TVDBCache)
        results = query.all()

        for qresult in results:

            logger.info("Running on item: " + qresult.title)

            showObj = easyTV.tvshowToDict(qresult.tvdbid).get(qresult.tvdbid)

            qresult.title = showObj.get('SeriesName').replace(".", " ").strip()
            qresult.network = showObj.get('Network')
            qresult.updated = datetime.now()
            qresult.posterImg = showObj.get('poster')

            if showObj.get('Overview'):
                qresult.desc = showObj.get('Overview').decode('utf-8')

            try:
                if showObj.get('poster'):
                    outpath = os.path.join('/home/media/.lazy/imgs/', qresult.tvdbid + '-tvdb.jpg')
                    urlretrieve(showObj.get('poster'), outpath)
            except:
                pass

            sGenres = ''

            if showObj.get('Genre'):
                for genre in showObj.get('Genre'):
                    sGenres += '|' + genre

            qresult.genres = sGenres.replace('|', '', 1)

            session.commit()
        """