import logging
import os
from django.shortcuts import render
from lazy_client_ui.forms import FindTVShow
from django.http import HttpResponseRedirect, HttpResponse
from lazy_client_core.utils import missingscanner
from lazy_client_core.models import TVShow
from lazy_common.tvdb_api import Tvdb

logger = logging.getLogger(__name__)


def tvshows(request):

    form = FindTVShow(request.POST or None)

    if request.method == "POST":
        #OK Lets have a look
        if form.is_valid():
            search = form.cleaned_data['search']

            local_shows = TVShow.objects.filter(title__icontains=search)
            tvdb = Tvdb()
            tvdb_shows = tvdb.search(search)

            print tvdb_shows



        return render(request, 'manage/tvshows/index.html', {'form': form})
    else:

        return render(request, 'manage/tvshows/index.html', {'form': form})