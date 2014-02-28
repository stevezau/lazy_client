from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from lazyweb.models import DownloadItem
from django.views.generic import TemplateView
from django.conf import settings
from django.shortcuts import render_to_response
import os
import logging


from lazyweb import utils

logger = logging.getLogger(__name__)

class IndexView(TemplateView):
    template_name = 'home/index.html'
    model = DownloadItem

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')

        if action == "stop":
            utils.stop_queue()

        if action == "start":
            utils.start_queue()

        return super(IndexView, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        context['downloading'] = DownloadItem.objects.filter(status=DownloadItem.DOWNLOADING).count()
        context['extracting'] = DownloadItem.objects.filter(status=DownloadItem.MOVE).count()
        context['queue'] = DownloadItem.objects.filter(status=DownloadItem.QUEUE).count()
        context['pending'] = DownloadItem.objects.filter(status=DownloadItem.PENDING).count()
        context['errors'] = DownloadItem.objects.filter(status=DownloadItem.ERROR).count()

        status = utils.queue_running()

        if status:
            context['status'] = "Running"
        else:
            context['status'] = "Stopped"


        statvfs = os.statvfs(settings.DATA_PATH)

        dt = statvfs.f_frsize * statvfs.f_blocks     # Size of filesystem in bytes
        df = statvfs.f_frsize * statvfs.f_bfree      # Actual number of free bytes

        percentfree = (df / float(dt)) * 100
        percentused = round(100 - percentfree, 2)

        context['gbFree'] = df / 1024 / 1024 / 1024
        context['percentUsed'] = percentused


        return context
