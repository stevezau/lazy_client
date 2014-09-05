from django.contrib import admin
from lazy_client_core.models import DownloadItem, Job, Movie, TVShow, Version

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
admin.site.register(Movie, ImdbcacheAdmin)
admin.site.register(TVShow, TvdbcacheAdmin)
