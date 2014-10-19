import logging
import os

from django.views.generic import FormView
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from lazy_client_ui.forms import Find
from lazy_client_core.models import DownloadItem
from lazy_client_core.utils import lazyapi
from django.shortcuts import render

logger = logging.getLogger(__name__)

class FindIndexView(FormView):
    template_name = 'find/index.html'
    form_class = Find

    def form_valid(self, form):
        return HttpResponseRedirect(reverse('other.find.search', kwargs={'search': form.cleaned_data['search']}))


def find(request):

    form = Find(request.GET or None)
    context = {'form': form}

    if request.method == "GET":
        #OK Lets have a look
        if form.is_valid():
            search = form.cleaned_data['search']

            ftp_results = {}

            try:
                logger.error("searching %s" % search)

                ftp_results['results'] = lazyapi.search_ftp(search)

                for result in ftp_results['results']:
                    result['name'] = os.path.split(result['path'])[-1]

            except lazyapi.LazyServerExcpetion as e:
                ftp_results['message'] = str(e)

            torrent_results = {}

            try:
                torrent_results['results'] = lazyapi.search_torrents(search)
            except lazyapi.LazyServerExcpetion as e:
                torrent_results['message'] = str(e)

            context['torrent_results'] = torrent_results
            context['ftp_results'] = ftp_results

            context['local_results'] = DownloadItem.objects.filter(title__icontains=search)

        return render(request, 'find/index.html', context)
    else:
        return render(request, 'find/index.html', context)