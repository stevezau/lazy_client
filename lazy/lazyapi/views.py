from lazyweb.models import DownloadItem, Imdbcache, Tvdbcache
from lazyapi.serializers import DownloadItemSerializer, ImdbItemSerializer, TvdbItemSerializer
from rest_framework import mixins
from rest_framework import generics
import json
from django.http import HttpResponse
from lazyweb.utils.tvdb_api import Tvdb
from lazyweb.exceptions import AlradyExists_Updated
from rest_framework.response import Response
from rest_framework import status
import logging

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
    queryset = Imdbcache.objects.all()[1:10]
    serializer_class = ImdbItemSerializer

class ImdbDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tvdbcache.objects.all()
    serializer_class = TvdbItemSerializer

class TvdbItemList(generics.ListCreateAPIView):
    queryset = Tvdbcache.objects.all()[1:10]
    serializer_class = TvdbItemSerializer


class TvdbDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tvdbcache.objects.all()
    serializer_class = TvdbItemSerializer

def get_tvdb_eps(request, showid, season):
    if request.is_ajax():
        tvdb = Tvdb()
        eps = tvdb[int(showid)][int(season)]

        results = []

        for ep in eps.keys():
            ep_obj = eps[ep]
            tvshow_json = {}
            tvshow_json['label'] = "%s: %s" % (ep_obj['episodenumber'], ep_obj['episodename'])
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
            tvshow_json = {}
            tvshow_json['label'] = season
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