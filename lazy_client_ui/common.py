__author__ = 'steve'
from importlib import import_module
import logging
from lazy_client_core.models import DownloadItem
from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)

def load_button_module(package, fn):
    try:
        mod = import_module(package)
        function = getattr(mod, fn)
        return function
    except Exception as e:
        logger.exception(e)
        raise Exception(e)


def num_downloading():
    return DownloadItem.objects.filter(status=DownloadItem.DOWNLOADING, retries__lte=settings.DOWNLOAD_RETRY_COUNT).count()


def num_extracting():
    return DownloadItem.objects.filter(Q(status=DownloadItem.RENAME) | Q(status=DownloadItem.EXTRACT), retries__lte=settings.DOWNLOAD_RETRY_COUNT).count()


def num_queue():
    return DownloadItem.objects.filter(status=DownloadItem.QUEUE, retries__lt=settings.DOWNLOAD_RETRY_COUNT).count()


def num_pending():
    return DownloadItem.objects.filter(status=DownloadItem.PENDING, retries__lt=settings.DOWNLOAD_RETRY_COUNT).count()


def num_error():
    return DownloadItem.objects.filter(~Q(status=DownloadItem.COMPLETE), retries__gt=settings.DOWNLOAD_RETRY_COUNT).count()


def num_complete(days=7):
    from datetime import timedelta
    from django.utils import timezone
    some_day_last_week = timezone.now().date() - timedelta(days=7)
    monday_of_last_week = some_day_last_week - timedelta(days=(some_day_last_week.isocalendar()[2] - 1))
    monday_of_this_week = monday_of_last_week + timedelta(days=7)
    return DownloadItem.objects.filter(status=DownloadItem.COMPLETE, dateadded__gte=monday_of_last_week, dateadded__lt=monday_of_this_week).count()

