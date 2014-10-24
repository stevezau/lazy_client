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
from lazy_common import utils

from lazy_client_core.utils.common import OverwriteStorage
from lazy_common.tvdb_api import Tvdb
from django.db import models
from lazy_common import metaparser

from celery.contrib.abortable import AbortableAsyncResult
from celery.contrib.abortable import AbortableTask
from djcelery_transactions import task
import time

logger = logging.getLogger(__name__)

from threading import Thread

class TVShowExcpetion():
    """
    """

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

@task(bind=True, base=AbortableTask)
def fix_missing_job(self, tvshow_id, fix):

    tvshow_obj = TVShow.objects.get(id=tvshow_id)

    scanner_thread = TVShowScanner(tvshow_obj, fix=fix)
    scanner_thread.start()

    try:
        while True:
            time.sleep(1)

            try:
                if self.is_aborted():
                    scanner_thread.abort()
                    scanner_thread.join()
                    break
            except:
                pass

            if not scanner_thread.isAlive():
                break
    finally:
        tvshow_obj.fix_jobid = None
        tvshow_obj.save()

def update_show_favs():
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
                tvshow.favorite = True
                try:
                    tvshow.save()
                except:
                    pass


        #now remove favs that should not be there
        for tvshow in TVShow.objects.filter(favorite=True):
            if tvshow.id not in tvdbfavs:
                logger.info("Removing show as fav as it was not marked as fav in thetvdb.com")
                tvshow.favorite = False
                tvshow.save()


###########################################
########### TV SHOW MAPPING ###############
###########################################

class TVShowMappings(models.Model):
    class Meta:
        """ Meta """
        db_table = 'tvshowmappings'
        ordering = ['-id']
        app_label = 'lazy_client_core'

    def __unicode__(self):
        return self.title

    title = models.CharField(max_length=150, db_index=True, unique=False)
    tvdbid = models.ForeignKey('TVShow')


#########################################
########### TV SHOW GENRES ##############
#########################################

class TVShowGenres(models.Model):
    class Meta:
        """ Meta """
        db_table = 'tvshow_genres'
        ordering = ['-id']
        app_label = 'lazy_client_core'

    genre = models.ForeignKey('GenreNames')
    tvdbid = models.ForeignKey('TVShow')


class GenreNames(models.Model):
    class Meta:
        """ Meta """
        db_table = 'genre_names'
        ordering = ['-id']
        app_label = 'lazy_client_core'

    def __unicode__(self):
        return self.genre

    def clean(self):
        self.genre = self.name.capitalize()

    genre = models.CharField(max_length=150, db_index=True, unique=True)


########################################
########### TV SHOW NETWORKS ###########
########################################

class TVShowNetworks(models.Model):
    class Meta:
        """ Meta """
        db_table = 'tvshow_networks'
        ordering = ['-id']
        app_label = 'lazy_client_core'

    def __unicode__(self):
        return self.network

    network = models.CharField(max_length=150, db_index=True, unique=True)

    def clean(self):
        self.genre = self.name.capitalize()

##################################
########### TV SHOWS ##############
###################################

class TVShow(models.Model):

    RUNNING = 1
    ENDED = 2

    STATUS_CHOICES = (
        (RUNNING, 'Running'),
        (ENDED, 'Ended'),
    )

    class Meta:
        db_table = 'tvdbcache'
        app_label = 'lazy_client_core'

    def __unicode__(self):
        return self.title

    title = models.CharField(max_length=200, db_index=True)
    posterimg = models.ImageField(upload_to=".", storage=OverwriteStorage(), blank=True, null=True)
    genres = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(max_length=255, blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)
    imdbid = models.ForeignKey('Movie', blank=True, null=True, on_delete=models.DO_NOTHING)
    localpath = models.CharField(max_length=255, blank=True, null=True)
    ignored = models.BooleanField(default=False)
    favorite = models.BooleanField(default=False)
    status = models.IntegerField(choices=STATUS_CHOICES, blank=True, null=True)
    fix_report = PickledObjectField()
    fix_jobid = models.CharField(max_length=255, blank=True, null=True)
    network = models.ForeignKey(TVShowNetworks, blank=True, null=True)

    tvdbapi = Tvdb(convert_xem=True)
    tvdb_obj = None

    def set_ignored(self, ignored):
        if ignored and self.is_favorite():
            #remove fav
            self.set_favorite(False)

        self.ignored = ignored

    def is_ignored(self):
        return self.ignored

    def killtask(self):
        task = self.get_task()

        if None is task:
            return True

        if task.ready():
            return True

        #lets try kill it
        task.abort()

        for i in range(0, 25):
            if task.ready():
                return True
            time.sleep(1)

    def cancel_fix_missing(self):
        self.killtask()

    def fix_missing(self, fix):
        if self.fix_job_running():
            raise AlreadyRunningException("Fix job already running")

        logger.error("Finding missing eps on %s : %s" % (self.title, fix))

        #Set initial status
        self.fix_report = {}
        for season, eps in fix.iteritems():
            for ep in eps:
                if season not in self.fix_report:
                    self.fix_report[season] = {}
                self.fix_report[season][ep] = "Searching"

        task = fix_missing_job.delay(self.id, fix)
        self.fix_jobid = task.task_id
        self.save()

    def get_task(self):
        if self.fix_jobid == None or self.fix_jobid == "":
            return None

        return AbortableAsyncResult(self.fix_jobid)

    def fix_job_running(self):
        #Find jobs running and if they are finished or not
        task = self.get_task()

        logger.debug("Job task state: %s" % task)

        if None is task:
            return False
        elif task.state == "SUCCESS" or task.state == "FAILURE" or task.state == "ABORTED":
            return False
        elif task.state == "PENDING":
            return True
        return True

    def stop_fix_job(self):
        task = self.get_task()

        if None is task:
            return

        if task.ready():
            return

        #lets try kill it
        task.abort()

        import time
        for i in range(0, 20):
            if task.ready():
                return

            time.sleep(1)

        raise Exception("Unable to kill download task/job")

    def get_local_path(self):
        if not self.localpath:
            #lets try find
            for title in self.get_titles():
                path = os.path.join(settings.TV_PATH, title)
                if os.path.exists(path):
                    logger.info("Found local path for tvshow as %s" % path)
                    self.localpath = path
                    self.save()

            #If didn't find existing find one
            if not self.localpath:
                if self.title:
                    self.localpath = os.path.join(settings.TV_PATH, self.title)
                    self.save()

        return self.localpath

    def is_favorite(self):
        return self.favorite

    def set_favorite(self, status):
        if status:
            if self.is_ignored():
                self.set_ignored(False)

            self.tvdbapi.add_fav(self.id)
            self.favorite = True
        else:
            self.tvdbapi.del_fav(self.id)
            self.favorite = False

        self.save()

    def delete_all(self):
        if self.exists():
            utils.delete(self.get_local_path())

    def exists(self):
        if os.path.exists(self.get_local_path()):
            return True

        return False

    def get_latest_ep(self, season):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj is not None:
            for ep in reversed(tvdb_obj[season].keys()):
                if self.ep_has_aired(season, ep):
                    return ep

    def get_next_ep(self, season):
        now = datetime.now()

        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj is not None:
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

        if tvdb_obj is not None:
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

        if tvdb_obj is not None:
            now = datetime.now() - timedelta(days=2)

            #loop through each season
            for season in reversed(tvdb_obj.keys()):

                #Lets loop through each ep..
                for ep in reversed(tvdb_obj[season].keys()):
                    if self.ep_has_aired(season, ep):
                        continue
                    else:
                        return season
        return 1

    def get_last_ep(self, season):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj is not None:
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

            if self.ep_has_aired(season, latest_ep):
                return True
        return False

    def get_existing_eps(self, season):
        from lazy_common import metaparser
        if self.get_local_path():
            season_folder = common.find_season_folder(self.get_local_path(), season)

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
        if not os.path.exists(self.get_local_path()):
            return

        from lazy_common import metaparser

        folders = [f for f in os.listdir(self.get_local_path()) if os.path.isdir(os.path.join(self.get_local_path(), f))]

        for folder_name in folders:

            if season == 0 and folder_name.lower() == "specials":
                return os.path.join(self.get_local_path(), folder_name)

            parser = metaparser.get_parser_cache(folder_name, metaparser.TYPE_TVSHOW)

            if 'season' in parser.details:
                if parser.details['season'] == season:
                    return os.path.join(self.get_local_path(), folder_name)

    def ep_has_aired(self, season, ep):
        tvdb_obj = self.get_tvdb_obj()
        now = datetime.now() - timedelta(days=2)

        if tvdb_obj is not None and season in tvdb_obj and ep in tvdb_obj[season]:
            ep_obj = tvdb_obj[season][ep]
            aired_date = ep_obj['firstaired']

            if aired_date is not None:
                aired_date = datetime.strptime(aired_date, '%Y-%m-%d')

                if now > aired_date:
                    return True
        return False

    def get_missing_eps_season(self, season):
        logger.info("Checking for missing eps in season season %s" % season)
        missing = []

        #get latest ep of this season
        tvdb_latest_ep = self.get_latest_ep(season)

        if tvdb_latest_ep:
            logger.info("Latest ep for season %s is %s" % (season, tvdb_latest_ep))

            if self.get_local_path():
                season_path = common.find_season_folder(self.get_local_path(), season)
            else:
                season_path = None

            if not season_path or not os.path.isdir(season_path):
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
        logger.info("Looking for missing eps in %s" % self.get_local_path())

        missing = {}

        tvdbobj = self.get_tvdb_obj()

        from lazy_client_core.models import DownloadItem
        dlitems = DownloadItem.objects.filter(tvdbid_id=self.id).exclude(status=DownloadItem.COMPLETE)

        for cur_season in self.get_seasons():
            if cur_season == 0:
                continue

            #do we want to process this season?
            missing_eps = self.get_missing_eps_season(cur_season)

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

                    eps_dict[ep]['downloading'] = False

                    #We alrady downloaing it?
                    for dlitem in dlitems:
                        if dlitem.is_downloading(cur_season, ep):
                            eps_dict[ep]['downloading'] = True

                missing[cur_season] = eps_dict

        return missing

    def get_missing(self):
        logger.info("Looking for missing eps in %s" % self.get_local_path())

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

    def get_eps(self, season, xem=True, aired=True):
        if xem:
            tvdb_obj = self.get_tvdb_obj(xem=xem)

        if aired:
            latest_ep = self.get_latest_ep(season)

            eps = []
            for ep in tvdb_obj[season].keys():
                if ep <= latest_ep:
                    eps.append(ep)
            return eps
        else:
            return tvdb_obj[season].keys()

    def set_titles(self, titles):
        #delete existing shows
        for obj in self.tvshowmappings_set.all():
            obj.delete()

        for title in titles:
            self.tvshowmappings_set.create(tvdbid=self.id, title=title)

    def get_titles(self, refresh=False):
        titles = [mapping.title for mapping in self.tvshowmappings_set.all()]
        return titles

    def get_tvdbid(self):
        if self.id:
            return self.id

        try:
            tvdb_obj = self.get_tvdb_obj()

            if tvdb_obj is not None:
                return int(tvdb_obj['id'])
        except:
            pass

    def get_tvdb_obj(self, xem=True):

        self.tvdbapi.config['convert_xem'] = xem

        if self.tvdb_obj is not None:
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
        else:
            for name in self.get_titles():
                try:
                    self.tvdb_obj = self.tvdbapi[name]
                    logger.info("Found matching tvdbcache item %s" % self.tvdb_obj['id'])
                    return self.tvdb_obj
                except:
                    pass

        return self.tvdb_obj

    @staticmethod
    def find_by_title(title):
        title = TVShow.clean_title(title)
        try:
            result = TVShowMappings.objects.get(title=title)
            return result.tvdbid
        except:
            pass


    @staticmethod
    def clean_title(title, lower=True):

        title = "".join(i for i in title if ord(i)<128)

        import re
        for search, replace in settings.TVSHOW_AUTOFIX_REPLACEMENTS.items():
            title = title.replace(search, replace)

        title = re.sub(" +", " ", title)

        if lower:
            title = title.lower()

        return title.strip()

    def get_network(self):
        if self.network:
            return self.network.network

    def set_network(self, network):
        try:
            network = TVShowNetworks.objects.get(network=network)
        except:
            network = TVShowNetworks(network=network)
            network.save()

        self.network = network

    def set_description(self, description):
        self.description = description

    def get_description(self):
        return self.description

    def set_genres(self, genres):
        for obj in self.tvshowgenres_set.all():
            obj.delete()

        for genre in genres:
            try:
                genre_obj = GenreNames.objects.get(genre=genre)
            except:
                genre_obj = GenreNames(genre=genre)
                genre_obj.save()

            self.tvshowgenres_set.create(tvdbid=self.id, genre=genre_obj)

    def get_genres(self):
        return [genre.genre for genre in self.tvshowgenres_set.all()]

    def set_poster(self, poster_url):
        try:
            img_download = NamedTemporaryFile(delete=True)
            img_download.write(urllib2.urlopen(str(poster_url)).read())
            img_download.flush()

            img_tmp = NamedTemporaryFile(delete=True)
            utils.resize_img(img_download.name, img_tmp.name, 180, 270, convert=settings.CONVERT_PATH, quality=60)
            self.posterimg.save(str(self.id) + '-tvdb.jpg', File(img_tmp))
            img_download.close()
            img_tmp.close()

        except Exception as e:
            logger.exception("error saving image: %s" % e.message)
            pass

    def get_posterimg(self):
        return self.posterimg

    def get_size(self):
        if os.path.exists(self.get_local_path()):
            return utils.get_size(self.get_local_path())

    def set_imdb(self, imdbid_id):
        self.imdbid_id = int(imdbid_id)

        from lazy_client_core.models.movie import Movie

        try:
            imdbobj = Movie.objects.get(id=int(imdbid_id))
        except ObjectDoesNotExist:
            imdbobj = Movie()
            imdbobj.id = int(imdbid_id)
            imdbobj.save()

    def get_imdb(self):
        return self.imdbid

    def get_status(self, refresh=False):
        return self.status

    def set_status(self, status):
        if status == "Continuing":
            self.status = self.RUNNING
        elif status == "Ended":
            self.status = self.ENDED

    def update_from_dict(self, details):
        if 'seriesid' in details:
            self.id = int(details['seriesid'])

        ### DESC ###
        if 'overview' in details:
            overview = details['overview'].encode('ascii', 'ignore')
            if overview and len(overview) > 0:
                self.set_description(overview)

        ### NETWORK ###
        if 'network' in details:
            self.set_network(details['network'].encode('ascii', 'ignore'))

        ### TITLES ###
        titles = []
        if 'seriesname' in details:
            self.title = self.clean_title(details['seriesname'])

        if 'aliasnames' in details:
            for alias in details['aliasnames']:
                clean_alias = self.clean_title(alias)
                if clean_alias not in titles:
                    titles.append(clean_alias)

        self.save()
        self.set_titles(titles)


    def update_from_tvdb(self, update_imdb=True):

        logger.info("Updating %s %s" % (str(self.id), self.title))
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj is not None:
            #### Titles ####
            titles = []
            if 'seriesname' in tvdb_obj.data and tvdb_obj['seriesname'] is not None:
                title = self.clean_title(tvdb_obj['seriesname'], lower=False)
                title_lower = title.lower()
                if title is not None:
                    titles.append(title_lower)
                    self.title = title

            #Alt names
            try:
                tvdbapi = Tvdb()
                search_results = tvdbapi.search(self.title)

                for result in search_results:
                    if result['seriesid'] == str(self.id):
                        if 'aliasnames' in result:
                            for alias in result['aliasnames']:
                                alias = self.clean_title(alias)
                                if alias not in titles:
                                    titles.append(alias)
                        break
            except:
                pass

            self.set_titles(titles)

            ### Network ###
            if 'network' in tvdb_obj.data and tvdb_obj['network']:
                network = tvdb_obj['network'].encode('ascii', 'ignore')
                if network:
                    self.set_network(network)

            ### Genres ###
            if 'genre' in tvdb_obj.data and tvdb_obj['genre']:
                genres = []
                genres_str = tvdb_obj['genre'].encode('ascii', 'ignore')
                for genre in genres_str.split("|"):
                    if len(genre) > 0:
                        genres.append(genre)

                self.set_genres(genres)

            ### DESC ###
            if 'overview' in tvdb_obj.data and tvdb_obj['overview']:
                overview = tvdb_obj['overview'].encode('ascii', 'ignore')
                if overview and len(overview) > 0:
                    self.set_description(overview)

            ### POSTER ###
            if 'poster' in tvdb_obj.data and tvdb_obj['poster']:
                self.set_poster(tvdb_obj['poster'])

            ### STATUS ###
            self.set_status(tvdb_obj['status'])

            ### IMDB ###
            if update_imdb and 'imdb_id' in tvdb_obj.data and tvdb_obj['imdb_id']:
                try:
                    imdbid_id = int(tvdb_obj['imdb_id'].lstrip("tt"))
                    self.set_imdb(imdbid_id)
                except:
                    pass

            self.updated = datetime.now()
        else:
            logger.info("Unable to get tvdbobject for %s" % self.title)

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
from lazy_client_core.exceptions import AlradyExists_Updated, AlradyExists
from lazy_common.tvdb_api.tvdb_exceptions import tvdb_seasonnotfound
import re


class AlreadyRunningException(Exception):
    """
    """

class TVShowScanner(Thread):

    def __init__(self, tvshow_obj, fix={}):
        Thread.__init__(self)
        self.tvshow_obj = tvshow_obj
        self.fix = fix
        self.ftp_entries = None
        self.queue_entries = None
        self.season_pre_scan = None
        #self.pre_scan = None
        self.aborted = False
        self.pre_scan = None

        #If none specified then try fix everything.. (all seasons, eps)
        if len(self.fix) == 0:
            for season in self.tvshow_obj.get_seasons():
                self.fix[season] = [0]

        #Now lets clear old logs
        for obj in self.tvshow_obj.downloadlog_set.all():
            obj.delete()

        self.tvshow_obj.fix_report = {}

        #Set initial status to searching
        for season, eps in self.fix.iteritems():
            if 0 in eps:
                #Fix all
                eps = self.tvshow_obj.get_missing_eps_season(season)

            for ep in eps:
                self.set_ep_status(season, ep, "Searching")

    def abort(self):
        self.aborted = True

    def valid_series_title(self, title):
        if self.tvshow_obj.is_valid_name(title):
            return True

    def is_season_pack(self, title):
        parser = metaparser.get_parser_cache(title, metaparser.TYPE_TVSHOW)

        #We don't want Disk or Part seasons
        if re.search('(?i)D[0-9]+|DVD[0-9]+', title):
            return False

        if parser.details['type'] == "season_pack" or parser.details['type'] == "season_pack_multi" and 'series' in parser.details:
            return True
        return False

    def valid_torrent_title(self, torrent):
        parser = metaparser.get_parser_cache(torrent, type=metaparser.TYPE_TVSHOW)
        if 'series' in parser.details:
            if 'year' in parser.details:
                series = TVShow.clean_title("%s %s" % (parser.details['series'], parser.details['year']))
            else:
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

    def ep_in_queue(self, season, ep):
        for dlitem in self.get_queue_entries():
            seasons = dlitem.get_seasons()
            if seasons and season in seasons:
                #Is this a season pack?
                if self.is_season_pack(dlitem.title):
                    self.log("Found season pack %s in the queue already will make sure we are downloading ep: %s" % (season, dlitem.title))
                    if dlitem.onlyget:
                        dlitem.add_download(season, ep)
                    return True
                else:
                    eps = dlitem.get_eps()
                    if ep in eps:
                        #Found it
                        return True
        return False

    def get_pre_scan(self):
        #First lets scan for all
        if not self.pre_scan:
            scc = {'results': []}
            revtt = {'results': []}
            tl = {'results': []}

            self.pre_scan = {'tl': tl, 'revtt': revtt, 'scc': scc}

            for name in self.tvshow_obj.get_titles():
                for x in range(0, 2):
                    try:
                        self.log("Getting a list from sites for %s" % name)
                        found = lazyapi.search_torrents(name, sites=["TL", "SCC", "REVTT"], max_results=400)

                        for site in found:
                            site_name = site['site'].lower()

                            if site['status'] != "finished":
                                self.log("Error searching torrents for %s as %s" % (site_name, site['message']))
                            else:
                                site_dict = None
                                if site_name == "tl":
                                    site_dict = tl
                                elif site_name == "revtt":
                                    site_dict = revtt
                                elif site_name == "scc":
                                    site_dict = scc

                                if site_dict is not None:
                                    #loop through each result
                                    if 'count' in site_dict:
                                        if len(site['results']) > site_dict['count']:
                                            site_dict['count'] = len(site['results'])
                                    else:
                                        site_dict['count'] = len(site['results'])

                                    if site_dict['count'] > 300:
                                        logger.error("Found %s entries from %s for %s" % (site_dict['count'], site_name, name))

                                    self.log("Found %s entries from %s" % (site_dict['count'], site_name))

                                    for result in site['results']:
                                        if result['title'] not in site_dict:
                                            if not self.is_season_pack(result['title']):
                                                if self.valid_torrent_title(result['title']):
                                                    site_dict['results'].append(result['title'])
                        break
                    except LazyServerExcpetion as e:
                        self.log("Error searching torrents for %s as %s" % (name, str(e)))

        return self.pre_scan

    def get_season_pre_scan(self):
        #First lets scan for all packs for show
        if not self.season_pre_scan:
            tl_packs = {'results': []}
            scc_archive = {'results': []}
            revtt_packs = {'results': []}
            self.season_pre_scan = {'tl_packs': tl_packs, 'scc_archive': scc_archive, 'revtt_packs': revtt_packs}

            for name in self.tvshow_obj.get_titles():
                for x in range(0, 2):
                    try:
                        self.log("Getting a list of season packs from sites for %s" % name)
                        found = lazyapi.search_torrents(name, sites=["TL_PACKS", "SCC_ARCHIVE", "REVTT_PACKS"], max_results=400)

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

                                    self.log("Found %s entries from %s" % (site_dict['count'], site_name))

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
                        self.log("Search ftp for %s" % name)
                        found = lazyapi.search_ftp(name)
                        if found:
                            for f in found:
                                if self.valid_torrent_title(os.path.basename(f['path'])):
                                    self.ftp_entries.append(f['path'])
                        break
                    except LazyServerExcpetion as e:
                        self.log("Error searching ftp for %s as %s" % (name, str(e)))

        return self.ftp_entries

    def add_new_download(self, ftp_path, season=None, eps=None, requested=False):
        from lazy_client_core.models import DownloadItem
        try:
            new_download = DownloadItem()
            new_download.ftppath = ftp_path.strip()
            new_download.tvdbid_id = self.tvshow_obj.id
            new_download.requested = requested
            new_download.type = metaparser.TYPE_TVSHOW

            if season:
                if eps and len(eps) > 0:
                    #download each ep
                    for ep in eps:
                        new_download.add_download(season, ep)
                else:
                    new_download.add_download(season, 0)

            new_download.save()

            if self.queue_entries:
                self.queue_entries.append(new_download)
        except AlradyExists_Updated:
            logger.debug("Updated existing download")
        except AlradyExists:
            logger.debug("Download Already exists")

    def log(self, msg):
        line = None

        try:
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0])

            caller = mod.__name__
            line = inspect.currentframe().f_back.f_lineno

            logmsg = "%s(%s): %s" % (caller, line, msg)

        except:
            logmsg = msg

        if line:
            logger.debug("%s: %s" % (line, msg))
        else:
            logger.debug(msg)

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

    def get_seasons(self, title):
        parser = metaparser.get_parser_cache(title, type=metaparser.TYPE_TVSHOW)
        return parser.get_seasons()

    def get_eps(self, title):
        parser = metaparser.get_parser_cache(title, type=metaparser.TYPE_TVSHOW)
        return parser.get_eps()

    def find_season(self, season, eps=None):
        #Step 1 - exist in queue already?
        self.log("Step 1: Looking for season %s, in the queue already" % season)
        for dlitem in self.get_queue_entries():
            seasons = self.get_pack_seasons(dlitem.title)
            if seasons and season in seasons:
                self.log("Found season %s in the queue already: %s" % (season, dlitem.title))
                if dlitem.onlyget:
                    #make sure this season is in the downloading seasons.. if not lets add it
                    if eps:
                        for ep in eps:
                            dlitem.add_download(season, ep)
                    else:
                        dlitem.add_download(season, 0)
                    dlitem.save()

                return True

        #Step 2 check the ftp for it
        self.log("Step 2: Looking for season %s, via the ftp" % season)
        for ftp_path in self.get_ftp_entries():
            found_seasons = self.get_pack_seasons(os.path.basename(ftp_path))
            if found_seasons and season in found_seasons:
                self.log("We found season %s on ftp in %s" % (season, ftp_path))
                self.add_new_download(ftp_path, season=season, eps=eps, requested=True)
                return True

        #Step 3 check the prescan
        self.log("Step 3: Looking for season %s, via the torrents (prescan)" % season)
        for site_name, site_dict in self.get_season_pre_scan().iteritems():
            for torrent in site_dict['results']:
                parser = metaparser.get_parser_cache(torrent, type=metaparser.TYPE_TVSHOW)
                found_seasons = parser.get_seasons()

                if found_seasons and season in found_seasons:
                    self.log("Found the season %s (via prescan) in %s" % (season, torrent))

                    try:
                        results = lazyapi.download_torrents([{'site': site_name, "title": torrent}])

                        #We should only get back 1 result
                        if len(results) == 1:
                            result = results[0]
                            if result['status'] == "finished":
                                ftp_path = result['ftp_path']
                                self.add_new_download(ftp_path, season=season, eps=eps, requested=True)
                                return True
                            else:
                                raise LazyServerExcpetion("Invalid return status %s %s" % (result['status'], result['message']))
                        else:
                            raise LazyServerExcpetion("Something went wrong, we got multiple results returned when we were expecting 1")
                    except LazyServerExcpetion as e:
                        self.log("Error downloading %s as %s" % (torrent, str(e)))

        return False

    def set_season_status(self, season, eps, found):
        self.tvshow_obj.fix_report[season] = {}
        for ep in eps:
            self.tvshow_obj.fix_report[season][ep] = found
        self.tvshow_obj.save()

    def set_ep_status(self, season, ep, found):
        if season not in self.tvshow_obj.fix_report:
            self.tvshow_obj.fix_report[season] = {}
        self.tvshow_obj.fix_report[season][ep] = found
        self.tvshow_obj.save()

    def run(self):
        self.tvshow_obj.update_from_tvdb()
        self.tvshow_obj.save()
        self.log("Attempting to fix %s" % self.tvshow_obj.title)
        logger.error("Attempting to fix %s" % self.tvshow_obj.title)

        try:
            for cur_season_no, eps in self.fix.iteritems():
                self.log("Attempting to fix season %s" % cur_season_no)

                try:
                    existing_eps = self.tvshow_obj.get_existing_eps(cur_season_no)
                    missing_eps = self.tvshow_obj.get_missing_eps_season(cur_season_no)
                    all_season_eps = self.tvshow_obj.get_eps(cur_season_no, aired=True)
                except tvdb_seasonnotfound:
                    self.log("Season was not found, aborting season %s" % cur_season_no)
                    continue

                #Lets figure out what eps we need to fix.
                if 0 in eps:
                    #Fix all
                    eps = missing_eps

                if self.aborted:
                    self.log("Aborting fix for %s" % self.tvshow_obj.title)

                    for cur_season_no, eps in self.fix.copy().iteritems():
                        #Set remaining seasons to aborted
                        self.set_season_status(cur_season_no, eps, "Aborted Search")
                    continue

                ##Figure out the percent
                if len(existing_eps) == 0:
                    downloaded_percent = 0
                elif len(missing_eps) == 0:
                    downloaded_percent = 100
                else:
                    downloaded_percent = 100 * len(existing_eps)/len(all_season_eps)

                if downloaded_percent < 65 and self.tvshow_obj.season_finished(cur_season_no):
                    #Has this season finished??
                    self.log("Season %s has finished broadcast and only %s percent of the epsiodes exists, will try search for the season pack" % (cur_season_no, downloaded_percent))
                    if self.find_season(cur_season_no, eps):
                        self.set_season_status(cur_season_no, eps, "Downloading")
                        continue

                #lets try sort out the inviduial eps.
                self.log("Sorting out individual eps on season %s" % cur_season_no)

                found_eps = []
                skip_eps = []

                for ep_no in eps:
                    if self.aborted:
                        self.log("Aborting fix for %s" % self.tvshow_obj.title)
                        #Lets cancel all the eps remaining
                        for ep in eps:
                            self.set_ep_status(cur_season_no, ep, "Aborted Search")
                        return

                    if ep_no in existing_eps:
                        self.log("Already exist skipping! %s x %s" % (cur_season_no, ep_no))
                        skip_eps.append(ep_no)
                        self.set_ep_status(cur_season_no, ep_no, "Already exists")
                        continue

                    #Check if its on the DB already
                    if self.ep_in_queue(cur_season_no, ep_no):
                        self.log("Already in the download queue skipping! %s x %s" % (cur_season_no, ep_no))
                        skip_eps.append(ep_no)
                        self.set_ep_status(cur_season_no, ep_no, "Already downloading")
                        continue

                    #Step 1 check the ftp for it
                    self.log("Step 1: Looking for ep %s, via the ftp" % ep_no)
                    do_continue = False
                    for ftp_path in self.get_ftp_entries():
                        found_seasons = self.get_seasons(os.path.basename(ftp_path))
                        if found_seasons and cur_season_no in found_seasons:
                            if ep_no in self.get_eps(os.path.basename(ftp_path)):
                                self.log("We found ep %s on ftp in %s" % (ep_no, ftp_path))
                                self.add_new_download(ftp_path, requested=True)
                                self.set_ep_status(cur_season_no, ep_no, "Downloading")
                                skip_eps.append(ep_no)
                                do_continue = True
                                break

                    if do_continue:
                        continue

                    #Step 3 check the prescan
                    self.log("Step 2: Looking for ep %s, via the torrents (prescan)" % ep_no)
                    site_names = ['scc', 'revtt', 'tl']
                    do_continue = False
                    do_break = False
                    for site_name in site_names:
                        site_dict = self.get_pre_scan()[site_name]

                        if do_break:
                            break

                        for torrent in site_dict['results']:
                            parser = metaparser.get_parser_cache(torrent, type=metaparser.TYPE_TVSHOW)
                            found_seasons = parser.get_seasons()

                            if found_seasons and cur_season_no in found_seasons:
                                if ep_no in parser.get_eps():
                                    self.log("Found the ep %s (via prescan) in %s" % (ep_no, torrent))
                                    found_eps.append({'site': site_name, 'torrent': torrent, 'ep_no': ep_no})
                                    do_continue = True
                                    break
                    if do_continue:
                        continue

                #lets deal with the ones we didn't find
                didnt_find_eps = []

                for ep_no in eps:
                    if ep_no in skip_eps:
                        continue
                    for found_ep in found_eps:
                        if found_ep['ep_no'] == ep_no:
                            continue
                    didnt_find_eps.append(ep_no)

                if len(didnt_find_eps) > 0 and self.tvshow_obj.season_finished(cur_season_no):
                    self.log("Didn't find eps %s.. lets try get season pack instead.." % didnt_find_eps)
                    #remove the skip eps from the eps to download as they were added via the ftp
                    for ep in skip_eps:
                        if ep in eps:
                            del eps[ep]

                    if self.find_season(cur_season_no, eps):
                        self.log("Download season for missing eps..")
                        self.set_season_status(cur_season_no, eps, "Downloading")
                        continue
                    else:
                        self.log("didn't get season pack")

                #report all eps we didn't find
                for ep in didnt_find_eps:
                    self.set_ep_status(cur_season_no, ep, "Not Found")

                #Lets download the found eps
                for found_ep in found_eps:
                    ep_no = found_ep['ep_no']

                    if self.aborted:
                        self.log("Aborting fix for %s" % self.tvshow_obj.title)
                        self.set_ep_status(cur_season_no, ep_no, "Cancelled")
                        continue

                    try:
                        results = lazyapi.download_torrents([{'site': found_ep['site'], "title": found_ep['torrent']}])

                        #We should only get back 1 result
                        if len(results) == 1:
                            result = results[0]
                            if result['status'] == "finished":
                                ftp_path = result['ftp_path']
                                self.add_new_download(ftp_path, requested=True)
                                self.set_ep_status(cur_season_no, ep_no, "Downloading")
                            else:
                                raise LazyServerExcpetion("Invalid return status %s %s" % (result['status'], result['message']))
                        else:
                            raise LazyServerExcpetion("Something went wrong, we got multiple results returned when we were expecting 1")
                    except LazyServerExcpetion as e:
                        self.log("Error downloading %s as %s" % (torrent, str(e)))
                        self.set_ep_status(cur_season_no, ep_no, str(e))
        except Exception as e:
            logger.exception(e)

        return

@receiver(post_save, sender=TVShow)
def add_new_tvdbitem(sender, created, instance, **kwargs):

    if created:
        logger.info("Adding a new tvdbitem, lets make sure its fully up to date")

        #First lets find the tvdbid
        if not instance.id:
            instance.id = instance.get_tvdbid()

        if not instance.title:
            instance.update_from_tvdb()

        if not instance.title:
            logger.error("Unable to figure out tvdb info")
            raise Exception("Unable to determine TVDB information")