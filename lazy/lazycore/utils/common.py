import difflib
from genericpath import isfile
import glob
import os
from os.path import join
import re
import shutil
import time
import zlib
from django.conf import settings
from easy_extract.archive_finder import ArchiveFinder
from lazycore.utils.rar import RarArchive


import logging

logger = logging.getLogger(__name__)

# see: http://goo.gl/kTQMs
SYMBOLS = {
    'customary': ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext': ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec': ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext': ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}


def get_lazy_errors():

    errors = []

    #Firte lets check if it should be running..
    for path in [
        settings.TMPFOLDER,
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

def strip_illegal_chars(s):
    new_s = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", s)
    new_s = re.sub(" +", " ", new_s)
    return new_s


def open_file(file, options):

    for x in range(0, 4):
        try:
            return open(file, options, 8192)
        except:
            time.sleep(1)
            pass

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


def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)


def compare_torrent_2_show(show, torrent):
    from lazycore.utils.metaparser import MetaParser

    torrent = torrent.replace(' ', '.')

    parser = MetaParser(torrent, type=MetaParser.TYPE_TVSHOW)

    if 'doco_channel' in parser.details:
        #we have a doco, lets strip the nato geo, doco title out for matching
        other_title = re.sub("History\.Channel|Discovery\.Channel|National\.Geographic", "", torrent)
        parser = MetaParser(other_title, type=MetaParser.TYPE_TVSHOW)

    if parser.details and 'series' in parser.details:
        tor_series_name = parser.details['series']

        #now compare them
        return how_similar(tor_series_name.lower(), show.lower())
    else:
        return 0


def how_similar(s1, s2):
    return difflib.SequenceMatcher(None, s1, s2).ratio()


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

    if f1 == f2:
        return f1

    f1_size = os.path.getsize(f1)
    __, f1_ext = os.path.splitext(f1)
    f1_ext = f1_ext.lower()
    f1_quality = get_file_quality(f1_ext)

    f2_size = os.path.getsize(f2)
    __, f2_ext = os.path.splitext(f2)
    f2_ext = f2_ext.lower()
    f2_quality = get_file_quality(f2_ext)

    if f1_quality > f2_quality:
        return f1

    if f2_quality > f1_quality:
        return f2

    #if the same format, whats bigger?
    if f1_quality == f2_quality:
        if f1_size > f2_size:
            return f1

        if f2_size > f1_size:
            return f2

    #last resort, return the bigger file
    if f1_size > f2_size:
        return f1

    if f2_size > f1_size:
        return f2

    return f1

def find_archives(path):
    archive_finder = ArchiveFinder(path, recursive=True, archive_classes=[RarArchive,])
    return archive_finder.archives


def get_regex(string, regex, group):
    search = re.search(regex, string, re.IGNORECASE)

    if search:
        return search.group(group)
def find_season_folder(path, season):

    if not os.path.exists(path):
        return

    from lazycore.utils.metaparser import MetaParser

    folders = [f for f in os.listdir(path) if os.path.isdir(join(path, f))]

    for folder_name in folders:

        if season == 0 and folder_name.lower() == "specials":
            return join(path, folder_name)

        parser = MetaParser(folder_name, MetaParser.TYPE_TVSHOW)

        if 'season' in parser.details:
            if parser.details['season'] == season:
                return join(path, folder_name)

def find_ep_season(folder, season, ep):

    from lazycore.utils.metaparser import MetaParser

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

    from lazycore.utils.metaparser import MetaParser

    media_files = []

    for root, __, files in os.walk(path):
        for f in files:
            fullpath = os.path.join(root, f)
            name, ext = os.path.splitext(f)
            parser = MetaParser(f)

            #Check its a video file
            if is_video_file(f):
                #check if it's a sample.
                if match_str_regex(settings.SAMPLES_REGEX, name):
                    continue

                path = os.path.join(root, f)
                folder = os.path.basename(os.path.dirname(path))

                if re.match('(?i)sample', folder):
                    continue

                media_files.append(fullpath)

    return media_files

def move_file(src, dest):
    from lazycore.utils import xbmc
    shutil.move(src, dest)

    xbmc.add_file(dest)


def get_size(local):
    local = local.strip()
    path_size = 0
    for path, directories, files in os.walk(local):
        for filename in files:
            path_size += os.lstat(os.path.join(path, filename)).st_size
        for directory in directories:
            path_size += os.lstat(os.path.join(path, directory)).st_size
    path_size += os.path.getsize(local)
    return path_size


def ignore_show(title):

    logger.debug("Need to ignore %s" % title)
    ins = open(settings.FLEXGET_IGNORE, "r+")


    for line in ins:
        if title in line:
            logger.debug("Show already ignored, not adding %s" % title)
            ins.close()
            return

    #if not lets add it
    logger.debug("Adding to ignore file %s " % title)
    ins.write("    - ^%s%s" % (title, os.linesep))
    ins.close()


def delete(f):

    for i in range(1, 3):
        try:
            if os.path.isdir(f):
                shutil.rmtree(f)
            elif os.path.isfile(f):
                os.remove(f)
            else:
                if not os.path.exists(f):
                    return
        except:
            pass

        time.sleep(3)

    #Last try
    if os.path.isdir(file):
        shutil.rmtree(file)
    else:
        os.remove(file)


def replace_regex(regex_list, string, replacement):

    for regex in regex_list:
        string = re.sub(regex, replacement, string)

    return string


def is_video_file(f):

    ext = os.path.splitext(f)[1][1:].strip()

    for vid_ext in settings.VIDEO_FILE_EXTS:
        if ext == vid_ext:
            return True
    return False


def match_str_regex(regex_list, string):
    matched = False

    for regex in regex_list:
        s = re.search(regex, string)

        if s:
            matched = True
            break

    return matched


def create_path(path):

    paths_to_create = []

    while not os.path.lexists(path):

        paths_to_create.insert(0, path)
        head,tail = os.path.split(path)
        if len(tail.strip())==0: # Just incase path ends with a / or \
            path = head
            head,tail = os.path.split(path)

        path = head

    for path in paths_to_create:
        os.mkdir(path)