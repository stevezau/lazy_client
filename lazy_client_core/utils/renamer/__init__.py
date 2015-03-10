from __future__ import division
import logging
import os

from django.core.exceptions import ObjectDoesNotExist

from lazy_client_core.utils.renamer.tvshow import TVRenamer
from lazy_client_core.utils.renamer.movie import MovieRenamer
from lazy_client_core.utils import common
from lazy_common.utils import is_video_file
from lazy_client_core.exceptions import *
from lazy_common import metaparser


logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes

def get_renamer_dlitem(download_item):
    #Check what type of download item we are dealing with
    parser = download_item.metaparser()

    if download_item.parser.type == metaparser.TYPE_UNKNOWN:
        raise RenameUnknownException("Unable to figure out if this is a movie or tvshow")

    if parser.type == metaparser.TYPE_MOVIE:
        return MovieRenamer(dlitem=download_item)

    if parser.type == metaparser.TYPE_TVSHOW:
        return TVRenamer(dlitem=download_item)

def get_renamer(path, type=metaparser.TYPE_UNKNOWN):

    #Check what type of download item we are dealing with
    parser = metaparser.get_parser_cache(os.path.basename(path), type)

    if parser.type == metaparser.TYPE_UNKNOWN:
        raise ObjectDoesNotExist("Unable to figure out if this is a movie or tvshow")

    if parser.type == metaparser.TYPE_MOVIE:
        return MovieRenamer()

    if parser.type == metaparser.TYPE_TVSHOW:
        return TVRenamer()


def rename(path, type=metaparser.TYPE_UNKNOWN, id=None):

    if id:
        from lazy_client_core.models import DownloadItem
        dlitem = DownloadItem.objects.get(id=id)
    else:
        dlitem = None

    if None is dlitem:
        renamer = get_renamer(path)
    else:
        renamer = get_renamer_dlitem(dlitem)

    #now lets do the renaming and moving
    if os.path.isfile(path):
        #check if its a video file
        if is_video_file(path):
            renamer.rename([path])
        else:
            raise InvalidFileException("Is not a valid video file %s" % path)
    else:
        #Get a list of media files
        media_files = common.get_video_files(path)

        if len(media_files) == 0:
            raise NoMediaFilesFoundException("No media files found")

        logger.debug("Found media files %s" % media_files)

        #offload the processing to the renamer
        renamer.rename(media_files)