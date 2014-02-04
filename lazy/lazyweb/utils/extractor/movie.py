from lazyweb.models import DownloadItem
import re, logging, os
from lazyweb import utils
from django.conf import settings
import shutil
from flexget.utils.imdb import ImdbSearch, ImdbParser

logger = logging.getLogger(__name__)


class MovieExtractor():


    #TODO: Need to refactor this code to make it cleaner

    def extract(self, download_item, dest_folder):

        if utils.match_str_regex(settings.MOVIE_PACKS_REGEX, download_item.title) and '.special.' not in download_item.title.lower():
                download_item.log("Movie pack detected")

                #Lets build up the first folder
                files = os.listdir(download_item.localpath)

                if not files or len(files) == 0:
                    msg = 'No folders or files in path %s' % download_item.localpath
                    logger.error(msg)
                    raise Exception(msg)

                for file in files:
                    filePath = os.path.join(download_item.localpath, file)

                    if os.path.isdir(filePath):
                        #Offload rest of processing to the action object
                        new_download_item = DownloadItem()

                        new_download_item.title = file
                        new_download_item.localpath = filePath
                        new_download_item.section = download_item.section

                        self.extract(new_download_item, dest_folder)
                    else:
                        #If its small its prob an nfo so ignore
                        size = os.path.getsize(filePath)
                        if size < 15120:
                            continue
                        else:
                            new_download_item = DownloadItem()
                            title = os.path.basename(filePath)

                            new_download_item.title = title
                            new_download_item.localpath = filePath
                            new_download_item.section = download_item.section

                            movextractor = MovieExtractor()
                            self.extract(new_download_item, dest_folder)

                #So we extracted it all.. lets reutrn true
                return True


        #Now we have an actual movie. lets extract
        dest_folder = os.path.abspath(dest_folder)

        if os.path.isdir(download_item.localpath):
            code = utils.unrar(download_item.localpath)

            if code == 0:
                src_files = utils.get_video_files(download_item.localpath)
            else:
                #failed.. lets do sfv check
                download_item.log('failed extract, lets check the sfv')
                sfvck = utils.check_crc(download_item)

                download_item.log("SFV CHECK " + str(sfvck))

                if(sfvck):
                    src_files = utils.get_video_files(download_item.localpath)
                else:
                    #reset it
                    msg = "CRC Errors in the download, deleted the errors and resetting back to the queue: %s" % code
                    download_item.status = DownloadItem.QUEUE
                    download_item.retries += 1
                    logger.error(msg)
                    raise Exception(msg)

            # Check if multi cds.. make sure we have
            cdnum = 1
            for f in os.listdir(download_item.localpath):
                if os.path.isdir(download_item.localpath + os.sep + f):
                    name = os.path.basename(f)

                    search = re.search('CD([0-9])', name, re.IGNORECASE)

                    number = 1

                    if search:
                        number = search.group(1)

                    if (cdnum < number):
                        cdnum = number

            if str(src_files.__len__()) != str(cdnum):
                msg = 'Not finished downloading'
                logger.error(msg)
                raise Exception(msg)

        elif os.path.isfile(download_item.localpath):
            __, ext = os.path.splitext(download_item.localpath)
            if re.match('(?i)\.(mkv|avi|m4v|mpg)', ext):
                src_files = [{'src': download_item.localpath, 'dst': None}]
            else:
                msg = 'Is not a media file'
                logger.error(msg)
                raise Exception(msg)

        if not src_files:
            msg = 'No media files found'
            logger.error(msg)
            raise Exception(msg)

        movie_name, movie_year = utils.get_movie_info(os.path.splitext(os.path.basename(download_item.localpath))[0])

        if movie_year:
            #We have all the info we need. Move the files.
            self.do_move(download_item, movie_name, movie_year, dest_folder, src_files)

        else:
            imdbS = ImdbSearch()
            results = imdbS.best_match(movie_name, movie_year)

            if results and results['match'] > 0.70:
                movieObj = ImdbParser()

                movieObj.parse(results['url'])

                if not movieObj.name:
                    raise Exception('Unable to get name')
                if not movieObj.year or movieObj.year == 0:
                    raise Exception('Unable to get year')

                movie_name = movieObj.name
                movie_year = movieObj.year

                #We have all the info we need. Move the files.
                self.do_move(download_item, movie_name, movie_year, dest_folder, src_files)

            else:
                msg = 'Unable to find movie: %s on imdb.com' % movie_name
                logger.error(msg)
                raise Exception(msg)

        return True


    def do_move(self, download_item, movie_name, movie_year, dest_folder, src_files):
            download_item.log('Found Movie: ' + movie_name + " (Year: " + str(movie_year) + ")")

            dest_folder = re.sub(settings.ILLEGAL_CHARS_REGEX, "", os.path.abspath(dest_folder + os.sep + movie_name + " (" + str(movie_year) + ")"))

            dest_folder = re.sub(" +", " ", dest_folder)

            if os.path.exists(dest_folder):
                if download_item.section == "XVID":
                    #Movie alraedy exists.. if this is an avi file and its an mkv then dont replace with a lower quality

                    existing_vid_files = utils.get_video_files(dest_folder)

                    if len(existing_vid_files) > 0:
                        download_item.log("Found an existing movie folder, lets make sure we are not replacing with a lower xvid quality")

                        fname, ext = os.path.splitext(existing_vid_files[0]['src'])

                        if ext == ".mkv":
                            download_item.log("Existing movie is in HD lets keep that one")
                            return
                        else:
                            # Delete the old movie
                            download_item.log('Deleting existing movie folder as its a lower quality ' + dest_folder)
                            shutil.rmtree(dest_folder)

            src_files = utils.setup_dest_files(src_files, dest_folder, movie_name + ' (' + str(movie_year) + ')')
            utils.move_files(src_files)