import re, subprocess, shutil, os, logging, time
from lazyweb.utils.tvdb_api import Tvdb
from django.conf import settings
from lazyweb import utils
from lazyweb.models import DownloadItem, TVShowMappings, Tvdbcache
import difflib

logger = logging.getLogger(__name__)

class TVExtractor:

    tvdbapi = Tvdb()

    #TODO: Need to refactor this code to make it cleaner

    def move_file(self, download_item, file):

        dst = file['dst']
        src = file['src']
        __, ext = os.path.splitext(src)

        ep = None
        season = None

        if 'ep' in file:
            ep = file['ep']

        if 'season' in file:
            season = file['season']

        if ep and season:
            #Does it already exist?
            logger.debug("Checking if season/ep already exist within %s" % os.path.dirname(dst))
            existing_files = utils.find_ep_season(os.path.dirname(dst), season, ep)
        else:
            logger.debug("Checking if files already exist within %s" % os.path.dirname(dst))
            existing_files = utils.find_exist_quality(dst)

        download_item.log("Found %s existing files" % len(existing_files))

        b_file = None
        
        if len(existing_files) > 0:
            #lets find the best one
            for f in existing_files:
                if b_file:
                    b_file = utils.compare_best_vid_file(b_file, f)
                else:
                    b_file = f
        else:
            b_file = src

        download_item.log("Best existing (quality) is %s" % b_file)

        #now lets figure out if this release is a better quality
        logger.debug(src)
        logger.debug(b_file)
        logger.debug(utils.compare_best_vid_file(src, b_file))

        if src == utils.compare_best_vid_file(src, b_file):
            #This is the best quality, lets remove the others
            for delfile in existing_files:
                os.remove(delfile)

            #now lets do the move
            utils.create_path(os.path.abspath(os.path.join(dst, '..')))
            shutil.move(src, dst)
            download_item.log('Moving file: ' + os.path.basename(src) + ' to: ' + dst)
        else:
            #better quality exists..
            download_item.log('NOT MOVING FILE AS BETTER QUALITY EXISTS file: ' + os.path.basename(src) + ' to: ' + dst)


    def extract(self, download_item, dest_folder):

        name = os.path.basename(download_item.localpath)

        download_item.log("Start extraction")

        if os.path.isdir(download_item.localpath) and utils.match_str_regex(settings.SAMPLES_REGEX, download_item.title):
            download_item.log("skipping sample folder %s" % download_item.title)
            return True

        has_override = False
        if download_item.epoverride > 0:
            has_override = True


        if os.path.isdir(download_item.localpath):

            if utils.match_str_regex(settings.TVSHOW_SEASON_MULTI_PACK_REGEX, download_item.title) and not has_override:

                download_item.log("Multi Season pack detected")

                #Lets build up the first folder
                files = os.walk(download_item.localpath).next()[1]

                if not files or len(files) == 0:
                    msg = 'No folders or files in path %s' % download_item.localpath
                    logger.error(msg)
                    raise Exception(msg)

                for file in files:
                    file_path = os.path.join(download_item.localpath, file)

                    if os.path.isdir(file_path):
                        #Offload rest of processing to the action object

                        new_download_item = DownloadItem()

                        new_download_item.title = file
                        new_download_item.localpath = file_path
                        new_download_item.section = download_item.section
                        new_download_item.ftppath = download_item.ftppath.strip() + os.sep + os.path.basename(file_path)
                        new_download_item.tvdbid = download_item.tvdbid
                        new_download_item.id = download_item.id

                        if self.extract(new_download_item, dest_folder):
                            shutil.rmtree(new_download_item.localpath)

                if os.path.exists(download_item.localpath):
                    return True

            elif utils.match_str_regex(settings.TVSHOW_SEASON_PACK_REGEX, download_item.title) and '.special.' not in download_item.title.lower() and not has_override:
                download_item.log("Season pack detected")

                #Lets build up the first folder
                files = os.listdir(download_item.localpath)

                if not files or len(files) == 0:
                    msg = 'No folders or files in path %s' % download_item.localpath
                    logger.error(msg)
                    raise Exception(msg)

                for file in files:
                    file_path = os.path.join(download_item.localpath, file)

                    if os.path.isdir(file_path):

                        #Offload rest of processing to the action object

                        new_download_item = DownloadItem()

                        new_download_item.title = file
                        new_download_item.localpath = file_path
                        new_download_item.ftppath = download_item.ftppath.strip() + os.sep + os.path.basename(file_path)
                        new_download_item.section = download_item.section
                        new_download_item.tvdbid = download_item.tvdbid
                        new_download_item.id = download_item.id

                        if self.extract(new_download_item, dest_folder):
                            shutil.rmtree(new_download_item.localpath)
                    else:
                        #If its small its prob an nfo so ignore
                        size = os.path.getsize(file_path)
                        if size < 15120:
                            continue
                        else:
                            new_download_item = DownloadItem()
                            title = os.path.basename(file_path)

                            new_download_item.title = title
                            new_download_item.localpath = file_path
                            new_download_item.section = download_item.section
                            new_download_item.tvdbid = download_item.tvdbid
                            new_download_item.id = download_item.id

                            self.extract(new_download_item, dest_folder)

                if os.path.exists(download_item.localpath):
                    return True

            else:
                code = utils.unrar(download_item.localpath)

                #Is this part of a season pack?
                parent_dir = os.path.basename(os.path.dirname(download_item.localpath))

                if code == 0:
                    src_files = utils.get_video_files(download_item.localpath)
                else:
                    download_item.log('failed extract err %s, lets check the sfv' % code)
                    sfvck = utils.check_crc(download_item)

                    download_item.log("SFV CHECK " + str(sfvck))

                    if sfvck:
                        #SFV passed, lets get vid files.. maybe it was extracted previously
                        src_files = utils.get_video_files(download_item.localpath)
                    else:
                        if utils.match_str_regex(settings.TVSHOW_SEASON_PACK_REGEX, parent_dir) or utils.match_str_regex(settings.TVSHOW_SEASON_MULTI_PACK_REGEX, parent_dir):
                            download_item.log("SFV check had errors, we cant set this to pending or it will download the whole thing again, it has been added as a seperate download")

                            mv_path = settings.TVHD_TEMP

                            #move download to the temp folder
                            shutil.move(download_item.localpath, mv_path)

                            new_download_item = DownloadItem()
                            new_download_item.tvdbid = download_item.tvdbid
                            new_download_item.imdbid = download_item.imdbid
                            new_download_item.section = download_item.section
                            new_download_item.ftppath = download_item.ftppath

                            new_download_item.save()
                            return

                        else:
                            msg = "CRC Errors in the download, deleted the errors and resetting back to the queue: %s" % code
                            download_item.status = DownloadItem.QUEUE
                            download_item.retries += 1
                            logger.error(msg)
                            raise Exception(msg)

        elif os.path.isfile(download_item.localpath):
            __, ext = os.path.splitext(download_item.localpath)
            if re.match('(?i)\.(mkv|avi|m4v|mpg|mp4)', ext):
                src_files = [{'src': download_item.localpath}]
            else:
                raise Exception('Is not a media file')

        if not src_files:
            raise Exception('No media files found')

        if len(src_files) > 1:
            raise Exception('Multiple video files found within release %s' % src_files)

        show_vid_file = src_files[0]

        if utils.match_str_regex(settings.TVSHOW_REGEX, download_item.title) or download_item.tvdbid is not None:
            #This is a normal tvshow..
            title = download_item.title

            if utils.match_str_regex(settings.TVSHOW_SPECIALS_REGEX, download_item.title) or utils.match_str_regex(settings.TVSHOW_SEASON_PACK_REGEX, download_item.title):
                if re.match('(?i).+S[0-9][0-9]E[0-9][0-9].+', download_item.title):
                    pass
                else:
                    if download_item.epoverride > 0 and download_item.seasonoverride >= 0:
                        #lets fake the ep
                        title = re.sub('\.S[0-9][0-9]\.', '.S01E01.', title)
                    else:
                        msg = "Cannot figure out which special this is on www.thetvdb.com, you need to do it manually"
                        download_item.status = DownloadItem.ERROR
                        download_item.message = msg
                        download_item.save()
                        raise Exception(msg)

            #We need to strip out nat geo etc from docos title
            if utils.match_str_regex(settings.DOCOS_REGEX, download_item.title):
                title = utils.replace_regex(settings.DOCOS_REGEX, download_item.title, "")
                parser = utils.get_series_info(title)
            else:
                parser = utils.get_series_info(title)

            if parser:
                series_name = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", parser.name).strip()
                series_name = re.sub(" +", " ", series_name).strip()

                series_season = str(parser.season).zfill(2)
                series_ep = str(parser.episode).zfill(2)
            else:
                raise Exception("Unable to get series info")

            try:
                showmap = TVShowMappings.objects.get(title=series_name.lower())
                if showmap:
                    download_item.tvdbid = showmap.tvdbid
            except:
                #none found
                pass

            #Do we have a linked tvdbid?
            if download_item.tvdbid:
                series_name = download_item.tvdbid.title

                series_name = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", series_name).strip()
                series_name = re.sub(" +", " ", series_name).strip()

            else:
                #lets try find it
                show_obj = self.tvdbapi[series_name]

                if 'id' in show_obj.data:
                    found_id = int(show_obj['id'])
                    download_item.log("Found show on tvdb %s" % found_id)

                    try:
                        existing_tvdb = Tvdbcache.objects.get(id=found_id)

                        if existing_tvdb:
                            download_item.log("Found show in database already %s" % existing_tvdb)
                            download_item.tvdbid_id = existing_tvdb.id
                    except:
                        #not found, lets add it
                        download_item.log("Adding show to the tvdbcache database")
                        new_tvdb = Tvdbcache()
                        new_tvdb.id = found_id
                        new_tvdb.update_from_tvdb()
                        download_item.tvdbid_id = new_tvdb.id
                else:
                    raise Exception("Could not find show: %s via thetvdb.com" % series_name)

            if download_item.epoverride > 0:
                if download_item.epoverride > 0:
                    series_ep = download_item.epoverride

                if download_item.seasonoverride >= 0:
                    series_season = download_item.seasonoverride

            else:
                #Lets try convert via thexem
                xem_season, xem_ep = self.tvdbapi.get_xem_show_convert(download_item.tvdbid_id, (series_season), int(series_ep))

                if xem_season is not None and xem_ep is not None:
                    download_item.log("Found entry on thexem, converted the season and ep to %s x %s" % (xem_season, xem_ep))
                    logger.debug(series_season)
                    series_season = str(xem_season)
                    series_ep = str(xem_ep)

            logger.debug("Season %s Ep %s" % (series_season, series_ep))

            #Now lets do the move
            if download_item.tvdbid_id:

                series_ep_name = None

                #lets get the ep name from tvdb
                try:
                    show_obj_season = self.tvdbapi[download_item.tvdbid_id][int(series_season)]

                    if show_obj_season:
                        try:
                            series_ep_name = utils.remove_unicode(show_obj_season[int(series_ep)]['episodename'])
                            series_ep_name = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", series_ep_name).strip()
                            series_ep_name = series_ep_name.replace("/", ".")
                            series_ep_name = series_ep_name.replace("\\", ".")
                        except:
                            download_item.log("Found the season but not the ep.. will fake the ep name")
                            series_ep_name = 'Episode %s' % series_ep
                except:
                    raise Exception('Could not find tvshow (TVDB) %s x %s' % (series_season, series_ep))

                # Now lets move the file
                download_item.log("Found season %s episode %s title: %s" % (series_season, series_ep, series_ep_name))

                #IS this a multiep
                multi = re.search("(?i)S([0-9]+)(E[0-9]+[E0-9]+).+", download_item.title)

                ep_id = 'E' + str(series_ep)

                if multi:
                    #we have a multi
                    ep_list = re.split("(?i)E", multi.group(2))

                    ep_id = ''

                    for ep_num in ep_list:
                        if ep_num != '':
                            ep_id += "E" + ep_num

                season_folder = utils.find_season_folder(dest_folder, int(series_season))

                if not season_folder:
                    season_folder = "Season" + str(series_season).lstrip("0")

                if download_item.tvdbid.localpath:
                    dest_folder_base = download_item.tvdbid.localpath
                else:
                    series_folder_name = utils.remove_unicode(series_name).strip()

                    dest_folder_base = os.path.abspath(dest_folder + os.sep + series_folder_name)
                    download_item.tvdbid.localpath = dest_folder_base
                    download_item.tvdbid.save()

                if int(series_season) == 0:
                    dest_folder = os.path.abspath(dest_folder_base + os.sep + "Specials")
                else:
                    dest_folder = os.path.abspath(dest_folder_base + os.sep + season_folder)

                dest_folder = dest_folder.strip()

                utils.create_path(dest_folder)

                ep_name = series_name + ' - ' + 'S' + str(series_season) + ep_id + ' - ' + series_ep_name

                __, ext = os.path.splitext(show_vid_file['src'])
                show_vid_file['dst'] = os.path.abspath(dest_folder + "/" + ep_name + ext)
                show_vid_file['season'] = int(series_season)
                show_vid_file['ep'] = int(series_ep)

                download_item.log(show_vid_file)

                self.move_file(download_item, show_vid_file)

                return True

        elif re.match('(?i)^(History\.Channel|Discovery\.Channel|National\.Geographic).+', download_item.title):
            #We have a doco, we treat the title as a movie
            series_name, __ = utils.get_movie_info(download_item.title)

            doco_folder = utils.get_regex(series_name, '(?i)(National Geographic Wild|National Geographic|Discovery Channel|History Channel)', 1)

            if not doco_folder:
                raise Exception('Unable to figure out the type of doco')

            dest_folder = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", os.path.abspath(dest_folder + os.sep + doco_folder + ' Docos'))
            dest_folder = re.sub(" +", " ", dest_folder)

            utils.create_path(dest_folder)

            series_name = re.sub("(?i)National Geographic|Discovery Channel|History Channel", "", series_name).strip()

            download_item.log('Found ' + doco_folder + ' Doco: ' + series_name)

            airdate = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(show_vid_file['src'])))

            __, ext = os.path.splitext(show_vid_file['src'])
            show_vid_file['dst'] = os.path.abspath(dest_folder + "/" + series_name + ' S00E01' + ext)

            nfo_file = os.path.abspath(dest_folder + os.sep + series_name + " S00E01.nfo")

            nfo_content = "<episodedetails> \n\
            <title>" + series_name  + "</title> \n\
            <season>0</season> \n\
            <episode>1</episode> \n\
            <aired>%s</aired> \n\
            <displayseason>0</displayseason>  <!-- For TV show specials, determines how the episode is sorted in the series  --> \n\
            <displayepisode>4096</displayepisode> \n\
            </episodedetails>" % airdate

            nfof = open(nfo_file, 'w')
            nfof.write(nfo_content)
            nfof.close()
            download_item.log('Wrote NFO file ' + nfo_file)

            self.move_file(download_item, show_vid_file)

            return True

        else:
            raise Exception("Unable to detect this show type")
