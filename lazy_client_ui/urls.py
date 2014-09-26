from django.conf.urls import patterns, url
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy

from lazy_client_ui.views import queue, config, other, manage
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
    url(r'^queue/manualfix/(?P<pk>\w+)/$', queue.DownloadsManuallyFixItem.as_view(), name='queue.manualfixitem'),
    url(r'^queue/(?P<type>\w+)/$', queue.QueueManage.as_view(), name='queue.index'),

    #Config - Redirect
    url(r'^config$', RedirectView.as_view(url=reverse_lazy('config.tvmap.index')), name='config.redirect'),
    url(r'^config/update/(?P<type>\w+)/$', config.update, name='config.update'),

    #Config - Approved Shows
    url(r'^config/approved/$', config.ApprovedIndexView.as_view(), name='config.approved.index'),
    url(r'^config/approved/list$', config.ApprovedListView.as_view(), name='config.approved.list'),
    url(r'^config/approved/add$', config.ApprovedCreate.as_view(), name='config.approved.add'),

    #Config - Ignored Shows
    url(r'^config/ignore/$', config.IgnoredIndexView.as_view(), name='config.ignore.index'),
    url(r'^config/ignore/list$', config.IgnoredListView.as_view(), name='config.ignore.list'),
    url(r'^config/ignore/add$', config.IgnoredCreate.as_view(), name='config.ignore.add'),

    #Config - Show Mappings
    url(r'^config/tvmap/$', config.TVMappingsIndexView.as_view(), name='config.tvmap.index'),
    url(r'^config/tvmap/add$', config.TVMappingsCreate.as_view(), name='config.tvmap.add'),
    url(r'^config/tvmap/list$', config.TVMappingsListView.as_view(), name='config.tvmap.list'),

    #Other - Redirect
    #url(r'^other/update/report_all/$', other.report_all, name='other.findmissing.report_all'),
    #url(r'^other/update/fix_all/$', other.fix_all, name='other.findmissing.fix_all'),
    url(r'^other/update/(?P<type>\w+)/$', other.update, name='other.update'),

    #Other - Find
    url(r'^find/$', other.find, name='find'),

    #Manage - TVShows
    url(r'^manage/tvshows/$', manage.tvshows, name='manage.tvshows.find'),
    url(r'^manage/tvshows/(?P<pk>\w+)/$', manage.TVShowDetail.as_view(), name='manage.tvshow.detail'),
    url(r'^other/findmissing/(?P<tvshow>(.+))/content$', other.FindMissingReportContent.as_view(), name='other.findmissing.report.content'),


    #Config - Jobs
    url(r'^other/jobs/$', other.JobIndexView.as_view(), name='other.jobs.index'),
    url(r'^other/jobs/list/$', other.JobListView.as_view(), name='other.jobs.list'),
    url(r'^other/jobs/get/(?P<pk>(.+))/$', other.JobDetailView.as_view(), name='other.jobs.get'),

)

