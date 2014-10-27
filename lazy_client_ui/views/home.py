from django.views.generic import TemplateView
from django.conf import settings
import os
import logging
from lazy_client_core.models import DownloadItem

logger = logging.getLogger(__name__)

class DebugView(TemplateView):
    template_name = 'home/debug.html'


    def get_context_data(self, **kwargs):
        context = super(DebugView, self).get_context_data(**kwargs)

        from lazy_client_core.utils import threadmanager

        context['queue'] = threadmanager.queue_manager

        return context

class IndexView(TemplateView):
    template_name = 'home/index.html'
    model = DownloadItem

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        from lazy_client_ui import common

        context['downloading'] = common.num_downloading()
        context['extracting'] = common.num_extracting()
        context['queue'] = common.num_queue()
        context['pending'] = common.num_pending()
        context['errors'] = common.num_error()
        context['complete'] = common.num_complete(days=14)

        from lazy_client_core.utils.threadmanager import queue_manager
        context['queue_running'] = queue_manager.queue_running()

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
