from django.contrib import admin
from lazy_client_core.models import DownloadItem, Job, Movie, TVShow, Version, TVShowMappings

class DownloadItemAdmin(admin.ModelAdmin):
    search_fields = ('title', 'localpath', 'ftppath')
    list_filter = ('status',)

class TVShowMappingsAdmin(admin.ModelAdmin):
    search_fields = ['title']

class ImdbcacheAdmin(admin.ModelAdmin):
    search_fields = ('title', 'id')

class VersionAdmin(admin.ModelAdmin):
    search_fields = ('version', 'id')

class TvdbcacheAdmin(admin.ModelAdmin):
    search_fields = ('title', 'id')

admin.site.register(DownloadItem, DownloadItemAdmin)
admin.site.register(TVShowMappings, TVShowMappingsAdmin)
admin.site.register(Job)
admin.site.register(Version, VersionAdmin)
admin.site.register(Movie, ImdbcacheAdmin)
admin.site.register(TVShow, TvdbcacheAdmin)
