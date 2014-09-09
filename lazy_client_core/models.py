from __future__ import division

from datetime import timedelta
import urllib2
import logging
import shutil
import os
import re
from datetime import datetime
import inspect
import time

from picklefield.fields import PickledObjectField
from requests.exceptions import HTTPError
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from south.modelsinspector import add_introspection_rules
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from flexget.utils.imdb import ImdbSearch, ImdbParser
from celery.contrib.abortable import AbortableAsyncResult
from django.db.models import Q

from lazy_client_core.utils import common
from PIL import Image
from lazy_common import utils

from lazy_client_core.utils.common import OverwriteStorage
from lazy_common.utils import bytes2human
from lazy_common import ftpmanager
from lazy_common.tvdb_api import Tvdb
from lazy_client_core.exceptions import AlradyExists_Updated, AlradyExists
from lazy_client_core.exceptions import DownloadException
from lazy_client_core.utils.jsonfield.fields import JSONField


logger = logging.getLogger(__name__)

add_introspection_rules([], ["^lazy_client_core\.utils\.jsonfield\.fields\.JSONField"])

from django.db import models

class Version(models.Model):
    class Meta:
        """ Meta """
        db_table = 'version'

    version = models.IntegerField()

#############################################################
#############################################################
####################### DOWNLOAD ITEM #######################
#############################################################
#############################################################

class DownloadItem(models.Model):
    class Meta:
        """ Meta """
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
    priority = models.IntegerField(default=10, null=True)
    requested = models.BooleanField(default=False)
    localsize = models.IntegerField(default=0, null=True)
    message = models.TextField(blank=True, null=True)
    imdbid = models.ForeignKey('Movie', blank=True, null=True, on_delete=models.DO_NOTHING)
    tvdbid = models.ForeignKey('TVShow', blank=True, null=True, on_delete=models.DO_NOTHING)
    onlyget = JSONField(blank=True, null=True)
    video_files = JSONField(blank=True, null=True)

    parser = None

    def get_season(self):
        parser = self.metaparser()
        if 'season' in parser.details:
            return parser.details['season']

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

        logger.debug(msg)

        try:
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0])

            caller = mod.__name__
            line = inspect.currentframe().f_back.f_lineno

            logmsg = "%s(%s): %s" % (caller, line, msg)

        except:
            logmsg = msg

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
                self.onlyget[add_season].append(add_ep)
            else:
                self.onlyget[add_season] = []
                self.onlyget[add_season].append(add_ep)

        #If we are in a downloading or move state then we must reset it
        if self.status == DownloadItem.DOWNLOADING or self.status == DownloadItem.RENAME:
            self.reset()

    def increate_priority(self):
        self.priority -= 1
        self.save()

    def decrease_prioritys(self):
        self.priority += 1
        self.save()

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
            try:
                path = getattr(settings, section + "_TEMP")
                instance.localpath = os.path.join(path, instance.title)
            except:
                raise Exception("Unable to find section path in config: %s" % section)

        parser = instance.metaparser()
        title = None

        if 'title' in parser.details:
            title = parser.details['title']

        if 'series' in parser.details:
            title = parser.details['series']

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
                    dlitem_title = dlitem_parser.details['series']

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

                if parser.details:
                    series_name = parser.details['series']

                    try:
                        match = tvdbapi[series_name]
                        logger.debug("Show found")
                        instance.tvdbid_id = int(match['id'])

                        if match['imdb_id'] is not None:
                            logger.debug("also found imdbid %s from thetvdb" % match['imdb_id'])
                            instance.imdbid_id = int(match['imdb_id'].lstrip("tt"))

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

    #If we have a tvdbid do we need to add it to the db or does it exist
    if instance.tvdbid_id is not None:
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

        except Exception as e:
            logger.exception("error gettig imdb %s information.. from website %s" %  (instance.imdbid_id, e.message))



#############################################################
#############################################################
########################## Movie ############################
#############################################################
#############################################################

class Movie(models.Model):

    class Meta:
        db_table = 'imdbcache'

    def __unicode__(self):
        return self.title

    title = models.CharField(max_length=200, db_index=True)
    score = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    votes = models.IntegerField(default=0, blank=True, null=True)
    year = models.IntegerField(default=0, blank=True, null=True)
    genres = models.CharField(max_length=200, blank=True, null=True)
    posterimg = models.ImageField(upload_to=".", storage=OverwriteStorage(), blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)
    localpath = models.CharField(max_length=255, blank=True, null=True)

    def get_genres(self):
        genres = []

        if self.genres:
            for genre in self.genres.split("|"):
                genres.append(genre)
        return genres

    def update_from_imdb(self):
        imdbtt = "tt" + str(self.id).zfill(7)

        logger.info("Updating %s %s" % (imdbtt, self.title))

        try:
            imdbobj = ImdbParser()
            imdbobj.parse(imdbtt)

            self.score = imdbobj.score
            self.title = imdbobj.name.encode('ascii', 'ignore')
            self.year = imdbobj.year
            self.votes = imdbobj.votes

            if imdbobj.plot_outline:
                self.description = imdbobj.plot_outline.encode('ascii', 'ignore')

            sGenres = ''

            if imdbobj.genres:
                for genre in imdbobj.genres:
                    sGenres += '|' + genre.encode('ascii', 'ignore')

            self.genres = sGenres.replace('|', '', 1)

            if imdbobj.photo:
                try:
                    img_download = NamedTemporaryFile(delete=True)
                    img_download.write(urllib2.urlopen(imdbobj.photo).read())
                    img_download.flush()

                    size = 214, 317

                    if os.path.getsize(img_download.name) > 0:
                        img_tmp = NamedTemporaryFile(delete=True)
                        im = Image.open(img_download.name)
                        im = im.resize(size, Image.ANTIALIAS)
                        im.save(img_tmp, "JPEG", quality=70)

                        self.posterimg.save(str(self.id) + '-imdb.jpg', File(img_tmp))
                except Exception as e:
                    logger.error("error saving image: %s" % e.message)

            self.save()
            self.updated = datetime.now()
            self.save()
        except HTTPError as e:
            if e.errno == 404:
                logger.error("Error entry was not found in imdn!")
                raise ObjectDoesNotExist()


@receiver(post_save, sender=Movie)
def add_new_imdbitem(sender, created, instance, **kwargs):

    if created:
        logger.info("Adding a new imdbitem, lets make sure its fully up to date")
        instance.update_from_imdb()


#######################################################
######################### JOBS ########################
#######################################################

class Job(models.Model):

    def __unicode__(self):
        return self.title

    type = models.IntegerField(blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)
    startdate = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    finishdate = models.DateTimeField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    report = JSONField(blank=True, null=True)

    class Meta:
        db_table = 'jobs'

    def log(self, msg):

        logger.debug(msg)

        try:
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0])

            caller = mod.__name__
            line = inspect.currentframe().f_back.f_lineno

            logmsg = "%s(%s): %s" % (caller, line, msg)

        except:
            logmsg = msg

        self.downloadlog_set.create(job_id=self.id, message=logmsg)


###################################################
###################### LOG ########################
###################################################


class DownloadLog(models.Model):

    def __unicode__(self):
        try:
            return self.title
        except:
            return "TITLE NOT FOUND"

    download_id = models.ForeignKey('DownloadItem', null=True, blank=True)
    job_id = models.ForeignKey('Job', null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'download_log'


#########################################################
#################### TV SHOW MAPPING ####################
#########################################################

class TVShowMappings(models.Model):
    class Meta:
        """ Meta """
        db_table = 'tvshowmappings'
        ordering = ['-id']

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



######################################################
##################### TV SHOW ########################
######################################################

class TVShowExcpetion():
    """
    """

class TVShow(models.Model):

    class Meta:
        db_table = 'tvdbcache'

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
            tvdbshow_obj = tvdbapi[os.path.basename(tvshow_path)]
            tvdbcache_obj = TVShow.objects.get(id=tvdbshow_obj)
            logger.debug("Found matching tvdbcache item %s" % self.tvdbcache_obj.id)
            return tvdbcache_obj
        except:
            pass

        raise Exception("Didn't find matchin tvshow object")

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

    def get_latest_season(self):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            now = datetime.now() - timedelta(days=2)

            #loop through each season
            for season in reversed(tvdb_obj.keys()):

                #Lets loop through each ep..
                for ep in reversed(tvdb_obj[season].keys()):
                    ep_obj = self.tvdbshow_obj[season][ep]

                    aired_date = ep_obj['firstaired']

                    if aired_date is not None:
                        aired_date = datetime.strptime(aired_date, '%Y-%m-%d')

                        if now > aired_date:
                            #Found the ep and season
                            return int(season)
        return 1

    def get_existing_eps(self, season):
        from lazy_common import metaparser
        if self.tvshow_path:
            season_folder = common.find_season_folder(self.tvshow_path, season)

            found = []

            if os.path.exists(season_folder):
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

    def get_missing_eps_season(self, season):
        logger.info("Checking for missing eps in season season %s" % season)
        missing = []

        #get latest ep of this season
        tvdb_latest_ep = self.get_latest_ep(season)
        logger.info("Latest ep for season %s is %s" % (season, tvdb_latest_ep))

        season_path = common.find_season_folder(self.tvshow_path, season)

        if not season_path or not os.path.isdir(season_path):
            missing.append("ALL")
        else:
            #Find all the existing Eps..
            existing_eps = self.get_existing_eps(season)

            #Now lets figure out whats actually missing
            for ep_no in range(1, tvdb_latest_ep + 1):
                if ep_no not in existing_eps:
                    missing.append(ep_no)

        return missing

    def get_missing(self, check_seasons=[]):
        logger.info("Looking for missing eps in %s" % self.tvshow_path)

        #If none specified then try fix everything.. (all seasons, eps)
        if len(check_seasons) == 0:
            for season in self.get_all_seasons():
                check_seasons.append(season)

        missing = {}

        for cur_season in range(1, self.latest_season + 1):
            #do we want to process this season?
            if cur_season not in check_seasons:
                logger.debug("Wont check season %s" % cur_season)
                continue
            else:
                missing_eps = self.get_missing_eps_season(cur_season)

            if len(missing_eps) > 0:
                missing[cur_season] = missing_eps

        return missing

    def get_seasons(self):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            tvdb_obj = self.tvdbapi[self.id]
            return tvdb_obj.keys()

    def get_eps(self, season):
        tvdb_obj = self.tvdbapi[self.id][season]
        return tvdb_obj.keys()

    def get_titles(self, refresh=True):

        if refresh:
            alt_names = []

            #Now lets figure out what title we should search for on sites
            for search, replace in settings.TVSHOW_AUTOFIX_REPLACEMENTS.items():
                fixed_name = self.title.replace(search, replace)

            alt_names.append(fixed_name)

            #list of alt names on tvdb.com
            search_results = self.tvdbapi.search(self.title)

            for result in search_results:
                if result['seriesid'] == str(self.id):
                    if 'aliasnames' in result:
                        for alias in result['aliasnames']:
                            if alias not in alt_names:
                                alt_names.append(alias)
                    break

            #show mappings
            mappings = TVShowMappings.objects.all().filter(tvdbid_id=self.id)

            for mapping in mappings:
                map_name = mapping.title

                for search, replace in settings.TVSHOW_AUTOFIX_REPLACEMENTS.items():
                    map_name = map_name.replace(search, replace)

                if map_name not in mappings:
                    alt_names.insert(0, map_name)

            self.alt_names = alt_names

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

    def get_tvdb_obj(self):
        if self.tvdb_obj:
            return self.tvdb_obj

        if self.id:
            try:
                self.tvdb_obj = self.tvdbapi[self.id]
                logger.info("Found on thetvdb %s" % self.tvdbshow_obj['id'])
                return self.tvdbshow_obj
            except:
                pass
        elif self.title:
            try:
                self.tvdbshow_obj = self.tvdbapi[self.title]
                logger.info("Found matching tvdbcache item %s" % self.tvdbshow_obj['id'])
                return self.tvdbshow_obj
            except:
                pass
        elif self.alt_names:
            for name in self.alt_name:
                try:
                    self.tvdb_obj = self.tvdbapi[name]
                    logger.info("Found matching tvdbcache item %s" % tvdbshow_obj['id'])
                    return tvdbshow_obj
                except:
                    pass

        return self.tvdb_obj

    def update_names(self):
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj and 'seriesname' in tvdb_obj.data:
                if tvdb_obj['seriesname'] is not None:
                    self.title = tvdb_obj['seriesname'].replace(".", " ").strip()

        self.alt_names = self.get_titles(refresh=True)

    def get_network(self, refresh=False):
        if refresh:
            tvdb_obj = self.get_tvdb_obj()

            if tvdb_obj and 'network' in tvdb_obj.data:
                if tvdb_obj['network'] is not None:
                    self.networks = tvdb_obj['network']

        return self.networks

    def get_description(self, refresh=False):
        if refresh:
            tvdb_obj = self.get_tvdb_obj()

            if 'overview' in tvdb_obj.data:
                if tvdb_obj['overview'] is not None:
                    self.description = tvdb_obj['overview'].encode('ascii', 'ignore')

        return self.description

    def get_genres(self, refresh=False):
        if refresh:
            tvdb_obj = self.get_tvdb_obj()

            if tvdb_obj and 'genre' in tvdb_obj.data:
                if tvdb_obj['genre'] is not None:
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

                        try:
                            imdbobj = Movie.objects.get(id=int(imdbid_id))
                        except ObjectDoesNotExist:
                            imdbobj = Movie()
                            imdbobj.id = int(imdbid_id)
                            imdbobj.save()

                    except:
                        pass

        return self.imdbid

    def update_from_tvdb(self):

        logger.info("Updating %s %s" % (str(self.id), self.title))
        tvdb_obj = self.get_tvdb_obj()

        if tvdb_obj:
            #Lets update everything..
            self.update_names()
            self.get_network(refresh=True)
            self.get_genres(refresh=True)
            self.get_description(refresh=True)
            self.get_posterimg(refresh=True)
            self.get_imdb(refresh=True)
            self.updated = datetime.now()
            self.save()

@receiver(post_save, sender=TVShow)
def add_new_tvdbitem(sender, created, instance, **kwargs):

    if created:
        logger.info("Adding a new tvdbitem, lets make sure its fully up to date")

        #First lets find the tvdbid
        if not instance.id:
            instance.id = instance.get_tvdbid()

        instance.update_from_tvdb()
