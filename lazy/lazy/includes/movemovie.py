'''
Created on 12/04/2012

@author: Steve
'''

import re
import os
import shutil
import logging

from flexget.utils.imdb import ImdbSearch, ImdbParser

from lazy.includes.schemadef import DownloadItem
from lazy.includes.exceptions import LazyError
from lazy.includes import functions


logger = logging.getLogger('MoveMovie')

def doMove(dlItem, movieName, movieYear, dstFolder, srcFiles):
        #We have all the info we need. Move the files.
        logger.debug('Found Movie: ' + movieName + " (Year: " + str(movieYear) + ")")
        dstFolder = functions.removeIllegalChars(os.path.abspath(dstFolder + os.sep + movieName + " (" + str(movieYear) + ")"))

        if os.path.exists(dstFolder):
            # Delete the old movie
            logger.info('Deleting existing movie folder ' + dstFolder)
            shutil.rmtree(dstFolder)

        srcFiles = functions.setupDstFiles(srcFiles, dstFolder, movieName + ' (' + str(movieYear) + ')')
        functions.moveFiles(srcFiles)
        if os.path.exists(dlItem.localpath):
            pass
            shutil.rmtree(dlItem.localpath)

def moveMovie(dlItem, dstFolder):

    if not os.path.exists(dstFolder):
        functions.raiseError(logger, 'Destination folder does not exist')    


    if re.match('(?i).+\.(TRiLOGY|PACK|Duology|Pentalogy)\..+', dlItem.title) and '.special.' not in dlItem.title.lower():
            logger.info("Movie pack detected")

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
                        newDLItem.section = dlItem.section

                        moveMovie(newDLItem, dstFolder)
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

                        moveMovie(newDLItem, dstFolder)

            if os.path.exists(dlItem.localpath):
                logger.debug('Deleting  ' + dlItem.localpath)
                shutil.rmtree(dlItem.localpath)
                return


    dstFolder = os.path.abspath(dstFolder)
    srcFiles = functions.getVidFiles(dlItem.localpath)
     
    if os.path.isdir(dlItem.localpath):
        code = functions.unrar(dlItem.localpath)
        if code == 0 or code == 20194 or code == 2560:
            srcFiles = functions.getVidFiles(dlItem.localpath)
        else:
            #failed.. lets do sfv check
            logger.info('failed extract, lets check the sfv')
            sfvck = functions.checkSFVPath(dlItem.localpath);

            logger.info("SFV CHECK " + str(sfvck))

            if(sfvck):
                srcFiles = functions.getVidFiles(dlItem.localpath)
            else:
                #reset it
                functions.raiseError(logger, "CRC Errors in th download, deleted the errors and resetting back to pending: %s" % code, 2)
        
        # Check if multi cds.. make sure we have
        cdnum = 1
        for f in os.listdir(dlItem.localpath):
            if os.path.isdir(dlItem.localpath + "/" + f):
                name = os.path.basename(f)
                number = functions.getRegex(name, 'CD([0-9])', 1)
                if number == None:
                    number = 1
                if (cdnum < number):
                    cdnum = number
        
        if str(srcFiles.__len__()) != str(cdnum):
            logger.info('nums: ' + str(cdnum) + ':' + str(srcFiles.__len__()))
            functions.raiseError(logger, 'Not finished downloading')
            
    elif os.path.isfile(dlItem.localpath):
        __, ext = os.path.splitext(dlItem.localpath)
        if re.match('(?i)\.(mkv|avi|m4v|mpg)', ext):
            srcFiles = [{'src': dlItem.localpath, 'dst': None}]
        else:
            functions.raiseError(logger, 'Is not a media file')
            
    if not srcFiles:
        functions.raiseError(logger, 'No media files found')
    
    movieName, movieYear = functions.getMovieInfo(os.path.splitext(os.path.basename(dlItem.localpath))[0])

    if movieYear:
        #We have all the info we need. Move the files.
        doMove(dlItem, movieName, movieYear, dstFolder, srcFiles)
        
    else:
        imdbS = ImdbSearch()
        results = imdbS.best_match(movieName, movieYear)

        if results and results['match'] > 0.70:
            movieObj = ImdbParser()
            
            movieObj.parse(results['url']) 
            
            if not movieObj.name:
                functions.raiseError(logger, 'Unable to get name')
            if not movieObj.year or movieObj.year == 0:
                functions.raiseError(logger, 'Unable to get year')

            movieName = movieObj.name
            movieYear = movieObj.year

            #We have all the info we need. Move the files.
            doMove(dlItem, movieName, movieYear, dstFolder, srcFiles)

        else:
            functions.raiseError(logger, 'Unable to find movie: ' + movieName + ' on imdb.com')
