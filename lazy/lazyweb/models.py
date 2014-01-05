from __future__ import division
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import logging, os, re
from lazyweb.utils.tvdb_api import Tvdb
from datetime import datetime
from lazyweb import utils
from urllib import urlretrieve
from flexget.utils.imdb import ImdbSearch, ImdbParser
from lazyweb.exceptions import AlradyExists_Updated
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
import urllib2
import pprint
from django.db import models
from jsonfield import JSONField


logger = logging.getLogger(__name__)

class TVShowMappings(models.Model):
    class Meta:
        """ Meta """
        db_table = 'tvshowmappings'
        ordering = ['-id']

    title = models.CharField(max_length=150, db_index=True, unique=True)
    tvdbid = models.ForeignKey('Tvdbcache', on_delete=models.DO_NOTHING)

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
    ftppath = models.CharField(max_length=255, db_index=True)
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
    message = models.CharField(max_length=255, blank=True, null=True)
    imdbid = models.ForeignKey('Imdbcache', blank=True, null=True, on_delete=models.DO_NOTHING)
    tvdbid = models.ForeignKey('Tvdbcache', blank=True, null=True, on_delete=models.DO_NOTHING)
    epoverride = models.IntegerField(default=0, blank=True, null=True)
    seasonoverride = models.IntegerField(default=0, blank=True, null=True)
    onlyget = JSONField(blank=True, null=True)

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

        self.killpid()

        if os.path.exists(self.localpath):
            try:
                shutil.rmtree(self.localpath)
            except:
                del self.localpath

        super(DownloadItem, self).delete()

    def killpid(self):
        import os, signal
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGILL)
            except OSError as e:
                pass

    def reset(self):
        self.killpid()
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

    def update_from_imdb(self):
        import unicodedata

        imdbtt = "tt" + str(self.id).zfill(7)
        logger.info("Updating %s %s" % (imdbtt, self.title))

        try:
            imdbobj = ImdbParser()
            imdbobj.parse(imdbtt)

            self.score = imdbobj.score
            self.title = imdbobj.name
            self.year = imdbobj.year
            self.votes = imdbobj.votes
            self.updated = datetime.now()


            if imdbobj.plot_outline:
                self.description = imdbobj.plot_outline.encode('utf-8').strip()

            sGenres = ''

            if imdbobj.genres:
                for genre in imdbobj.genres:
                    sGenres += '|' + unicodedata.normalize('NFKD', genre).encode('ascii','ignore').title()

            self.genres = sGenres.replace('|', '', 1)

            if imdbobj.photo:
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(urllib2.urlopen(imdbobj.photo).read())
                img_temp.flush()

                self.posterimg.save(str(self.id) + '-imdb.jpg', File(img_temp))

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
                    self.description = tvdb_obj['overview'].encode('utf-8').strip()

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
            logger.error("Error updating entry %s" % e)

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

    if instance.id is None:
        logger.debug("Adding a new download %s" % instance.ftppath)

        #Check if it exists already..

        count = DownloadItem.objects.all().filter(ftppath=instance.ftppath).count()

        if count >= 1:
            existing_obj = DownloadItem.objects.get(ftppath=instance.ftppath)
            logger.info("Found existing record %s" % instance.ftppath)

            if existing_obj.status == DownloadItem.COMPLETE:
                #its complete... maybe delete it so we can re-add
                existing_obj.delete()
            else:
                #lets update it with the new downloaded eps
                if instance.onlyget is not None:
                    for get_season , get_eps in instance.onlyget.iteritems():
                        for get_ep in get_eps:
                            existing_obj.add_download(get_season, get_ep)

                    existing_obj.reset()
                    existing_obj.save()
                    raise AlradyExists_Updated()
                else:
                    raise Exception("download already exists")

        #Get section
        if instance.status is None:
            instance.status = 1

        #Get section and title
        if instance.section is None:
            split = instance.ftppath.split("/")
            section = split[1]
            title = split[-1]

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

    tvdbapi = Tvdb()

    is_tv_show = utils.match_str_regex(settings.TVSHOW_REGEX, instance.title)

    #must be a tvshow
    if is_tv_show:
        if instance.tvdbid_id is None:
            logger.debug("Looks like we are working with a TVShow")

            #We need to try find the series info
            parser = utils.get_series_info(instance.title)

            logger.info(parser)

            if parser:
                seriesName = parser.name

                logger.info(seriesName)

                try:
                    match = tvdbapi[seriesName]
                    logger.debug("Show found")
                    instance.tvdbid_id = int(match['id'])

                    if match['imdb_id'] is not None:
                        logger.debug("also found imdbid %s from thetvdb" % match['imdb_id'])
                        instance.imdbid_id = int(match['imdb_id'].lstrip("tt"))

                except Exception as e:
                    raise Exception("Error finding : %s via thetvdb.com due to  %s" % (seriesName, e.message))
            else:
                raise Exception("Unable to parse series info")

    #must be a movie!
    else:
        if instance.imdbid_id is None:
            logger.debug("Looks like we are working with a Movie")
            #Lets try find the movie details
            movieName, movieYear = utils.get_movie_info(instance.title)

            imdbs = ImdbSearch()
            results = imdbs.best_match(movieName, movieYear)

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
                    instance.tvdbid.update_from_tvdb()
        except ObjectDoesNotExist as e:
            logger.debug("Getting tvdb data for release")

            #Get latest tvdb DATA
            tvdb_obj = tvdbapi[int(instance.tvdbid_id)]

            new_tvdb_item = Tvdbcache()
            new_tvdb_item.title = tvdb_obj['seriesname'].replace(".", " ").strip()
            new_tvdb_item.id = int(tvdb_obj['id'])
            new_tvdb_item.save()

    #If we have a imdbid do we need to add it to the db or does it exist
    if instance.imdbid_id is not None:
        try:
            if instance.imdbid:
                #Do we need to update it
                curTime = datetime.now()
                diff = curTime - instance.imdbid.updated.replace(tzinfo=None)
                hours = diff.seconds / 60 / 60

                if hours > 24:
                    instance.imdbid.update_from_imdb()

        except ObjectDoesNotExist as e:

            logger.debug("Getting IMDB data for release")

            try:
                #Get latest IMDB DATA
                imdbobj = ImdbParser()
                imdbobj.parse("tt" + str(instance.imdbid_id))

                if imdbobj.name:
                    #insert into db
                    new_imdb = Imdbcache()
                    new_imdb.title = imdbobj.name
                    new_imdb.id = int(imdbobj.imdb_id.lstrip("tt"))
                    new_imdb.save()

            except Exception as e:
                logger.exception("error gettig imdb information.. from website " + e.message)
