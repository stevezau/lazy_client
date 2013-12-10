'''
Created on 10/08/2011

@author: jdankbaar
'''
import logging
import os
from datetime import datetime
from urllib import urlretrieve
import unicodedata
import re

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from flexget.utils.imdb import ImdbSearch, ImdbParser
import tvdb_api

from lazy.includes.manager import Session, config
from lazy.includes.schemadef import DownloadItem
from lazy.includes.schemadef import ImdbCache, TVDBCache
import lazy.includes.functions as functions
import signal

logger = logging.getLogger('Download')


class addrelease:
    
    __path = None
    __type = None
    __parser = None
    __pending = False
    __imdbid = None
    __waiting = False
    __msg = None
    __tvdbid = None
    __requested = None
    __apiTVDB = tvdb_api.Tvdb(banners = True)

    def __init__(self, parentParser):
       
        self.__parser = parentParser
        self.__checkArgs(parentParser)

        self.__apiTVDB = tvdb_api.Tvdb(banners = True)
    
    def __checkArgs(self, parser):
        group = parser.add_argument_group("Download release from FTP")

        group.add_argument('-d', required=True, action="store", dest='path', help='FTP Path')
        group.add_argument('-i', action="store", dest='imdb_id', help='IMDB ID')
        group.add_argument('-t', action="store", dest='tvdb_id', help='TVDB ID')
        group.add_argument('-w', action="store_true", dest='waiting', help='waiting status')
        group.add_argument('-m', action="store", dest='msg', help='add msg')
        group.add_argument('--getEps', action="store", dest='getEps', help='only get the eps.. seasonNo:EpNo,seasonNo:EpNo etc')
        group.add_argument('-p', action="store_true", dest='pending', help='mark this as a pending download')
        group.add_argument('-r', action="store_true", dest='requested', help='requested download')
        
        result = parser.parse_args()
        self.__path = result.path.strip()
        self.__pending = result.pending
        self.__imdbid = result.imdb_id
        self.__tvdbid = result.tvdb_id
        self.__waiting = result.waiting
        self.__msg = result.msg
        self.__getEps = result.getEps
        self.__requested = result.requested


    def execute(self):
        
        session = Session()

        #Get path and title
        split = self.__path.split("/")
        section = split[1]
        title = split[-1]

        if not section:
            functions.raiseError(logger, 'Unable to determine section from path %s' % self.__path)

        if not title:
            functions.raiseError(logger, 'Unable to determine title from path %s' % self.__path)

        #Check if it exists already..
        query = session.query(DownloadItem).filter(DownloadItem.path == self.__path)

        try:
            found = query.one()

            logger.debug("found existing record")
            #found existing entry..
            if self.__getEps:
                #we might need to update this entry..
                #if its already started then kill the job and reset it with the appended eps
                if found.status == DownloadItem.DOWNLOAD_STARTED or found.status == DownloadItem.DOWNLOAD_MOVE or found.status == DownloadItem.DOWNLOAD_PENDING or found.status == DownloadItem.DOWNLOAD_NEW:
                    if found.lftppid != 0:
                        os.kill(int(found.lftppid), signal.SIGTERM)
                    found.status == DownloadItem.DOWNLOAD_NEW
                    found.retries = 0

                    if found.getEps and found.getEps != '':
                        #append
                        found.getEps = str(found.getEps) + "," + str(self.__getEps)
                    else:
                        #do nothing as its downloading the whole season
                        pass

                    session.commit()
                    logger.debug("Found existing record, updated it and reset")
                    return
            else:
                if found.status == DownloadItem.DOWNLOAD_COMPLETE:
                    #Lets delete it so we can get it again for some reason
                    session.delete(found)
                    session.commit()
                else:
                    functions.raiseError(logger, "Release already exists %s" % self.__path)

        except NoResultFound:
            pass
        except MultipleResultsFound:
            functions.raiseError(logger, "Release already exists %s" % self.__path)

        try:
            path = config.get("sections", section + "_TEMP")
        except:
            functions.raiseError(logger, "Unable to find section path in config: %s" % section)

        self.__lazyPath = config.get('general', 'lazy_home')

        self.__imdbid = functions.extract_id(self.__imdbid)
        tvdbid = self.__tvdbid

        try:

            if re.match('(?i)(.+\.[P|H]DTV\..+|.+\.S[0-9]+E[0-9]+.+|.+\.S[0-9]+\..+|.+\.S[0-9]+-S[0-9]+\..+)', title) and tvdbid is None:

                if re.match('(?i)^(History\.Channel|Discovery\.Channel|National\.Geographic).+', title):
                    title = re.sub(r'(History\.Channel|Discovery\.Channel|National\.Geographic\.Wild|National\.Geographic)\.', r'', title)
                    parser = functions.getSeriesInfo(title)
                else:
                    parser = functions.getSeriesInfo(title)

                if parser:
                    seriesName = parser.name
                    proper = parser.proper

                    try:
                        matches = self.__apiTVDB[seriesName]
                        print matches
                        logger.debug("Show found")
                        tvdbid = matches['id']


                    except Exception as e:
                        functions.raiseError(logger, "Error finding : %s via thetvdb.com due to  %s" % (seriesName, e.message))

                else:
                    functions.raiseError(logger, "Unable to parse series info")
            else:
                #Lets try find the movie details
                movieName, movieYear = functions.getMovieInfo(title)

                imdbS = ImdbSearch()
                results = imdbS.best_match(movieName, movieYear)

                if results and results['match'] > 0.70:
                    movieObj = ImdbParser()

                    movieObj.parse(results['url'])

                    self.__imdbid = movieObj.imdb_id


            if tvdbid is not None:
                #Does it already exist?
                query = session.query(TVDBCache).filter(TVDBCache.tvdbid == tvdbid)
                count = query.count()
                results = query.all()

                if count == 1:
                    #found the record
                    for qresult in results:
                        logger.debug("Found existing tvdb record")
                        #Do we need to update it
                        curTime = datetime.now()

                        hours = 0

                        if qresult.updated is None:
                            hours = 50
                        else:
                            diff = curTime - qresult.updated
                            hours =  diff.seconds / 60 / 60

                        if hours == 0:

                            try:
                                logger.info("Updating tvdb cache info as its old")
                                showObj = self.__apiTVDB[int(tvdbid)]
                                qresult.update(showObj)
                                session.commit()
                            except Exception as e:
                                logger.error("Error getting series data from tvdb %s %s" % (seriesName, e.message))

                elif count == 0:

                    logger.debug("Getting tvdb data for release")

                    #Get latest tvdb DATA
                    showObj = self.__apiTVDB[int(tvdbid)]
                    newTVDB = TVDBCache()
                    newTVDB.tvdbid = showObj['id']
                    newTVDB.update(showObj)

                    session.add(newTVDB)
                    session.commit()


            if self.__imdbid is not None:
                #Does it already exist?

                query = session.query(ImdbCache).filter(ImdbCache.imdbid == self.__imdbid)
                count = query.count()
                results = query.all()

                if count == 1:
                    #found the record
                    for qresult in results:
                        logger.debug("Found existing imdb record")
                        #Do we need to update it
                        curTime = datetime.now()
                        diff = curTime - qresult.updated
                        hours =  diff.seconds / 60 / 60

                        if hours > 0:
                            logger.info("Updating imdb cache info as its old")
                            imdbObj = ImdbParser()
                            imdbObj.parse(qresult.imdbid)

                            qresult.score = imdbObj.score
                            qresult.votes = imdbObj.votes
                            qresult.updated = datetime.now()
                            qresult.desc = imdbObj.plot_outline

                            sGenres = ''

                            if imdbObj.genres:
                                for genre in imdbObj.genres:
                                    sGenres += '|' + unicodedata.normalize('NFKD', genre).encode('ascii','ignore').title()

                            qresult.genres = sGenres.replace('|', '', 1)

                            if imdbObj.photo:
                                basePath = self.__lazyPath + os.sep + "imgs"
                                outpath = os.path.join(basePath, qresult.imdbid + '.jpg')
                                urlretrieve(imdbObj.photo, outpath)
                                qresult.posterImg = imdbObj.photo

                            session.commit()

                elif count == 0:

                    logger.debug("Getting IMDB data for release")

                    try:
                        #Get latest IMDB DATA
                        imdbObj = ImdbParser()
                        imdbObj.parse(self.__imdbid)

                        if imdbObj.name:
                            #insert into db
                            newIMDB = ImdbCache()
                            newIMDB.imdbid = imdbObj.imdb_id
                            newIMDB.score = imdbObj.score
                            newIMDB.title = imdbObj.name
                            newIMDB.year = imdbObj.year
                            newIMDB.votes = imdbObj.votes
                            newIMDB.updated = datetime.now()
                            newIMDB.desc = imdbObj.plot_outline

                            sGenres = ''

                            if imdbObj.genres:
                                for genre in imdbObj.genres:
                                    sGenres += '|' + unicodedata.normalize('NFKD', genre).encode('ascii','ignore').title()

                            newIMDB.genres = sGenres.replace('|', '', 1)

                            if imdbObj.photo:
                                basePath = self.__lazyPath + os.sep + "imgs"
                                outpath = os.path.join(basePath, imdbObj.imdb_id + '.jpg')
                                urlretrieve(imdbObj.photo, outpath)
                                newIMDB.posterImg = imdbObj.photo

                            session.add(newIMDB)
                            session.commit()
                    except Exception as e:
                        logger.exception("error gettig imdb information.. from website " + e.message)
        except Exception as e:
            logger.exception("Failed for some reason:" + e.message)




        #Add to the database
        newDL = DownloadItem()

        newDL.title = title
        newDL.path = self.__path

        local = path + "/" + title
        newDL.localpath = local.strip()

        newDL.section = section
        newDL.lftppid = 0
        newDL.retries = 0
        newDL.sizeonserver = 0

        newDL.localsize = 0
        newDL.imdbID = self.__imdbid
        newDL.tvdbid = tvdbid
        newDL.dateadded = datetime.now()

        if self.__getEps:
            newDL.getEps = self.__getEps

        if self.__requested:
            newDL.requested = 1

        if self.__msg:
            newDL.message = self.__msg

        if self.__pending:
            newDL.status = newDL.DOWNLOAD_PENDING
        elif self.__waiting:
            newDL.status = newDL.DOWNLOAD_WAITING
        else:
            newDL.status = newDL.DOWNLOAD_NEW

        session.add(newDL)
        session.commit()

        logger.info("Added release to database")
