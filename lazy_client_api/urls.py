from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from lazy_client_api.views import *

urlpatterns = patterns('',

    url(r'^server/$', 'lazy_client_api.views.server_api', name="server_api"),

    url(r'^downloads/$', DownloadItemList.as_view(), name="download_api"),
    url(r'^downloads/add/$', 'lazy_client_api.views.downloads', name="server_api"),
    url(r'^downloads/(?P<pk>[0-9]+)/$', DownloadItemDetail.as_view(), name="download_api_detail"),
    url(r'^downloads/(?P<pk>[0-9]+)/action/$', 'lazy_client_api.views.download_action', name="api.downloads.action"),

    url(r'^imdb/$', ImdbItemList.as_view(), name="imdb_api"),
    url(r'^tvdb/$', TvdbItemList.as_view(), name="tvdb_api"),
    url(r'^tvshow/(?P<pk>[0-9]+)/$', TVShowDetail.as_view(), name="api.tvshow"),
    url(r'^tvshow/(?P<pk>[0-9]+)/action/$', 'lazy_client_api.views.tvshow_action', name="api.tvshow.detail"),

    #Search imdb.com
    url(r'^search_imdb/$', 'lazy_client_api.views.search_imdb', name='search_imdb'),

    #Search TVShow via thetvdb.com
    url(r'^search_tvdb/$', 'lazy_client_api.views.search_tvdb', name='search_tvdb'),
    url(r'^get_tvdb_season/(?P<showid>[0-9]+)/$', 'lazy_client_api.views.get_tvdb_season', name='get_tvdb_season'),
    url(r'^get_tvdb_eps/(?P<showid>[0-9]+)/(?P<season>[0-9]+)/$', 'lazy_client_api.views.get_tvdb_eps', name='get_tvdb_eps'),

)


urlpatterns = format_suffix_patterns(urlpatterns)