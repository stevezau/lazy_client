__author__ = 'Steve'
import os, logging
from lazyweb.utils.ftpmanager import FTPManager
from lazyweb import utils
from lazyweb.models import Tvdbcache
from lazyweb.utils.tvdb_api import Tvdb
import re
import os
import logging
from datetime import datetime, timedelta
import subprocess
from lazyweb.exceptions import *
from lazyweb.models import DownloadItem
import sys
import pprint
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings


logger = logging.getLogger(__name__)

class TVShowScanner:

    #EP STATUS
    EP_MISSING = "ep_missing"
    DOWNLOADING_EP_FROM_FTP = "downloading_from_ftp"
    EP_ALREADY_PROCESSED = "ep_already_processed"
    FOUND_EP = "found_ep"
    FOUND_EP_TORRENT = "found_ep_torrent"
    EP_FAILED = "failed_ep"
    DIDNT_FIND_EP = "didnt_find_ep"

    #SEASON STATUS
    SEASON_MISSING = "missing"
    WONT_FIX = "wont_fix"
    SEASON_EXISTS = "exists"
    DOWNLOADING_SEASON = "downloading_entire_season"

    #BOTH
    ALREADY_IN_QUEUE = "already_in_queue"


    missing_eps = None
    tvshow_path = None
    tvshow_name = None
    search_names = None

    def __init__(self, tvshow_path):

        #first lets check the tvshow exist
        if not os.path.exists(tvshow_path):
            raise Exception("TVShow path does not exist %s" % tvshow_path)

        self.tvshow_path = tvshow_path
        self.tvshow_name = os.path.basename(tvshow_path)

        tvdbapi = Tvdb(convert_xem=True)

        #Now lets figure out the tvdbid
        try:
            self.tvdbcache_obj = Tvdbcache.objects.get(localpath=self.tvshow_path)

            logger.debug("Found matching tvdbcache item %s" % self.tvdbcache_obj.id)
            if not self.tvdbcache_obj:
                raise Exception("Unable to find a matching tvdbcache for this tvshow path")

            self.tvdbshow_obj = tvdbapi[self.tvdbcache_obj.id]

        except ObjectDoesNotExist:
            #try find via thetvdb
            try:
                self.tvdbshow_obj = tvdbapi[self.tvshow_name]
                self.tvdbcache_obj = Tvdbcache.objects.get(id=int(self.tvdbshow_obj['id']))
                logger.debug("Found matching tvdbcache item %s" % self.tvdbcache_obj.id)
            except:
                #didnt find it.. error out here
                raise Exception("Unable to find the tvdb.com information for this show")

        try:
            self.latest_season = self.get_latest_season()
        except:
            raise Exception("Unable to get latest season")


        self.search_names = self.tvdbcache_obj.names()

    def get_latest_ep(self, season):
        now = datetime.now() - timedelta(days=2)

        for ep in reversed(self.tvdbshow_obj[season].keys()):
                ep_obj = self.tvdbshow_obj[season][ep]

                airedDate = ep_obj['firstaired']

                if airedDate is not None:
                    aired_date = datetime.strptime(airedDate, '%Y-%m-%d')

                    if (now > aired_date):
                        #Found the ep and season
                        return ep
        return 1

    def get_tvshow_missing_report(self, check_seasons=[]):

        if len(check_seasons) == 0:
            #Check all seasons
            check_seasons = self.tvdbshow_obj.keys()

        logger.info("Looking for missing eps in %s" % self.tvshow_path)

        missing = {}

        for cur_season in range(1, self.latest_season + 1):

            #do we want to process this season?
            if cur_season not in check_seasons:
                logger.debug("Wont check season %s" % cur_season)
                continue

            #get latest ep of this season
            tvdb_latest_ep = self.get_latest_ep(cur_season)

            if tvdb_latest_ep == 0:
                tvdb_latest_ep = 1

            season_folder = "Season%s" % cur_season
            season_path = os.path.join(self.tvshow_path, season_folder)

            downloaded_eps = []

            missing[cur_season] = {}

            if not os.path.isdir(season_path):
                missing[cur_season]['status'] = self.SEASON_MISSING
                missing[cur_season]['percent'] = 0
                missing[cur_season]['latest_ep'] = tvdb_latest_ep
            else:
                missing[cur_season]['status'] = self.SEASON_EXISTS

                for season_dir_file in os.listdir(season_path):
                    ep_file = os.path.join(season_path, season_dir_file)

                    if utils.is_video_file(ep_file):
                        season, eps = utils.get_ep_season_from_title(ep_file)

                        if season == cur_season:
                            for ep in eps:
                                downloaded_eps.append(ep)


            missing_eps = []

            ##Now check we have them
            for ep_no in range(1, tvdb_latest_ep + 1):
                if ep_no not in downloaded_eps:
                    if 'eps' not in missing[cur_season]:
                        missing[cur_season]['eps'] = {}

                    missing[cur_season]['eps'][ep_no] = self.EP_MISSING
                    missing_eps.append(ep_no)

            ##Figure out the percent
            if len(downloaded_eps) == 0:
                downloaded_percent = 0
            elif len(missing_eps) == 0:
                downloaded_percent = 100
            else:
                downloaded_eps_total = tvdb_latest_ep - len(missing_eps)
                downloaded_percent = 100 * downloaded_eps_total/tvdb_latest_ep

            missing[cur_season]['percent'] = downloaded_percent

            logger.debug("%s percent of season %s exists." % (downloaded_percent, cur_season))



        return missing


    def get_latest_season(self):
        now = datetime.now() - timedelta(days=2)

        #loop through each season
        for season in reversed(self.tvdbshow_obj.keys()):

            #Lets loop through each ep..
            for ep in reversed(self.tvdbshow_obj[season].keys()):
                ep_obj = self.tvdbshow_obj[season][ep]

                aired_date = ep_obj['firstaired']

                if aired_date is not None:
                    aired_date = datetime.strptime(aired_date, '%Y-%m-%d')

                    if (now > aired_date):
                        #Found the ep and season
                        return int(season)
        return 1

    def _append_error(self, err_msg):
        if not 'errors' in self.missing_eps:
            self.missing_eps['errors'] = []

        self.missing_eps['errors'].append(err_msg)


    def attempt_fix_report(self, ftp_dir=None, check_seasons=[], fix_missing_seasons=False):

        force_seasons = check_seasons

        if len(check_seasons) == 0:
            #Check all seasons
            check_seasons = self.tvdbshow_obj.keys()

        logger.debug("Attempting to fix %s" % self.search_names[0])

        #first we need to get a listing from the FTP so we know whats on there..
        if ftp_dir is None:
            try:
                self.ftp_manager = FTPManager()

                self.ftp_dir = []

                for curfolder, dirs, files in self.ftp_manager.ftpwalk("/TVHD", max_depth=0):
                    for file in files:
                        file_found = str(os.path.join(curfolder, file[0]))
                        self.ftp_dir.append(file_found)

                    for dir in dirs:
                        dir_found = str(os.path.join(curfolder, dir[0]))
                        self.ftp_dir.append(dir_found)

                for curfolder, dirs, files in self.ftp_manager.ftpwalk("/REQUESTS", max_depth=0):
                    for file in files:
                        file_found = str(os.path.join(curfolder, file[0]))
                        self.ftp_dir.append(file_found)

                    for dir in dirs:
                        dir_found = str(os.path.join(curfolder, dir[0]))
                        self.ftp_dir.append(dir_found)

                if len(self.ftp_dir) == 0:
                    raise Exception("Unable to get directory listing from FTP")
            except Exception as e:
                logger.exception(e)
                raise Exception("Unable to get directory listing from FTP: %" % e.message)
        else:
            self.ftp_dir = ftp_dir


        self.missing_eps = self.get_tvshow_missing_report(check_seasons=check_seasons)

        #First lets sort out the whole missing seasons
        missing_whole_seasons = self._get_missing_whole_seasons(force_seasons=force_seasons, fix_missing_seasons=fix_missing_seasons)

        #fix missing season folders
        existing_seasons_in_db = self._get_seasons_in_queue()

        self.__pre_scan = None

        logger.debug("lets check if the seasons are already being downloaded")

        for season in missing_whole_seasons:
            if self._exists_db_season_check(season, existing_seasons_in_db):
                logger.info("Season %s already being downloaded, making sure it will download season %s" % (season, season))
                self._delete_season_from_dict(season)
                self.missing_eps[season] = {}
                self.missing_eps[season]['status'] = self.ALREADY_IN_QUEUE

        logger.debug("Now we have to find the rest of the missing seasons on torrent sites")

        missing_whole_seasons = self._get_missing_whole_seasons(force_seasons=force_seasons, fix_missing_seasons=fix_missing_seasons)

        for season in missing_whole_seasons:
            if self._try_download_season(season):
                logger.debug("Found and downloading season %s" % season)
                self._delete_season_from_dict(season)
                self.missing_eps[season] = {}
                self.missing_eps[season]['status'] = self.DOWNLOADING_SEASON

        # All the seasons are now sorted out.. lets try sort out the inviduial eps.
        check_missing_eps = self.missing_eps.copy()

        #FIRST LETS DO A PRESCAN
        self.ep_pre_scan = None

        for cur_season_no in check_missing_eps:
            cur_season_obj = check_missing_eps[cur_season_no]

            #If it already all exists then ignore
            if 'percent' in cur_season_obj and cur_season_obj['percent'] >= 100:
                #all exists
                logger.debug("The whole season %s exists, skipping" % cur_season_no)
                continue

            if cur_season_obj['status'] != self.SEASON_MISSING:
                if cur_season_obj['status'] == self.SEASON_EXISTS and cur_season_obj['percent'] < 100:
                    pass
                else:
                    logger.debug("Skipping seasons %s as %s" % (cur_season_no, cur_season_obj['status']))
                    continue

            #lets try sort out the inviduial eps.
            logger.debug("Sorting out individual eps on season %s" % cur_season_no)

            already_processed_eps = []
            found = []

            copy_of_missing_eps = cur_season_obj['eps'].copy()


            for ep_no, ep_status in copy_of_missing_eps.items():

                if ep_no in already_processed_eps:
                    logger.info("Skipping ep %s as it was found previously" % ep_no)
                    self._delete_ep_from_dict(cur_season_no, ep_no)
                    found_ep = {"status": self.EP_ALREADY_PROCESSED, "ep_no": ep_no}
                    found.append(found_ep)
                    continue

                #first check if its on the DB already
                if self._ep_exists_in_db(cur_season_no, ep_no):
                    logger.debug("Already in the download queue skipping! %s x %s" % (cur_season_no, ep_no))

                    found_ep = {"status": self.ALREADY_IN_QUEUE, "ep_no": ep_no}
                    found.append(found_ep)
                    continue

                #second lets check the ftp for it
                found_ftp_path = self._ep_exists_on_ftp(cur_season_no, ep_no)

                if found_ftp_path is not None and found_ftp_path != "":
                    self._delete_ep_from_dict(cur_season_no, ep_no)
                    logger.info("Already exists on the ftp.. will download from there %s x %s" % (cur_season_no, ep_no))
                    found_ep = {"status": self.DOWNLOADING_EP_FROM_FTP, "ep_no": ep_no, "ftp_path": found_ftp_path}
                    found.append(found_ep)
                    continue

                logger.debug("Not on ftp.. lets try find it via torrent sites")

                sites = ['scc', 'tl', 'revtt']

                do_continue = False

                for site in sites:
                    try:
                        logger.debug("first check the prescan to try save time")
                        if self.ep_pre_scan is None:
                            logger.debug("doing a prescan for eps")
                            self.ep_pre_scan = self.ftp_manager.getTVTorrentsPreScan(self.search_names)
                            logger.debug("finished doing a prescan for eps")

                        if self.ep_pre_scan is not None:
                            for pre_scan_site, torrents in self.ep_pre_scan.iteritems():
                                for torrent in torrents:
                                    #check season and ep number
                                    try:
                                        pre_scan_season, pre_scan_eps = utils.get_ep_season_from_title(torrent)

                                        if pre_scan_season == cur_season_no:
                                            for pre_scan_ep in pre_scan_eps:
                                                if int(pre_scan_ep) == ep_no:
                                                    logger.info("found match in the pre scan %s %s" % (season,ep_no))
                                                    do_continue = True
                                                    found_ep = {'status': self.FOUND_EP_TORRENT, 'tor_site': pre_scan_site, 'torrent': torrent, 'ep_no': int(ep_no)}
                                                    found.append(found_ep)
                                                    self._delete_ep_from_dict(cur_season_no, ep_no)
                                                    do_continue = True
                                                    break

                                    except:
                                        pass


                        torrentEps, foundEps = self.ftp_manager.getTVTorrents(site, self.search_names, cur_season_no, ep_no)

                        if foundEps:
                            for foundEp in foundEps:
                                already_processed_eps.append(int(foundEp))

                        if len(torrentEps) >= 1:
                            found_ep = {'status': self.FOUND_EP_TORRENT, 'tor_site': site, 'torrent': torrentEps[0], 'ep_no': int(ep_no)}
                            found.append(found_ep)
                            self._delete_ep_from_dict(cur_season_no, ep_no)
                            do_continue = True
                            break
                    except Exception as e:
                        ep_info = str(cur_season_no) + 'x' + str(ep_no)
                        logger.exception("Error searching for ep %s on site site %s because %s" % (ep_info , site, e.message))
                        self._append_error("SHOWERROR: problem getting info for ep %s on site site %s because %s" % (ep_info ,site, e.message))
                        continue

                if do_continue:
                    continue
                else:
                    logger.info("CANNOT FIND  %s x %s  " % (cur_season_no, ep_no))

            check_missing_eps = self.missing_eps.copy()

            #First lets deal with the ones we didnt find
            if len(self._get_missing_eps_from_season(cur_season_no)) > 0:
                logger.info("Hmm we didnt find them all.. lets try get season pack instead..")
                try:
                    get_eps = {}
                    get_eps[cur_season_no] = []

                    #add the missing eps to the get list
                    for ep_no in check_missing_eps[cur_season_no]['eps']:
                        get_eps[cur_season_no].append(ep_no)

                    #add the already found eps to the get list
                    for ep_obj in found:
                        get_eps[cur_season_no].append(ep_obj['ep_no'])

                    if self._try_download_season(cur_season_no, onlyget=get_eps):
                        logger.debug("Download entire season instead of each eps..")
                        self._delete_season_from_dict(cur_season_no)
                        self.missing_eps[cur_season_no] = {}
                        self.missing_eps[cur_season_no]['status'] = self.DOWNLOADING_SEASON
                        continue
                    else:
                        logger.info("didnt get season pack")
                        #Set all eps to didnt find
                        missing = self._get_missing_eps_from_season(cur_season_no)
                        for ep_no in missing:
                            self.missing_eps[cur_season_no]['eps'][ep_no] = self.DIDNT_FIND_EP

                except Exception as e:
                    logger.exception(e)
                    logger.info("Problem searching for season season pack, lets download what we have")

            if found > 0:
                #we found some so lets mark the season as exists
                self.missing_eps[cur_season_no]['status'] = self.SEASON_EXISTS

                for ep_obj in found:

                    ep_no = ep_obj['ep_no']

                    if ep_obj['status'] == self.DOWNLOADING_EP_FROM_FTP:

                        new_download = DownloadItem()
                        new_download.ftppath = ep_obj['ftp_path'].strip()
                        new_download.tvdbid_id = self.tvdbcache_obj.id
                        new_download.save()

                        self._delete_ep_from_dict(cur_season_no, ep_no)
                        self.missing_eps[cur_season_no]['eps'][ep_no] = self.DOWNLOADING_EP_FROM_FTP

                    elif ep_obj['status'] == self.EP_ALREADY_PROCESSED:
                        self._delete_ep_from_dict(cur_season_no, ep_no)
                        self.missing_eps[cur_season_no]['eps'][ep_no] = self.FOUND_EP

                    elif ep_obj['status'] == self.ALREADY_IN_QUEUE:
                        self._delete_ep_from_dict(cur_season_no, ep_no)
                        self.missing_eps[cur_season_no]['eps'][ep_no] = self.ALREADY_IN_QUEUE

                    elif ep_obj['status'] == self.FOUND_EP_TORRENT:
                        try:
                            ftp_path = self.ftp_manager.downloadTVTorrent(ep_obj['tor_site'], ep_obj['torrent'])

                            if ftp_path and ftp_path != '':
                                logger.debug("Adding ep to db %s" % ftp_path)

                                new_download = DownloadItem()
                                new_download.ftppath = ftp_path.strip()
                                new_download.tvdbid_id = self.tvdbcache_obj.id
                                new_download.requested = True
                                new_download.save()

                                self._delete_ep_from_dict(cur_season_no, ep_no)
                                self.missing_eps[cur_season_no]['eps'][ep_no] = self.FOUND_EP_TORRENT

                            else:
                                self._append_error("Failed to download ep %s x %s" % (cur_season_no, ep_no))
                                self._delete_ep_from_dict(cur_season_no, ep_no)
                                self.missing_eps[cur_season_no]['eps'][ep_no] = self.EP_FAILED
                        except Exception as e:
                            logger.exception(e)
                            self._append_error("Failed downloading %s cause: %s" % (ep_obj['torrent'], e.message))
                            logger.debug("failed downloading %s cause: %s" % (ep_obj['torrent'], e.message))
                    else:
                        self._append_error("problem trying to sort out ep %s contact steve as this should not happen" % str(ep_obj))

        return self.missing_eps


    def _delete_ep_from_dict(self, season, ep):
        try:
            del self.missing_eps[season]['eps'][ep]
        except:
            pass

    def _delete_season_eps_from_dict(self, season):
        try:
            del self.missing_eps[season]['eps']
        except:
            pass

    def _delete_season_from_dict(self, season):
        try:
            del self.missing_eps[season]
        except:
            pass

    def _get_missing_eps_from_season(self, season):

        missing = []

        if 'eps' in self.missing_eps[season]:
            for ep_no, status in self.missing_eps[season]['eps'].iteritems():
                if status == self.EP_MISSING:
                    missing.append(ep_no)

        return missing

    def _ep_exists_on_ftp(self, season, ep):

        logger.debug("Checking if ep is on the ftp: %s   %s x %s" % (self.search_names[0], season, ep))

        for ftp_rls in self.ftp_dir:

            ftp_rls_name = os.path.basename(ftp_rls)

            if utils.match_str_regex(settings.TVSHOW_SPECIALS_REGEX, ftp_rls_name):
                continue


            highest_match = 0

            for name in self.search_names:
                similar = utils.compare_torrent_2_show(name, ftp_rls_name)

                if similar > highest_match:
                    highest_match = similar

            if highest_match > 0.93:

                ftp_season_no, ftp_ep_nos = utils.get_ep_season_from_title(ftp_rls_name)

                if int(ftp_season_no) == season:
                    for ftp_ep in ftp_ep_nos:
                        if ep == int(ftp_ep):
                            logger.info("FOUND ep on ftp %s" % ftp_rls)
                            return ftp_rls

        return None

    def _season_exists_on_ftp(self, season):

        logger.debug("Checking if season is on the ftp: %s   %s" % (self.tvshow_name, season))

        for ftp_rls in self.ftp_dir:

            ftp_rls_name = os.path.basename(ftp_rls)

            #there are no seasons in /TVHD
            if ftp_rls.startswith("/TVHD"):
                continue

            if utils.match_str_regex(settings.TVSHOW_SPECIALS_REGEX, ftp_rls_name):
                continue

            #Check if this is a season pack
            is_season_pack = utils.match_str_regex(settings.TVSHOW_SEASON_PACK_REGEX, ftp_rls_name)
            is_multi_season_pack = utils.match_str_regex(settings.TVSHOW_SEASON_MULTI_PACK_REGEX, ftp_rls_name)

            if is_season_pack or is_multi_season_pack:
                highest_match = 0

                for name in self.search_names:
                    similar = utils.compare_torrent_2_show(name, ftp_rls_name)

                    if similar > highest_match:
                        highest_match = similar

                if highest_match > 0.93:
                    ftp_season_nos = utils.get_season_from_title(ftp_rls_name)

                    #multi seasons?
                    if ftp_season_nos:
                        #loop though each of them
                        if season in ftp_season_nos:
                            return ftp_rls, ftp_season_nos
            else:
                continue

        return False, []


    def _add_new_download(self, ftp_path, onlyget=None, requested=False):
        try:
            new_download = DownloadItem()
            new_download.ftppath = ftp_path.strip()
            new_download.tvdbid_id = self.tvdbcache_obj.id
            new_download.requested = requested

            if onlyget:
                for get_season, get_eps in onlyget.iteritems():
                    for get_ep in get_eps:
                        new_download.add_download(get_season, get_ep)

            new_download.save()
        except AlradyExists_Updated:
            logger.debug("Updated existing download")

    def _try_download_season(self, season, onlyget=None):

        #now lets check the ftp for it
        logger.debug("Trying to download season %s, frist lets check the ftp" % season)

        ftp_path, got_seasons = self._season_exists_on_ftp(season)

        if ftp_path:
            logger.debug("Found existing season on the ftp %s" % ftp_path)
            if len(got_seasons) == 1:
                self._add_new_download(ftp_path, onlyget, requested=True)
            else:
                #found multi season
                if onlyget == None:
                    onlyget = {}
                    onlyget[season] = []
                    onlyget[season].append(0)

                    self._add_new_download(ftp_path, onlyget, requested=True)
                else:
                    self._add_new_download(ftp_path, onlyget, requested=True)

            self.ftp_dir.append(ftp_path.strip())
            return True

        #lets check on on the prescan
        if self.__pre_scan == None:
            logger.debug("Doing a prescan for seasons to try speed things up")
            found_scc = self.ftp_manager.getTVTorrentsSeason('scc-archive', self.search_names, 0)
            found_tl = self.ftp_manager.getTVTorrentsSeason('tl-packs', self.search_names, 0)

            self.__pre_scan = {'scc-archive': found_scc, 'tl-packs': found_tl}

            logger.debug("Finished prescan")

        if self.__pre_scan is not None:
            for site in self.__pre_scan:
                logger.debug("looking for season %s in the first preliminary scan on site %s" % (season, site))
                torrents = self.__pre_scan[site]

                #TODO FIND THE BEST MATCH HERE..
                for torrent in torrents:
                    found_seasons = utils.get_season_from_title(torrent)

                    if season in found_seasons:
                        logger.debug("looks like we found the season (season prescan scan) %s in %s" % (season, torrent))

                        seasonPath = self.ftp_manager.downloadTVSeasonTorrent(site, torrent)

                        if seasonPath is not False and seasonPath != '':
                            if len(got_seasons) == 1:
                                self._add_new_download(seasonPath, onlyget, requested=True)
                            else:
                                #found multi season
                                if onlyget == None:
                                    onlyget = {}
                                    onlyget[season] = []
                                    onlyget[season].append(0)

                                    self._add_new_download(seasonPath, onlyget, requested=True)
                                else:
                                    self._add_new_download(seasonPath, onlyget, requested=True)

                            self.ftp_dir.append(seasonPath.strip())
                            return True

        logger.debug("Didnt find it via the prescan, Lets try find it via each torrent site")

        sites = ['scc-archive', 'revtt', 'tl']

        for site in sites:
            logger.debug("Looking for season pack on %s" % site)

            try:
                torrentSeasons = self.ftp_manager.getTVTorrentsSeason(site, self.search_names, season)
            except Exception as e:
                logger.exception(e)
                logger.info("Error when trying to get torrent listing from site %s... %s" % (site, e.message))
                continue

            if len(torrentSeasons) >= 1:
                #Lets find the best match! we prefer a single season
                bestMatch = ''
                smallestSize = 0

                for torrent in torrentSeasons:
                    seasons = utils.get_season_from_title(torrent)

                    if len(seasons) == 1:
                        bestMatch = torrent
                        break
                    else:
                        if smallestSize > len(seasons):
                            bestMatch = torrent

                if bestMatch == '':
                    bestMatch = torrentSeasons[0]

                try:
                    logger.info("Telling FTP to download from %s in requests %s" % (site, bestMatch))

                    seasonPath = self.ftp_manager.downloadTVSeasonTorrent(site, bestMatch)

                    if seasonPath is not False and seasonPath != '':
                        got_seasons = utils.get_season_from_title(bestMatch)

                        if len(got_seasons) == 1:
                            self._add_new_download(seasonPath, onlyget, requested=True)
                        else:
                            #found multi season
                            if onlyget == None:
                                onlyget = {}
                                onlyget[season] = []
                                onlyget[season].append(0)

                                self._add_new_download(seasonPath, onlyget, requested=True)
                            else:
                                self._add_new_download(seasonPath, onlyget, requested=True)

                        self.ftp_dir.append(seasonPath.strip())
                        return True
                    else:
                        return False
                except Exception as e:
                    logger.exception(e)
                    logger.debug("Error download season pack %s because %s" % (bestMatch, e.message))
                    return False


        return False


    def _ep_exists_in_db(self, season, ep):
        items = DownloadItem.objects.all().exclude(status=DownloadItem.COMPLETE)

        for entry in items:

            highest_match = 0

            for name in self.search_names:
                similar = utils.compare_torrent_2_show(name, entry.title)

                if similar > highest_match:
                    highest_match = similar


            if highest_match > 0.93:

                entry_season, entry_eps = utils.get_ep_season_from_title(entry.title)

                if entry_season == season:
                    for epNo in entry_eps:
                        if epNo == ep:
                            return True

        return False


    def _exists_db_season_check(self, season, existing_seasons_in_db):
        #lets check if its in the db already
        for entry in existing_seasons_in_db:

            if utils.match_str_regex(settings.TVSHOW_SPECIALS_REGEX, entry.title):
                continue

            existing_seasons = utils.get_season_from_title(entry.title)

            for existing_season in existing_seasons:
                if existing_season == season:
                    if len(existing_seasons) > 1:
                        if entry.onlyget:
                            #make sure this season is in the downloading seasons.. if not lets add it
                            logger.debug("Found multi season %s in the queue already on torrent %s" % (season, entry.title))

                            downloading = False

                            for get_season, get_eps in entry.onlyget:
                                if get_season == season:
                                    for get_ep in get_eps:
                                        if get_ep == 0:
                                            #we are getting it..
                                            logger.debug("Yep we are already downloading the season..")
                                            downloading = True
                                            break

                            #We are not downloading it, lets add it
                            if not downloading:
                                entry.add_download(season, 0)
                        else:
                            #we are getting the whole thing..
                            logger.debug("Found existing season %s being downloaded in queue already %s" % (season, entry.title))
                            return True
                    else:
                        logger.debug("Found existing season %s being downloaded in queue already %s" % (season, entry.title))
                        return True

                    return True
        return False


    def _get_missing_whole_seasons(self, force_seasons=[], fix_missing_seasons=False):

        missing_seasons = []

        if self.missing_eps is None:
            self.missing_eps = self.get_tvshow_missing_report()
            missing_eps = self.missing_eps.copy()
        else:
            missing_eps = self.missing_eps.copy()

        for cur_season_no in missing_eps:

            cur_season = self.missing_eps[cur_season_no]

            if cur_season['status'] == self.SEASON_EXISTS or cur_season['status'] == self.SEASON_MISSING:

                if cur_season['status'] == self.SEASON_EXISTS and cur_season['percent'] < 50:
                    missing_seasons.append(cur_season_no)
                    continue

                if cur_season['status'] == self.SEASON_EXISTS:
                    if fix_missing_seasons:
                        missing_seasons.append(cur_season_no)
                else:
                    if cur_season_no in force_seasons:
                        missing_seasons.append(cur_season_no)
                    else:
                        logger.debug("Skipping season %s as we are not meant to fix it" % cur_season_no)
                        self._delete_season_eps_from_dict(cur_season_no)
                        self.missing_eps[cur_season_no]['status'] = self.WONT_FIX


        return missing_seasons


    def _get_seasons_in_queue(self):
        found = []

        items = DownloadItem.objects.all().exclude(status=DownloadItem.COMPLETE)

        for entry in items:
            #loop through the series names for a match

            highest_match = 0

            for name in self.search_names:
                similar = utils.compare_torrent_2_show(name, entry.title)

                if similar > highest_match:
                    highest_match = similar

            if highest_match >= 0.93:
                #IS this just a season
                if utils.match_str_regex(settings.TVSHOW_SEASON_PACK_REGEX, entry.title) or utils.match_str_regex(settings.TVSHOW_SEASON_MULTI_PACK_REGEX, entry.title):
                    found.append(entry)

        return found