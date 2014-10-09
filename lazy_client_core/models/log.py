from django.db import models
import logging
from lazy_client_core.utils.jsonfield.fields import JSONField
import inspect


logger = logging.getLogger(__name__)

class DownloadLog(models.Model):

    def __unicode__(self):
        try:
            return self.title
        except:
            return "TITLE NOT FOUND"

    download_id = models.ForeignKey('DownloadItem', null=True, blank=True)
    tvshow_id = models.ForeignKey('TVShow', null=True, blank=True)
    job_id = models.ForeignKey('Job', null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'download_log'
        app_label = 'lazy_client_core'


#######################################################
######################### JOBS ########################
#######################################################

class Job(models.Model):

    def __unicode__(self):
        return self.title

    type = models.IntegerField(blank=True, null=True)
    status = models.IntegerField(blank=True, null=True)
    startdate = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    finishdate = models.DateTimeField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    report = JSONField(blank=True, null=True)

    class Meta:
        db_table = 'jobs'
        app_label = 'lazy_client_core'

    def log(self, msg):

        logger.debug(msg)

        try:
            frm = inspect.stack()[1]
            mod = inspect.getmodule(frm[0])

            caller = mod.__name__
            line = inspect.currentframe().f_back.f_lineno

            logmsg = "%s(%s): %s" % (caller, line, msg)

        except:
            logmsg = msg

        self.downloadlog_set.create(job_id=self.id, message=logmsg)
