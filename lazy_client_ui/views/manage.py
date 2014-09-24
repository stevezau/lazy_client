import logging
import os
from django.shortcuts import render
from lazy_client_ui.forms import FindTVShow
from django.http import HttpResponseRedirect, HttpResponse
from lazy_client_core.utils import missingscanner
from lazy_client_core.models import TVShow
from lazy_common.tvdb_api import Tvdb
from django.views.generic import TemplateView, ListView, DetailView, UpdateView

logger = logging.getLogger(__name__)

class TVShowDetail(DetailView):
    model = TVShow
    template_name = "manage/tvshows/detail.html"


def tvshows(request):

    form = FindTVShow(request.GET or None)

    context = {'form': form}

    if request.method == "GET":
        #OK Lets have a look
        if form.is_valid():
            search = form.cleaned_data['search']

            shows = list(TVShow.objects.filter(title__icontains=search))

            tvdb = Tvdb()

            #Get a list of local showids
            local_ids = [s.id for s in shows]

            #Remove local shows found in tvdb
            for show in tvdb.search(search):
                if show['id'] not in local_ids:
                    tvshow = TVShow(show['id'])
                    tvshow.update_from_tvdb(update_imdb=False)
                    shows.append(tvshow)

            context['shows'] = shows
        return render(request, 'manage/tvshows/index.html', context)
    else:

        return render(request, 'manage/tvshows/index.html', context)