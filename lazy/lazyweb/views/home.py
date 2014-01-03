from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from lazyweb.models import DownloadItem
from django.views.generic import TemplateView
from django.conf import settings
from django.shortcuts import render_to_response
import os

class IndexView(TemplateView):
    template_name = 'home/index.html'
    model = DownloadItem

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        context['downloading'] = DownloadItem.objects.filter(status=DownloadItem.DOWNLOADING).count()
        context['extracting'] = DownloadItem.objects.filter(status=DownloadItem.MOVE).count()
        context['queue'] = DownloadItem.objects.filter(status=DownloadItem.QUEUE).count()
        context['pending'] = DownloadItem.objects.filter(status=DownloadItem.PENDING).count()
        context['errors'] = DownloadItem.objects.filter(status=DownloadItem.ERROR).count()

        statvfs = os.statvfs(settings.DATA_PATH)

        dt = statvfs.f_frsize * statvfs.f_blocks     # Size of filesystem in bytes
        df = statvfs.f_frsize * statvfs.f_bfree      # Actual number of free bytes

        context['gbFree'] = df / 1024 / 1024 / 1024
        context['percentUsed'] = 100 - dt / df

        return context
