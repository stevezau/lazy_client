__author__ = 'Steve'
from django.conf import settings
import os
from lazy_client_core.models import Job
from lazy_client_core.utils.missingscanner.tvshow import TVShow
from celery import task
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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

@task(bind=True)
def report_all():
    #Store results in db as this report can take a while to run
    job = Job()

    job.title = "Report ALL Shows Missing"
    job.save()

    report = {}

    for dir in os.listdir(settings.TV_PATH):

        tvshow_path = os.path.join(settings.TV_PATH, dir)

        try:
            scanner = TVShow(tvshow_path)
            report[dir] = scanner.get_tvshow_missing_report()

        except Exception as e:
            logger.exception(e)
            logger
            error = [e.message]
            report[dir] = {}
            report[dir]['errors'] = error

        job.report = report
        job.save()

    job.finishdate = datetime.now()
    job.report = report
    job.save()


def show_report(tvshow_path):
    report = {}

    try:
        tvshow = TVShow(tvshow_path)

        #Lets get the missing eps
        missing = tvshow.get_missing()

        for season in tvshow.get_all_seasons():
            missing_eps = tvshow.get_missing_eps_season(season)
            existing_eps = tvshow.get_existing_eps(season)
            download_eps

        report[os.path.basename(tvshow_path)] = scanner.get_tvshow_missing_report()
    except Exception as e:
        logger.exception(e)
        error = [e.message]
        report[os.path.basename(tvshow_path)] = {}
        report[os.path.basename(tvshow_path)]['errors'] = error

    return report

@task(bind=True)
def fix_all():
    job = Job()
    job.title = "Fix all shows"
    job.save()

    report = {}

    for dir in os.listdir(settings.TV_PATH):

        tvshow_path = os.path.join(settings.TV_PATH, dir)

        try:
            scanner = TVShow(tvshow_path)
            report[dir] = scanner.attempt_fix_report()

        except Exception as e:
            logger.exception(e)
            error = [e.message]
            report[dir] = {}
            report[dir]['errors'] = error

        job.report = report
        job.save()

    job.finishdate = datetime.now()
    job.report = report
    job.save()

@task(bind=True)
def fix_show(self, tvshow_path, fix={}):
    job = Job()
    job.title = "%s Fix seasons %s" % (os.path.basename(tvshow_path), fix)
    job.save()

    report = {}

    try:
        job.log("Attempting to fix %s" % self.search_names[0])
        tvshow = TVShow(tvshow_path)

        #If none specified then try fix everything.. (all seasons, eps)
        if len(fix) == 0:
            for season in tvshow.get_all_seasons():
                fix[season] = [0]

        tvshow_missing = self.get_missing(check_seasons=fix.keys())

        #Now lets compare whats missing vs what we are trying to fix...
        for season, eps in tvshow_missing.iteritems():
            if season not in fix.keys():
                job.log("Won't fix %s as it appears all the eps actually exist" % season)
                continue
            for ep in eps:
                pass

        for season in tvshow_missing:
            job.log("Season %s is missing " % season['eps'].keys())

        #First lets sort out the whole missing seasons
        missing_whole_seasons = self._get_missing_whole_seasons(force_seasons=force_seasons, fix_missing_seasons=fix_missing_seasons)

        #fix missing season folders
        existing_seasons_in_db = self._get_seasons_in_queue()

        self.__pre_scan = None

        self.log("lets check if the seasons are already being downloaded")

        for season in missing_whole_seasons:
            if self._exists_db_season_check(season, existing_seasons_in_db):
                self.log("Season %s already being downloaded, making sure it will download season %s" % (season, season))
                self._delete_season_from_dict(season)
                self.missing_eps[season] = {}
                self.missing_eps[season]['status'] = self.ALREADY_IN_QUEUE

        missing_whole_seasons = self._get_missing_whole_seasons(force_seasons=force_seasons, fix_missing_seasons=fix_missing_seasons)

        self.log("Now we have to find the rest of the missing seasons via the server.. " % missing_whole_seasons)

        for season in missing_whole_seasons:
            if self._try_download_season(season):
                self.log("Found and downloading season %s" % season)
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
                            self.ep_pre_scan = ftpmanager.getTVTorrentsPreScan(self.search_names)
                            logger.debug("finished doing a prescan for eps")

                        if self.ep_pre_scan is not None:
                            do_break = False

                            for pre_scan_site, torrents in self.ep_pre_scan.iteritems():
                                for torrent in torrents:
                                    #check season and ep number
                                    try:
                                        parser = metaparser.get_parser_cache(torrent, type=metaparser.TYPE_TVSHOW)
                                        pre_scan_season = parser.get_season()
                                        pre_scan_eps = parser.get_eps()

                                        if pre_scan_season == cur_season_no:
                                            for pre_scan_ep in pre_scan_eps:
                                                if int(pre_scan_ep) == ep_no:
                                                    logger.info("found match in the pre scan %s %s" % (season,ep_no))
                                                    do_continue = True
                                                    do_break = True
                                                    found_ep = {'status': self.FOUND_EP_TORRENT, 'tor_site': pre_scan_site, 'torrent': torrent, 'ep_no': int(ep_no)}
                                                    found.append(found_ep)
                                                    self._delete_ep_from_dict(cur_season_no, ep_no)
                                                    break

                                    except:
                                        pass
                            if do_break:
                                break

                        torrentEps, foundEps = ftpmanager.getTVTorrents(site, self.search_names, cur_season_no, ep_no)

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
                            #TODO: EXception checking and none checking
                            ftp_path = ftpmanager.download_torrent(ep_obj['tor_site'], ep_obj['torrent'], gettv=True)

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








        report[os.path.basename(tvshow_path)] = scanner.attempt_fix_report(check_seasons=seasons)
    except Exception as e:
        logger.exception(e)
        error = [e.message]
        report[os.path.basename(tvshow_path)] = {}
        report[os.path.basename(tvshow_path)]['errors'] = error

    job.report = report
    job.finishdate = datetime.now()
    job.save()