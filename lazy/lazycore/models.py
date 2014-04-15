from __future__ import division
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import logging, os, re
from lazycore.utils.tvdb_api import Tvdb
from datetime import datetime
from flexget.utils.imdb import ImdbSearch, ImdbParser
from lazycore.exceptions import AlradyExists_Updated, AlradyExists
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
import urllib2
from lazycore.utils import ftpmanager
import inspect
from celery.result import AsyncResult
from lazycore.exceptions import DownloadException
import time
from lazycore.utils.jsonfield.fields import JSONField
from celery.task.control import revoke
from lazycore.utils.ftpmanager.mirror import FTPMirror
from django.core.cache import cache

from django.db.models import Q
from flexget.utils import qualities

logger = logging.getLogger(__name__)

from south.modelsinspector import add_introspection_rules

add_introspection_rules([], ["^lazycore\.utils\.jsonfield\.fields\.JSONField"])


class TVShowMappings(models.Model):
    class Meta:
        """ Meta """
        db_table = 'tvshowmappings'
        ordering = ['-id']

    title = models.CharField(max_length=150, db_index=True, unique=True)
    tvdbid = models.ForeignKey('Tvdbcache', on_delete=models.DO_NOTHING)


class DownloadLog(models.Model):

    def __unicode__(self):
        try:
            return self.title
        except:
            return "TITLE NOT FOUND"

    download_id = models.ForeignKey('DownloadItem')
    date = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'download_log'


class Version(models.Model):
    class Meta:
        """ Meta """
        db_table = 'version'

    version = models.IntegerField()


class DownloadItem(models.Model):
    class Meta:
        """ Meta """
        db_table = 'download'
        ordering = ['id']

    def __unicode__(self):
        return self.title

    QUEUE = 1
    DOWNLOADING = 2
    MOVE = 3
    COMPLETE = 4
    ERROR = 5
    PENDING = 6

    JOB_NO_RESPONSE = 10
    JOB_RUNNING = 11
    JOB_PENDING = 12
    JOB_FAILED = 13
    JOB_NOT_FOUND = 14
    JOB_FINISHED = 15

    STATUS_CHOICES = (
        (QUEUE, 'Queue'),
        (DOWNLOADING, 'Downloading'),
        (MOVE, 'Move'),
        (COMPLETE, 'Complete'),
        (ERROR, 'Error'),
        (PENDING, 'Pending'),

    )

    title = models.CharField(max_length=150, db_index=True, blank=True, null=True)
    section = models.CharField(max_length=10, db_index=True, blank=True, null=True)
    ftppath = models.CharField(max_length=255, db_index=True, unique=True)
    localpath = models.CharField(max_length=255, blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, blank=True, null=True)
    pid = models.IntegerField(default=0, null=True)
    taskid = models.CharField(max_length=255, blank=True, null=True)
    retries = models.IntegerField(default=0, null=True)
    dateadded = models.DateTimeField(db_index=True, auto_now_add=True, blank=True)
    dlstart = models.DateTimeField(blank=True, null=True)
    remotesize = models.BigIntegerField(default=0, null=True)
    priority = models.IntegerField(default=10, null=True)
    requested = models.BooleanField(default=False)
    localsize = models.IntegerField(default=0, null=True)
    message = models.TextField(blank=True, null=True)
    imdbid = models.ForeignKey('Imdbcache', blank=True, null=True, on_delete=models.DO_NOTHING)
    tvdbid = models.ForeignKey('Tvdbcache', blank=True, null=True, on_delete=models.DO_NOTHING)
    epoverride = models.IntegerField(default=0, blank=True, null=True)
    seasonoverride = models.IntegerField(default=0, blank=True, null=True)
    onlyget = JSONField(blank=True, null=True)

    def extract(self):

        LOCK_EXPIRE = 60 * 10
        lock_id = "model-%s-lock" % self.title
        acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.delete(lock_id)

        if not acquire_lock():
            logger.debug("Already extracting %s , exiting" % self.download_item.title)
            raise Exception("Already extracting")

        try:
            parser = self.metaparser()

            if parser.type == parser.TYPE_TVSHOW:
                from lazycore.utils.extractor.tvshow import TVExtractor
                extractor = TVExtractor()
                extractor.extract()
            elif parser.type == parser.TYPE_MOVIE:
                from lazycore.utils.extractor.movie import MovieExtractor
            else:
                raise Exception("Unable to figure out if this is a movie or tvshow")
        finally:
            release_lock()

    def metaparser(self):
        from lazycore.utils.metaparser import MetaParser

        if self.section == "HD" or self.section == "XVID":
            parser = MetaParser(self.title, type=MetaParser.TYPE_MOVIE)
        elif self.section == "TVHD":
            parser = MetaParser(self.title, type=MetaParser.TYPE_TVSHOW)
        else:
            parser = MetaParser(self.title)

        return parser

    def download(self):

        self.dlstart = datetime.now()

        #Find jobs running and if they are finished or not
        task = self.get_task()

        logger.debug("Job task state: %s" % task)

        if None is task:
            pass
        elif task.state == "REVOKED":
            logger.info("%s was revoked. ignore" % self.ftppath)
            return
        elif task.state == "SUCCESS" or task.state == "FAILURE":
            pass
        else:
            self.log("%s already being downloaded" % self.ftppath)
            return

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

        task = self.get_task()

        if None is task:
            logger.debug("No job associated with this downloaditem")
            return self.JOB_NOT_FOUND

        state = task.state

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
                    from lazycore.utils import common
                    speed = common.bytes2human(result['speed'], "%(value).1f %(symbol)s/sec")


        return speed

    def still_alive(self):
        task = self.get_task()

        try:
            if task:
                result = task.result

                logger.debug("Task result :%s" % result)

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
            logger.debug("No taskid found for %s" % self.title)
            return None

        return AsyncResult(self.taskid)


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
        if self.status == DownloadItem.DOWNLOADING or self.status == DownloadItem.MOVE:
            self.reset()

    def increate_priority(self):
        self.priority -= 1
        self.save()

    def decrease_prioritys(self):
        self.priority += 1
        self.save()

    def delete(self):
        import os, shutil

        try:
            self.killtask()
        except:
            pass

        if os.path.exists(self.localpath):
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

        if task.state == "PENDING":
            revoke(self.taskid, terminate=True, signal='SIGKILL')
            return

        if task.ready():
            return

        #lets try kill it
        for i in range(0, 6):
            task = self.get_task()
            revoke(self.taskid, terminate=True, signal='SIGKILL')

            if task.ready():
                return

            time.sleep(5)

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


class Imdbcache(models.Model):

    class Meta:
        db_table = 'imdbcache'

    def __unicode__(self):
        return self.title

    title = models.CharField(max_length=200, db_index=True)
    score = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    votes = models.IntegerField(default=0, blank=True, null=True)
    year = models.IntegerField(default=0, blank=True, null=True)
    genres = models.CharField(max_length=200, blank=True, null=True)
    posterimg = models.ImageField(upload_to=".", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)
    localpath = models.CharField(max_length=255, blank=True, null=True)

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
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(urllib2.urlopen(imdbobj.photo).read())
                img_temp.flush()

                self.posterimg.save(str(self.id) + '-imdb.jpg', File(img_temp))

            self.save()
            self.updated = datetime.now()
            self.save()
        except Exception as e:
            logger.error("Error updating entry %s" % e)

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

class Tvdbcache(models.Model):

    class Meta:
        db_table = 'tvdbcache'

    def __unicode__(self):
        return self.title

    title = models.CharField(max_length=200, db_index=True)
    posterimg = models.ImageField(upload_to=".", blank=True, null=True)
    networks = models.CharField(max_length=50, blank=True, null=True)
    genres = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(max_length=255, blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)
    imdbid = models.ForeignKey('Imdbcache', blank=True, null=True, on_delete=models.DO_NOTHING)
    localpath = models.CharField(max_length=255, blank=True, null=True)

    def get_seasons(self):
        tvdbapi = Tvdb()
        tvdb_obj = tvdbapi[self.id]
        return tvdb_obj.keys()

    def get_eps(self, season):
        tvdbapi = Tvdb()
        tvdb_obj = tvdbapi[self.id][season]
        return tvdb_obj.keys()

    def names(self):
        alt_names = []

        #Now lets figure out what title we should search for on sites
        fixed_name = self.title

        for search, replace in settings.TVSHOW_AUTOFIX_REPLACEMENTS.items():
            fixed_name = fixed_name.replace(search, replace)

        alt_names.append(fixed_name)

        #if self.title not in alt_names:
        #    alt_names.append(self.title)

        #list of alt names on tvdb.com
        try:
            tvdbapi = Tvdb()
            search_results = tvdbapi.search(self.title)

            for result in search_results:
                if result['seriesid'] == str(self.id):
                    if 'aliasnames' in result:
                        for alias in result['aliasnames']:
                            if alias not in alt_names:
                                alt_names.append(alias)
                    break
        except:
            pass

        #show mappings
        try:
            mappings = TVShowMappings.objects.all().filter(tvdbid_id=self.id)

            if mappings:
                for map in mappings:
                    map_name = map.title

                    for search, replace in settings.TVSHOW_AUTOFIX_REPLACEMENTS.items():
                        map_name = map_name.replace(search, replace)

                    if map_name not in mappings:
                        alt_names.append(map_name)

        except Exception as e:
            logger.exception(e)
            pass

        return alt_names

    def update_from_tvdb(self):
        logger.info("Updating %s %s" % (str(self.id), self.title))

        try:
            tvdbapi = Tvdb(banners=True)
            tvdb_obj = tvdbapi[self.id]

            self.updated = datetime.now()

            if 'seriesname' in tvdb_obj.data:
                if tvdb_obj['seriesname'] is not None:
                    self.title = tvdb_obj['seriesname'].replace(".", " ").strip()

            if 'network' in tvdb_obj.data:
                if tvdb_obj['network'] is not None:
                    self.networks = tvdb_obj['network']

            if 'overview' in tvdb_obj.data:
                if tvdb_obj['overview'] is not None:
                    self.description = tvdb_obj['overview'].encode('ascii', 'ignore')

            if 'imdb_id' in tvdb_obj.data:
                if tvdb_obj['imdb_id'] is not None:
                    try:
                        imdbid_id = tvdb_obj['imdb_id'].lstrip("tt")
                        self.imdbid_id = int(imdbid_id)

                        try:
                            imdbobj = Imdbcache.objects.get(id=int(imdbid_id))
                        except ObjectDoesNotExist:
                            imdbobj = Imdbcache()
                            imdbobj.id = int(imdbid_id)
                            imdbobj.save()

                    except:
                        pass

            if '_banners' in tvdb_obj.data:
                if tvdb_obj['_banners'] is not None:
                    bannerData = tvdb_obj['_banners']

                    if 'poster' in bannerData.keys():
                        posterSize = bannerData['poster'].keys()[0]
                        posterID = bannerData['poster'][posterSize].keys()[0]
                        posterURL = bannerData['poster'][posterSize][posterID]['_bannerpath']

                        try:
                            img_temp = NamedTemporaryFile(delete=True)
                            img_temp.write(urllib2.urlopen(posterURL).read())
                            img_temp.flush()

                            self.posterimg.save(str(self.id) + '-tvdb.jpg', File(img_temp))
                        except Exception as e:
                            logger.error("error saving image: %s" % e.message)
                            pass

            if 'genre' in tvdb_obj.data:
                if tvdb_obj['genre'] is not None:
                    self.genres = tvdb_obj['genre']

            self.save()
        except Exception as e:
            logger.exception("Error updating entry %s" % e)

@receiver(pre_save, sender=TVShowMappings)
def create_tvdb_on_add(sender, instance, **kwargs):

    instance.title = instance.title.lower()

    if instance.id is None:
        logger.debug("Adding a new tv mapping %s" % instance.title)

        #lets look for existing tvdbshow.. if not add it and get the details from tvdb.com
        try:
            existing = Tvdbcache.objects.get(id=instance.tvdbid_id)

            if existing:
                logger.debug("Found existing tvdb record")
                pass
        except:
            logger.debug("Didnt find tvdb record, adding a new one")
            new = Tvdbcache()
            new.id = instance.tvdbid_id
            new.update_from_tvdb()



@receiver(post_save, sender=Tvdbcache)
def add_new_tvdbitem(sender, created, instance, **kwargs):

    if created:
        logger.info("Adding a new tvdbitem, lets make sure its fully up to date")
        instance.update_from_tvdb()

@receiver(post_save, sender=Imdbcache)
def add_new_imdbitem(sender, created, instance, **kwargs):

    if created:
        logger.info("Adding a new imdbitem, lets make sure its fully up to date")
        instance.update_from_imdb()

@receiver(pre_save, sender=DownloadItem)
def add_new_downloaditem_pre(sender, instance, **kwargs):

    from lazycore.utils.metaparser import MetaParser

    if instance.id is None:
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
                    for get_season , get_eps in instance.onlyget.iteritems():
                        for get_ep in get_eps:
                            existing_obj.add_download(get_season, get_ep)

                    existing_obj.reset()
                    existing_obj.save()
                    raise AlradyExists_Updated(existing_obj)
                else:
                    logger.debug("download already exists.. ignore this")
                raise AlradyExists_Updated(existing_obj)
        except ObjectDoesNotExist:
            pass

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

            #Check if already in queue (maybe this is higher quality or proper).
            for dlitem in DownloadItem.objects.all().filter(Q(status=DownloadItem.QUEUE) | Q(status=DownloadItem.DOWNLOADING) | Q(status=DownloadItem.PENDING)):
                dlitem_title = None
                dlitem_parser = dlitem.metaparser()

                if 'title' in dlitem_parser.details:
                    dlitem_title = dlitem_parser.details['title']

                if 'series' in dlitem_parser.details:
                    dlitem_title = dlitem_parser.details['series']

                if dlitem_title and dlitem_title.lower() == title.lower():

                    check = False

                    if parser.type == MetaParser.TYPE_TVSHOW:
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


    tvdbapi = Tvdb()

    type = instance.metaparser().type

    from lazycore.utils.metaparser import MetaParser

    #must be a tvshow
    if type == MetaParser.TYPE_TVSHOW:
        if instance.tvdbid_id is None:
            logger.debug("Looks like we are working with a TVShow")

            #We need to try find the series info
            parser = instance.metaparser()

            if parser.details:
                series_name = parser.details['series']

                logger.info(series_name)

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

            #Get latest tvdb DATA
            tvdb_obj = tvdbapi[int(instance.tvdbid_id)]

            new_tvdb_item = Tvdbcache()
            new_tvdb_item.title = tvdb_obj['seriesname'].replace(".", " ").strip()
            new_tvdb_item.id = int(tvdb_obj['id'])
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
                except Exception as e:
                        logger.exception("Error updating IMDB info %s" % e.message)

        except ObjectDoesNotExist as e:

            logger.debug("Getting IMDB data for release")

            #Get latest IMDB DATA
            imdbobj = ImdbParser()
            try:
                imdbobj.parse("tt" + str(instance.imdbid_id))

                if imdbobj.name:
                    #insert into db
                    new_imdb = Imdbcache()
                    new_imdb.title = imdbobj.name
                    new_imdb.id = int(imdbobj.imdb_id.lstrip("tt"))
                    new_imdb.save()
            except Exception as e:
                logger.exception("error gettig imdb %s information.. from website %s" %  (instance.imdbid_id, e.message))
                instance.imdbid_id = None

        except Exception as e:
            logger.exception("error gettig imdb %s information.. from website %s" %  (instance.imdbid_id, e.message))
            instance.imdbid_id = None

