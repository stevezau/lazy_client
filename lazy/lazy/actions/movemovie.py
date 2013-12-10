#!/usr/bin/python2.7
import re
import os
import shutil
import logging

from flexget.utils.imdb import ImdbSearch, ImdbParser

from lazy.includes import functions


logger = logging.getLogger('MoveMovie')

class movemovie:

    __srcFile = None
    __dstFolder = None
    __movieName = None
    __movieYear = None
    __srcFiles = None
    __clean = False
    
    def __checkArgs(self, parser):
        group = parser.add_argument_group("MoveRelease")

        group.add_argument('-s', required=True, action="store", dest='srcFolder', help='Source file')
        group.add_argument('-d', required=True, action="store", dest='dstFolder', help='Dest file')
        group.add_argument('--clean', action="store_true", dest='clean', help='Remove source files if moved successfully')

        result = parser.parse_args()
    
        self.__clean = result.clean
        self.__srcFile = result.srcFolder
        self.__dstFolder = result.dstFolder

    def __init__(self, parentParser):
        self.__checkArgs(parentParser)
           
    def __moveMovie(self):
            #We have all the info we need. Move the files.
            logger.debug('Found Movie: ' + self.__movieName + " (Year: " + str(self.__movieYear) + ")")
            self.__dstFolder = functions.removeIllegalChars(os.path.abspath(self.__dstFolder + os.sep + self.__movieName + " (" + str(self.__movieYear) + ")"))

            if os.path.exists(self.__dstFolder):
                # Delete the old movie
                logger.info('Deleting existing movie folder ' + self.__dstFolder)
                shutil.rmtree(self.__dstFolder)

            self.__srcFiles = functions.setupDstFiles(self.__srcFiles, self.__dstFolder, self.__movieName + ' (' + str(self.__movieYear) + ')')
            functions.moveFiles(self.__srcFiles)
            if self.__clean and os.path.exists(self.__srcFile):
                shutil.rmtree(self.__srcFile)

    def execute(self):
    
        #Check files and folders exist
        if not os.path.exists(self.__srcFile):
            functions.raiseError(logger, 'Source folder does not exist')
        if not os.path.exists(self.__dstFolder):
            functions.raiseError(logger, 'Destination folder does not exist')
        #if not os.path.isdir(self.__srcFolder):
        #    functions.raiseError(logger, 'Source is not a folder')
        if not os.path.isdir(self.__dstFolder):
            functions.raiseError(logger, 'Destination is not a folder')        

        self.__dstFolder = os.path.abspath(self.__dstFolder)
        self.__srcFiles = functions.getVidFiles(self.__srcFile)
         
        if os.path.isdir(self.__srcFile):
            self.__srcName = os.path.basename(os.path.basename(self.__srcFile))
            code = functions.unrar(self.__srcFile)
            if code == 0 or code == 20194 or code == 2560:
                self.__srcFiles = functions.getVidFiles(self.__srcFile)
            else:
                # failed.. lets do sfv check
                if(functions.checkSFVPath(self.__srcFile)):
                    self.__srcFiles = functions.getVidFiles(self.__srcFile)
                else:
                    #reset it
                    functions.raiseError(logger, "CRC Errors in the download, deleted the errors and resetting back to pending: %s" % code)

                return
            
            # Check if multi cds.. make sure we have
            cdnum = 1
            for f in os.listdir(self.__srcFile):
                if os.path.isdir(self.__srcFile + "/" + f):
                    name = os.path.basename(f)
                    number = functions.getRegex(name, 'CD([0-9])', 1)
                    if number == None:
                        number = 1
                    if (cdnum < number):
                        cdnum = number
                        
            if str(self.__srcFiles.__len__()) != str(cdnum):
                logger.info('nums: ' + str(cdnum) + ':' + str(self.__srcFiles.__len__()))
                functions.raiseError(logger, 'Not finished downloading')
                
        elif os.path.isfile(self.__srcFile):
            __, ext = os.path.splitext(self.__srcFile)
            if re.match('(?i)\.(mkv|avi|m4v|mpg)', ext):
                self.__srcName = os.path.basename(self.__srcFile)
                self.__srcFiles = [{'src': self.__srcFile, 'dst': None}]
            else:
                functions.raiseError(logger, 'Is not a media file')
                
        if not self.__srcFiles:
            functions.raiseError(logger, 'No media files found')
        test = functions.getMovieInfo(os.path.splitext(os.path.basename(self.__srcFile))[0])
        print test
        self.__movieName, self.__movieYear = functions.getMovieInfo(os.path.splitext(os.path.basename(self.__srcFile))[0])

        if self.__movieYear:
            #We have all the info we need. Move the files.
            self.__moveMovie()
            
        else:
            imdbS = ImdbSearch()
            results = imdbS.best_match(self.__movieName, self.__movieYear)

            if results and results['match'] > 0.70:
                movieObj = ImdbParser()
                print movieObj
                movieObj.parse(results['url']) 
                
                if not movieObj.name:
                    functions.raiseError(logger, 'Unable to get name')
                if not movieObj.year or movieObj.year == 0:
                    functions.raiseError(logger, 'Unable to get year')

                self.__movieName = movieObj.name
                self.__movieYear = movieObj.year

                #We have all the info we need. Move the files.
                self.__moveMovie()

            else:
                functions.raiseError(logger, 'Unable to find movie: ' + self.__movieName + ' on imdb.com')
