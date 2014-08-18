from genericpath import isfile
import os
from os.path import join
import re
import shutil
import time
import logging

from django.conf import settings
from easy_extract.archive_finder import ArchiveFinder
from lazy_client_core.utils.rar import RarArchive
from lazy_common import utils

logger = logging.getLogger(__name__)

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

def get_lazy_errors():

    errors = []

    #Firte lets check if it should be running..
    for path in [
        settings.MEDIA_ROOT,
        settings.DATA_PATH,
        settings.INCOMING_PATH,
        settings.TVHD,
        settings.TVHD_TEMP,
        settings.XVID,
        settings.XVID_TEMP,
        settings.REQUESTS_TEMP,
        settings.HD,
        settings.HD_TEMP
    ]:

        if not os.path.exists(path):
            errors.append("Path does not exist: %s" % path)
        if not os.access(path, os.W_OK):
            errors.append("Path is not writable: %s" % path)

    #Check Free space
    if os.path.exists(settings.DATA_PATH):
        statvfs = os.statvfs(settings.DATA_PATH)

        dt = statvfs.f_frsize * statvfs.f_blocks     # Size of filesystem in bytes
        df = statvfs.f_frsize * statvfs.f_bfree      # Actual number of free bytes

        free_gb = df / 1024 / 1024 / 1024

        if free_gb < settings.FREE_SPACE:
            errors.append("Not enough free space %s GB free" % free_gb)

    return errors


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

    from lazy_common.metaparser import MetaParser

    folders = [f for f in os.listdir(path) if os.path.isdir(join(path, f))]

    for folder_name in folders:

        if season == 0 and folder_name.lower() == "specials":
            return join(path, folder_name)

        parser = MetaParser(folder_name, MetaParser.TYPE_TVSHOW)

        if 'season' in parser.details:
            if parser.details['season'] == season:
                return join(path, folder_name)

def find_ep_season(folder, season, ep):

    from lazy_common.metaparser import MetaParser

    files = []

    for f in os.listdir(folder):
        try:
            if isfile:
                files.append(join(folder, f))
        except:
            pass


    found = []

    for f in files:
        name = os.path.basename(f)


        parser = MetaParser(name, type=MetaParser.TYPE_TVSHOW)

        f_season = parser.get_season()
        f_eps = parser.get_eps()

        if f_season == season:
            if ep in f_eps:
                #We found one
                found.append(join(folder, f))

    return found



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

    xbmc.add_file(dest)


def ignore_show(title):

    logger.debug("Need to ignore %s" % title)
    ins = open(settings.FLEXGET_IGNORE, "r+")

    for line in ins:
        if title == line:
            logger.debug("Show already ignored, not adding %s" % title)
            ins.close()
            return

    #if not lets add it
    logger.debug("Adding to ignore file %s " % title)
    ins.write("    - ^%s%s" % (title, os.linesep))
    ins.close()






