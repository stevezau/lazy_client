import json
import logging

from rest_framework import generics
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import status
from flexget.utils.imdb import ImdbSearch
from lazy_client_core.models import DownloadItem, TVShow, Movie
from lazy_client_api.serializers import DownloadItemSerializer, ImdbItemSerializer, TvdbItemSerializer
from lazy_common.tvdb_api import Tvdb
from lazy_client_core.exceptions import AlradyExists_Updated, AlradyExists, Ignored
from rest_framework.decorators import api_view
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from lazy_common import metaparser

logger = logging.getLogger(__name__)


class DownloadItemList(generics.ListCreateAPIView):
    queryset = DownloadItem.objects.all()[1:10]
    serializer_class = DownloadItemSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.DATA, files=request.FILES)

        if serializer.is_valid():
            serializer.object.ftppath = request.DATA['ftppath']
            serializer.data['ftppath'] = request.DATA['ftppath']
            self.pre_save(serializer.object)
            self.object = serializer.save(force_insert=True)
            self.post_save(self.object, created=True)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED,
                            headers=headers)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        try:
            return super(DownloadItemList, self).post(request, *args, **kwargs)
        except AlradyExists_Updated as e:
            serializer = DownloadItemSerializer(e.existingitem)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Ignored as e:
            return Response({"status": "failed", "message": str(e)}, status=status.HTTP_202_ACCEPTED)


class DownloadItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = DownloadItem.objects.all()
    serializer_class = DownloadItemSerializer

class ImdbItemList(generics.ListCreateAPIView):
    queryset = Movie.objects.all()[1:10]
    serializer_class = ImdbItemSerializer

class ImdbDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Movie.objects.all()
    serializer_class = TvdbItemSerializer

class TvdbItemList(generics.ListCreateAPIView):
    queryset = TVShow.objects.all()[1:10]
    serializer_class = TvdbItemSerializer

class TVShowDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = TVShow.objects.all()
    serializer_class = TvdbItemSerializer

@api_view(['POST'])
def server_api(request):
    from rest_framework import status

    if request.method == "POST":
        if 'action' not in request.DATA:
            error = {'status': 'failed', 'detail': "invalid action"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        action = request.DATA['action']

        if action == "stop_queue":
            from lazy_client_core.utils.threadmanager import queue_manager
            queue_manager.pause()
            return Response({'status': 'success', 'detail': "Queue Stopped"})

        if action == "start_queue":
            from lazy_client_core.utils.threadmanager import queue_manager
            queue_manager.resume()
            return Response({'status': 'success', 'detail': "Queue started"})


@api_view(['POST'])
def downloads(request):
    from rest_framework import status

    if request.method == "POST":
        if 'site' not in request.DATA:
            error = {'status': 'failed', 'detail': "missing site"}
            return Response(error)

        if 'download' not in request.DATA:
            error = {'status': 'failed', 'detail': "missing download"}
            return Response(error)

        site = request.DATA['site'].lower()
        download = request.DATA['download']

        logger.error("downloading %s %s" % (site, download))

        if site == "ftp":
            #Lets add to the queue directly
            new_download_item = DownloadItem()
            new_download_item.status = DownloadItem.QUEUE
            new_download_item.ftppath = download
            new_download_item.requested = True

            try:
                new_download_item.save()
            except AlradyExists:
                error = {'status': 'failed', 'detail': "Already downloaded previously"}
                return Response(error)
            except AlradyExists_Updated:
                pass
            except Exception as e:
                print type(e)
                error = {'status': 'failed', 'detail': str(e)}
                return Response(error)

            return Response({'status': 'success', 'detail': "added to queue : %s" % download})
        else:
            from lazy_client_core.utils import lazyapi
            try:
                results = lazyapi.download_torrents([{'site': site, "title": download}])
            except lazyapi.LazyServerExcpetion as e:
                logger.exception(e)
                error = {'status': 'failed', 'detail': str(e)}
                return Response(error)

            for result in results:
                if result['status'] != "finished":
                    error = {'status': 'failed', 'detail': "Unable to download as %s " % result['message']}
                    return Response(error)

                try:
                    #Now add it to the queue
                    new_download_item = DownloadItem()
                    new_download_item.status = DownloadItem.QUEUE
                    new_download_item.ftppath = result['ftp_path']
                    new_download_item.requested = True

                    if 'type' in result:
                        if result['type'] == "tvshow":
                            new_download_item.type = metaparser.TYPE_TVSHOW
                        elif result['type'] == "movie":
                            new_download_item.type = metaparser.TYPE_MOVIE

                    new_download_item.save()
                except AlradyExists:
                    error = {'status': 'failed', 'detail': "Already downloaded previously"}
                    return Response(error)
                except AlradyExists_Updated:
                    pass
                except Exception as e:
                    error = {'status': 'failed', 'detail': str(e)}
                    return Response(error)

            return Response({'status': 'success', 'detail': "added to queue : %s" % download})

    #error not found
    error = {'status': 'failed', 'detail': "invalid action"}
    return Response(error, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def tvshow_action(request, pk):
    if request.method == "POST":
        if 'action' not in request.DATA:
            error = {'status': 'failed', 'detail': "invalid action"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        try:
            tvshow = TVShow.objects.get(id=pk)
        except ObjectDoesNotExist:
            error = {'status': 'failed', 'detail': "unable to find tvshow"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        action = request.DATA['action']

        if action == "delete_all":
            tvshow.delete_all()
            return Response({'status': 'success', 'detail': "delete all epsiodes"})

        if action == "clear_results":
            tvshow.fix_report = ""
            tvshow.save()
            return Response({'status': 'success', 'detail': ""})

        if action == "fix_missing":
            #Check for existing running job
            fix_missing = {}
            print request.DATA

            if 'fix' not in request.DATA:
                error = {'status': 'failed', 'detail': "no eps to fix"}
                return Response(error, status=status.HTTP_200_OK)

            if tvshow.ignored:
                return Response({'status': 'failed', 'detail': "show marked as ignored"})

            for season_str in request.DATA['fix']:
                try:
                    season = int(season_str)
                except:
                    continue

                eps = []

                for ep in request.DATA['fix'][season_str]:
                    try:
                        eps.append(int(ep))
                    except:
                        continue

                if len(eps) > 0:
                    fix_missing[season] = eps

            if len(fix_missing) == 0:
                error = {'status': 'failed', 'detail': "no eps to fix"}
                return Response(error, status=status.HTTP_200_OK)

            from lazy_client_core.models.tvshow import AlreadyRunningException
            try:
                tvshow.fix_missing(fix_missing)
                return Response({'status': 'success', 'detail': ""})
            except AlreadyRunningException:
                return Response({'status': 'failed', 'detail': "Already searching for missing jobs, you can only run one at a time."})

        if action == "toggle_fav":
            if tvshow.favorite:
                tvshow.set_favorite(False)
            else:
                tvshow.set_favorite(True)

            tvshow.save()
            return Response({'status': 'success', 'detail': "favorite state toggled", "state": tvshow.favorite})

        if action == "toggle_ignore":
            if tvshow.is_ignored():
                tvshow.set_ignored(False)
            else:
                tvshow.set_ignored(True)

            tvshow.save()
            return Response({'status': 'success', 'detail': "ignored state toggled", "state": tvshow.ignored})

        if action == "get_missing":
            if not tvshow.get_local_path():
                return Response({'status': 'failed', 'detail': "path does not exist",})

            missing = tvshow.get_missing()
            return Response({'status': 'success', 'detail': "", "missing": missing})

    return Response({'status': 'fail', 'detail': "invalid action"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def download_action(request, pk):
    from rest_framework import status

    if request.method == "POST":
        if 'action' not in request.DATA:
            error = {'status': 'failed', 'detail': "invalid action"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        action = request.DATA['action']

        if action == "ignore":
            from lazy_common import metaparser

            try:
                dlitem = DownloadItem.objects.get(id=pk)

                if dlitem.tvdbid:
                    dlitem.tvdbid.set_ignored(True)
                    dlitem.tvdbid.save()

                if dlitem.imdbid:
                    dlitem.imdbid.ignored = True
                    dlitem.imdbid.save()

                dlitem.delete()

                return Response({'status': 'success', 'detail': "ignored %s" % dlitem.title})

            except ObjectDoesNotExist:
                error = {'status': 'failed', 'detail': "unable to find download item"}
                return Response(error, status=status.HTTP_400_BAD_REQUEST)

        if action == "seconds_left":
            try:
                dlitem = DownloadItem.objects.get(pk=pk)

                from lazy_client_core.utils import lazyapi
                seconds_left = lazyapi.seconds_left(dlitem)

                return Response({'status': 'success', 'detail': seconds_left})
            except ObjectDoesNotExist as e:
                return Response({'status': 'success', 'detail': -1})

        if action == "seconds_left":
            try:
                dlitem = DownloadItem.objects.get(pk=pk)

                from lazy_client_core.utils import lazyapi
                seconds_left = lazyapi.seconds_left(dlitem)

                return Response({'status': 'success', 'detail': seconds_left})
            except ObjectDoesNotExist as e:
                return Response({'status': 'success', 'detail': -1})


        if action == "approve":
            try:
                dlitem = DownloadItem.objects.get(pk=pk)
                dlitem.status = DownloadItem.QUEUE
                dlitem.save()
                return Response({'status': 'success', 'detail': "approved pk: %s" % pk})
            except ObjectDoesNotExist as e:
                error = {'status': 'failed', 'detail': "unable to find download item"}
                return Response(error, status=status.HTTP_400_BAD_REQUEST)

        if action == "retry":
            try:
                dlitem = DownloadItem.objects.get(pk=pk)
                dlitem.retries = 0
                dlitem.save()
                return Response({'status': 'success', 'detail': "retrying pk: %s" % pk})
            except ObjectDoesNotExist as e:
                error = {'status': 'failed', 'detail': "unable to find download item"}
                return Response(error, status=status.HTTP_400_BAD_REQUEST)

        if action == "reset":
            try:
                dlitem = DownloadItem.objects.get(pk=pk)
                dlitem.reset()
                return Response({'status': 'success', 'detail': "reset pk: %s" % pk})
            except ObjectDoesNotExist as e:
                error = {'status': 'failed', 'detail': "unable to find download item"}
                return Response(error, status=status.HTTP_400_BAD_REQUEST)

        if action == "delete":
            try:
                dlitem = DownloadItem.objects.get(pk=pk)
                dlitem.delete()
                return Response({'status': 'success', 'detail': "deleted pk: %s" % pk})
            except ObjectDoesNotExist as e:
                error = {'status': 'failed', 'detail': "unable to find download item"}
                return Response(error, status=status.HTTP_400_BAD_REQUEST)


        #Action not found
        error = {'status': 'failed', 'detail': "invalid action"}
        return Response(error, status=status.HTTP_400_BAD_REQUEST)

def get_tvdb_eps(request, showid, season):
    if request.is_ajax():
        tvdb = Tvdb()
        eps = tvdb[int(showid)][int(season)]

        results = []

        for ep in eps.keys():
            ep_obj = eps[ep]
            tvshow_json = {}
            tvshow_json['label'] = "Ep %s - %s" % (ep_obj['episode_number'], ep_obj['episodename'])
            tvshow_json['value'] = ep_obj['episode_number']
            results.append(tvshow_json)

        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)

def get_tvdb_season(request, showid):
    if request.is_ajax():
        tvdb = Tvdb()
        show = tvdb[int(showid)]
        results = []

        for season in show.keys():
            if season == 0:
                label = "Specials"
            else:
                label = "Season %s" % season

            tvshow_json = {}
            tvshow_json['label'] = label
            tvshow_json['value'] = season
            results.append(tvshow_json)

        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)

def search_tvdb(request):
    if request.is_ajax():
        q = request.GET.get('term', '')
        tvdb = Tvdb()
        search = tvdb.search(q)

        results = []

        if len(search) == 0:
            tvshow_json = {}
            tvshow_json['id'] = "NO SHOWS FOUND"
            tvshow_json['label'] = "NO SHOWS FOUND"
            tvshow_json['value'] = "NO SHOWS FOUND"
            results.append(tvshow_json)
        else:
            for tvshow in search:
                tvshow_json = {}
                tvshow_json['id'] = tvshow['seriesid']
                tvshow_json['label'] = tvshow['seriesname']
                tvshow_json['value'] = tvshow['seriesname']
                results.append(tvshow_json)

        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)


def search_imdb(request):

    if request.is_ajax():
        q = request.GET.get('term', '')
        imdbS = ImdbSearch()
        search = imdbS.search(q)

        results = []

        if len(search) == 0:
            movie_json = {}
            movie_json['id'] = "NO MOVIES FOUND"
            movie_json['label'] = "NO MOVIES FOUND"
            movie_json['value'] = "NO MOVIES FOUND"
            results.append(movie_json)
        else:
            for movie in search:
                movie_json = {}
                movie_json['id'] = int(movie['imdb_id'].lstrip('tt'))

                title = movie['name']

                if 'year' in movie:
                    title += " (%s)" % movie['year']

                movie_json['label'] = title
                movie_json['value'] = title
                results.append(movie_json)

        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)