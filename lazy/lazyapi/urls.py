from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from lazyapi.views import *

urlpatterns = patterns('',
    url(r'^downloads/$', DownloadItemList.as_view(), name="download_api"),
    url(r'^downloads/(?P<pk>[0-9]+)/$', DownloadItemDetail.as_view(), name="download_api_detail"),
    url(r'^imdb/$', ImdbItemList.as_view(), name="imdb_api"),
    url(r'^tvdb/$', TvdbItemList.as_view(), name="tvdb_api"),
    url(r'^tvdb/(?P<pk>[0-9]+)/$', TvdbDetail.as_view(), name="tvdb_api_detail"),
    url(r'^tvdb/(?P<pk>[0-9]+)/$', ImdbDetail.as_view(), name="tvdb_api_detail"),


    #Search TVShow via thetvdb.com
    url(r'^search_tvdb/$', 'lazyapi.views.search_tvdb', name='search_tvdb'),
    url(r'^search_tvdb_season/(?P<showid>[0-9]+)/(?P<season>[0-9]+)/$', 'lazyapi.views.search_tvdb_season', name='search_tvdb_season'),
)


urlpatterns = format_suffix_patterns(urlpatterns)