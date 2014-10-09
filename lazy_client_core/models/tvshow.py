from __future__ import division

from datetime import timedelta
import urllib2
import logging
import os
from datetime import datetime

import inspect
from picklefield.fields import PickledObjectField
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from lazy_client_core.utils import common
from PIL import Image
from lazy_common import utils

from lazy_client_core.utils.common import OverwriteStorage
from lazy_common.tvdb_api import Tvdb
from django.db import models
from lazy_common import metaparser

logger = logging.getLogger(__name__)


class TVShowMappings(models.Model):
    class Meta:
        """ Meta """
        db_table = 'tvshowmappings'
        ordering = ['-id']
        app_label = 'lazy_client_core'

    title = models.CharField(max_length=150, db_index=True, unique=True)
    tvdbid = models.ForeignKey('TVShow', on_delete=models.DO_NOTHING)


@receiver(pre_save, sender=TVShowMappings)
def create_tvdb_on_add(sender, instance, **kwargs):

    instance.title = instance.title.lower()

    if instance.id is None:
        logger.debug("Adding a new tv mapping %s" % instance.title)

        #lets look for existing tvdbshow.. if not add it and get the details from tvdb.com
        try:
            existing = TVShow.objects.get(id=instance.tvdbid_id)

            if existing:
                logger.debug("Found existing tvdb record")
                pass
        except:
            logger.debug("Didnt find tvdb record, adding a new one")
            new = TVShow()
            new.id = instance.tvdbid_id
            new.update_from_tvdb()


class TVShowExcpetion():
    """
    """



class TVShow(models.Model):

    class Meta:
        db_table = 'tvdbcache'
        app_label = 'lazy_client_core'

    def __unicode__(self):
        return self.title

    title = models.CharField(max_length=200, db_index=True)
    posterimg = models.ImageField(upload_to=".", storage=OverwriteStorage(), blank=True, null=True)
    networks = models.CharField(max_length=50, blank=True, null=True)
    genres = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(max_length=255, blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)
    imdbid = models.ForeignKey('Movie', blank=True, null=True, on_delete=models.DO_NOTHING)
    localpath = models.CharField(max_length=255, blank=True, null=True)
    alt_names = PickledObjectField(blank=True, null=True)
    ignored = models.BooleanField(default=False)
    favorite = models.BooleanField(default=False)
    fix_report = PickledObjectField()

    tvdbapi = Tvdb(convert_xem=True)
    tvdb_obj = None

    @staticmethod
    def get_by_path(tvshow_path):
        tvshow_path = os.path.normpath(tvshow_path)

        #First lets search by path
        try:
            tvshow_obj = TVShow.objects.get(tvshow_path)
            logger.debug("Found matching tvshow item %s" % tvshow_obj.title)
            return tvshow_obj
        except ObjectDoesNotExist:
            pass

        #Lets try find it by ID on TheTVDB.com
        try:
            tvdbapi = Tvdb(convert_xem=True)
            tvdb_obj = tvdbapi[os.path.basename(tvshow_path)]
            tvdbcache_obj = TVShow.objects.get(id=tvdb_obj)
            logger.debug("Found matching tvdbcache item %s" % tvdbcache_obj.id)
            return tvdbcache_obj
        except:
            pass

        raise Exception("Didn't find matchin tvshow object")

    @staticmethod
    def update_favs():
        tvdbapi = Tvdb()
        tvdbfavs = tvdbapi.get_favs()

        if tvdbfavs and len(tvdbfavs) > 0:
            #now lets sort them all out
            for tvdbfav in tvdbfavs:
                try:
                    tvshow = TVShow.objects.get(id=tvdbfav)
                    tvshow.favorite = True
                    tvshow.save()
                except ObjectDoesNotExist:
                    #not found, lets add it
                    tvshow = TVShow()
                    tvshow.id = tvdbfav
                    tvshow.update_from_tvdb()
                    tvshow.favorite = True
                    tvshow.save()

            #now remove favs that should not be there
            for tvshow in TVShow.objects.filter(favorite=True):
                if tvshow.id not in tvdbfavs:
                    logger.info("Removing show as fav as it was not marked as fav in thetvdb.com")
                    tvshow.favorite = False
                    tvshow.save()

    def set_favorite(self, status):
        if status:
            self.tvdbapi.add_fav(self.id)
            self.favorite = True
        else:
            self.tvdbapi.del_fav(self.id)
            self.favorite = False

        self.save()

    def delete_all(self):
        if self.exists():
            utils.delete(self.localpath)

    def exists(self):
        if os.path.exists(self.localpath):
            return True

        return False

    def get_genres_list(self):
        genres = []

        if self.genres:
            for genre in self.genres.split("|"):
                if len(genre) > 1:
                    genres.append(genre)
        return genres

    def get_networks(self):
        networks = []

        if self.networks:
            for network in self.networks.split("|"):
                networks.append(network)

        return networks

    def get_latest_ep(self, season):
        now = datetime.now() - timedelta(days=2)

        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            for ep in reversed(tvdb_obj[season].keys()):
                    ep_obj = tvdb_obj[season][ep]

                    aired_date = ep_obj['firstaired']

                    if aired_date is not None:
                        aired_date = datetime.strptime(aired_date, '%Y-%m-%d')

                        if now > aired_date:
                            if ep == 0:
                                return 1
                            else:
                                return ep
        return 1

    def get_next_ep(self, season):
        now = datetime.now()

        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            for ep in tvdb_obj[season].keys():
                    ep_obj = tvdb_obj[season][ep]

                    aired_date = ep_obj['firstaired']

                    if aired_date is not None:
                        aired_date = datetime.strptime(aired_date, '%Y-%m-%d') + timedelta(days=1)

                        if aired_date.date() == datetime.today().date():
                            if ep == 0:
                                return 1
                            else:
                                return ep

                        if now < aired_date:
                            if ep == 0:
                                return 1
                            else:
                                return ep
        return 1

    def get_next_season(self):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            now = datetime.now() - timedelta()

            #loop through each season
            for season in reversed(tvdb_obj.keys()):
                #Lets loop through each ep..
                prev_season = season

                for ep in tvdb_obj[season].keys():
                    ep_obj = self.tvdb_obj[season][ep]

                    aired_date = ep_obj['firstaired']

                    if aired_date:
                        aired_date = datetime.strptime(aired_date, '%Y-%m-%d') + timedelta(days=1)

                        if now < aired_date:
                            #Found the ep and season
                            return season


    def get_latest_season(self):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            now = datetime.now() - timedelta(days=2)

            #loop through each season
            for season in reversed(tvdb_obj.keys()):

                #Lets loop through each ep..
                for ep in reversed(tvdb_obj[season].keys()):
                    ep_obj = self.tvdb_obj[season][ep]

                    aired_date = ep_obj['firstaired']

                    if aired_date is not None:
                        aired_date = datetime.strptime(aired_date, '%Y-%m-%d')

                        if now > aired_date:
                            #Found the ep and season
                            return int(season)
        return 1

    def get_last_ep(self, season):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            season_obj = self.tvdb_obj[season]
            return season_obj.keys()[-1]

    def get_ep(self, season, ep):
        tvdb_obj = self.get_tvdb_obj()
        return tvdb_obj[season][ep]

    def season_finished(self, season):
        latest_season = self.get_latest_season()
        if latest_season > season:
            return True
        if latest_season < season:
            return False

        if season == latest_season:
            latest_ep = self.get_last_ep(season)

            try:
                ep_obj = self.get_ep(season, latest_ep)
                aired_date = ep_obj['firstaired']
                aired_date = datetime.strptime(aired_date, '%Y-%m-%d')
                now = datetime.now() - timedelta(days=2)

                if now > aired_date:
                    return True
            except:
                pass

        return False

    def get_existing_eps(self, season):
        from lazy_common import metaparser
        if self.localpath:
            season_folder = common.find_season_folder(self.localpath, season)

            found = []

            if season_folder and os.path.exists(season_folder):
                files = [f for f in os.listdir(season_folder) if os.path.isfile(os.path.join(season_folder, f))]

                for f in files:
                    if utils.is_video_file(f):
                        parser = metaparser.get_parser_cache(os.path.basename(f), type=metaparser.TYPE_TVSHOW)
                        f_season = parser.get_season()
                        f_eps = parser.get_eps()

                        if season == f_season:
                            for ep in f_eps:
                                found.append(ep)
            return found

    def find_season_folder(self, season):

        if not os.path.exists(self.localpath):
            return

        from lazy_common import metaparser

        folders = [f for f in os.listdir(self.localpath) if os.path.isdir(os.path.join(self.localpath, f))]

        for folder_name in folders:

            if season == 0 and folder_name.lower() == "specials":
                return os.path.join(self.localpath, folder_name)

            parser = metaparser.get_parser_cache(folder_name, metaparser.TYPE_TVSHOW)

            if 'season' in parser.details:
                if parser.details['season'] == season:
                    return os.path.join(self.localpath, folder_name)

    def get_missing_eps_season(self, season):
        logger.info("Checking for missing eps in season season %s" % season)
        missing = []

        #get latest ep of this season
        tvdb_latest_ep = self.get_latest_ep(season)
        logger.info("Latest ep for season %s is %s" % (season, tvdb_latest_ep))

        season_path = common.find_season_folder(self.localpath, season)

        if not season_path or not os.path.isdir(season_path):
            logger.info(season)
            missing = self.get_eps(season)
        else:
            #Find all the existing Eps..
            existing_eps = self.get_existing_eps(season)

            #Now lets figure out whats actually missing
            for ep_no in range(1, tvdb_latest_ep + 1):
                if ep_no not in existing_eps:
                    missing.append(ep_no)

        return missing

    def get_missing_details(self):
        logger.info("Looking for missing eps in %s" % self.localpath)

        missing = {}

        for cur_season in self.get_seasons():
            if cur_season == 0:
                continue

            #do we want to process this season?
            missing_eps = self.get_missing_eps_season(cur_season)

            tvdbobj = self.get_tvdb_obj()

            if len(missing_eps) > 0:
                eps_dict = {}

                for ep in missing_eps:
                    try:
                        ep_dict = tvdbobj[cur_season][ep]

                        if 'episodename' in ep_dict:
                            ep_dict['episodename'] = ep_dict['episodename'].encode('ascii', 'ignore')
                        eps_dict[ep] = ep_dict
                    except:
                        eps_dict[ep] = {'episodenumber': ep}

                missing[cur_season] = eps_dict

        return missing

    def get_missing(self):
        logger.info("Looking for missing eps in %s" % self.localpath)

        missing = {}

        for cur_season in self.get_seasons():
            if cur_season == 0:
                continue

            missing_eps = self.get_missing_eps_season(cur_season)

            if len(missing_eps) > 0:
                missing[cur_season] = missing_eps

        return missing

    def get_seasons(self, xem=True):
        tvdb_obj = self.get_tvdb_obj()

        if xem:
            tvdb_obj

        return tvdb_obj.keys()

    def get_eps(self, season, xem=True):
        if xem:
            tvdb_obj = self.get_tvdb_obj(xem=xem)

        return tvdb_obj[season].keys()

    def get_titles(self, refresh=False):

        if refresh or not self.alt_names:
            alt_names = []

            #Now lets figure out what title we should search for on sites
            alt_names.append(self.clean_title(self.title))

            #list of alt names on tvdb.com
            tvdbapi = Tvdb()
            search_results = tvdbapi.search(self.title)

            for result in search_results:
                if result['seriesid'] == str(self.id):
                    if 'aliasnames' in result:
                        for alias in result['aliasnames']:
                            alias = self.clean_title(alias)
                            if alias not in alt_names:
                                alt_names.append(alias)
                    break

            #show mappings
            mappings = TVShowMappings.objects.all().filter(tvdbid_id=self.id)

            for mapping in mappings:
                map_name = mapping.title

                map_name = self.clean_title(map_name)

                if map_name not in mappings:
                    alt_names.insert(0, map_name)

            self.alt_names = alt_names
            self.save()

        return self.alt_names

    def get_tvdbid(self):
        if self.id:
            return self.id

        try:
            tvdb_obj = self.get_tvdb_obj()

            if tvdb_obj:
                return int(tvdb_obj['id'])
        except:
            pass

    def get_tvdb_obj(self, xem=True):

        self.tvdbapi.config['convert_xem'] = xem

        if self.tvdb_obj:
            return self.tvdb_obj

        if self.id:
            try:
                self.tvdb_obj = self.tvdbapi[self.id]
                logger.info("Found on thetvdb %s" % self.tvdb_obj['id'])
                return self.tvdb_obj
            except:
                pass
        elif self.title:
            try:
                self.tvdb_obj = self.tvdbapi[self.title]
                logger.info("Found matching tvdbcache item %s" % self.tvdb_obj['id'])
                return self.tvdb_obj
            except:
                pass
        elif self.alt_names:
            for name in self.alt_name:
                try:
                    self.tvdb_obj = self.tvdbapi[name]
                    logger.info("Found matching tvdbcache item %s" % self.tvdb_obj['id'])
                    return self.tvdb_obj
                except:
                    pass

        return self.tvdb_obj

    @staticmethod
    def clean_title(title):
        import re
        for search, replace in settings.TVSHOW_AUTOFIX_REPLACEMENTS.items():
            title = title.replace(search, replace)

        return re.sub(" +", " ", title).lower()

    def update_names(self):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj and 'seriesname' in tvdb_obj.data and  tvdb_obj['seriesname'] is not None:
                title = self.clean_title(tvdb_obj['seriesname'])

                if title is not None:
                    self.title = title

        self.alt_names = self.get_titles(refresh=True)

    def get_network(self, refresh=False):
        if refresh:
            tvdb_obj = self.get_tvdb_obj()

            if tvdb_obj and 'network' in tvdb_obj.data and tvdb_obj['network']:
                networks = tvdb_obj['network'].encode('ascii', 'ignore')
                if networks and len(networks) > 0:
                    self.networks = networks

        return self.networks

    def get_description(self, refresh=False):
        if refresh:
            tvdb_obj = self.get_tvdb_obj()

            if 'overview' in tvdb_obj.data and tvdb_obj['overview']:
                overview = tvdb_obj['overview'].encode('ascii', 'ignore')
                if overview and len(overview) > 0:
                    self.description = tvdb_obj['overview'].encode('ascii', 'ignore')

        return self.description

    def get_genres(self, refresh=False):
        if refresh:
            tvdb_obj = self.get_tvdb_obj()

            if tvdb_obj and 'genre' in tvdb_obj.data and tvdb_obj['genre']:
                genre = tvdb_obj['genre'].encode('ascii', 'ignore')
                if genre and len(genre) > 0:
                    self.genres = tvdb_obj['genre']

        return self.genres

    def get_posterimg(self, refresh=False):
        if refresh:
            tvdb_obj = self.get_tvdb_obj()

            if tvdb_obj and '_banners' in tvdb_obj.data:
                if tvdb_obj['_banners'] is not None:
                    banner_data = tvdb_obj['_banners']

                    if 'poster' in banner_data.keys():
                        posterSize = banner_data['poster'].keys()[0]
                        posterID = banner_data['poster'][posterSize].keys()[0]
                        posterURL = banner_data['poster'][posterSize][posterID]['_bannerpath']

                        try:
                            img_download = NamedTemporaryFile(delete=True)
                            img_download.write(urllib2.urlopen(posterURL).read())
                            img_download.flush()

                            size = (214, 317)

                            if os.path.getsize(img_download.name) > 0:
                                img_tmp = NamedTemporaryFile(delete=True)
                                im = Image.open(img_download.name)
                                im = im.resize(size, Image.ANTIALIAS)
                                im.save(img_tmp, "JPEG", quality=70)

                                self.posterimg.save(str(self.id) + '-tvdb.jpg', File(img_tmp))
                        except Exception as e:
                            logger.error("error saving image: %s" % e.message)
                            pass
        return self.posterimg

    def get_imdb(self, refresh=True):
        if refresh:
            tvdb_obj = self.get_tvdb_obj()

            if tvdb_obj and 'imdb_id' in tvdb_obj.data:
                if tvdb_obj['imdb_id'] is not None:
                    try:
                        imdbid_id = tvdb_obj['imdb_id'].lstrip("tt")
                        self.imdbid_id = int(imdbid_id)

                        from lazy_client_core.models.movie import Movie

                        try:
                            imdbobj = Movie.objects.get(id=int(imdbid_id))
                        except ObjectDoesNotExist:
                            imdbobj = Movie()
                            imdbobj.id = int(imdbid_id)
                            imdbobj.save()

                    except:
                        pass

        return self.imdbid

    def get_status(self):
        tvdb_obj = self.get_tvdb_obj()

        try:
            status = tvdb_obj['status']

            if status == "Continuing":
                return 1
            elif status == "Ended":
                return 2
        except:
            pass

        return 3

    def update_from_tvdb(self, update_imdb=True):

        logger.info("Updating %s %s" % (str(self.id), self.title))
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            #Lets update everything..
            self.update_names()
            self.get_network(refresh=True)
            self.get_genres(refresh=True)
            self.get_description(refresh=True)
            self.get_posterimg(refresh=True)
            if update_imdb:
                self.get_imdb(refresh=True)
            self.updated = datetime.now()

            self.save()

    def is_valid_name(self, name):
        name = self.clean_title(name)
        for title in self.get_titles():
            #Sometimes people forgot to add s, sometimes they add s
            if name.endswith("s") and name.rstrip("s") == title:
                return True

            if name == title:
                return True
        return False

from lazy_client_core.utils import lazyapi
from lazy_client_core.utils.lazyapi import LazyServerExcpetion
from lazy_client_core.exceptions import AlradyExists_Updated
import re


class TVShowScanner:

    def __init__(self, tvshow_obj, fix={}):
        self.tvshow_obj = tvshow_obj
        self.fix = fix
        self.ftp_entries = None
        self.queue_entries = None
        self.season_pre_scan = None

        #If none specified then try fix everything.. (all seasons, eps)
        if len(self.fix) == 0:
            for season in self.tvshow_obj.get_seasons():
                self.fix[season] = [0]

    def is_season_pack(self, title):
        parser = metaparser.get_parser_cache(title, metaparser.TYPE_TVSHOW)

        #We don't want Disk or Part seasons
        if re.search('(?i)D[0-9]+|DVD[0-9]+', title):
            return False

        if parser.details['type'] == "season_pack" or parser.details['type'] == "season_pack_multi" and 'series' in parser.details:
            return True
        return False

    def valid_series_title(self, title):
        if self.tvshow_obj.is_valid_name(title):
            return True

    def valid_torrent_title(self, torrent):
        parser = metaparser.get_parser_cache(torrent, type=metaparser.TYPE_TVSHOW)
        if 'series' in parser.details:
            series = TVShow.clean_title(parser.details['series'])
            if self.valid_series_title(series):
                return True
        return False

    def get_queue_entries(self):
        if not self.queue_entries:
            from lazy_client_core.models import DownloadItem
            self.queue_entries = []

            for dlitem in DownloadItem.objects.all().exclude(status=DownloadItem.COMPLETE):
                if self.tvshow_obj.id == dlitem.tvdbid_id:
                    self.queue_entries.append(dlitem)
                    continue

                if self.valid_torrent_title(dlitem.title):
                    self.queue_entries.append(dlitem)

        return self.queue_entries

    def get_season_pre_scan(self):
        if not self.season_pre_scan:
            tl_packs = {'results': []}
            scc_archive = {'results': []}
            revtt_packs = {'results': []}
            self.season_pre_scan = {'tl_packs': tl_packs, 'scc_archive': scc_archive, 'revtt_packs': revtt_packs}

            for name in self.tvshow_obj.get_titles():
                for x in range(0, 2):
                    try:
                        logger.info("Search torrent sites for %s" % name)
                        found = lazyapi.search_torrents(name, sites=["TL_PACKS", "SCC_ARCHIVE", "REVTT_PACKS"])

                        for site in found:
                            site_name = site['site'].lower()

                            if site['status'] != "finished":
                                self.log("Error searching torrents for %s as %s" % (site_name, site['message']))
                            else:
                                site_dict = None
                                if site_name == "tl_packs":
                                    site_dict = tl_packs
                                elif site_name == "revtt_packs":
                                    site_dict = revtt_packs
                                elif site_name == "scc_archive":
                                    site_dict = scc_archive

                                if site_dict is not None:
                                    #loop through each result
                                    if 'count' in site_dict:
                                        if len(site['results']) > site_dict['count']:
                                            site_dict['count'] = len(site['results'])
                                    else:
                                        site_dict['count'] = len(site['results'])

                                    for result in site['results']:
                                        if result['title'] not in site_dict:
                                            if self.is_season_pack(result['title']):
                                                if self.valid_torrent_title(result['title']):
                                                    site_dict['results'].append(result['title'])
                        break
                    except LazyServerExcpetion as e:
                        self.log("Error searching torrents for %s as %s" % (name, str(e)))

        return self.season_pre_scan

    def get_ftp_entries(self):
        if not self.ftp_entries:
            self.ftp_entries = []

            for name in self.tvshow_obj.get_titles():
                for x in range(0, 3):
                    try:
                        logger.info("Search ftp for %s" % name)
                        found = lazyapi.search_ftp(name)
                        if found:
                            for f in found:
                                if self.valid_torrent_title(os.path.basename(f['path'])):
                                    self.ftp_entries.append(f['path'])
                        break
                    except LazyServerExcpetion as e:
                        self.log("Error searching ftp for %s as %s" % (name, str(e)))

        return self.ftp_entries

    def add_new_download(self, ftp_path, onlyget=None, requested=False):
        from lazy_client_core.models import DownloadItem
        try:
            new_download = DownloadItem()
            new_download.ftppath = ftp_path.strip()
            new_download.tvdbid_id = self.tvshow_obj.id
            new_download.requested = requested

            if onlyget:
                for get_season, get_eps in onlyget.iteritems():
                    for get_ep in get_eps:
                        new_download.add_download(get_season, get_ep)

            new_download.save()

            if self.queue_entries:
                self.queue_entries.append(new_download)
        except AlradyExists_Updated:
            logger.debug("Updated existing download")

    def log(self, msg):
        logger.info(msg)

        try:
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0])

            caller = mod.__name__
            line = inspect.currentframe().f_back.f_lineno

            logmsg = "%s(%s): %s" % (caller, line, msg)

        except:
            logmsg = msg

        self.tvshow_obj.downloadlog_set.create(tvshow_id=self.tvshow_obj.id, message=logmsg)

    def get_pack_seasons(self, title):
        parser = metaparser.get_parser_cache(title, type=metaparser.TYPE_TVSHOW)

        if 'special' in parser.details:
            return

        if self.is_season_pack(title):
            series = TVShow.clean_title(parser.details['series'])

            for name in self.tvshow_obj.get_titles():
                if name.lower() == series.lower():
                    return parser.get_seasons()

    def sort_onlyget(self, found_seasons, get_season, onlyget):
        if len(found_seasons) > 1 and  None is onlyget:
            onlyget = {get_season: [0]}
        return onlyget

    def find_season(self, season, onlyget=None):

        #Step 1 - exist in queue already?
        self.log("Step 1: Looking for season %s, in the queue already" % season)
        for dlitem in self.get_queue_entries():
            seasons = self.get_pack_seasons(dlitem.title)

            if season in seasons:
                self.log("Found season %s in the queue already: %s" % (season, dlitem.title))
                if dlitem.onlyget:
                    #make sure this season is in the downloading seasons.. if not lets add it
                    dlitem.add_download(season, 0)
                    dlitem.save()

                return True

        #Step 2 check the ftp for it
        self.log("Step 2: Looking for season %s, via the ftp" % season)

        for ftp_path in self.get_ftp_entries():
            found_seasons = self.get_pack_seasons(os.path.basename(ftp_path))
            if season in found_seasons:
                self.log("We found season %s on ftp in %s" % (season, ftp_path))
                self.add_new_download(ftp_path, self.sort_onlyget(found_seasons, season, onlyget), requested=True)
                return True

        #Step 3 check the prescan
        self.log("Step 3: Looking for season %s, via the torrents (prescan)" % season)
        for site_name, site_dict in self.get_season_pre_scan().iteritems():
            for torrent in site_dict['results']:
                parser = metaparser.get_parser_cache(torrent, type=metaparser.TYPE_TVSHOW)
                found_seasons = parser.get_seasons()

                if season in found_seasons:
                    self.log("Found the season %s (via prescan) in %s" % (season, torrent))

                    try:
                        result = lazyapi.download_torrents([{'site': site_name, "title": torrent}])

                        #We should only get back 1 result
                        if len(result) == 1 and result[0]['status'] == "finished":
                            result = result[0]
                            ftp_path = result['ftp_path']
                            self.add_new_download(ftp_path, self.sort_onlyget(found_seasons, season, onlyget), requested=True)
                        else:
                            raise LazyServerExcpetion("Invalid return status %s %s" % (result['status'], result['message']))
                    except LazyServerExcpetion as e:
                        self.log("Error downloading %s as %s" % (torrent, str(e)))

        self.log("Step 4: lets try find it via each site")

        for site_name, site_dict in self.get_season_pre_scan():

            if site_dict['count'] < 50:
                self.log("Skipping %s as all the results were already checked in the prescan" % site_name)
                continue

            try:
                torrentSeasons = ftpmanager.getTVTorrentsSeason(site, self.search_names, season)
            except Exception as e:
                logger.exception(e)
                logger.info("Error when trying to get torrent listing from site %s... %s" % (site, e.message))
                continue

            if len(torrentSeasons) >= 1:
                #Lets find the best match! we prefer a single season
                bestMatch = ''
                smallestSize = 0

                for torrent in torrentSeasons:

                    parser = metaparser.get_parser_cache(torrent, type=metaparser.TYPE_TVSHOW)
                    seasons = parser.get_seasons()

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

                    #TODO: CHECK SEASONPATH NONE AND EXCPETION
                    seasonPath = ftpmanager.download_torrent(site, bestMatch)

                    if seasonPath is not False and seasonPath != '':

                        parser = metaparser.get_parser_cache(bestMatch, type=metaparser.TYPE_TVSHOW)
                        got_seasons = parser.get_seasons()

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

                        self.existing_server_entries.append(seasonPath.strip())
                        return True
                    else:
                        return False
                except Exception as e:
                    logger.exception(e)
                    logger.debug("Error download season pack %s because %s" % (bestMatch, e.message))
                    return False


        return False


    def fix(self):

        #First lets check if existing job is running
        #if self.fix and 'status' in self.fix:
        #    if self.fix['status'] != "finished":
        #        raise Exception("Error starting job as one was already found")

        #Now lets clear old logs
        #for obj in self.downloadlog_set.all():
        #    obj.delete()

        try:
            self.tvshow_obj.update_names()
            self.tvshow_obj.save()
            self.log("Attempting to fix %s" % self.search_names[0])

            tvshow_missing = {}
            found_seasons = {}

            for cur_season_no in self.fix.copy():
                self.log("Attempting to fix season %" % cur_season_no)

                existing_eps = self.get_existing_eps(cur_season_no)
                missing_eps = self.get_missing_eps_season(cur_season_no)
                all_season_eps = self.get_eps(cur_season_no)

                percent = (float((len(missing_eps) - len(existing_eps))) / float(len(all_season_eps))) * 100

                if percent < 80 and self.season_finished(cur_season_no):
                    #Has this season finished??
                    self.log("Season %s has finished broadcast and only %s percent of the epsiodes exists, will try search for the season pack" % (cur_season_no, percent))
                    self.find_season(cur_season_no)


                #lets try sort out the inviduial eps.
                logger.debug("Sorting out individual eps on season %s" % cur_season_no)

                already_processed_eps = []
                found = []

                copy_of_missing_eps = cur_season_obj['eps'].copy()



            return





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


@receiver(post_save, sender=TVShow)
def add_new_tvdbitem(sender, created, instance, **kwargs):

    if created:
        logger.info("Adding a new tvdbitem, lets make sure its fully up to date")

        #First lets find the tvdbid
        if not instance.id:
            instance.id = instance.get_tvdbid()

        instance.update_from_tvdb()
