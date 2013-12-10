#!/usr/bin/python2.7
import logging

from flexget.utils.imdb import ImdbSearch, ImdbParser

from lazy.includes.manager import config
from lazy.includes.manager import Session
from lazy.includes.schemadef import DownloadItem
from lazy.includes import functions


logger = logging.getLogger('MoveMovie')

class cleandb:
    
    def __init__(self, parentParser):
        global config
        self.__config = config
    
    def doStuff(self, session, qresult):
        #we have a imdbid, lets check it
        movieObj = ImdbParser()
        movieObj.parse(qresult.imdbID) 
                
        if 'english' not in movieObj.languages:
            print movieObj.languages
            logger.info('Deleteing the movie as its not in english!')
            session.delete(qresult)
            session.commit()
            session.flush()
        
        if movieObj.votes < 200:
            logger.info('Deleteing the movie as it has no votes')
            session.delete(qresult)
            session.commit()
            session.flush()
            
        if movieObj.score < 5.5:
            logger.info('Deleteing the movie as it has crap rating.')
            session.delete(qresult)
            session.commit()
            session.flush()
            
        if movieObj.score > 7 and movieObj.votes > 1000:
            logger.info('Good Movie!!')
            qresult.status = 1
            session.commit()
            session.flush()
        
    def execute(self):
    
        session = Session()
        query = session.query(DownloadItem).filter(DownloadItem.status == 6)
        results = query.all()  

        for qresult in results:
            #lets get the record
            if qresult.imdbID:
                logger.info("Running on item: " + qresult.title)
                self.doStuff(session, qresult)
                
            else:
                logger.info("NO IMDB DATA FOR " + qresult.title)
                movieName, movieYear = functions.getMovieInfo(qresult.title)
                
                imdbS = ImdbSearch()
                results = imdbS.best_match(movieName, movieYear)

                if results and results['match'] > 0.70:
                    qresult.imdbID = functions.extract_id(results['url'])
                    session.commit()
                    self.doStuff(session, qresult)
                            
                