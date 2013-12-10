'''
Created on 22/07/2011

@author: Steve
'''
from urllib import urlretrieve
from datetime import datetime
import os
import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.exc import OperationalError


Base = declarative_base()
logger = logging.getLogger('DBStuff')

def loadSchema(engine):
        # create all tables, doesn't do anything to existing tables
        try:
            Base.metadata.create_all(bind=engine)
        except OperationalError, e:
            raise Exception(e.message)
        
        
class DownloadItem(Base):

    DOWNLOAD_NEW = 1
    DOWNLOAD_STARTED = 2
    DOWNLOAD_MOVE = 3
    DOWNLOAD_COMPLETE = 4
    DOWNLOAD_WAITING = 5
    DOWNLOAD_PENDING = 6

    __tablename__ = 'download'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    section = Column(String, index=True)
    path = Column(String, index=True)
    getEps = Column(String)
    localpath = Column(String)
    status = Column(Integer)
    lftppid = Column(Integer)
    retries = Column(Integer)
    dateadded = Column(DateTime, index=True)
    dlstart = Column(DateTime)
    remotesize = Column(Integer)
    priority = Column(Integer, default=10)
    localsize = Column(Integer)
    message = Column(String)
    imdbID = Column(Integer)
    tvdbid = Column(String, index=True)
    epOverride = Column(Integer)
    requested = Column(Integer)

    
class ImdbCache(Base):

    __tablename__ = 'imdbcache'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    score = Column(Float)
    imdbid = Column(String, index=True)
    votes = Column(Integer)
    year = Column(Integer)
    genres = Column(String)
    posterImg = Column(String)
    desc = Column(String)
    updated = Column(DateTime)

class TVDBCache(Base):

    __tablename__ = 'tvdbcache'

    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    tvdbid = Column(String, index=True)
    posterImg = Column(String)
    network = Column(String)
    genre = Column(String)
    desc = Column(String)
    updated = Column(DateTime)

    def update(self, showObj):
        self.title = showObj['seriesname'].replace(".", " ").strip()
        self.updated = datetime.now()

        if 'network' in showObj.data:
            self.network = showObj['network']

        if 'overview' in showObj.data:
            self.desc = showObj['overview'].decode('utf-8')


        if '_banners' in showObj.data:

            bannerData = showObj['_banners']


            if 'poster' in bannerData.keys():
                posterSize = bannerData['poster'].keys()[0]
                posterID = bannerData['poster'][posterSize].keys()[0]
                posterURL = bannerData['poster'][posterSize][posterID]['_bannerpath']

                try:
                    outpath = os.path.join('/home/media/.lazy/imgs', self.tvdbid + '-tvdb.jpg')
                    urlretrieve(posterURL, outpath)
                    self.posterImg = posterURL
                except Exception as e:
                    logger.error("error saving image: %s" % e.message)
                    pass

        if 'genre' in showObj.data:
            self.genres = showObj['genre']


class Job(Base):

    TYPE_MISSING_REPORT = 1
    TYPE_TEMP_REPORT = 2

    FINISHED = 1
    ERROR = 2




    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)
    type = Column(Integer, index=True)
    outFile = Column(String)
    status = Column(Integer)
    startDate = Column(DateTime)
    finishDate = Column(DateTime)
    title = Column(String)