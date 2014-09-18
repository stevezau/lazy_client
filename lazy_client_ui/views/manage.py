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

            #Get a list of local showids
            local_ids = [show.id for show in local_shows]

            #Remove local shows found in tvdb
            tvdb_shows = []
            for show in tvdb.search(search):
                if show['id'] not in local_ids:
                    tvdb_shows.append(show)

            import pprint
            pprint.pprint(tvdb.search(search), indent=4)

        return render(request, 'manage/tvshows/index.html', {'form': form, 'tvdb_shows': tvdb_shows, 'local_shows': local_shows})
    else:

        return render(request, 'manage/tvshows/index.html', {'form': form})