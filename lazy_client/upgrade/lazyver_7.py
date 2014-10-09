__author__ = 'steve'
from lazy_client_core.models import TVShow, Movie
from lazy_client_core.models import DownloadItem
import logging
from django.db.models import Q
from lazy_common.tvdb_api import Tvdb
from django.conf import settings
import shutil

logger = logging.getLogger(__name__)

def upgrade():

    for dlitem in DownloadItem.objects.filter(~Q(status=DownloadItem.COMPLETE), retries__gt=settings.DOWNLOAD_RETRY_COUNT).order_by('priority','id'):
        dlitem.retries = 0
        dlitem.save()

    #Lets set the favs
    TVShow.update_favs()

    #Now lets remove duplicates in Ignore.yml
    lines_seen = set()
    outfile = open(settings.FLEXGET_IGNORE + "temp", "w")
    for line in open(settings.FLEXGET_IGNORE, "r"):
        if line not in lines_seen: # not a duplicate
            outfile.write(line)
            lines_seen.add(line)
        else:
            logger.info("Removing duplicate line %s" % line)
    outfile.close()

    shutil.move(settings.FLEXGET_IGNORE + "temp", settings.FLEXGET_IGNORE)


    #Then figure out the ignored via the ignore.yml
    found_count = 0
    not_count = 0
    for line in open(settings.FLEXGET_IGNORE, "r"):
        if line.startswith("    - ^"):
            show_name = line.replace("    - ^", "").replace(".", " ").strip()

            try:
                found = TVShow.objects.get(title=show_name)
                found.ignored = True
                found.save()
                found_count += 1
            except:
                print show_name
                not_count += 1

    if found_count:
        logger.info("%s shows marked as ignored" % found_count)

    if not_count:
        logger.info("%s shows marked as ignored but not found in database" % not_count)
