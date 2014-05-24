__author__ = 'steve'

def upgrade():
    from lazy_client_core.models import DownloadItem

    for dlitem in DownloadItem.objects.filter(status=5):
        dlitem.status = DownloadItem.EXTRACT
        dlitem.message = None
        dlitem.retries = 0
        dlitem.save()
