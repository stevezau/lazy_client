from django.views.generic import TemplateView
from django.conf import settings
import os
import logging
from django.db.models import Q

from lazy_client_core.models import DownloadItem
from lazy_client_core.utils.queuemanager import QueueManager


logger = logging.getLogger(__name__)

class IndexView(TemplateView):
    template_name = 'home/index.html'
    model = DownloadItem

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == "stop":
            QueueManager.stop_queue()

        if action == "start":
            QueueManager.start_queue()

        return super(IndexView, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        context['downloading'] = DownloadItem.objects.filter(status=DownloadItem.DOWNLOADING, retries__lte=settings.DOWNLOAD_RETRY_COUNT).count()
        context['extracting'] = DownloadItem.objects.filter(Q(status=DownloadItem.RENAME) | Q(status=DownloadItem.EXTRACT), retries__lte=settings.DOWNLOAD_RETRY_COUNT).count()
        context['queue'] = DownloadItem.objects.filter(status=DownloadItem.QUEUE, retries__lte=settings.DOWNLOAD_RETRY_COUNT).count()
        context['pending'] = DownloadItem.objects.filter(status=DownloadItem.PENDING, retries__lte=settings.DOWNLOAD_RETRY_COUNT).count()
        context['errors'] = DownloadItem.objects.filter(~Q(status=DownloadItem.COMPLETE), retries__gt=settings.DOWNLOAD_RETRY_COUNT).count()

        context['queue_running'] = QueueManager.queue_running()

        if os.path.exists(settings.DATA_PATH):
            statvfs = os.statvfs(settings.DATA_PATH)

            dt = statvfs.f_frsize * statvfs.f_blocks     # Size of filesystem in bytes
            df = statvfs.f_frsize * statvfs.f_bfree      # Actual number of free bytes

            percentfree = (df / float(dt)) * 100
            percentused = round(100 - percentfree, 2)

            context['free_gb'] = df / 1024 / 1024 / 1024
            context['percent_used'] = percentused
        else:
            context['free_gb'] = 0
            context['percent_used'] = 0

        return context
