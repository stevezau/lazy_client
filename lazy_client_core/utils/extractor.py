from __future__ import division
import logging
import os
from django.core.cache import cache
from lazy_client_core.exceptions import ExtractException, ExtractCRCException
from lazy_client_core.utils import common
from lazy_common.utils import delete

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes

def do_extract(path):
    #First lets try extract everything.
    archives = common.find_archives(path)

    found_bad_archives = []

    for archive in archives:
        archive_path = os.path.join(archive.path, archive.name)
        logger.info("Extracting %s" % archive_path)

        code = archive.extract()

        if code == 0:
            continue
        else:
            logger.info("Extract failed on %s with error code %s, will now do CRC check on all archives" % (archive_path, code))

            found_bad_archives = archive.crc_check()

            for bad_archive in found_bad_archives:
                try:
                    logger.debug("Deleting bad archive %s" % bad_archive)
                    delete(bad_archive)
                except:
                    pass

    if len(found_bad_archives) > 0:
        raise ExtractCRCException("Failed due to CRC errors in files")

def extract(path):

    if not os.path.isdir(path):
        raise ExtractException("Folder not found")

    #Check files and folders exist
    lock_id = "extract-%s-lock" % path
    acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)

    if not acquire_lock():
        logger.debug("Already extracting %s , exiting" % path)
        return

    try:
        do_extract(path)
    finally:
        release_lock()
