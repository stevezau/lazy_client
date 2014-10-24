import logging
import os
from django.shortcuts import render
from lazy_client_ui.forms import FindTVShow, FindMovie
from django.http import HttpResponseRedirect, HttpResponse
from lazy_client_core.models import TVShow, TVShowMappings
from lazy_common.tvdb_api import Tvdb
from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView, DetailView, UpdateView
from lazy_client_core.utils import xbmc
from lazy_client_core.exceptions import XBMCConnectionError, InvalidXBMCURL
from lazy_common import metaparser
from lazy_client_core.utils import common

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
                #Find all shows that are marked as ignored and exist still
                context['ignored_exist'] = [tvshow for tvshow in TVShow.objects.filter(ignored=True) if tvshow.exists()]

                #Find all shows that are marked as ignored and exist still
                context['eneded_watched'] = []

                context['alerts'] = []
                do_break = False

                for tvshow in TVShow.objects.filter(status=TVShow.ENDED):
                    if not os.path.exists(tvshow.get_local_path()):
                        continue

                    all_watched = True
                    files = common.get_video_files(tvshow.get_local_path())

                    for f in files:
                        try:
                            playcount = xbmc.get_file_playcount(f)
                            if not playcount or not playcount > 0:
                                all_watched = False
                                break
                        except InvalidXBMCURL as e:
                            msg = "Invalid XBMC URL in lazysettings.py. The media server can provide more accurate cleanup suggestions if you link it to XBMC"
                            if msg not in context['alerts']:
                                context['alerts'].append(msg)
                            context['eneded_watched'] = []
                            do_break = True
                            break
                        except XBMCConnectionError as e:
                            msg = "Cannot connect to XBMC. The media server can provide more accurate cleanup suggestions if you link it to XBMC"
                            if msg not in context['alerts']:
                                context['alerts'].append(msg)
                            context['eneded_watched'] = []
                            do_break = True

                    if do_break:
                        break

                    if all_watched:
                        context['eneded_watched'].append(tvshow)

                #Find all shows that have no watched eps
                context['none_watched'] = []

                for tvshow in TVShow.objects.filter(status=TVShow.ENDED):
                    if not os.path.exists(tvshow.get_local_path()):
                        continue

                    none_watched = True
                    files = common.get_video_files(tvshow.get_local_path())

                    do_break = False

                    for f in files:
                        try:
                            playcount = xbmc.get_file_playcount(f)
                            if playcount and playcount > 0:
                                none_watched = False
                                break
                        except InvalidXBMCURL as e:
                            msg = "Invalid XBMC URL in lazysettings.py. The media server can provide more accurate cleanup suggestions if you link it to XBMC"
                            if msg not in context['alerts']:
                                context['alerts'].append(msg)
                            context['none_watched'] = []
                            do_break = True
                            break
                        except XBMCConnectionError as e:
                            msg = "Cannot connect to XBMC. The media server can provide more accurate cleanup suggestions if you link it to XBMC"
                            if msg not in context['alerts']:
                                context['alerts'].append(msg)
                            context['none_watched'] = []
                            do_break = True
                            break
                    if do_break:
                        break

                    if none_watched:
                        context['none_watched'].append(tvshow)

                return render(request, 'manage/tvshows/cleanup.html', context)

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
                    tvshow = TVShow()
                    tvshow.update_from_dict(show)
                    shows.append(show)

            from operator import itemgetter, attrgetter, methodcaller
            shows = sorted(shows, key=methodcaller('exists'), reverse=True)

            if len(shows) == 1:
                return redirect('manage.tvshows.detail', pk=shows[0].id)

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

def tv_schedule(request):
    return render(request, 'manage/tvshows/schedule.html', {})



def movies(request):

    form = FindMovie(request.GET or None)

    context = {'form': form}

    return render(request, 'manage/movies/index.html', context)


