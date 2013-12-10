#!/usr/bin/python2.7
import os
import logging
from datetime import datetime
from urllib import urlretrieve
import unicodedata

from flexget.utils.imdb import ImdbParser

from lazy.includes.manager import config
from lazy.includes.manager import Session
from lazy.includes.schemadef import ImdbCache
from lazy.includes.schemadef import DownloadItem, TVDBCache
from lazy.includes.easytvdb import EasyTVDB


logger = logging.getLogger('MoveMovie')

class cleanimdb:
    
    def __init__(self, parentParser):
        global config
        self.__config = config

    def execute(self):

        easyTV = EasyTVDB('9fbbdb8fb05b90f9b71fed41025f559a47db2c47')
    
        session = Session()
        query = session.query(DownloadItem).order_by(DownloadItem.id.desc())
        results = query.all()

        for qresult in results:

            logger.info("Running on item: " + qresult.title)

            #lets get the record
            if qresult.tvdbid:
                #Does it already exist?
                query = session.query(TVDBCache).filter(TVDBCache.tvdbid == qresult.tvdbid)
                count = query.count()
                results = query.all()

                if count == 1:
                    #found the record
                    for tvdbqresult in results:
                        logger.debug("Found existing tvdb record")
                        #Do we need to update it
                        curTime = datetime.now()
                        diff = curTime - tvdbqresult.updated
                        hours =  diff.seconds / 60 / 60

                        if hours == 0:
                            logger.info("Updating tvdb cache info as its old")
                            showObj = easyTV.tvshowToDict(qresult.tvdbid).get(qresult.tvdbid)

                            tvdbqresult.title = showObj.get('SeriesName').replace(".", " ").strip()
                            tvdbqresult.network = showObj.get('Network')
                            tvdbqresult.updated = datetime.now()
                            tvdbqresult.posterImg = showObj.get('poster')

                            if showObj.get('Overview'):
                                tvdbqresult.desc = showObj.get('Overview').decode('utf-8')

                            try:
                                if showObj.get('poster'):
                                    outpath = os.path.join('/home/media/.lazy/imgs', qresult.tvdbid + '-tvdb.jpg')
                                    urlretrieve(showObj.get('poster'), outpath)
                            except:
                                pass

                            sGenres = ''

                            if showObj.get('Genre'):
                                for genre in showObj.get('Genre'):
                                    sGenres += '|' + genre

                            tvdbqresult.genres = sGenres.replace('|', '', 1)

                            session.commit()

                elif count == 0:

                    logger.debug("Getting tvdb data for release")

                    #Get latest tvdb DATA
                    showObj = easyTV.tvshowToDict(qresult.tvdbid).get(qresult.tvdbid)

                    if showObj.get('SeriesName'):
                        newTVDB = TVDBCache()

                        newTVDB.title = showObj.get('SeriesName').replace(".", " ").strip()
                        newTVDB.network = showObj.get('Network')
                        newTVDB.updated = datetime.now()
                        newTVDB.posterImg = showObj.get('poster')

                        if showObj.get('Overview'):
                            newTVDB.desc = showObj.get('Overview').decode('utf-8')

                        newTVDB.tvdbid = qresult.tvdbid

                        sGenres = ''

                        try:
                            if showObj.get('poster'):
                                outpath = os.path.join('/home/media/.lazy/imgs', showObj.get('id') + '-tvdb.jpg')
                                urlretrieve(showObj.get('poster'), outpath)
                        except:
                            pass

                        if showObj.get('Genre'):
                            for genre in showObj.get('Genre'):
                                sGenres += '|' + genre

                        newTVDB.genres = sGenres.replace('|', '', 1)

                        session.add(newTVDB)
                        session.commit()



            if qresult.imdbID:

                #Does it already exist?
                query = session.query(ImdbCache).filter(ImdbCache.imdbid == qresult.imdbID)

                count = query.count()
                results = query.all()


                if count == 1:
                    #found the record
                    for imdbqresult in results:
                        logger.debug("Found existing imdb record")
                        #Do we need to update it
                        curTime = datetime.now()
                        diff = curTime - imdbqresult.updated
                        hours =  diff.seconds / 60 / 60

                        if hours == 0:
                            logger.info("Updating imdb cache info as its old")
                            imdbObj = ImdbParser()
                            imdbObj.parse(qresult.imdbID)

                            imdbqresult.score = imdbObj.score
                            imdbqresult.votes = imdbObj.votes
                            imdbqresult.updated = datetime.now()
                            imdbqresult.desc = imdbObj.plot_outline

                            sGenres = ''

                            if imdbObj.genres:
                                for genre in imdbObj.genres:
                                    sGenres += '|' + unicodedata.normalize('NFKD', genre).encode('ascii','ignore').title()

                            imdbqresult.genres = sGenres.replace('|', '', 1)

                            if imdbObj.photo:
                                outpath = os.path.join('/home/media/.lazy/imgs', imdbObj.imdb_id + '.jpg')
                                urlretrieve(imdbObj.photo, outpath)
                                imdbqresult.posterImg = imdbObj.photo

                            session.commit()

                elif count == 0:

                    logger.debug("Getting IMDB data for release")

                    #Get latest IMDB DATA
                    imdbObj = ImdbParser()
                    imdbObj.parse(qresult.imdbID)

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
                        outpath = os.path.join('/home/media/.lazy/imgs', imdbObj.imdb_id + '.jpg')
                        urlretrieve(imdbObj.photo, outpath)
                        newIMDB.posterImg = imdbObj.photo

                        session.add(newIMDB)
                        session.commit()

