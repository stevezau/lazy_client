#!/usr/bin/python2.7
import os
import logging
import shutil
import re
import pprint
from datetime import datetime
import json

from flexget.utils.imdb import ImdbSearch, ImdbParser

from lazy.includes.manager import config
from lazy.includes.manager import Session
from lazy.includes.schemadef import ImdbCache
from lazy.includes import functions


logger = logging.getLogger('MoveMovie')

class cleanmovies:

    __movFolder = None
    __xbmcDB = None
    
    def __checkArgs(self, parser):
        group = parser.add_argument_group("MoveRelease")

        group.add_argument('-s', required=True, action="store", dest='movFolder', help='movFolder')

        result = parser.parse_args()
    
        self.__movFolder = result.movFolder

        
    def __checkConfig(self):

        xbmcDB = self.__config.get('general', 'xbmc_db')
        
        if xbmcDB:
            self.__xbmcDB = xbmcDB
        else:
            functions.raiseError(logger, 'XBMC DB is not set')
        
    def __init__(self, parentParser):
        global config
        self.__config = config
        
        self.__parser = parentParser
        self.__checkArgs(parentParser)
        self.__checkConfig()

    def execute(self):
        #Check files and folders exist
        if not os.path.exists(self.__movFolder):
            functions.raiseError(logger, 'Source folder does not exist')

        session = Session()
        movies = {}

        for dir in os.listdir(self.__movFolder):
            
            path =  os.path.join(self.__movFolder, dir)
            
            imdbMovie = None
            
            if os.path.isdir(path):
                
                m = re.match('(.*)\(([0-9]+)\)', dir)
                
                if m is not None:
                    title = m.group(1)
                    year = int(m.group(2))
                else:
                    continue

                #if year < 2010:
                #    continue  
                
                logger.info("Working with movie: %s" % dir)
                
                query = session.query(ImdbCache).filter(ImdbCache.title == title)
                count = query.count()
                results = query.all()    
                
                if count > 1:
                    #skip
                    continue
                
                elif count == 1:
                    #found the record
                    for qresult in results:
                
                        #Do we need to update it
                        curTime = datetime.now()
                        diff = curTime - qresult.updated
                    
                        hours =  diff.seconds / 60;
                        
                        if hours > 48:
                            logger.info("Updating movie info as its old")
                            movieObj = ImdbParser()
                            movieObj.parse(qresult.imdbid)
                                   
                            qresult.score = movieObj.score
                            qresult.votes = movieObj.votes
                            qresult.updated = datetime.now()
                            qresult.genres = json.dumps(movieObj.genres)
                         
                            session.commit()
                    
                        imdbMovie = qresult
                        
                elif count == 0:
                    #lets get the record
                    imdbS = ImdbSearch()
                    result = imdbS.best_match(title, year)     
                        
                    if result and result['match'] > 0.70:
                        movieObj = ImdbParser()
                        movieObj.parse(result['url']) 
                        
                        if not movieObj.name:
                            logger.error('Unable to get name')
                            continue
                        if not movieObj.year or movieObj.year == 0:
                            logger.error('Unable to get year')
                            continue  
                        
                        if 'english' not in movieObj.languages:
                            print movieObj.languages
                            logger.info('Deleteing the movie as its not in english!')
                            shutil.rmtree(path)   
                            continue
                        
                        #interset into db
                        newMovie = ImdbCache()
                        newMovie.imdbid = movieObj.imdb_id
                        newMovie.score = movieObj.score
                        newMovie.title = title
                        newMovie.year = year
                        newMovie.votes = movieObj.votes
                        newMovie.updated = datetime.now()
                        newMovie.genres = json.dumps(movieObj.genres)
                        
                        session.add(newMovie)
                        session.commit()
                        
                        imdbMovie = newMovie      
                    
                
                if imdbMovie is not None:
                    
                    if imdbMovie.genres is not None:
                                     
                        if 'romance' in imdbMovie.genres:
                            if imdbMovie.score < 6.0 or (imdbMovie.votes < 2000 and imdbMovie.score < 7.0):
                                logger.info('adding movie: %s  with score %s and votes %s and genre %s' %(imdbMovie.title,imdbMovie.score,imdbMovie.votes,str(imdbMovie.genres)))
                                movies[dir] = {'genre': imdbMovie.genres, 'score': imdbMovie.score, 'votes': imdbMovie.votes , 'name': imdbMovie.title}
                                #shutil.rmtree(path)                         

                    if imdbMovie.score < 5.0 or (imdbMovie.votes < 2000 and imdbMovie.score < 7.0):
                        
                        logger.info('adding movie: %s  with score %s and votes %s' %(imdbMovie.title,imdbMovie.score,imdbMovie.votes))
                        movies[dir] = {'score': imdbMovie.score, 'votes': imdbMovie.votes , 'name': imdbMovie.title}
                        shutil.rmtree(path) 
                        
                    
                else:
                    logger.info("Unable to get movie data: %s" % dir)
                    
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(movies)
                    
                    