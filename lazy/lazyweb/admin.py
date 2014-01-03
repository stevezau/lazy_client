from django.contrib import admin
from lazyweb.models import DownloadItem, Job, Imdbcache, Tvdbcache

class DownloadItemAdmin(admin.ModelAdmin):
    search_fields = ('title', 'localpath', 'ftppath')


admin.site.register(DownloadItem, DownloadItemAdmin)
admin.site.register(Job)
admin.site.register(Imdbcache)
admin.site.register(Tvdbcache)
