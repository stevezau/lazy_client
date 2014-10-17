import logging
import os
from django.shortcuts import render
from lazy_client_ui.forms import FindTVShow
from django.http import HttpResponseRedirect, HttpResponse
from lazy_client_core.models import TVShow, TVShowMappings
from lazy_common.tvdb_api import Tvdb
from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView, DetailView, UpdateView

logger = logging.getLogger(__name__)

class TVShowDetail(UpdateView):
    model = TVShow
    template_name = "manage/tvshows/detail.html"


def tvshows(request):

    form = FindTVShow(request.GET or None)

    context = {'form': form}

    if request.method == "GET":
        if 'show' in request.GET:
            if request.GET['show'] == "approved":
                context['shows'] = TVShow.objects.filter(favorite=True)
                context['show_fav'] = True

            if request.GET['show'] == "ignored":
                context['shows'] = TVShow.objects.filter(ignored=True)
                context['show_ignore'] = True

            if request.GET['show'] == "ended":
                shows = []
                for show in TVShow.objects.filter(status=TVShow.ENDED).exclude(localpath__isnull=True).exclude(localpath__exact=''):
                    if os.path.exists(show.localpath):
                        shows.append(show)

                context['shows'] = shows
                context['show_delete'] = True

            if request.GET['show'] == "cleanup":
                context['shows'] = TVShow.objects.filter(favorite=True)
                context['show_fav'] = True

                #We need to do a cleanup suggestion



            return render(request, 'manage/tvshows/index.html', context)

        if form.is_valid():
            search = form.cleaned_data['search']

            show_mappings = list(TVShowMappings.objects.filter(title__icontains=search, ))
            show_ids = [s.tvdbid_id for s in show_mappings]
            found_shows = TVShow.objects.filter(id__in=show_ids)
            shows = [show for show in found_shows]

            tvdb = Tvdb()

            #Get a list of local showids
            local_ids = [s.id for s in shows]

            #Remove local shows found in tvdb
            for show in tvdb.search(search):
                if show['id'] not in local_ids:
                    tvshow = TVShow(show['id'])
                    tvshow.save()
                    tvshow.update_from_tvdb(update_imdb=False)
                    shows.append(tvshow)

            from operator import itemgetter, attrgetter, methodcaller
            shows = sorted(shows, key=methodcaller('exists'), reverse=True)

            if len(shows) == 1:
                return redirect('manage.tvshow.detail', pk=shows[0].id)

            context['shows'] = shows
        return render(request, 'manage/tvshows/index.html', context)
    else:

        return render(request, 'manage/tvshows/index.html', context)

class TVShowMissing(DetailView):
    model = TVShow
    template_name = "manage/tvshows/tvshow_missing.html"


class TVShowMissingResults(DetailView):
    model = TVShow
    template_name = "manage/tvshows/tvshow_missing_results.html"


class TVShowMissingLog(DetailView):
    model = TVShow
    template_name = "manage/tvshows/log.html"


def movies(request):

    return render(request, 'manage/movies/index.html', {})


