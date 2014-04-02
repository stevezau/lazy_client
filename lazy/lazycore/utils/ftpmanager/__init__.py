'''
Created on 06/04/2012

@author: Steve
'''
from __future__ import division
import logging
import os
import re
from ftplib import FTP_TLS
from django.conf import settings
from lazycore import utils
import time
from lazycore.utils import common
from lazycore.utils.metaparser import MetaParser
from lazycore.exceptions import FTPException

logger = logging.getLogger(__name__)

ftps = FTP_TLS()

def cwd(dir):
    if is_connected():
        ftps.cwd(dir)

def is_connected():
    try:
        ftps.voidcmd("noop")
        return True
    except:
        #we are not connected.. lets retry connect
        logger.debug("We are not connected to the ftp, lets reconnect")
        connect()
        return True

def ftpwalk(top, topdown=True, onerror=None, cur_depth=0, max_depth=9, inc_top=False):
    """
    Generator that yields tuples of (root, dirs, nondirs).
    """

    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.path.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.

    if cur_depth == 0 and inc_top:
        cur_depth += 1
        size = get_size(top)
        yield os.path.dirname(top), [[os.path.basename(top), size]], []

    # Make the FTP object's current directory to the top dir.
    logger.debug(top)
    cwd(top)

    try:
        dirs, nondirs = listdir()
    except os.error, err:
        if onerror is not None:
            onerror(err)
        return

    if cur_depth >= max_depth:
        yield top, dirs, nondirs
        return

    next_depth = cur_depth + 1

    if topdown:
        yield top, dirs, nondirs
    for entry in dirs:
        dname = entry[0]
        path = os.path.join(top, dname)
        for x in ftpwalk(path, topdown=topdown, onerror=onerror, cur_depth=next_depth, max_depth=max_depth):
            yield x

    if not topdown:
            yield top, dirs, nondirs

def listdir():
    """
    List the contents of the FTP opbject's cwd and return two tuples of

       (filename, size, mtime, mode, link)

    one for subdirectories, and one for non-directories (normal files and other
    stuff).  If the path is a symbolic link, 'link' is set to the target of the
    link (note that both files and directories can be symbolic links).

    Note: we only parse Linux/UNIX style listings; this could easily be
    extended.
    """
    dirs, nondirs = [], []

    listing = []

    sendcmd("PRET LIST")

    if is_connected():
        ftps.retrlines('MLSD', listing.append)

    for line in listing:
        # Parse, assuming a UNIX listing
        line_values = line.split(";")

        if len(line_values) < 6:
            logger.info('Warning: Error reading short line')
            continue

        file_type = line_values[0].strip()
        filename = line_values[-1].lstrip()

        if common.match_str_regex(settings.FTP_IGNORE_FILES, filename):
            continue

        # Get the file size.
        size = int(line_values[1].strip("size="))

        entry = (filename, size)

        if file_type == "type=dir":
            dirs.append(entry)
        else:
            nondirs.append(entry)

    return dirs, nondirs

def get_files_for_download(folder):
    found_files = []
    size = 0

    #TODO: Improve this checking..
    if common.is_video_file(folder):
        #we have a file
        size = get_size(folder)
        file_found = [folder, size]
        found_files.append(file_found)
    else:
        #we have a folder
        for curfolder, dirs, files in ftpwalk(folder):
            for file in files:
                file_found = [str(os.path.join(curfolder, file[0])), file[1]]
                found_files.append(file_found)
                size += file[1]

    return found_files, size


def close():
    try:
        ftps.close()
    except:
        pass


def connect():
    connected = False
    retry_count = 0
    last_error = ""

    while not connected:
        #How many times have we retried??

        if retry_count >= settings.FTP_TIMEOUT_RETRY_COUNT:
            raise FTPException(last_error)

        if retry_count > 0:
            logger.debug("Delaying before trying again, attempt %s" % retry_count)
            time.sleep(settings.FTP_TIMEOUT_RETRY_DELAY)

        try:
            logger.debug("Trying to connect")
            #first lets close any existing connections
            close()
            ftps.set_debuglevel(0)
            ftps.connect(settings.FTP_IP, settings.FTP_PORT, timeout=settings.FTP_TIMEOUT_WAIT)
            logger.debug("Connected")
            logger.debug("Logging in")
            ftps.login(settings.FTP_USER, settings.FTP_PASS)
            logger.debug("Login success!")
            connected = True
        except Exception as e:
            last_error = e.message
            retry_count += 1
            logger.debug("Error during connect/login: %s" % e.message)


def get_required_folders_for_multi(folder, onlyget):

    onlyget_clean_seasons = []
    onlyget_clean_eps = {}

    #sanatise onlyget
    for season, eps in onlyget.items():
        if len(eps) == 0 or 0 in eps:
            #get whole season
            onlyget_clean_seasons.append(int(season))
            continue

        get_eps = []

        for ep in eps:
            try:
                if int(ep) in get_eps:
                    #duplicate
                    continue
                else:
                    get_eps.append(int(ep))
            except:
                pass

        if len(get_eps) > 0:
            onlyget_clean_eps[int(season)] = get_eps

    skippath = []
    size = 0
    urls = []

    logger.debug("Need to get Eps: %s" % onlyget_clean_eps)
    logger.debug("Need to get Seasons: %s" % onlyget_clean_seasons)


    #lets find them all
    for curdir, dirs, files in ftpwalk(folder, max_depth=4, inc_top=True):

        if len(onlyget_clean_eps) == 0 and len(onlyget_clean_seasons) == 0:
            break


        for path in skippath:
            if path.startswith(curdir) or path == curdir:
                continue

        for file in files:

            #first lets check if something we might be interested in
            if len(onlyget_clean_eps) == 0 and len(onlyget_clean_seasons) == 0:
                break

            parser = MetaParser(file[0], type=MetaParser.TYPE_TVSHOW)

            if 'container' in parser.details:

                #we have a file
                found_eps = parser.get_eps()
                found_ep_season = parser.get_season()

                if found_ep_season in onlyget_clean_eps.keys():
                    eps = onlyget_clean_eps[found_ep_season]

                    if found_eps in eps:
                        onlyget_clean_eps[found_ep_season].remove(ep)

                    if len(found_eps) > 1:
                        #multi ep
                        process = False

                        for ep in found_eps:
                            if ep in eps:
                                process = True

                        if process:
                            logger.debug("We found a multi ep match, we must download this! %s" % file[0])
                            file_found = [(str(os.path.join(curdir, file[0])), file[1])]
                            size += file[1]
                            urls = urls + file_found

                            for ep in found_eps:
                                try:
                                    onlyget_clean_eps[found_ep_season].remove(ep)
                                except:
                                    pass

                    elif len(found_eps) == 1:
                        if found_eps[0] in eps:
                            logger.debug("We found a match, we must download this! %s" % file[0])
                            file_found = [(str(os.path.join(curdir, file[0])), file[1])]
                            size += file[1]
                            urls = urls + file_found
                            onlyget_clean_eps[found_ep_season].remove(found_eps[0])

        #Lets check if required items are in folders
        for dir in dirs:
            if len(onlyget_clean_eps) == 0 and len(onlyget_clean_seasons) == 0:
                break

            dir = dir[0]
            full_dir = os.path.join(curdir, dir)

            parser = MetaParser(dir, type=MetaParser.TYPE_TVSHOW)

            type = parser.details['type']

            #lets make sure it has a season


            #multi season pack
            if type == "season_pack_multi":
                logger.debug("Multi Season pack detected %s" % dir)

                seasons = parser.get_seasons()

                #first do we even want to bother
                process = False

                for season in seasons:
                    if season in onlyget_clean_seasons or season in onlyget_clean_eps.keys():
                        #we want to process this
                        process = True

                if not process:
                    skippath.append(full_dir)
                    continue

            elif type == "season_pack":
                logger.debug("Season pack detected %s" % dir)

                seasons = parser.get_seasons()

                for season in seasons:
                    if season in onlyget_clean_seasons:
                        onlyget_clean_seasons.remove(season)
                        logger.debug("we must download this one! %s " % dir)
                        skippath.append(full_dir)
                        found_urls, found_size = get_files_for_download(full_dir)
                        size += found_size
                        urls = urls + found_urls

            elif type == "episode":
                skippath.append(full_dir)

                #first lets check if something we might be interested in
                found_eps = parser.get_eps()
                found_ep_season = parser.get_season()

                if found_ep_season in onlyget_clean_eps.keys():
                    eps = onlyget_clean_eps[found_ep_season]

                    if len(found_eps) > 1:
                        #multi ep

                        process = False

                        for ep in found_eps:
                            if ep in eps:
                                process = True

                        if process:
                            logger.debug("We found a multi ep match, we must download this! %s" % dir)
                            skippath.append(full_dir)
                            found_urls, found_size = get_files_for_download(full_dir)
                            size += found_size
                            urls = urls + found_urls

                            for ep in found_eps:
                                try:
                                    onlyget_clean_eps[found_ep_season].remove(ep)
                                except:
                                    pass

                    elif len(found_eps) == 1:
                        if found_eps[0] in eps:
                            logger.debug("We found a match, we must download this! %s" % dir)
                            skippath.append(full_dir)
                            found_urls, found_size = get_files_for_download(full_dir)
                            size += found_size
                            urls = urls + found_urls
                            eps.remove(found_eps[0])

    for season, eps in onlyget_clean_eps.copy().iteritems():
        if len(eps) == 0:
            del onlyget_clean_eps[season]

    logger.debug("Left Eps: %s" % onlyget_clean_eps)
    logger.debug("Left Seasons: %s" % onlyget_clean_seasons)

    if len(onlyget_clean_eps) > 0 or len(onlyget_clean_seasons) > 0:
        raise Exception("Unable to find all the required ep's within season pack")

    return urls, size


def get_size(remote):
    if is_connected():
        size = ftps.size(remote)

    return size


#TODO: FIX THIS up
def getTVTorrentsPreScan(search_names):

    sites = ['scc', 'tl', 'revtt']

    torrents = {}
    torrents['scc'] = []
    torrents['tl'] = []
    torrents['revtt'] = []

    show_name = search_names[-1]

    for site in sites:

        cmdremote = "%s" % (show_name)
        cmd = "site torrent search %s %s" % (site, cmdremote)

        out = sendcmd(cmd)

        logger.debug(out)

        for line in iter(out.splitlines()):
            line = line.lower()

            #do fuzzy match
            match = re.search("(?i)200- (.+s([0-9][0-9])e([0-9][0-9]).+)\ [0-9]", line.strip())

            if match:
                #found a torrent..
                torrent = match.group(1).strip()

                ratio = common.compare_torrent_2_show(show_name, torrent)

                if ratio >= 0.93:
                    logger.debug("Adding torrent to prescan %s" % torrent)
                    torrents[site].append(torrent)

    return torrents

#TODO: FIX THIS up
def getTVTorrents(site, search_names, season, ep):

    from lazycore.models import DownloadItem

    logger.info("Searching %s torrents for   %s S%s E%s" % (site, search_names[0], str(season).zfill(2), str(ep).zfill(2)))

    torrents = []
    str_season = str(season).zfill(2)
    str_ep = str(ep).zfill(2)

    for show_name in search_names:

        cmdremote = "%s S%sE%s" % (show_name, str_season, str_ep)
        cmd = "site torrent search %s %s" % (site, cmdremote)

        out = sendcmd(cmd)

        logger.debug(out)

        for line in iter(out.splitlines()):
            line = line.lower()

            #do fuzzy match
            match = re.search("(?i)200- (.+s([0-9][0-9])e([0-9][0-9]).+)\ [0-9]", line.strip())

            if match:
                #found a torrent..
                torrent = match.group(1).strip()

                ratio = common.compare_torrent_2_show(show_name, torrent)

                if ratio >= 0.93:
                    logger.debug("Potential found match %s" % match.group(1))

                    parser = MetaParser(match.group(1), type=MetaParser.TYPE_TVSHOW)

                    torSeason = parser.get_season()
                    torEps = parser.get_eps()

                    try:
                        if int(torSeason) == season:
                            for torEp in torEps:
                                logger.info("found match %s %s" % (season,ep))
                                if int(torEp) == ep:
                                    torrents.append(torrent)
                                    return torrents, torEps

                    except Exception as e:
                        logger.exception(e.message)

    return torrents, []


#TODO: FIX THIS up
def getTVTorrentsSeason(site, show_names, season=0):

    str_season = str(season).zfill(2)

    logger.info("Searching %s torrents for   %s S%s" % (site, show_names[0], str_season))

    torrents = []

    for show_name in show_names:

        if season == 0:
            cmdremote = show_name
        else:
            cmdremote = "%s S%s" % (show_name, str_season)

        cmd = "site torrent search %s %s" % (site, cmdremote)

        out = sendcmd(cmd)

        logger.debug(out)

        for line in iter(out.splitlines()):

            #do fuzzy match
            match = re.search("200- ((.+)S([0-9][0-9])[-0-9\ .].+)\ [0-9]", line.strip())

            if match:
                #found a torrent..
                torrent = match.group(1).strip()

                ratio = common.compare_torrent_2_show(show_name, torrent)

                if ratio >= 0.93:
                    #its for this show..

                    if common.match_str_regex(settings.TVSHOW_SPECIALS_REGEX, torrent):
                        continue

                    try:

                        if season == 0:
                            logger.info("Found match %s" % torrent)
                            #we want to return it all!!
                            torrents.append(torrent)
                        else:
                            parser = MetaParser(line.strip(), type=MetaParser.TYPE_TVSHOW)
                            torSeasons = parser.get_seasons()

                            if season in torSeasons:
                                logger.info("Found match %s" % torrent)
                                torrents.append(torrent)

                    except:
                        logger.error("Error converting season and ep to int %s" % line)
                        continue

    return torrents


def sendcmd(cmd):
    if is_connected():
        if cmd != "PRET LIST":
            logger.debug("sending command to ftp %s" % cmd)
        return ftps.sendcmd(cmd)


def download_torrent(site, torrent, gettv=False):
    tor_cmd = "download"

    if gettv:
        tor_cmd = "gettv"

    ftpresult = sendcmd("site torrent %s %s %s" % (tor_cmd, site, torrent))

    path = None
    error = None

    for line in ftpresult.split("\n"):

        path_found = common.get_regex(line, "200- Finished grabbing Torrent file. Now starting the torrent, when completed the files will show up under (.+)", 1)
        error_found = common.get_regex(line, "200- ERROR: (.+)", 1)
        already_downloaded_path = common.get_regex(line, "ERROR: Torrent already downloaded here: (.+)", 1)

        if path_found and path_found != "":
            path = path_found

        if error_found and error_found != "":
            error = error_found

        if already_downloaded_path and already_downloaded_path != "":
            error = None
            path = already_downloaded_path

    if error:
        raise Exception(error)

    if path:
        return path


def search_torrents(search):
    ftpresult = sendcmd("site torrent search all %s" % search)

    if ftpresult and ftpresult != '':
        logger.debug("Got our results, lets display")
        results = {}

        cur_site = {}
        results['global'] = cur_site

        process_tors = False

        for line in ftpresult.split("\n"):
            error = common.get_regex(line, "[0-9]+- ERROR: (.+)", 1)

            if error:
                if "errors" in cur_site:
                    cur_site['errors'].append(error)
                else:
                    cur_site['errors'] = []
                    cur_site['errors'].append(error)

            found_site = common.get_regex(line, '.+===.+Matches Found on\ ([A-Za-z\-0-9]+)', 1)

            if found_site:
                #found a new site
                cur_site = {}
                results[found_site] = cur_site

            if common.match_str_regex(['200- TORRENT.+SIZE.+'], line):
                process_tors = True

            if process_tors:
                found_torrent = common.get_regex(line, '200- (.+)\ ([0-9]+\.[0-9]+.[MBGB]+).+', 1)
                found_size = common.get_regex(line, '200- (.+)\ ([0-9]+\.[0-9]+.[MBGB]+).+', 2)

                if found_size:
                    found_size = found_size.strip()

                if found_torrent:

                    found_torrent = found_torrent.strip()

                    #we found a torrent
                    if 'torrents' in cur_site:
                        cur_site['torrents'][found_torrent] = {}
                        cur_site['torrents'][found_torrent]['name'] = found_torrent
                        cur_site['torrents'][found_torrent]['size'] = found_size
                    else:
                        cur_site['torrents'] = {}
                        cur_site['torrents'][found_torrent] = {}
                        cur_site['torrents'][found_torrent]['name'] = found_torrent
                        cur_site['torrents'][found_torrent]['size'] = found_size

        logger.debug("Results are %s" % results)
        return results


