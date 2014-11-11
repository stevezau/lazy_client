from django.views.generic import TemplateView
from django.conf import settings
import os
import logging
from lazy_client_core.models import DownloadItem

logger = logging.getLogger(__name__)

class DebugView(TemplateView):
    template_name = 'home/debug.html'

    def dumpstacks(self):
        import threading, traceback, sys
        id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
        code = []
        for threadId, stack in sys._current_frames().items():
            code.append("\n# Thread: %s(%d)" % (id2name.get(threadId,""), threadId))
            for filename, lineno, name, line in traceback.extract_stack(stack):
                code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
                if line:
                    code.append("  %s" % (line.strip()))
        return "\n".join(code)

    def get_context_data(self, **kwargs):
        context = super(DebugView, self).get_context_data(**kwargs)

        context['thread_stack'] = self.dumpstacks()
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

        context['mount_points'] = []

        from lazy_client_core.utils import common as core_common

        for mount_point in core_common.get_mount_points():
            free_bytes = core_common.get_fs_freespace(mount_point)
            free_gb = free_bytes / 1024 / 1024 / 1024
            percentused = core_common.get_fs_percent_used(mount_point)

            context['mount_points'].append({"mount_point": mount_point, "free_gb": free_gb, "percent_used": percentused})

        return context
