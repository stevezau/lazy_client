from django.http import HttpResponse, HttpResponseRedirect
from lazyweb.models import DownloadItem
from django.views.generic import TemplateView, ListView, FormView, DetailView
from django.core.exceptions import ObjectDoesNotExist
from lazyweb import utils
import logging
from django.core.urlresolvers import reverse
from lazyweb.utils.tvdb_api import Tvdb


logger = logging.getLogger(__name__)

class DownloadLog(DetailView):
    model = DownloadItem
    template_name = "downloads/log.html"

    def get_context_data(self, **kwargs):
        context = super(DownloadLog, self).get_context_data(**kwargs)
        context['selectable'] = False
        logs = self.get_object().downloadlog_set.all()
        context['logs'] = logs
        return context


class DownloadsManuallyFix(ListView):
    model = DownloadItem
    template_name = "downloads/manualfix.html"

    def post(self, request, *args, **kwargs):
        items = request.POST.getlist('item')

        if items:
            request.session["fixitems"] = items
            return HttpResponseRedirect(reverse('downloads.manualfix'))

        for objid in request.POST:
            if utils.match_str_regex(["[0-9]+"], objid):
                values = request.POST.getlist(objid)

                ep_override = None
                season_override = None

                for value in values:
                    if value.startswith("ses~"):
                        season_override = value.replace("ses~", "")

                    if value.startswith("ep~"):
                        ep_override = value.replace("ep~", "")

                if ep_override is None or season_override is None:
                    continue

                ep_override = int(ep_override)
                season_override = int(season_override)

                dlitem = DownloadItem.objects.get(id=int(objid))
                dlitem.seasonoverride = season_override
                dlitem.epoverride = ep_override
                dlitem.status = DownloadItem.MOVE
                dlitem.retries = 0
                dlitem.save()

        return HttpResponseRedirect(reverse('downloads.index', kwargs={'type':"error"}))


    def get_queryset(self):
        items = self.request.session["fixitems"]
        items = map(int, items)
        return DownloadItem.objects.filter(pk__in=items)


class DownloadsIndexView(TemplateView):
    template_name = 'downloads/index.html'
    model = DownloadItem

    def get_context_data(self, **kwargs):
        context = super(DownloadsIndexView, self).get_context_data(**kwargs)
        context['type'] = self.kwargs.get('type')
        return context


class DownloadsListView(ListView):
    template_name = 'downloads/downloaditem_content.html'
    model = DownloadItem

    type = None
    dlget = DownloadItem.DOWNLOADING

    def get_context_data(self, **kwargs):
        context = super(DownloadsListView, self).get_context_data(**kwargs)
        context['type'] = self.type

        if self.dlget == DownloadItem.PENDING:
            context['doregroup'] = True
            queryset = self.get_queryset()
            context['object_list_regroup'] = sorted(queryset, key=self.key_function)

        return context


    def get_queryset(self):
        """Return the last five published polls."""

        self.type = self.kwargs.get('type')

        #convert type to int
        for dlint in DownloadItem.STATUS_CHOICES:
            if dlint[1].lower() == self.type.lower():
                self.dlget = dlint[0]

        #only get a max of 10 for
        if self.dlget == DownloadItem.COMPLETE:
           return DownloadItem.objects.all().filter(status=self.dlget).order_by('-id').filter()[0:30]
        elif self.dlget == DownloadItem.QUEUE:
            return DownloadItem.objects.all().filter(status=self.dlget).order_by('priority','id')
        else:
            return DownloadItem.objects.all().filter(status=self.dlget)

    def key_function(self, dlitem):
        try:
            if dlitem.tvdbid is None:
                return (dlitem.id, None)
            else:
                return (dlitem.tvdbid.id, dlitem.id)
        except:
            return (dlitem.id, None)


def approvemore(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    tvdbapi = Tvdb()

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)

            if dlitem.tvdbid_id:
                dlitem.status = DownloadItem.QUEUE
                dlitem.save()
                tvdbapi.add_fav(dlitem.tvdbid_id)
                response.write("Approved and will continue to get %s\n" % dlitem.title)
            else:
                response.write("Unable to approve and continue to get more %s and it has no associated tvdb entry, try just approve it instead") % item

        except ObjectDoesNotExist:
            status = 210
            response.write("Unable to approve %s as it was not found") % item

    response.status_code = status
    return response


def ignore(items):
    import re

    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)
            series_data = utils.get_series_info(dlitem.title)

            if series_data:
                ignoretitle = series_data.name.replace(" ", ".")
                utils.ignore_show(ignoretitle)
                dlitem.delete()
                response.write("Deleted and ignored %s\n" % ignoretitle)
            else:
                dlitem.delete()
                response.write("Unable to figure out the series name, DELETED BUT NOT IGNORED (DO IT MANUALLY)\n")

        except ObjectDoesNotExist:
            status = 210
            response.write("Unable to ignore %s as it was not found\n") % item

    response.status_code = status
    return response


def retry(items):

    import re

    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)

            percent_complete = dlitem.get_percent_complete()

            print percent_complete

            if percent_complete > 99:
                dlitem.status = DownloadItem.MOVE
                dlitem.message = "Retrying extraction"
                dlitem.retries = 2
                dlitem.save()
                response.write("Moved to extraction %s\n" % dlitem.title)
            else:
                dlitem.status = DownloadItem.QUEUE
                dlitem.message = "Retrying download"
                dlitem.retries = 2
                dlitem.save()
                response.write("Moved to queue for downloading %s\n" % dlitem.title)

        except ObjectDoesNotExist:
            status = 210
            response.write("Unable to retry %s as it was not found") % item

    response.status_code = status
    return response


def delete(items):

    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)
            dlitem.delete()
            response.write("Deleted %s\n" % dlitem.title)
        except Exception as e:
            logger.exception(e)
            status = 210
            response.write("Unable to delete %s as %s" % (item, e.message))

    response.status_code = status
    return response


def reset(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)
            dlitem.reset()
            response.write("Reset %s\n" % dlitem.title)
        except Exception as e:
            status = 210
            response.write("Unable to delete %s as %s" % (item, e.message))

    response.status_code = status
    return response


def force_reset(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)
            dlitem.reset(force=True)
            response.write("Reset %s\n" % dlitem.title)
        except Exception as e:
            status = 210
            response.write("Unable to delete %s as %s" % (item, e.message))

    response.status_code = status
    return response



def decreasepri(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)
            dlitem.decrease_prioritys()
            response.write("Decreased priority of %s to level %s\n" % (dlitem.title, dlitem.priority))
        except ObjectDoesNotExist:
            status = 210
            response.write("Unable to decrease priority %s as it was not found") % item

    response.status_code = status
    return response


def increasepri(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)
            dlitem.increate_priority()
            response.write("Increased priority of %s to level %s\n" % (dlitem.title, dlitem.priority))
        except ObjectDoesNotExist:
            status = 210
            response.write("Unable to increase priority %s as it was not found") % item

    response.status_code = status
    return response


def approve(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)
            dlitem.status = DownloadItem.QUEUE
            dlitem.save()
            response.write("Approved %s\n" % dlitem.title)
        except ObjectDoesNotExist:
            status = 210
            response.write("Unable to approve %s as it was not found") % item

    response.status_code = status
    return response


def update(request, type):

    if request.method == 'POST':
        items = request.POST.getlist('item')

        if len(items) == 0:
            return HttpResponse("Nothing selected", content_type="text/plain", status=210)
        try:
            function = utils.load_button_module("lazyweb.views.downloads", type)
            return function(items)
        except Exception as e:
            logger.exception(e)
            return HttpResponse("Error processing update %s" % e, content_type="text/plain", status=220)

    return HttpResponse("Invalid request", content_type="text/plain")

