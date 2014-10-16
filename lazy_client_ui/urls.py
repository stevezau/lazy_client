from django.conf.urls import patterns, url
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy
from django.views.generic import TemplateView

from lazy_client_ui.views import queue, config, find, manage
from lazy_client_ui.views import home

urlpatterns = patterns('',

    #Login
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}, name="login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name="logout"),

    #Home - Default Index
    url(r'^$', home.IndexView.as_view(), name='home'),

    #Downloads
    url(r'^queue/log/(?P<pk>\w+)/$', queue.DownloadLog.as_view(), name='queue.log'),
    url(r'^queue/log/(?P<pk>\w+)/clear$', queue.downloadlog_clear, name='queue.log.clear'),
    url(r'^queue/manualfix/(?P<pk>\w+)/success/$', queue.DownloadsManuallyFixItemSuccess.as_view(), name="queue.manualfixitem.success"),
    url(r'^queue/manualfix/(?P<pk>\w+)/$', queue.DownloadsManuallyFixItem.as_view(), name='queue.manualfixitem'),
    url(r'^queue/(?P<type>\w+)/$', queue.QueueManage.as_view(), name='queue.index'),


    #Config - Show Mappings
    url(r'^config/tvmap/$', config.TVMappingsIndexView.as_view(), name='config.tvmap.index'),
    url(r'^config/tvmap/add$', config.TVMappingsCreate.as_view(), name='config.tvmap.add'),
    url(r'^config/tvmap/list$', config.TVMappingsListView.as_view(), name='config.tvmap.list'),

    #Other - Find
    url(r'^find/$', find.find, name='find'),

    #Manage - TVShows
    url(r'^manage/tvshows/$', manage.tvshows, name='manage.tvshows.find'),
    url(r'^manage/tvshows/(?P<pk>\w+)/$', manage.TVShowDetail.as_view(), name='manage.tvshow.detail'),
    url(r'^manage/tvshows/(?P<pk>\w+)/missing/$', manage.TVShowMissing.as_view(), name='manage.tvshow.missing'),
    url(r'^manage/tvshows/(?P<pk>\w+)/missing/results/$', manage.TVShowMissingResults.as_view(), name='manage.tvshow.missing.results'),
    url(r'^manage/tvshows/(?P<pk>\w+)/missing/log/$', manage.TVShowMissingLog.as_view(), name='manage.tvshow.missing.log'),


    #Manage - Movies
    url(r'^manage/movies/$', manage.movies, name='manage.movies.find'),
    #url(r'^manage/tvshows/(?P<pk>\w+)/$', manage.TVShowDetail.as_view(), name='manage.tvshow.detail'),
    #url(r'^other/findmissing/(?P<tvshow>(.+))/content$', other.FindMissingReportContent.as_view(), name='other.findmissing.report.content'),

)

