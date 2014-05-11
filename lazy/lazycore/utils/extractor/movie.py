from lazycore.models import Imdbcache
import re, logging, os
from django.conf import settings
from flexget.utils.imdb import ImdbSearch, ImdbParser
from lazycore.utils import common
from lazycore.utils.metaparser import MetaParser
from lazycore.exceptions import ExtractException, InvalidFileException, NoMediaFilesFoundException, RenameException

logger = logging.getLogger(__name__)

class MovieRenamer:

    dest_folder = settings.HD

    download_item = None

    def __init__(self, dlitem=None):
        self.download_item = dlitem

    def log(self, msg):
        if self.download_item:
            self.download_item.log(msg)
        else:
            logger.info(msg)

    def _sort_files(self, files):

        renames_files = []
        already_processed = []

        for f in files:

            logger.debug("Sorting %s" % f)

            if f in already_processed:
                logger.debug("File already processed, skipping")
                continue

            file_name = os.path.basename(f)
            file_parser = MetaParser(file_name, type=MetaParser.TYPE_MOVIE)

            if 'cdNumber' in file_parser.details:

                logger.debug("Found Multi CD movie")

                title = file_parser.details['title']

                #we dealing with a CD1, CD2 situiation
                multi_cd_files = []

                for f in files:
                    other_file_parser = MetaParser(os.path.basename(f), type=MetaParser.TYPE_MOVIE)

                    try:

                        #Check if this is a cd type file
                        if not 'cdNumber' in other_file_parser.details:
                            continue

                        #Check if its a type of movie
                        if not other_file_parser.details['type'] == "movie":
                            continue

                        #Ensure its the same movie
                        if not other_file_parser.details['title'] == file_parser.details['title']:
                            continue

                        #DO we have year information? If so lets ensure its the same year
                        if 'year' in file_parser.details:

                            if 'year' not in other_file_parser.details:
                                continue
                            if other_file_parser.details['year'] != file_parser.details['year']:
                                continue

                        #We have a match!
                        already_processed.append(f)
                        multi_cd_files.append(f)
                    except Exception as e:
                        continue
                        logger.exception(e)

                logger.debug("Multi CDs found %s" % multi_cd_files)

                if len(multi_cd_files) > 1:
                    renames_files.append({'parser': file_parser, 'files': multi_cd_files})

            else:
                #lets process this movie file
                renames_files.append({'parser': file_parser, 'files': [f]})

        return renames_files


    def _move_movies(self, movies):

        for movie in movies:

            file_parser = movie['parser']
            files = movie['files']

            #First lets check if we are associated to an IMDB Movie
            if len(movies) == 1 and self.download_item and self.download_item.imdbid:
                #Single movie with 1 file, lets rename it!
                #Ok lets use the data from IMDB Obj
                year = self.download_item.imdbid.year
                title = self.download_item.imdbid.title

                if (None is year or year == "") and 'year' in file_parser.details:
                    year = file_parser.details['year']

                self._do_rename_movie(title, year, files, imdb_id=self.download_item.imdbid.id)

            else:
                try:
                    f_title = None
                    f_year = None

                    if 'year' in file_parser.details:
                        f_year = file_parser.details['year']
                    if 'title' in file_parser.details:
                        f_title = file_parser.details['title']

                    title, year, imdbid = self.get_imdb_details(f_title, f_year)
                    #We have all the info we need. Move the files.
                    self._do_rename_movie(title, year, files, imdb_id=imdbid)
                except RenameException as e:
                    if self.download_item:
                        raise e
                    else:
                        logger.debug("Unable to move %s as %s" % (movie, e))


    def get_imdb_details(self, title, year):
        imdbS = ImdbSearch()
        results = imdbS.best_match(title, year)

        if results and results['match'] > 0.93:
            movie_obj = ImdbParser()
            movie_obj.parse(results['url'])

            if not movie_obj.name:
                raise RenameException('Unable to get name')
            if not movie_obj.year or movie_obj.year == 0:
                raise RenameException('Unable to get year')

            title = movie_obj.name
            year = movie_obj.year
            imdbid = movie_obj.imdb_id.lstrip("tt")

        else:
            raise RenameException('Unable to find movie: %s on imdb.com' % title)

        return title, year, imdbid

    def _do_rename_movie(self, movie_name, movie_year, src_media_files, imdb_id=None):
        movie_full_name = "%s (%s)" % (movie_name, movie_year)
        movie_full_name = common.strip_illegal_chars(movie_full_name)
        dest_folder = os.path.join(self.dest_folder, movie_full_name)

        existing_folders = []

        imdbcache_obj = None

        #Ok we need to make sure the movie does not exist already..
        if imdb_id:
            try:
                imdbcache_obj = Imdbcache.objects.get(id=imdb_id)

                logger.debug("Found existing imdbcache object for movie")

                if os.path.exists(imdbcache_obj.localpath):
                    existing_folders.append(imdbcache_obj.localpath)
                    logger.debug("Found existing folder form imdbcache %s" % imdbcache_obj.localpath)
            except:
                #didnt find it so lets add it..
                try:
                    logger.debug("Didnt find imdbcache object, will add it")
                    imdbcache_obj = Imdbcache()
                    imdbcache_obj.id = int(imdb_id)
                    imdbcache_obj.update_from_imdb()
                    imdbcache_obj.save()
                except:
                    pass

        if os.path.exists(dest_folder):
            #check if not in there already
            found = False
            for f in existing_folders:
                if f == dest_folder:
                    found = True

            if not found:
                existing_folders.append(dest_folder)
                logger.debug("Found existing folder form puporsed dest_folder %s" % dest_folder)

        existing_vid_files = []

        if len(existing_folders) > 0:
            #We have existing movie folders, lets figure out what is the best quality..
            existing_vid_files = []

            for folder in existing_folders:
                vid_files = common.get_video_files(folder)

                for f in vid_files:
                    parser = MetaParser(os.path.basename(f), type=MetaParser.TYPE_MOVIE)

                    if 'cdNumber' in parser.details and parser.details['cdNumber'] != 1:
                        continue
                    else:
                        existing_vid_files.append(f)

            if len(existing_vid_files) == 0:
                self.log("Existing folders but no media files, will delete existing folders")

                for folder in existing_folders:
                    common.delete(folder)


        if len(existing_vid_files) > 0:
            self.log("Found existing media files, need to figure out what is the best quality %s" % existing_vid_files)

            best = existing_vid_files[0]

            for cur_file in existing_vid_files:
                best = common.compare_best_vid_file(cur_file, best)

            #Is the best one existing or belong to this current download item?? (NEW)
            self.log("Best existing video file is %s, now lets compare that quality to this download item" % best)

            best = common.compare_best_vid_file(best, src_media_files[0])

            if best == src_media_files[0]:
                self.log("This download item has the best quality, will delete all other folders/files")

                for folder in existing_folders:
                    common.delete(folder)

            else:
                self.log("Better quality already exists.. wont extract this")
                return

        if len(src_media_files) > 1:
            self.log("Multiple Media files found for movie, must be multi cd")

            #Now lets do the renaming

            move_files = []

            print src_media_files

            for f in src_media_files:
                file_parser = MetaParser(os.path.basename(f), type=MetaParser.TYPE_MOVIE)

                if 'cdNumber' in file_parser.details:
                    ext = os.path.splitext(f)[1][1:].strip()
                    file_name = "%s CD%s.%s" % (os.path.basename(dest_folder), file_parser.details['cdNumber'], ext)
                    dest_file = os.path.join(dest_folder, file_name)
                    move = {"from": f, "to": dest_file}
                    move_files.append(move)

                else:
                    raise RenameException('Multiple files but could not locate CD numbering')

            common.create_path(dest_folder)

            for move_file in move_files:
                self.log("Moving %s to %s" % (move_file['from'], move_file['to']))
                common.move_file(move_file['from'], move_file['to'])
        else:
            common.create_path(dest_folder)
            ext = os.path.splitext(src_media_files[0])[1][1:].strip()
            file_name = "%s.%s" % (os.path.basename(dest_folder), ext)
            dest_file = os.path.join(dest_folder, file_name)
            self.log("Moving %s to %s" % (src_media_files[0], dest_file))
            common.move_file(src_media_files[0], dest_file)

        #Now lets set imdbcache local path..
        if imdbcache_obj:
            imdbcache_obj.localpath = dest_folder
            imdbcache_obj.save()


    def rename(self, files):

        movies = self._sort_files(files)

        if self.download_item:
            download_item_parser = self.download_item.metaparser()

            #If this is a movie (not a pack etc, then we should only have 1 media file)
            if download_item_parser.details['type'] == 'movie':
                #Single Movie
                if len(movies) == 0:
                    raise ExtractException("Didn't find any media files?")

                if len(movies) > 1:
                    raise ExtractException("Detected as a single movie but found multiple media files?")

        self._move_movies(movies)