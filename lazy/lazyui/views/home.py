from django.views.generic import TemplateView
from django.conf import settings
import os
import logging

from lazycore.models import DownloadItem
from lazycore.utils.queuemanager import QueueManager


logger = logging.getLogger(__name__)

class IndexView(TemplateView):
    template_name = 'home/index.html'
    model = DownloadItem

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')

        if action == "stop":
            QueueManager.stop_queue()

        if action == "start":
            QueueManager.start_queue()

        return super(IndexView, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        context['downloading'] = DownloadItem.objects.filter(status=DownloadItem.DOWNLOADING).count()
        context['extracting'] = DownloadItem.objects.filter(status=DownloadItem.MOVE).count()
        context['queue'] = DownloadItem.objects.filter(status=DownloadItem.QUEUE).count()
        context['pending'] = DownloadItem.objects.filter(status=DownloadItem.PENDING).count()
        context['errors'] = DownloadItem.objects.filter(status=DownloadItem.ERROR).count()

        context['queue_running'] = QueueManager.queue_running()

        statvfs = os.statvfs(settings.DATA_PATH)

        dt = statvfs.f_frsize * statvfs.f_blocks     # Size of filesystem in bytes
        df = statvfs.f_frsize * statvfs.f_bfree      # Actual number of free bytes

        percentfree = (df / float(dt)) * 100
        percentused = round(100 - percentfree, 2)

        context['free_gb'] = df / 1024 / 1024 / 1024
        context['percent_used'] = percentused

        return context
