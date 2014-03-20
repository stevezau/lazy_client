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
from rest_framework import status
from rest_framework.response import Response
from lazycore.utils.rar import RarArchive
from rest_framework.views import exception_handler
from lazycore.exceptions import AlradyExists


import logging

logger = logging.getLogger(__name__)

# see: http://goo.gl/kTQMs
SYMBOLS = {
    'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}


def strip_illegal_chars(s):
    return re.sub(settings.ILLEGAL_CHARS_REGEX, " ", s)


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

    if match_str_regex(settings.DOCOS_REGEX, torrent):
        #we have a doco, lets strip the nato geo, doco title out for matching
        other_title = re.sub("History\.Channel|Discovery\.Channel|National\.Geographic", "", torrent)
        parser = MetaParser(other_title)
    else:
        parser = MetaParser(torrent)

    if 'series' in parser.details:
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


def crc(fileName):
    prev=0

    ##for the script to work on any sfv file no matter where it's located , we have to parse the absolute path of each file within sfv
    ##so, we will add the file path to each file name , pretty neat huh ?
    fileName=os.path.join(fileName)

    #print fileName
    if os.path.exists(fileName):
        store=open(fileName, "rb")
        for eachLine in store:
            prev = zlib.crc32(eachLine, prev)
        return "%x"%(prev & 0xFFFFFFFF)
        store.close()


def get_file_quality(ext):
    ext = ext.lower()

    if ext == "mkv":
        return 20

    if ext == "avi":
        return 10

    if ext == "mp4":
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


def check_crc(dlitem):
    path = dlitem.localpath
    dlitem.log("Checking SFV in path %s" % path)

    os.chdir(path)

    foundSFV = False

    for sfvFile in glob.glob("*.sfv"):
        foundSFV = True
        #DO SFV CHECK
        s = open(sfvFile)

        if os.path.getsize(sfvFile) == 0:
            dlitem.log('empty sfv file')
            return False

        names_list = []
        sfv_list = []

        ##loop thru all lines of sfv, removes all unnecessary /r /n chars, split each line to two values,creates two distinct arrays
        for line in s.readlines():
            if line.startswith(';'):
                continue
            m=line.rstrip('\r\n')
            m=m.split(' ')
            names_list.append(m[0])
            sfv_list.append(m[1])

        i = 0
        no_errors = True

        while(len(names_list)>i):
            calc_sfv_value=crc(names_list[i])


            if sfv_list[i].lstrip('0')==calc_sfv_value:
                logger.debug("CRC Check True: %s" % names_list[i])
                pass
            else:
                dlitem.log("there was a problem with file deleting it " + names_list[i])
                logger.debug("CRC Check False!!!: %s" % names_list[i])
                no_errors=False
                try:
                    os.remove(names_list[i])
                except:
                    pass

            i = i+1

        if (no_errors):
            return True
        else:
            return False

    if not foundSFV:
        logger.debug("No SFV FOUND, lets check via unrar")

        first_rar = None

        #first lets find the name of the first rar file
        for file in os.listdir(dlitem.localpath):
            if re.match(".+\.rar$", file):
                #this has to be it!
                first_rar = os.path.join(dlitem.localpath, file)

            if re.match(".+\.r00$", file):
                #might be it
                first_rar = os.path.join(dlitem.localpath, file)

        if first_rar is None:
            dlitem.log("Could not find the rar file!")

        else:
            #lets do the check
            pass

    return False


def unrar(path):
    logger.info("Unraring folder %s" % path)
    archive_finder = ArchiveFinder(path, recursive=True, archive_classes=[RarArchive,])
    errCode = 0

    for archive in archive_finder.archives:
        errCode = archive.extract()

    logger.debug("Extract return code was %s" % str(errCode))
    return errCode


def get_regex(string, regex, group):
    search = re.search(regex, string, re.IGNORECASE)

    if search:
        return search.group(group)


def get_cd_number(file_name):

    by_cd = get_regex(os.path.basename(os.path.dirname(file_name)), "^CD([0-9]+)$", 1)
    by_num = get_regex(os.path.basename(file_name), "(?i)CD([0-9])", 1)
    by_letter = get_regex(os.path.basename(file_name), "-([A-Za-z])\.(avi|iso|mkv)$", 1)

    if by_cd:
        return by_cd
    elif by_num:
        return by_num
    elif by_letter:
        return [ord(char) - 96 for char in by_letter.lower()][0]
    else:
        return


def find_season_folder(path, seasonn):

    folders = [f for f in os.listdir(path) if os.path.isdir(join(path, f))]

    for folder in folders:
        folder_name = os.path.basename(folder)

        for regex in settings.TVSHOW_SEASON_REGEX:
            match = re.search(regex, folder_name, re.IGNORECASE)

            if match:
                found_season = int(match.group(1))

                if found_season == seasonn:
                    return join(path, folder)


def find_exist_quality(dst):

    file, ext = os.path.splitext(dst)

    found = []

    if os.path.exists(file + ".mkv"):
        found.append(file + ".mkv")

    if os.path.exists(file + ".avi"):
        found.append(file + ".avi")

    if os.path.exists(file + ".mp4"):
        found.append(file + ".mp4")

    return found


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


def setup_dest_files(src_files, dst_folder, title):
    # Setup file dest
    if src_files.__len__() > 1:
        for f in src_files:

            cd = get_cd_number(f['src'])

            if cd:
                __, ext = os.path.splitext(f['src'])
                f['dst'] = os.path.abspath(dst_folder + "/" + title + " CD" + str(cd) + ext)
            else:
                raise Exception('Multiple files but could not locate CD numbering')
    elif src_files.__len__() == 1:
        __, ext = os.path.splitext(src_files[0]['src'])
        src_files[0]['dst'] = os.path.abspath(dst_folder + "/" + title + ext)
    else:
        raise Exception('No files to move')

    return src_files


def get_video_files(path):

    src_files = []

    for root, __, files in os.walk(path):
        for file in files:
            name, ext = os.path.splitext(file)
            if re.match('(?i)\.(mkv|iso|avi|m4v|mpg|mp4)', ext):

                #check if it's a sample.
                if match_str_regex(settings.SAMPLES_REGEX, name):
                    continue

                path = os.path.join(root,file)
                folder = os.path.basename(os.path.dirname(path))

                logger.debug('path: ' + path)
                logger.debug('folder: ' + folder)

                if re.match('(?i)sample', folder):
                    continue

                file = {'src': path}
                src_files.append(file)

    return src_files


def custom_exception_handler(exc):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc)

    if isinstance(exc, AlradyExists):
        return Response({'detail': 'already exists'},
                        status=status.HTTP_202_ACCEPTED)

    return response


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


def delete(file):
    if os.path.isdir(file):
        shutil.rmtree(file)
    else:
        os.remove(file)


def replace_regex(regex_list, string, replacement):

    for regex in regex_list:
        string = re.sub(regex, replacement, string)

    return string


def is_video_file(file):
    for ext in settings.VIDEO_FILE_EXTS:
        if file.endswith(ext):
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


def move_file(src, dst, check_existing=False):

    dst = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", dst)

    create_path(os.path.abspath(os.path.join(dst, '..')))

    do_move = True

    if check_existing:
        fileName, fileExtension = os.path.splitext(dst)
        if os.path.isfile(fileName + ".mp4"):
            os.remove(fileName + ".mp4")
        if os.path.isfile(fileName + ".mkv"):
            #skip this as we dont want to replace SD with HD
            if 'proper' in src.lower():
                do_move = True
            else:
                do_move = False

        if os.path.isfile(fileName + ".avi"):
            os.remove(fileName + ".avi")
    if do_move:
        shutil.move(src, dst)
        logger.info('Moving file: ' + os.path.basename(src) + ' to: ' + dst)
    else:
        logger.info('NOT MOVING FILE AS BETTER QUALITY EXISTS file: ' + os.path.basename(src) + ' to: ' + dst)


def move_files(src_files, check_existing=False):

    if not src_files:
        raise Exception('No files to move', 1)

    for file in src_files:
        move_file(file['src'], file['dst'], check_existing)