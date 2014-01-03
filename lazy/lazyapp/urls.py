from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import RedirectView
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'lazyapp.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^lazy/api/', include('lazyapi.urls')),
    url(r'lazy/', include('lazyweb.urls')),
    url(r'^$', RedirectView.as_view(url='/lazy'), name='lazyhome'),
)

urlpatterns += patterns("",
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True }),
        )
