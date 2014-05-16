import re, os, logging, time
from lazycore.utils import common
from lazycore.utils.tvdb_api import Tvdb
from django.conf import settings
from lazycore.models import DownloadItem, TVShowMappings, Tvdbcache
from lazycore.utils.metaparser import MetaParser
from lazycore.exceptions import ExtractException, InvalidFileException, ManuallyFixException, RenameException


logger = logging.getLogger(__name__)

class TVRenamer:

    dest_folder_base = settings.TVHD
    tvdbapi = Tvdb()
    download_item = None

    def __init__(self, dlitem=None):
        self.download_item = dlitem

    def log(self, msg):
        if self.download_item:
            self.download_item.log(msg)
        else:
            logger.info(msg)

    def create_docs_folder(self, path):
        if not os.path.exists(path):
            #create path
            common.create_path(path)

        #check for nfo file
        nfo_file = os.path.join(path, "tvshow.nfo")

        if not os.path.isfile(nfo_file):
            #Lets create it
            with open(nfo_file, 'w') as f:
                f.write("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\" ?>")
                f.write("<tvshow>")
                f.write("    <title>%s</title>" % os.path.basename(path))
                f.write("    <showtitle>%s</showtitle>" % os.path.basename(path))
                f.write("</tvshow>")

    def _move_tvshow_files(self, tvshow_files):

        if self.download_item:
            download_item_parser = self.download_item.metaparser()

            #If this is a tvshow (not a pack etc, then we should only have 1 media file)
            if download_item_parser.details['type'] == 'tvshow':
                #Single show
                if len(tvshow_files) == 0:
                    raise ExtractException("Didn't find any media files?")

                if len(tvshow_files) > 1:
                    raise ExtractException("Detected as a single tvshow but found multiple media files?")


        for tvshow_file in tvshow_files:

            tvshow_file_ep = None
            tvshow_file_season = None
            tvshow_file_metaparser = None
            tvdbcache_obj = None
            ext = os.path.splitext(tvshow_file)[1][1:].strip()

            ep_override = None
            season_override = None

            #Check for overrides
            if self.download_item:
                #This is part of a download item
                tvshow_file_metaparser = self.download_item.metaparser()

                if self.download_item.epoverride > 0:
                    if self.download_item.epoverride > 0:
                        ep_override = self.download_item.epoverride

                    if self.download_item.seasonoverride >= 0:
                        season_override = self.download_item.seasonoverride
            else:
                tvshow_file_metaparser = MetaParser(os.path.basename(tvshow_file))

            #if this is a special then it needs to be manually processed if there is no override
            if 'special' in tvshow_file_metaparser.details:
                if None is ep_override:
                    raise ManuallyFixException("Cannot figure out which special this is on www.thetvdb.com, you need to do it manually")

                if None is season_override:
                    raise ManuallyFixException("Cannot figure out which special this is on www.thetvdb.com, you need to do it manually")

            #Show mappings
            try:
                showmap = TVShowMappings.objects.get(title=tvshow_file_metaparser.details['series'].lower())

                if showmap:
                    if self.download_item:
                        self.download_item.tvdbid = showmap
                    tvdbcache_obj = showmap
            except:
                #none found
                pass

            #Ok lets figure out the tvdbid details
            if self.download_item and self.download_item.tvdbid:
                #We have a linked tvdbcache_obj
                tvdbcache_obj = self.download_item.tvdbid
            else:
                #we need to figure it out
                tvdbcache_obj = self.get_tvdb_details(tvshow_file_metaparser.details['series'])

            #Lets figure out the series_ep and series_season
            if 'season' in tvshow_file_metaparser.details:
                tvshow_file_season = tvshow_file_metaparser.details['season']
            if 'episodeNumber' in tvshow_file_metaparser.details:
                tvshow_file_ep = tvshow_file_metaparser.details['episodeNumber']
            if season_override:
                tvshow_file_season = season_override
            if ep_override:
                tvshow_file_ep = ep_override

            #Ok now lets sort out the file names etc
            #Docos first
            print tvshow_file_metaparser.details
            print tvdbcache_obj

            if 'doco_channel' in tvshow_file_metaparser.details and not tvdbcache_obj:
                #Ok we have a doco that was not found on thetvdb.. lets shove it into the Docs folder
                dest_folder = os.path.join(self.dest_folder_base, tvshow_file_metaparser.details['doco_channel'])
                self.create_docs_folder(dest_folder)

                airdate = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(tvshow_file)))

                tvshow_file_name = tvshow_file_metaparser.details['series']

                if 'title' in tvshow_file_metaparser.details:
                    tvshow_file_name += " %s" % tvshow_file_metaparser.details['title']

                if tvshow_file_season:
                    tvshow_file_name += " S%s" % tvshow_file_season

                if tvshow_file_ep:
                    tvshow_file_name += " E%s" % tvshow_file_ep

                tvshow_file_name = common.strip_illegal_chars(tvshow_file_name)

                tvshow_file_name += " S00E01"
                tvshow_file_nfo_name = "%s.nfo" % tvshow_file_name
                tvshow_file_name += ".%s" % ext

                tvshow_file_nfo_dest = os.path.join(dest_folder, tvshow_file_nfo_name)
                tvshow_file_dest = os.path.join(dest_folder, tvshow_file_name)

                nfo_content = "<episodedetails> \n\
                <title>" + os.path.splitext(tvshow_file_name)[0] + "</title> \n\
                <season>0</season> \n\
                <episode>1</episode> \n\
                <aired>%s</aired> \n\
                <displayseason>0</displayseason>  <!-- For TV show specials, determines how the episode is sorted in the series  --> \n\
                <displayepisode>4096</displayepisode> \n\
                </episodedetails>" % airdate

                nfof = open(tvshow_file_nfo_dest, 'w')
                nfof.write(nfo_content)
                nfof.close()
                self.log('Wrote NFO file %s' % tvshow_file_nfo_dest)

                #Lets do the move..
                if os.path.isfile(tvshow_file_dest):
                    common.delete(tvshow_file_dest)

                common.move_file(tvshow_file, tvshow_file_dest)
                self.log('Moving file: %s to %s' % (tvshow_file, tvshow_file_dest))
                return

            #NOW FOR NORMAL SHOWS
            if not tvdbcache_obj:
                raise RenameException("Unable to find show on tvdb")

            if None is tvshow_file_ep:
                raise RenameException("Unable to figure out the epsiode number")

            if None is tvshow_file_season:
                raise RenameException("Unable to figure out the season number")

            #Lets try convert via thexem
            if 'episodeList' not in tvshow_file_metaparser.details:
                xem_season, xem_ep = self.tvdbapi.get_xem_show_convert(tvdbcache_obj.id, tvshow_file_season, tvshow_file_ep)

                if xem_season is not None and xem_ep is not None:
                    self.log("Found entry on thexem, converted the season and ep to %s x %s" % (xem_season, xem_ep))
                    tvshow_file_season = int(xem_season)
                    tvshow_file_ep = int(xem_ep)

            tvshow_file_ep_name = None

            #lets get the ep name from tvdb
            try:
                show_obj_season = self.tvdbapi[tvdbcache_obj.id][int(tvshow_file_season)]
                if show_obj_season:
                    try:
                        tvshow_file_ep_name = show_obj_season[int(tvshow_file_ep)]['episodename'].encode('ascii', 'ignore')
                        tvshow_file_ep_name = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", tvshow_file_ep_name).strip()
                        tvshow_file_ep_name = tvshow_file_ep_name.replace("/", ".")
                        tvshow_file_ep_name = tvshow_file_ep_name.replace("\\", ".")
                    except:

                        if 'title' in tvshow_file_metaparser and tvshow_file_metaparser['title'] != "":
                            self.log("Found the season but not the ep title on thetvdb.. will use title from the release name")
                            tvshow_file_ep_name = tvshow_file_metaparser['title']
                            tvshow_file_ep_name = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", tvshow_file_ep_name).strip()
                        else:
                            self.log("Found the season but not the ep.. will fake the ep name")
                            tvshow_file_ep_name = 'Episode %s' % tvshow_file_ep
            except:
                pass

            #Lets figure out the series name
            if None is tvshow_file_ep_name:
                raise Exception('Could not find tvshow (TVDB) %s x %s' % (tvshow_file_season, tvshow_file_ep))

            # Now lets move the file
            self.log("Found season %s episode %s title: %s" % (tvshow_file_season, tvshow_file_ep, tvshow_file_ep_name))

            #figure out ep/season name
            tvshow_file_ep_id = ''

            if 'episodeList' in tvshow_file_metaparser.details:
                for ep_num in tvshow_file_metaparser.details['episodeList']:
                    tvshow_file_ep_id += "E" + str(ep_num).zfill(2)
            else:
                tvshow_file_ep_id = "S%sE%s" % (str(tvshow_file_season).zfill(2), str(tvshow_file_ep).zfill(2))

            #Now lets figure out the dest_folder
            if tvdbcache_obj.localpath:
                #we already have a set path..
                dest_folder = tvdbcache_obj.localpath
            else:
                dest_folder = os.path.join(self.dest_folder_base, common.strip_illegal_chars(tvdbcache_obj.title))
                tvdbcache_obj.localpath = dest_folder
                tvdbcache_obj.save()

            season_folder = common.find_season_folder(dest_folder, int(tvshow_file_season))

            if season_folder:
                dest_folder = season_folder
            else:
                if tvshow_file_season == 0:
                    dest_folder = os.path.join(dest_folder, "Specials")
                else:
                    name = "Season%s" % tvshow_file_season
                    dest_folder = os.path.join(dest_folder, name)

            dest_folder = dest_folder.strip()
            common.create_path(dest_folder)

            tvshow_file_dest = "%s - %s - %s.%s" % (common.strip_illegal_chars(tvdbcache_obj.title), tvshow_file_ep_id, common.strip_illegal_chars(tvshow_file_ep_name), ext)
            tvshow_file_dest = os.path.join(dest_folder, tvshow_file_dest)

            self.move_file(tvshow_file, tvshow_file_dest, tvshow_file_season, tvshow_file_ep)

    def move_file(self, src, dest, season, ep):

        #Ok before we move we must check if the ep already exists
        existing_files = common.find_ep_season(os.path.dirname(dest), season, ep)

        b_file = None

        if len(existing_files) > 0:
            self.log("Found %s existing files" % len(existing_files))

            #lets find the best one
            for f in existing_files:
                if b_file:
                    b_file = common.compare_best_vid_file(b_file, f)
                else:
                    b_file = f

            self.log("Best existing (quality) is %s" % b_file)

            #now lets figure out if this release is a better quality
            if src == common.compare_best_vid_file(src, b_file):
                #This is the best quality, lets remove the others
                for f in existing_files:
                    common.delete(f)
            else:
                #better quality exists..
                self.log("NOT MOVING FILE AS BETTER QUALITY EXISTS %s" % b_file)
                return

        #now lets do the move
        common.create_path(os.path.dirname(dest))
        self.log('Moving file: %s to %s' % (src, dest))
        common.move_file(src, dest)



    def get_tvdb_details(self, tvshow_title):

        tvdbcache_obj = None

        try:

            show_obj = self.tvdbapi[tvshow_title]

            if 'id' in show_obj.data:
                found_id = int(show_obj['id'])
                self.log("Found show on tvdb %s" % found_id)

                try:
                    tvdbcache_obj = Tvdbcache.objects.get(id=found_id)

                    if tvdbcache_obj:
                        self.log("Found show in database already %s" % tvdbcache_obj.title)
                except:
                    #not found, lets add it
                    self.log("Adding show to the tvdbcache database")
                    tvdbcache_obj = Tvdbcache()
                    tvdbcache_obj.id = found_id
                    tvdbcache_obj.update_from_tvdb()
        except:
            pass

        return tvdbcache_obj

    def rename(self, tvshow_files):
        self._move_tvshow_files(tvshow_files)