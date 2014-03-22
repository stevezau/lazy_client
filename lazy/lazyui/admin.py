from django.contrib import admin
from lazycore.models import DownloadItem, Job, Imdbcache, Tvdbcache, Version

class DownloadItemAdmin(admin.ModelAdmin):
    search_fields = ('title', 'localpath', 'ftppath')

class ImdbcacheAdmin(admin.ModelAdmin):
    search_fields = ('title', 'id')

class VersionAdmin(admin.ModelAdmin):
    search_fields = ('version', 'id')

class TvdbcacheAdmin(admin.ModelAdmin):
    search_fields = ('title', 'id')

admin.site.register(DownloadItem, DownloadItemAdmin)
admin.site.register(Job)
admin.site.register(Version, VersionAdmin)
admin.site.register(Imdbcache, ImdbcacheAdmin)
admin.site.register(Tvdbcache, TvdbcacheAdmin)
