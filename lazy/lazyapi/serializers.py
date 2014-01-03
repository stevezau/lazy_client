from django.forms import widgets
from rest_framework import serializers
from lazyweb.models import DownloadItem, Tvdbcache, Imdbcache
import logging
import rest_framework.relations
logger = logging.getLogger(__name__)

class DownloadItemSerializer(serializers.ModelSerializer):
    tvdbid_id = serializers.IntegerField(required=False)
    imdbid_id = serializers.IntegerField(required=False)

    class Meta:
        model = DownloadItem
        fields = ('title', 'ftppath', 'imdbid_id', 'tvdbid_id', 'status', 'section', 'localpath', 'status')

class ImdbItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = Imdbcache
        fields = ('id', 'title', 'score', 'votes', 'year', 'genres', 'description')

class TvdbItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = Tvdbcache
        fields = ('id', 'title', 'posterimg', 'networks', 'genres', 'description', 'imdbid')