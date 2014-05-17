from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings


admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'lazy_client.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include('lazy_client_api.urls')),
    url(r'^lazy/api/', include('lazy_client_api.urls')),
    url(r'', include('lazy_client_ui.urls')),
)

urlpatterns += patterns("",
        (r'^lazy/media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
        )
