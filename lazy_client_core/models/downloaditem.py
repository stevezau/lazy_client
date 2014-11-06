from __future__ import division

import logging
import shutil
import os
import re
from datetime import datetime
import inspect
import time
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from flexget.utils.imdb import ImdbSearch, ImdbParser
from django.db.models import Q
from lazy_common.tvdb_api import Tvdb
from lazy_client_core.exceptions import AlradyExists_Updated, AlradyExists, Ignored
from lazy_client_core.utils.jsonfield.fields import JSONField

from lazy_common.tvdb_api.tvdb_exceptions import tvdb_shownotfound
from django.db import models
from lazy_client_core.models.tvshow import TVShow
from lazy_client_core.models.movie import Movie

logger = logging.getLogger(__name__)


class DownloadItem(models.Model):
    class Meta:
        """ Meta """
        app_label = 'lazy_client_core'
        db_table = 'download'
        ordering = ['id']

    def __unicode__(self):
        return self.title

    PENDING = 6
    QUEUE = 1
    DOWNLOADING = 2
    EXTRACT = 3
    RENAME = 5
    COMPLETE = 4

    JOB_NO_RESPONSE = 10
    JOB_RUNNING = 11
    JOB_PENDING = 12
    JOB_FAILED = 13
    JOB_NOT_FOUND = 14
    JOB_FINISHED = 15

    STATUS_CHOICES = (
        (QUEUE, 'Queue'),
        (DOWNLOADING, 'Downloading'),
        (RENAME, 'Rename'),
        (COMPLETE, 'Complete'),
        (PENDING, 'Pending'),
        (EXTRACT, 'Extract'),
    )

    TYPE_TVSHOW = 1
    TYPE_MOVIE = 2
    TYPE_UNKNOWN = 3

    TYPES = (
        (TYPE_TVSHOW, 'TVShow'),
        (TYPE_MOVIE, 'Movie'),
        (TYPE_UNKNOWN, 'Unknown')
    )


    title = models.CharField(max_length=150, db_index=True, blank=True, null=True)
    title_clean = models.CharField(max_length=150, blank=True, null=True)
    section = models.CharField(max_length=10, db_index=True, blank=True, null=True)
    ftppath = models.CharField(max_length=255, db_index=True, unique=True)
    localpath = models.CharField(max_length=255, blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, blank=True, null=True)
    pid = models.IntegerField(default=0, null=True)
    type = models.IntegerField(choices=TYPES, blank=True, default=TYPE_UNKNOWN)
    taskid = models.CharField(max_length=255, blank=True, null=True)
    retries = models.IntegerField(default=0)
    dateadded = models.DateTimeField(db_index=True, auto_now_add=True, blank=True)
    dlstart = models.DateTimeField(blank=True, null=True)
    remotesize = models.BigIntegerField(default=0, null=True)
    priority = models.IntegerField(default=5, null=True)
    requested = models.BooleanField(default=False)
    localsize = models.IntegerField(default=0, null=True)
    message = models.TextField(blank=True, null=True)
    imdbid = models.ForeignKey('Movie', blank=True, null=True, on_delete=models.SET_NULL)
    tvdbid = models.ForeignKey('TVShow', blank=True, null=True, on_delete=models.SET_NULL)
    onlyget = JSONField(blank=True, null=True)
    video_files = JSONField(blank=True, null=True)

    epsiodes = JSONField(blank=True, null=True)
    seasons = JSONField(blank=True, null=True)
    date = models.DateTimeField(null=True, blank=True)
    quality = JSONField(blank=True, null=True)

    parser = None

    def get_title_clean(self):

        if not self.title_clean:
            parser = self.metaparser()
            title = ""
            series = False

            if 'doco_channel' in parser.details:
                title += "%s: " % parser.details['doco_channel']

            if 'series' in parser.details:

                title += parser.details['series']
                series = True

            if 'title' in parser.details:
                if series:
                    title += ": %s" % parser.details['title']
                else:
                    title += " %s" % parser.details['title']

            if 'date' in parser.details:
                title += " %s" % parser.details['date'].strftime('%m.%d.%Y')

            if len(title) > 0:
                self.title_clean = title
                self.save()

        return self.title_clean

    def is_season_pack(self):
        parser = self.metaparser()

        if parser:
            #We don't want Disk or Part seasons
            if re.search('(?i)D[0-9]+|DVD[0-9]+', self.title):
                return False

            if parser.details['type'] == "season_pack" or parser.details['type'] == "season_pack_multi" and 'series' in parser.details:
                return True
            return False

    def is_downloading(self, season, ep):
        seasons = self.get_seasons()

        if seasons and season in seasons:
            if self.is_season_pack():
                if self.onlyget:
                    #check for this ep
                    if str(season) in self.onlyget and ep in self.onlyget[str(season)]:
                        return True
                else:
                    #downloading all eps
                    return True
            else:
                if ep in self.get_eps():
                    return True
        return False

    def get_seasons(self):
        if not self.seasons:
            parser = self.metaparser()
            seasons = parser.get_seasons()

            if len(seasons) > 0:
                self.seasons = seasons
                self.save()

        return self.seasons

    def get_eps(self):
        if not self.epsiodes:
            epsiodes = []
            parser = self.metaparser()

            if 'episodeList' in parser.details:
                epsiodes = parser.details['episodeList']
            elif 'episodeNumber' in parser.details:
                epsiodes = [parser.details['episodeNumber']]
            if len(epsiodes) > 0:
                self.epsiodes = epsiodes
                self.save()

        return self.epsiodes

    def get_quality(self):
        if not self.quality:
            parser = self.metaparser()
            quality = []

            if parser.quality.resolution:
                quality.append(parser.quality.resolution.name)

            if parser.quality and parser.quality.source:
                quality.append(parser.quality.source.name)

            if len(quality) == 0 and 'format' in parser.details:
                quality.append(parser.details['format'])

            formatted_quality = []
            for q in quality:
                if q.lower() == "hdtv":
                    q = "HDTV"
                if q.lower() == "xvid":
                    q = "XVID"
                if q.lower() == "sdtv":
                    q = "SDTV"
                if q.lower() == "bluray":
                    q = "Blu-Ray"
                if q.lower() == "dvdrip":
                    q = "DVDRip"

                formatted_quality.append(q)

            if len(formatted_quality) > 0:
                self.quality = formatted_quality
                self.save()

        return self.quality

    def get_date(self):
        if not self.date:
            parser = self.metaparser()
            if 'date' in parser.details:
                self.date = parser.details['date']
                self.save()
            elif 'year' in parser.details:
                self.date = datetime.strptime(parser.details['year'], '%Y')
                self.save()

        return self.date

    def retry(self):
        self.dlstart = None
        self.retries = 0
        self.video_files = None
        self.save()

    def get_type(self):
        from lazy_common import metaparser

        if self.type and self.type != metaparser.TYPE_UNKNOWN:
            return self.type

        if self.tvdbid_id:
            self.type = metaparser.TYPE_TVSHOW
            return self.type

        if self.section == "TVHD":
            self.type = metaparser.TYPE_TVSHOW
            return self.type

        if self.section == "HD" or self.section == "XVID":
            self.type = metaparser.TYPE_MOVIE
            return self.type

        if self.video_files:
            first_file = self.video_files[0]

            if 'tvdbid_id' in first_file:
                self.type = metaparser.TYPE_TVSHOW
                return self.type
            if 'imdbid_id' in first_file:
                self.type = metaparser.TYPE_MOVIE
                return self.type

        #Ok lets try let metaparser figure out the type
        parser = metaparser.get_parser_cache(self.title)
        if parser and parser.details:
            self.type = parser.type

        return self.type

    def metaparser(self):
        from lazy_common import metaparser

        if None is self.parser:
            type = self.get_type()

            if type == metaparser.TYPE_TVSHOW:
                self.parser = metaparser.get_parser_cache(self.title, type=metaparser.TYPE_TVSHOW)
            elif type == metaparser.TYPE_MOVIE:
                self.parser = metaparser.get_parser_cache(self.title, type=metaparser.TYPE_MOVIE)
            else:
                self.parser = metaparser.get_parser_cache(self.title)

        return self.parser

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
            logger.debug("%s:%s: %s " % (caller, line, msg))
        else:
            logger.debug(msg)


        self.downloadlog_set.create(download_id=self.id, message=logmsg)

    def get_speed(self):
        from lazy_client_core.utils import threadmanager
        return threadmanager.queue_manager.get_speed(self.id)

    def add_download(self, add_season, add_ep):

        add_season = str(add_season)

        if not self.onlyget:
            self.onlyget = {}

        if add_ep == 0:
            #if we are getting the whole season then remove any existing season/ep downloads
            try:
                del self.onlyget[add_season]
            except:
                pass

            self.onlyget[add_season] = []
            self.onlyget[add_season].append(add_ep)
        else:
            #we need to append the ep
            if add_season in self.onlyget:
                if 0 not in self.onlyget[add_season]:
                    self.onlyget[add_season].append(add_ep)
            else:
                self.onlyget[add_season] = []
                self.onlyget[add_season].append(add_ep)

        #If we are in a downloading or move state then we must reset it
        if self.status == DownloadItem.DOWNLOADING or self.status == DownloadItem.RENAME:
            self.reset()

    def delete(self):

        self.killjob()

        if self.localpath and os.path.exists(self.localpath):
            try:
                shutil.rmtree(self.localpath)
            except:
                del self.localpath

        super(DownloadItem, self).delete()

    def download_retry(self):
        #First lets try kill the task
        self.killjob(self)
        self.download()

    def killjob(self):
        from lazy_client_core.utils.threadmanager import queue_manager
        queue_manager.abort_dlitem(self.id)

    def reset(self, force=False):
        self.killjob()
        self.status = self.QUEUE
        self.save()

    def get_local_size(self):
        import os
        total_size = 0

        if not os.path.exists(self.localpath):
            return

        if os.path.isdir(self.localpath):
            for dirpath, dirnames, filenames in os.walk(self.localpath):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
        elif os.path.isfile(self.localpath):
            total_size = os.path.getsize(self.localpath)

        return total_size

    def get_finish_date(self):
        if self.status == DownloadItem.DOWNLOADING:
            from datetime import timedelta

            total_size = self.remotesize
            downloaded = self.get_local_size()
            speed = self.get_speed()

            if speed > 0:
                remaining = total_size - downloaded
                seconds_left = remaining / speed
                return datetime.now() + timedelta(seconds=seconds_left)

    def get_percent_complete(self):

        percent_complete = 0

        if self.status == DownloadItem.COMPLETE:
            return 100

        total_size = self.get_local_size()

        if self.remotesize == 0:
            percent_complete = 0
        else:
            if total_size > 0:
                percent_complete = total_size / self.remotesize * 100

        return percent_complete

    def clear_log(self):
        for obj in self.downloadlog_set.all():
            obj.delete()



@receiver(pre_save, sender=DownloadItem)
def add_new_downloaditem_pre(sender, instance, **kwargs):

    if instance.id is None:
        from lazy_common import metaparser
        logger.debug("Adding a new download %s" % instance.ftppath)

        instance.ftppath = instance.ftppath.strip()

        #Check if it exists already..
        try:
            existing_obj = DownloadItem.objects.get(ftppath=instance.ftppath)

            if existing_obj:
                logger.info("Found existing record %s" % instance.ftppath)

            if existing_obj.status == DownloadItem.COMPLETE:
                #its complete... maybe delete it so we can re-add if its older then 2 weeks?
                curTime = datetime.now()
                hours = 0

                if existing_obj.dateadded is None:
                    hours = 300
                else:
                    diff = curTime - existing_obj.dateadded.replace(tzinfo=None)
                    hours = diff.total_seconds() / 60 / 60

                if hours > 288:
                    existing_obj.delete()
                else:
                    raise AlradyExists()
            else:
                #lets update it with the new downloaded eps
                if instance.onlyget is not None:
                    for get_season, get_eps in instance.onlyget.iteritems():
                        for get_ep in get_eps:
                            existing_obj.add_download(get_season, get_ep)

                    existing_obj.reset()
                    existing_obj.save()
                    raise AlradyExists_Updated(existing_obj)
                raise AlradyExists_Updated(existing_obj)

        except ObjectDoesNotExist:
            pass

        #Set default status as download queue
        if instance.status is None:
            instance.status = 1

        #Get section and title
        if instance.section is None:
            split = instance.ftppath.split("/")

            try:
                section = split[1]
                title = split[-1]
            except:
                raise Exception("Unable to determine section from path %s" % instance.ftppath)

            if section:
                instance.section = section
            else:
                raise Exception("Unable to determine section from path %s" % instance.ftppath)

            if title:
                instance.title = title
            else:
                raise Exception("Unable to determine title from path %s" % instance.ftppath)

        #Figure out the local path
        if instance.localpath is None:
            if section == "XVID" or section == "HD":
                path = settings.MOVIE_PATH_TEMP
            elif section == "TVHD" or section == "TV":
                path = settings.TV_PATH_TEMP
            elif section == "REQUESTS":
                path = settings.REQUESTS_PATH_TEMP
            else:
                raise Exception("Unable to find section path in config: %s" % section)

            instance.localpath = os.path.join(path, instance.title)

        parser = instance.metaparser()
        title = None

        if 'title' in parser.details:
            title = parser.details['title']

        if 'series' in parser.details:
            title = TVShow.clean_title(parser.details['series'])

        if title:
            logger.info("Looking for existing %s in the queue" % title)

            type = instance.get_type()

            #Check if already in queue (maybe this is higher quality or proper).
            for dlitem in DownloadItem.objects.all().filter(Q(status=DownloadItem.QUEUE) | Q(status=DownloadItem.DOWNLOADING) | Q(status=DownloadItem.PENDING)):

                #If its a tvshow and the tvdbid does not match then skip
                if type == metaparser.TYPE_TVSHOW and dlitem.tvdbid_id and instance.tvdbid_id:
                    if instance.tvdbid_id != dlitem.tvdbid_id:
                        continue

                if type == metaparser.TYPE_MOVIE and dlitem.imdbid_id and instance.imdbid_id:
                    if instance.imdbid_id != dlitem.imdbid_id:
                        continue

                dlitem_title = None
                dlitem_parser = dlitem.metaparser()

                if 'title' in dlitem_parser.details:
                    dlitem_title = dlitem_parser.details['title']

                if 'series' in dlitem_parser.details:
                    dlitem_title = TVShow.clean_title(dlitem_parser.details['series'])

                if dlitem_title and dlitem_title.lower() == title.lower():

                    check = False
                    if parser.type == metaparser.TYPE_TVSHOW:
                        if 'season' in parser.details and 'episodeNumber' in parser.details and 'season' in dlitem_parser.details and 'episodeNumber' in dlitem_parser.details:
                            if parser.details['season'] == dlitem_parser.details['season'] and parser.details['episodeNumber'] == dlitem_parser.details['episodeNumber']:
                                check = True
                    else:
                        check = True

                    if check:

                        logger.info("Found %s already in queue, lets see what is better quality" % dlitem.title)

                        if dlitem_parser.quality > parser.quality:
                            logger.info("Download already existsin queue with better quality will ignore this one")
                            raise AlradyExists_Updated(dlitem)
                        else:
                            logger.info("Deleting %s from queue as it has a lower quality" % dlitem.title)
                            dlitem.delete()

        #Ok now we know its a valid downloaditem lets add it to the db
        tvdbapi = Tvdb()
        type = instance.get_type()

        from lazy_common import metaparser

        #must be a tvshow
        if type == metaparser.TYPE_TVSHOW:
            if instance.tvdbid_id is None:
                logger.debug("Looks like we are working with a TVShow, lets try find the tvdb object")

                #We need to try find the series info
                parser = instance.metaparser()

                if parser.details and 'series' in parser.details:
                    series_name = TVShow.clean_title(parser.details['series'])

                    #search via database first
                    found = TVShow.find_by_title(series_name)

                    if found:
                        instance.tvdbid_id = found.id
                    else:
                        try:
                            match = tvdbapi[series_name]
                            logger.debug("Show found")
                            instance.tvdbid_id = int(match['id'])

                            if match['imdb_id'] is not None:
                                logger.debug("also found imdbid %s from thetvdb" % match['imdb_id'])
                                instance.imdbid_id = int(match['imdb_id'].lstrip("tt"))
                        except tvdb_shownotfound:
                            logger.exception("Error finding show on thetvdb %s" % series_name)
                        except Exception as e:
                            logger.exception("Error finding : %s via thetvdb.com due to  %s" % (series_name, e.message))
                else:
                    logger.exception("Unable to parse series info")

        else:
            #must be a movie!
            if instance.imdbid_id is None:
                logger.debug("Looks like we are working with a Movie")
                #Lets try find the movie details
                parser = instance.metaparser()

                movie_title = parser.details['title']

                if 'year' in parser.details:
                    movie_year = parser.details['year']
                else:
                    movie_year = None

                imdbs = ImdbSearch()
                results = imdbs.best_match(movie_title, movie_year)

                if results and results['match'] > 0.70:
                    movieObj = ImdbParser()
                    movieObj.parse(results['url'])

                    logger.debug("Found imdb movie id %s" % movieObj.imdb_id)

                    instance.imdbid_id = int(movieObj.imdb_id.lstrip("tt"))
                else:
                    logger.debug("Didnt find a good enough match on imdb")

        #Now we have sorted both imdbid and thetvdbid lets sort it all out

        #If we have a tvdbid do we need to add it to the db or does it exist or ignored?
        if instance.tvdbid_id is not None and instance.tvdbid_id != "":

            #Does it already exist?
            try:
                if instance.tvdbid:
                    #Do we need to update it
                    curTime = datetime.now()
                    hours = 0

                    if instance.tvdbid.updated is None:
                        hours = 50
                    else:
                        diff = curTime - instance.tvdbid.updated.replace(tzinfo=None)
                        hours = diff.total_seconds() / 60 / 60

                    if hours > 24:
                        try:
                            instance.tvdbid.update_from_tvdb()
                            instance.tvdbid.save()
                        except Exception as e:
                            logger.exception("Error updating TVDB info %s" % e.message)
            except ObjectDoesNotExist as e:
                logger.debug("Getting tvdb data for release")

                new_tvdb_item = TVShow()
                new_tvdb_item.id = instance.tvdbid_id
                try:
                    new_tvdb_item.save()
                except:
                    instance.tvdbid = None
                    pass

            if instance.tvdbid.ignored:
                logger.info("Show wont be added as it is marked as ignored")
                raise Ignored("Show wont be added as it is marked as ignored")

        #If we have a imdbid do we need to add it to the db or does it exist
        if instance.imdbid_id is not None and instance.imdbid_id != "":
            try:
                if instance.imdbid:
                    #Do we need to update it
                    curTime = datetime.now()
                    imdb_date = instance.imdbid.updated

                    try:
                        if imdb_date:
                            diff = curTime - instance.imdbid.updated.replace(tzinfo=None)
                            hours = diff.total_seconds() / 60 / 60
                            if hours > 24:
                                instance.imdbid.update_from_imdb()
                        else:
                            instance.imdbid.update_from_imdb()
                    except ObjectDoesNotExist as e:
                            logger.info("Error updating IMDB info as it was not found")

            except ObjectDoesNotExist as e:
                logger.debug("Getting IMDB data for release")

                new_imdb = Movie()
                new_imdb.id = instance.imdbid_id

                try:
                    new_imdb.save()
                except ObjectDoesNotExist:
                    instance.imdbid_id = None

            if instance.imdbid.ignored:
                logger.info("Movie wont be added as it is marked as ignored")
                raise Ignored("Movie cannot be added as it is marked as ignored")
