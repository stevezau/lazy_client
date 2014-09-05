from django.forms import widgets
from rest_framework import serializers
from lazy_client_core.models import DownloadItem, TVShow, Movie
import logging
import rest_framework.relations
logger = logging.getLogger(__name__)
from rest_framework import status
from rest_framework.response import Response


class DownloadItemSerializer(serializers.ModelSerializer):
    tvdbid_id = serializers.IntegerField(required=False)
    imdbid_id = serializers.IntegerField(required=False)
    ftppath = serializers.CharField(required=True)

    class Meta:
        model = DownloadItem
        fields = ('title', 'imdbid_id', 'tvdbid_id', 'status', 'section', 'localpath', 'status')


class ImdbItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = Movie
        fields = ('id', 'title', 'score', 'votes', 'year', 'genres', 'description')


class TvdbItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = TVShow
        fields = ('id', 'title', 'posterimg', 'networks', 'genres', 'description', 'imdbid')