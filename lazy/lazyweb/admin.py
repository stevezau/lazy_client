from django.contrib import admin
from lazyweb.models import DownloadItem, Job, Imdbcache, Tvdbcache

class DownloadItemAdmin(admin.ModelAdmin):
    search_fields = ('title', 'localpath', 'ftppath')

class ImdbcacheAdmin(admin.ModelAdmin):
    search_fields = ('title', 'id')

class TvdbcacheAdmin(admin.ModelAdmin):
    search_fields = ('title', 'id')

admin.site.register(DownloadItem, DownloadItemAdmin)
admin.site.register(Job)
admin.site.register(Imdbcache, ImdbcacheAdmin)
admin.site.register(Tvdbcache, TvdbcacheAdmin)
