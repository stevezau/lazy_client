__author__ = 'Steve'
from importlib import import_module
from django.conf import settings
from django.http import HttpResponse
import logging, re, os, glob, zlib, shutil
from rest_framework.views import exception_handler
from lazyweb.exceptions import AlradyExists
from rest_framework import status, exceptions
from rest_framework.response import Response
from easy_extract.archive_finder import ArchiveFinder
from lazyweb.utils.rar import RarArchive
import difflib

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

def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on format.
    symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs

      >>> bytes2human(0)
      '0.0 B'
      >>> bytes2human(0.9)
      '0.0 B'
      >>> bytes2human(1)
      '1.0 B'
      >>> bytes2human(1.9)
      '1.0 B'
      >>> bytes2human(1024)
      '1.0 K'
      >>> bytes2human(1048576)
      '1.0 M'
      >>> bytes2human(1099511627776127398123789121)
      '909.5 Y'

      >>> bytes2human(9856, symbols="customary")
      '9.6 K'
      >>> bytes2human(9856, symbols="customary_ext")
      '9.6 kilo'
      >>> bytes2human(9856, symbols="iec")
      '9.6 Ki'
      >>> bytes2human(9856, symbols="iec_ext")
      '9.6 kibi'

      >>> bytes2human(10000, "%(value).1f %(symbol)s/sec")
      '9.8 K/sec'

      >>> # precision can be adjusted by playing with %f operator
      >>> bytes2human(10000, format="%(value).5f %(symbol)s")
      '9.76562 K'
    """
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

def get_season_from_title(title):

    #TODO USE settings form seasons multi pack regex etc
    multi = re.search('(?i)S([0-9]+)-S([0-9]+)[\. ]', title)
    multi2 = re.search('(?i)S([0-9]+)-([0-9]+)[\. ]', title)

    if multi:
        #found a multi match
        start_season = int(multi.group(1))
        end_season = int(multi.group(2))

        seasons = []

        for season_no in range(start_season, end_season + 1):
            seasons.append(int(season_no))

        return seasons

    elif multi2:
        #found a multi match
        start_season = int(multi2.group(1))
        end_season = int(multi2.group(2))

        seasons = []
        for season_no in range(start_season, end_season + 1):
            seasons.append(int(season_no))

        return seasons
    else:
        match = re.search('(?i)S([0-9][0-9])', title)

        seasons = []
        if match:
            seasons.append(int(match.group(1)))

            return seasons

    return False


def get_ep_season_from_title(title):
    eps = []
    season = 00

    multi = re.search("(?i)S([0-9]+)(E[0-9]+[E0-9]+).+", title, re.IGNORECASE)

    if multi:
        #multi eps found
        epList = re.split("(?i)E", multi.group(2))
        season = multi.group(1)

        for epNum in epList:
            if epNum != '':
                eps.append(int(epNum))

        return int(season), eps

    normal = re.search("(?i)S([0-9]+)E([0-9]+)", title, re.IGNORECASE)

    if normal:
            try:
                eps.append(int(normal.group(2)))
                season = int(normal.group(1))

                return season, eps
            except:
                eps = [0]
                season = 0
    else:
        eps = [0]
        season = 0

    return season, eps


def compare_torrent_2_show(show, torrent):

    torrent = torrent.replace(' ', '.')
    #are we dealing with a season pack here
    pack = re.search('(?i).+\.S[0-9]+\..+|.+\.S[0-9]+-S[0-9]+\..+|.+\.S[0-9]+-[0-9]+\..+', torrent)

    if pack:
        #we have a season pack , lets fake the ep id so we can get a title return
        torrent = re.sub('(?i)\.S[0-9]+\.|\.S[0-9]+-[0-9]+\.|\.S[0-9]+-S[0-9]+\.', '.S01E01.', torrent)

    #TODO ADD THIS TO SETTINGS FILE
    if match_str_regex(settings.DOCOS_REGEX, torrent):
        #we have a doco, lets strip the nato geo, doco title out for matching
        other_title = re.sub("History\.Channel|Discovery\.Channel|National\.Geographic", "", torrent)
        parser = get_series_info(other_title)
    else:
        parser = get_series_info(torrent)

    if parser:
        tor_series_name = parser.name

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


def check_crc(dlitem):
    path = dlitem.localpath
    dlitem.log(__name__, "Checking SFV in path %s" % path)

    os.chdir(path)

    foundSFV = False

    for sfvFile in glob.glob("*.sfv"):
        foundSFV = True
        #DO SFV CHECK
        s = open(sfvFile)

        if os.path.getsize(sfvFile) == 0:
            dlitem.log(__name__, 'empty sfv file')
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
                dlitem.log(__name__, "there was a problem with file deleting it " + names_list[i])
                logger.debug("CRC Check False!!!: %s" % names_list[i])
                no_errors=False
                try:
                    os.remove(names_list[i])
                except:
                    pass

            i=i+1

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

    by_cd = get_movie_info(os.path.basename(os.path.dirname(file_name)), "^CD([0-9]+)$", 1)
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


def setup_dest_files(src_files, dst_folder, title):
    # Setup file dest
    if src_files.__len__() > 1:
        for file in src_files:

            cd = get_cd_number(file['src'])

            if cd:
                __, ext = os.path.splitext(file['src'])
                file['dst'] = os.path.abspath(dst_folder + "/" + title + " CD" + str(cd) + ext)
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

                file = {'src': path, 'dst': None}
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


def load_button_module(package, fn):

    try:
        mod = import_module(package)
        function = getattr(mod, fn)
        return function
    except Exception as e:
        logger.exception(e)
        raise Exception(e)


def ignore_show(title):
    ins = open(settings.FLEXGET_IGNORE, "r+")

    for line in ins:
        if title in line:
            ins.close()
            return

    #if not lets add it
    ins.write("    - ^%s.S%s" % (title, os.linesep))
    ins.close()


def get_series_info(title):
    from flexget.plugins.metainfo.series import MetainfoSeries

    series_info = MetainfoSeries()
    parser = series_info.guess_series(title, allow_seasonless=True)

    return parser

def delete(file):
    if os.path.isdir(file):
        shutil.rmtree(file)
    else:
        os.remove(file)

def get_movie_info(title):
    from flexget.utils.titles import MovieParser

    parser = MovieParser()
    parser.data = title
    parser.parse()

    name = parser.name
    year = parser.year

    if name == '':
        logger.error('Failed to parse name from %s' % title)
        return None

    logger.debug('smart_match name=%s year=%s' % (name, str(year)))

    return name, year

def get_special_name(name):

    special_name = ''

    for quality in settings.QUALITY_REGEX:
        if quality in name:
            special_name = name.split(quality)[0]

    special_name = replace_regex([".+S[0-9]+"], special_name, "")

    special_name = special_name.replace(".", " ")
    special_name = special_name.strip()

    return special_name


def replace_regex(regex_list, string, replacement):

    for regex in regex_list:
        string = re.sub(regex, replacement, string)

    return string


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

def move_files(src_files, check_existing=False):

    if not src_files:
        raise Exception('No files to move', 1)

    for file in src_files:
        move_file(file['src'], file['dst'], check_existing)


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