__author__ = 'steve'
from lazy_client_core.models import DownloadItem, TVShow, DownloadLog, Movie
import logging
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import pytz
logger = logging.getLogger(__name__)

def convert_datetime(dt):
    dt = pytz.timezone(timezone.get_default_timezone_name()).localize(dt)
    return dt

def upgrade():

    #Convert all dates to timezone aware
    for d in DownloadItem.objects.all():
        if d.date and timezone.is_naive(d.date):
            d.date = convert_datetime(d.date)

        if d.dateadded and timezone.is_naive(d.dateadded):
            d.dateadded = convert_datetime(d.dateadded)

        if d.dlstart and timezone.is_naive(d.dlstart):
            d.dlstart = convert_datetime(d.dlstart)

        d.save()

    for t in TVShow.objects.all():
        if t.updated and timezone.is_naive(t.updated):
            t.updated = convert_datetime(t.updated)

        t.save()

    for m in Movie.objects.all():
        if m.updated and timezone.is_naive(m.updated):
            m.updated = convert_datetime(m.updated)

        m.save()

    #clear out logs
    DownloadLog.objects.all().delete()

    #delete cache


    #Delete all metaparser cache
    from lazy_common.models import MetaParserCache
    for p in MetaParserCache.objects.all():
        p.delete()

    #Update all download items
    count = DownloadItem.objects.all().count()
    i = 0
    for d in DownloadItem.objects.all():
        logger.debug("%s/%s Parsing %s" % (i, count, d.title))
        d.parse_title()
        d.save()
        i += 1

    #Update tvshow objects
    count = TVShow.objects.all().count()
    up_to = 0
    for tvshow in TVShow.objects.all():
        try:
            up_to += 1
            print "### %s / %s" % (up_to, count)
            tvshow.update_from_tvdb()
        except:
            pass
