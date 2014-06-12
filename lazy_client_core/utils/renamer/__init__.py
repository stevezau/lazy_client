from __future__ import division
from lazy_client_core.models import DownloadItem
import logging, os
import re, shutil
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from lazy_client_core.utils.common import match_str_regex
from lazy_client_core.utils.renamer.tvshow import TVRenamer
from lazy_client_core.utils.renamer.movie import MovieRenamer
from django.core.cache import cache
from lazy_client_core.exceptions import ExtractException, ExtractCRCException
from lazy_client_core.utils import common
from datetime import datetime
from lazy_client_core.exceptions import *
from lazy_client_core.utils.metaparser import MetaParser

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes

def get_renamer_dlitem(download_item):
    #Check what type of download item we are dealing with
    parser = download_item.metaparser()

    if download_item.parser.type == MetaParser.TYPE_UNKNOWN:
        raise RenameUnknownException("Unable to figure out if this is a movie or tvshow")

    if parser.type == MetaParser.TYPE_MOVIE:
        return MovieRenamer(dlitem=download_item)

    if parser.type == MetaParser.TYPE_TVSHOW:
        return TVRenamer(dlitem=download_item)

def get_renamer(path, type=MetaParser.TYPE_UNKNOWN):

    #Check what type of download item we are dealing with
    parser = MetaParser(os.path.basename(path), type)

    if parser.type == MetaParser.TYPE_UNKNOWN:
        raise ObjectDoesNotExist("Unable to figure out if this is a movie or tvshow")

    if parser.type == MetaParser.TYPE_MOVIE:
        return MovieRenamer()

    if parser.type == MetaParser.TYPE_TVSHOW:
        return TVRenamer()


def rename(path, type=MetaParser.TYPE_UNKNOWN, dlitem=None):

    if None is dlitem:
        renamer = get_renamer(path)
    else:
        renamer = get_renamer_dlitem(dlitem)

    #now lets do the renaming and moving
    if os.path.isfile(path):
        #check if its a video file
        if common.is_video_file(path):
            renamer.rename(path)
        else:
            raise InvalidFileException("Is not a valid video file %s" % path)
    else:
        #Get a list of media files
        media_files = common.get_video_files([path])

        if len(media_files) == 0:
            raise NoMediaFilesFoundException("No media files found")

        logger.debug("Found media files %s" % media_files)

        #offload the processing to the renamer
        renamer.rename(media_files)