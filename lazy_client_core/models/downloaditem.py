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
from celery.contrib.abortable import AbortableAsyncResult
from django.db.models import Q
from lazy_common import ftpmanager
from lazy_common.tvdb_api import Tvdb
from lazy_client_core.exceptions import AlradyExists_Updated, AlradyExists, Ignored
from lazy_client_core.exceptions import DownloadException
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

    title = models.CharField(max_length=150, db_index=True, blank=True, null=True)
    section = models.CharField(max_length=10, db_index=True, blank=True, null=True)
    ftppath = models.CharField(max_length=255, db_index=True, unique=True)
    localpath = models.CharField(max_length=255, blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, blank=True, null=True)
    pid = models.IntegerField(default=0, null=True)
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

    parser = None

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
                    if season in self.onlyget and ep in self.onlyget[season]:
                        return True
                else:
                    #downloading all eps
                    return True
            else:
                if ep in self.get_eps():
                    return True
        return False

    def get_season(self):
        parser = self.metaparser()
        if 'season' in parser.details:
            return parser.details['season']

    def get_seasons(self):
        parser = self.metaparser()
        return parser.get_seasons()

    def get_eps(self):
        parser = self.metaparser()

        if 'episodeList' in parser.details:
            return parser.details['episodeList']
        elif 'episodeNumber' in parser.details:
            return [parser.details['episodeNumber']]

    def get_quality(self):
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

        return formatted_quality

    def get_year(self):
        parser = self.metaparser()

        if 'year' in parser.details:
            return parser.details['year']

    def retry(self):
        self.dlstart = None
        self.retries = 0
        self.video_files = None
        self.save()

    def get_type(self):
        from lazy_common import metaparser

        if self.tvdbid_id:
            return metaparser.TYPE_TVSHOW

        if self.section == "TVHD":
            return metaparser.TYPE_TVSHOW

        if self.section == "HD" or self.section == "XVID":
            return metaparser.TYPE_MOVIE

        if self.video_files:
            first_file = self.video_files[0]

            if 'tvdbid_id' in first_file:
                return metaparser.TYPE_TVSHOW
            if 'imdbid_id' in first_file:
                return metaparser.TYPE_MOVIE

        return metaparser.TYPE_UNKNOWN


    def metaparser(self):
        from lazy_common import metaparser

        if None is self.parser:
            type = self.get_type()

            if type == metaparser.TYPE_TVSHOW:
                self.parser = metaparser.get_parser_cache(self.title, type=metaparser.TYPE_TVSHOW)
            elif type == metaparser.TYPE_MOVIE:
                self.parser = metaparser.get_parser_cache(self.title, type=metaparser.TYPE_MOVIE)
            else:

                title_parser = metaparser.get_parser_cache(self.title)

                is_tv_show = False

                if 'series' in title_parser.details or re.search("(?i).+\.[P|H]DTV\..+", self.title):
                    is_tv_show = True

                if is_tv_show:
                    self.parser = metaparser.get_parser_cache(self.title, type=metaparser.TYPE_TVSHOW)
                else:
                    self.parser = metaparser.get_parser_cache(self.title, type=metaparser.TYPE_MOVIE)

                if None is self.parser:
                    self.parser = title_parser

        return self.parser

    def download(self):

        self.dlstart = datetime.now()

        #Find jobs running and if they are finished or not
        task = self.get_task()

        logger.debug("Job task state: %s" % task)

        if None is task:
            pass
        elif task.state == "SUCCESS" or task.state == "FAILURE" or task.state == "ABORTED":
            pass
        elif task.state == "PENDING":
            raise DownloadException("%s might of been started already status: %s" % (self.ftppath, task.state))
        else:
            raise DownloadException("%s already being downloaded, task status %s" % (self.ftppath, task.state))

        if self.onlyget:
            #we dont want to get everything.. lets figure this out
            files, remotesize = ftpmanager.get_required_folders_for_multi(self.ftppath, self.onlyget)
        else:
            files, remotesize = ftpmanager.get_files_for_download(self.ftppath)

        if remotesize > 0 and len(files) > 0:
            self.remotesize = remotesize
        else:
            raise DownloadException("Unable to get size and files on the FTP")

        #Time to start.
        from lazy_client_core.utils.mirror import FTPMirror
        mirror = FTPMirror()
        task = mirror.mirror_ftp_folder.delay(files, self)
        self.taskid = task.task_id
        self.message = None
        self.status = DownloadItem.DOWNLOADING
        self.save()

    def task_result(self):
        try:
            task = self.get_task()
            return task.result
        except:
            pass

    def download_status(self):
        logger.debug("%s Getting status of download: " % self.title)
        logger.debug("task id is %s" % self.taskid)

        from celery.backends.amqp import BacklogLimitExceeded
        task = self.get_task()

        if None is task:
            logger.debug("No job associated with this downloaditem")
            return self.JOB_NOT_FOUND

        try:
            state = task.state
        except BacklogLimitExceeded:
            return self.JOB_FAILED

        logger.debug("Task state :%s" % state)

        status = self.JOB_PENDING

        if state == "SUCCESS":
            status = self.JOB_FINISHED

        if state == "FAILURE":
            status = self.JOB_FAILED

        if state == "RUNNING":
            status = self.JOB_RUNNING


        return status


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

        speed = 0

        if self.still_alive():
            task = self.get_task()

            if task:
                result = task.result
                if 'speed' in result:
                    speed = result['speed']

        return speed

    def still_alive(self):
        task = self.get_task()

        try:
            if task:
                result = task.result

                seconds_now = time.mktime(datetime.now().timetuple())

                if result and 'updated' in result:
                    seconds_updated = result['updated']

                    seconds = seconds_now - seconds_updated

                    if seconds < 240:
                        #we have received an update in the last 240 seconds, its still running
                        return True
        except:
            pass

        return False

    def get_task(self):
        if self.taskid == None or self.taskid == "":
            return None

        return AbortableAsyncResult(self.taskid)


    def add_download(self, add_season, add_ep):
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

        try:
            self.killtask()
        except:
            pass

        if self.localpath and os.path.exists(self.localpath):
            try:
                shutil.rmtree(self.localpath)
            except:
                del self.localpath

        super(DownloadItem, self).delete()

    def download_retry(self):
        #First lets try kill the task
        try:
            self.killtask()
        except:
            pass

        self.taskid = None
        self.download()

    def last_error(self):
        task = self.get_task()
        last_error = ""

        task = self.get_task()

        if task:
            result = task.result
            if 'last_error' in result:
                last_error = result['last_error']

        return last_error

    def killtask(self):
        task = self.get_task()

        if None is task:
            return

        if task.ready():
            return

        #lets try kill it
        task.abort()

        for i in range(0, 20):
            if task.ready():
                return

            time.sleep(1)

        raise Exception("Unable to kill download task/job")

    def reset(self, force=False):
        if force:
            try:
                self.killtask()
            except:
                pass
        else:
            self.killtask()

        self.status = self.QUEUE
        self.taskid = None
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
                    hours = diff.seconds / 60 / 60

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
                    #now compare them
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
                            if parser.details['season'] == dlitem_parser.details['season'] and parser.details['season'] == dlitem_parser.details['episodeNumber']:
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
        type = instance.metaparser().type

        from lazy_common import metaparser

        #must be a tvshow
        if type == metaparser.TYPE_TVSHOW:
            if instance.tvdbid_id is None:
                logger.debug("Looks like we are working with a TVShow")

                #We need to try find the series info
                parser = instance.metaparser()

                if parser.details and 'series' in parser.details:
                    series_name = TVShow.clean_title(parser.details['series'])

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
                    hours = diff.seconds / 60 / 60

                if hours > 24:
                    try:
                        instance.tvdbid.update_from_tvdb()
                    except Exception as e:
                        logger.exception("Error updating TVDB info %s" % e.message)
        except ObjectDoesNotExist as e:
            logger.debug("Getting tvdb data for release")

            new_tvdb_item = TVShow()
            new_tvdb_item.id = instance.tvdbid_id
            new_tvdb_item.save()

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
                        hours = diff.seconds / 60 / 60
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
