__author__ = 'steve'
from lazy_client_core.models import TVShow, Movie, TVShowMappings
from lazy_client_core.models import DownloadItem
import logging
from django.db.models import Q
from lazy_common.tvdb_api import Tvdb
from lazy_common.tvdb_api.tvdb_exceptions import tvdb_error
from django.conf import settings
from lazy_client_core.models.tvshow import update_show_favs
import shutil
import datetime

logger = logging.getLogger(__name__)

def upgrade():

    #Delete all mappings
    for mapping in TVShowMappings.objects.all():
        mapping.delete()

    #Reset error downloads
    for dlitem in DownloadItem.objects.filter(~Q(status=DownloadItem.COMPLETE), retries__gt=settings.DOWNLOAD_RETRY_COUNT).order_by('priority','id'):
        dlitem.retries = 0
        dlitem.save()

    #Delete all metaparser cache
    from lazy_common.models import MetaParserCache
    for p in MetaParserCache.objects.all():
        p.delete()

    #Update tvshow objects
    tvshows = TVShow.objects.all()

    tvdb = Tvdb()

    for tvshow in tvshows:
        #First lets make sure we can get the object on thetvdb, it could of been deleted
        if tvshow.get_tvdb_obj() is None:
            try:
                tvdb[int(tvshow.id)]
            except tvdb_error as e:
                if "HTTP Error 404" in str(e):
                    logger.info("Deleting %s due to 404 error" % tvshow.title)
                    tvshow.delete()
                    continue
            except KeyError:
                logger.info("Deleting %s due to KeyError" % tvshow.title)
                tvshow.delete()
                continue
            except IndexError:
                logger.info("Deleting %s due to IndexError" % tvshow.title)
                tvshow.delete()
                continue
        else:
            tvshow.update_from_tvdb()

        if "Duplicate of" in tvshow.title:
            tvshow.delete()
            continue

        if tvshow.title is None or tvshow.title == "" or tvshow.title == " " or len(tvshow.title) == 0:
            logger.info("Deleting %s" % tvshow.title)
            tvshow.delete()
            continue


    #Lets set the favs
    update_show_favs()

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
            show_name = TVShow.clean_title(show_name)

            try:
                found = TVShow.find_by_title(show_name)
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
