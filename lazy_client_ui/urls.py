from django.conf.urls import patterns, url
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy

from lazy_client_ui.views import downloads, config, other
from lazy_client_ui.views import home

from django.contrib.auth.views import login

urlpatterns = patterns('',

    #Login
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}, name="login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name="logout"),


    #Home - Default Index
    url(r'^$', home.IndexView.as_view(), name='home'),

    #Downloads
    url(r'^downloads$', RedirectView.as_view(url=reverse_lazy('downloads.index', args=['downloading'])), name='downloads.redirect'),
    url(r'^downloads/get/(?P<type>\w+)/$', downloads.DownloadsListView.as_view(), name='downloads.get'),
    url(r'^downloads/log/(?P<pk>\w+)/$', downloads.DownloadLog.as_view(), name='downloads.log'),
    url(r'^downloads/log/(?P<pk>\w+)/clear$', downloads.downloadlog_clear, name='downloads.log.clear'),
    url(r'^downloads/update/(?P<action>\w+)/$', downloads.update, name='downloads.update'),
    url(r'^downloads/manualfix/$', downloads.DownloadsManuallyFix.as_view(), name='downloads.manualfix'),
    url(r'^downloads/manualfix/(?P<pk>\w+)/$', downloads.DownloadsManuallyFixItem.as_view(), name='downloads.manualfixitem'),
    url(r'^downloads/(?P<type>\w+)/$', downloads.DownloadsIndexView.as_view(), name='downloads.index'),

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
    url(r'^other$', RedirectView.as_view(url=reverse_lazy('other.find.index')), name='other.redirect'),
    url(r'^other/update/report_all/$', other.report_all, name='other.findmissing.report_all'),
    url(r'^other/update/fix_all/$', other.fix_all, name='other.findmissing.fix_all'),
    url(r'^other/update/(?P<type>\w+)/$', other.update, name='other.update'),

    #Config - Find
    url(r'^other/find/$', other.FindIndexView.as_view(), name='other.find.index'),
    url(r'^other/find/(?P<search>(.+))/$', other.SearchIndexView.as_view(), name='other.find.search'),
    url(r'^other/find/(?P<search>(.+))/content$', other.FindListView.as_view(), name='other.find.list'),

    #Config - Find Missing
    url(r'^other/findmissing/$', other.FindMissingIndexView.as_view(), name='other.findmissing.index'),
    url(r'^other/findmissing/(?P<tvshow>(.+))/$', other.FindMissingReport.as_view(), name='other.findmissing.report'),
    url(r'^other/findmissing/(?P<tvshow>(.+))/content$', other.FindMissingReportContent.as_view(), name='other.findmissing.report.content'),


    #Config - Jobs
    url(r'^other/jobs/$', other.JobIndexView.as_view(), name='other.jobs.index'),
    url(r'^other/jobs/list/$', other.JobListView.as_view(), name='other.jobs.list'),
    url(r'^other/jobs/get/(?P<pk>(.+))/$', other.JobDetailView.as_view(), name='other.jobs.get'),

)

