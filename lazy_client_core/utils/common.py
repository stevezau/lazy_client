from genericpath import isfile
import os
from os.path import join
import re
import shutil
import time
import logging
from lazy_common import utils
from django.conf import settings
from easy_extract.archive_finder import ArchiveFinder
from lazy_client_core.utils.rar import RarArchive
from lazy_common import utils
from django.core.files.storage import FileSystemStorage

from django.db.models.fields import CharField
from lazy_common import metaparser

logger = logging.getLogger(__name__)


class LowerCaseCharField(CharField):
    """
    Defines a charfield which automatically converts all inputs to
    lowercase and saves.
    """

    def pre_save(self, model_instance, add):
        """
        Converts the string to lowercase before saving.
        """
        current_value = getattr(model_instance, self.attname)
        setattr(model_instance, self.attname, current_value.lower())
        return getattr(model_instance, self.attname)



class OverwriteStorage(FileSystemStorage):

    def get_available_name(self, name):
        """Returns a filename that's free on the target storage system, and
        available for new content to be written to.

        Found at http://djangosnippets.org/snippets/976/

        This file storage solves overwrite on upload problem. Another
        proposed solution was to override the save method on the model
        like so (from https://code.djangoproject.com/ticket/11663):

        def save(self, *args, **kwargs):
            try:
                this = MyModelName.objects.get(id=self.id)
                if this.MyImageFieldName != self.MyImageFieldName:
                    this.MyImageFieldName.delete()
            except: pass
            super(MyModelName, self).save(*args, **kwargs)
        """
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name

def merge_tvshow(existing_tvshow, from_path):
    from lazy_client_core.models import TVShow

    existing_vid_files = existing_tvshow.get_existing_eps()
    print "B"
    from_files = get_video_files(from_path)
    print "C"
    from_files += get_files(from_path, [".nfo"])

    print "21"
    if len(from_files) == 0:
        logger.info("No video files to merge deleting from folder")
        shutil.rmtree(from_path)
        return

    for f in from_files:
        try:
            #Check if the season/ep exists in existing files
            file_name, ext = os.path.splitext(os.path.basename(f))
            file_name = TVShow.clean_title(file_name)
            f_parser = metaparser.get_parser_cache(file_name, metaparser.TYPE_TVSHOW, title_only=False)

            for existing_file in existing_vid_files:
                if ext != ".nfo" and f_parser.get_season() == existing_file.season.season:
                    f_eps = f_parser.get_eps()
                    if existing_file.epsiode in f_eps:
                        logger.info("Wont move ep %s as it already exists in dest" % f)
                        continue

            tvshow_season = existing_tvshow.get_season(f_parser.get_season())

            if tvshow_season:
                season_path = tvshow_season.get_path()
                if season_path:
                    utils.create_path(season_path)
                    dest_path = os.path.join(season_path, file_name)

                    logger.info('Moving file: %s to %s' % (f, dest_path))
                    move_file(f, dest_path)
                else:
                    logger.info("Unable to find season path for %s" % f)

            logger.info("Unable to move file %s to %s" % (f, season_path))
        except Exception as e:
            logger.info("Unable to move file %s as %s" % (f, str(e)))

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def fail_color(msg):
    return bcolors.FAIL + msg + bcolors.ENDC

def green_color(msg):
    return bcolors.OKGREEN + msg + bcolors.ENDC

def blue_color(msg):
    return bcolors.OKBLUE + msg + bcolors.ENDC

def get_mount_points():
    mount_points = []

    for path in [
        settings.INCOMING_PATH,
        settings.MOVIE_PATH,
        settings.TV_PATH,
        settings.TV_PATH_TEMP,
        settings.MOVIE_PATH_TEMP,
        settings.REQUESTS_PATH_TEMP,
    ]:

        if os.path.exists(path):
            mount_point = get_mount_point(path)

            if mount_point not in mount_points:
                mount_points.append(mount_point)

    return mount_points

def get_lazy_errors():

    errors = []

    #Firte lets check if it should be running..
    for path in [
        settings.MEDIA_ROOT,
        settings.INCOMING_PATH,
        settings.MOVIE_PATH,
        settings.TV_PATH,
        settings.TV_PATH_TEMP,
        settings.MOVIE_PATH_TEMP,
        settings.REQUESTS_PATH_TEMP,
    ]:

        path = os.path.realpath(path)

        if not os.path.exists(path):
            errors.append("Path does not exist: %s" % path)
        if not os.access(path, os.W_OK):
            errors.append("Path is not writable: %s" % path)

    #Check Free space
    for mount_point in get_mount_points():
        if os.path.exists(mount_point):
            free_bytes = get_fs_freespace(mount_point)
            free_gb = free_bytes / 1024 / 1024 / 1024

            if free_gb < settings.FREE_SPACE:
                errors.append("Not enough free space %s GB free" % free_gb)

    return errors

def get_mount_point(pathname):
    "Get the mount point of the filesystem containing pathname"
    pathname = os.path.normcase(os.path.realpath(pathname))
    parent_device = path_device= os.stat(pathname).st_dev
    while parent_device == path_device:
        mount_point= pathname
        pathname = os.path.dirname(pathname)
        if pathname == mount_point: break
        parent_device = os.stat(pathname).st_dev
    return mount_point

def get_mounted_device(pathname):
    "Get the device mounted at pathname"
    # uses "/proc/mounts"
    pathname = os.path.normcase(pathname) # might be unnecessary here
    try:
        with open("/proc/mounts", "r") as ifp:
            for line in ifp:
                fields = line.rstrip('\n').split()
                # note that line above assumes that
                # no mount points contain whitespace
                if fields[1] == pathname:
                    return fields[0]
    except EnvironmentError:
        pass
    return None # explicit

def get_fs_freespace(pathname):
    "Get the free space of the filesystem containing pathname"
    stat = os.statvfs(pathname)
    # use f_bfree for superuser, or f_bavail if filesystem
    # has reserved space for superuser
    return stat.f_bfree*stat.f_bsize

def get_fs_percent_used(pathname):
    "Get the free space of the filesystem containing pathname"
    stat = os.statvfs(pathname)
    # use f_bfree for superuser, or f_bavail if filesystem
    # has reserved space for superuser
    total = (stat.f_blocks * stat.f_frsize)
    used = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
    try:
        percent = ret = (float(used) / total) * 100
    except ZeroDivisionError:
        percent = 0

    return percent

def truncate_file(file, size):
    if os.path.exists(file):
        fh = open(file, 'rb+')
        fh.seek(-size, 2)
        data = fh.read()
        fh.seek(0) # rewind
        fh.write(data)
        fh.truncate()
        fh.close()

def strip_illegal_chars(s):
    new_s = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", s)
    new_s = re.sub(" +", " ", new_s)

    return new_s.strip()


def open_file(file, options):

    for x in range(0, 4):
        try:
            return open(file, options, 8192)
        except:
            time.sleep(1)

    #one last try!
    return open(file, options, 8192)


def close_file(file):

    for x in range(0, 4):
        try:
            file.close()
        except:
            time.sleep(1)
            pass

    #one last try
    file.close()


def remove_ignore(title):
    ins = open(settings.FLEXGET_IGNORE, "r")
    newlines = []

    for line in ins:
        print ("line: %s   title: %s" % (line, title))
        if title in line:
            continue
        else:
            newlines.append(line)
    ins.close()

    #Now lets write the new lines
    ins = open(settings.FLEXGET_IGNORE, "w")
    ins.writelines(newlines)


def get_file_quality(ext):
    ext = ext.lower()

    if ext == ".mkv":
        return 20

    if ext == ".avi":
        return 10

    if ext == ".mp4":
        return 10

    return 10


def compare_best_vid_file(f1, f2):
    from datetime import datetime

    if f1 == f2:
        return f1

    f1_size = os.path.getsize(f1)
    __, f1_ext = os.path.splitext(f1)
    f1_ext = f1_ext.lower()
    f1_quality = get_file_quality(f1_ext)
    f1_date = datetime.fromtimestamp(os.path.getmtime(f1))

    f2_size = os.path.getsize(f2)
    __, f2_ext = os.path.splitext(f2)
    f2_ext = f2_ext.lower()
    f2_quality = get_file_quality(f2_ext)
    f2_date = datetime.fromtimestamp(os.path.getmtime(f2))

    if f1_quality > f2_quality:
        logger.info("%s quality better then %s" % (f1, f2))
        return f1

    if f2_quality > f1_quality:
        logger.info("%s quality better then %s" % (f2, f1))
        return f2

    #Same format, whats the difference in percent and date
    if f1_size > f2_size:
        difference = 100 * (f1_size - f2_size) / f1_size
    else:
        difference = 100 * (f2_size - f1_size) / f2_size

    if f1_date > f2_date:
        delta = f1_date - f2_date
    else:
        delta = f2_date - f1_date

    #if the same format
    if f1_quality == f2_quality:

        #massive different in size
        if difference > 50:
            #whats bigger?
            if f1_size > f2_size:
                logger.info("%s is same quality MUCH bigger then  %s" % (f1, f2))
                return f1

            if f2_size > f1_size:
                logger.info("%s is same quality but MUCH bigger then  %s" % (f2, f1))
                return f2

        #less then 10 days.. lets take the newer one
        if delta.days < 10:
            #Look for proper
            if 'proper' in f1.lower():
                logger.info("%s is a proper rather then %s" % (f1, f2))
                return f1

            if 'proper' in f2.lower():
                logger.info("%s is a proper rather then %s" % (f2, f1))
                return f2

            #Do it by date
            if f1_date > f2_date:
                logger.info("%s is newer then %s" % (f1, f2))
                return f1
            else:
                logger.info("%s is newer then %s" % (f2, f1))
                return f2

        #whats bigger?
        if f1_size > f2_size:
            logger.info("%s is same quality but bigger then  %s" % (f1, f2))
            return f1

        if f2_size > f1_size:
            logger.info("%s is same quality but bigger then  %s" % (f2, f1))
            return f2


    #last resort, return the bigger file
    if f1_size > f2_size:
        logger.info("%s is bigger then  %s" % (f1, f2))
        return f1

    if f2_size > f1_size:
        logger.info("%s is bigger then  %s" % (f2, f1))
        return f2

    return f1

def find_archives(path):
    archive_finder = ArchiveFinder(path, recursive=True, archive_classes=[RarArchive,])
    return archive_finder.archives


def find_season_folder(path, season):

    if not os.path.exists(path):
        return

    from lazy_common import metaparser

    folders = [f for f in os.listdir(path) if os.path.isdir(join(path, f))]

    for folder_name in folders:

        if season == 0 and folder_name.lower() == "specials":
            return join(path, folder_name)

        parser = metaparser.get_parser_cache(folder_name, metaparser.TYPE_TVSHOW)

        if 'season' in parser.details:
            if parser.details['season'] == season:
                return join(path, folder_name)


def find_ep_season(season_folder, season, ep):

    from lazy_common import metaparser
    from lazy_common import utils

    files = [f for f in os.listdir(season_folder) if os.path.isfile(join(season_folder, f))]
    found = []

    for f in files:
        if utils.is_video_file(f):
            name = os.path.basename(f)
            parser = metaparser.get_parser_cache(name, type=metaparser.TYPE_TVSHOW)

            f_season = parser.get_season()
            f_eps = parser.get_eps()

            if f_season == season:
                if ep in f_eps:
                    #We found one
                    found.append(join(season_folder, f))

    return found

def get_from_dict(obj, key):
    if obj and key in obj:
        return obj[key]

def get_files(path, ext=[]):

    files = []

    for root, __, files in os.walk(path):
        for f in files:
            fullpath = os.path.join(root, f)

            name, ext = os.path.splitext(f)

            if ext.lower() in ext:
                files.append(fullpath)

    return files

def get_video_files(path):

    logger.debug("finding video files in path %s" % path)

    media_files = []

    for root, __, files in os.walk(path):
        for f in files:
            fullpath = os.path.join(root, f)

            if os.path.getsize(fullpath) < 16777216:
                continue

            name, ext = os.path.splitext(f)

            #Check its a video file
            if utils.is_video_file(f):
                #check if it's a sample.
                if utils.match_str_regex(settings.SAMPLES_REGEX, name):
                    continue

                path = os.path.join(root, f)
                folder = os.path.basename(os.path.dirname(path))

                if re.match('(?i)sample', folder):
                    continue

                media_files.append(fullpath)

    return media_files

def move_file(src, dest):
    from lazy_client_core.utils import xbmc
    shutil.move(src, dest)

    try:
        xbmc.add_file(dest)
    except:
        pass


def ignore_show(title):

    logger.debug("Need to ignore %s" % title)
    ins = open(settings.FLEXGET_IGNORE, "r+")

    for line in ins:

        line = line.rstrip("\n")

        if line.startswith("    - ^"):
            line_title = line.replace("    - ^", "")
        elif line.startswith("    - "):
            line_title = line.replace("    - ", "")
        else:
            continue

        if line_title.lower().replace(".", " ") == title.lower().replace(".", " "):
            logger.debug("Show already ignored, not adding %s" % title)
            ins.close()
            return

    #if not lets add it
    logger.debug("Adding to ignore file %s " % title)
    ins.write("    - ^%s%s" % (title, os.linesep))
    ins.close()






