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
from lazy_client_core.exceptions import AlradyExists_Updated, AlradyExists
from rest_framework.decorators import api_view
from django.core.exceptions import ObjectDoesNotExist

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

class TvdbDetail(generics.RetrieveUpdateDestroyAPIView):
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
            from lazy_client_core.utils.queuemanager import QueueManager
            QueueManager.stop_queue()
            return Response({'status': 'success', 'detail': "Queue Stopped"})

        if action == "start_queue":
            from lazy_client_core.utils.queuemanager import QueueManager
            QueueManager.start_queue()
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
def download_action(request, pk):
    from rest_framework import status

    if request.method == "POST":
        if 'action' not in request.DATA:
            error = {'status': 'failed', 'detail': "invalid action"}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

        action = request.DATA['action']

        if action == "ignore":
            from lazy_common import metaparser
            from lazy_client_core.utils import common

            try:
                dlitem = DownloadItem.objects.get(id=pk)

                if dlitem.get_type() == metaparser.TYPE_TVSHOW:
                    series_data = dlitem.metaparser()

                    if series_data:
                        ignoretitle = series_data.details['series'].replace(" ", ".")
                        common.ignore_show(ignoretitle)
                        dlitem.delete()
                    else:
                        dlitem.delete()

                    return Response({'status': 'success', 'detail': "ignored show %s" % ignoretitle})
                else:
                    return Response({'status': 'failed', 'detail': "cannot ignore as not a TVShow"})

            except ObjectDoesNotExist:
                error = {'status': 'failed', 'detail': "unable to find download item"}
                return Response(error, status=status.HTTP_400_BAD_REQUEST)

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
            tvshow_json['label'] = "Ep %s - %s" % (ep_obj['episodenumber'], ep_obj['episodename'])
            tvshow_json['value'] = ep_obj['episodenumber']
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