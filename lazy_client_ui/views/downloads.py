from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import TemplateView, ListView, DetailView, UpdateView
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ValidationError
import logging
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from lazy_client_core.models import DownloadItem, Tvdbcache
from lazy_client_ui import common
from lazy_client_core.utils import common as commoncore
from lazy_client_core.utils.tvdb_api import Tvdb
from lazy_client.forms import DownloadItemManualFixForm


logger = logging.getLogger(__name__)

class DownloadLog(DetailView):
    model = DownloadItem
    template_name = "downloads/log.html"

    def post(self, request, *args, **kwargs):
        items = request.POST.getlist('item')

        if items:
            request.session["fixitems"] = items
            self.request.session.modified = True
            return HttpResponseRedirect(reverse('downloads.manualfixitem', kwargs={'pk': items[0]}))

        return super(DownloadsManuallyFix, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DownloadLog, self).get_context_data(**kwargs)
        context['selectable'] = False
        logs = self.get_object().downloadlog_set.all()
        context['logs'] = logs
        return context

class DownloadsManuallyFix(TemplateView):
    model = DownloadItem
    template_name = "downloads/manualfix.html"

    def post(self, request, *args, **kwargs):
        items = request.POST.getlist('item')

        if items:
            request.session["fixitems"] = items
            self.request.session.modified = True
            return HttpResponseRedirect(reverse('downloads.manualfixitem', kwargs={'pk': items[0]}))

        return super(DownloadsManuallyFix, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        #Lets get current item
        items = self.request.session["fixitems"]

        if len(items) > 0:
            return HttpResponseRedirect(reverse('downloads.manualfixitem', kwargs={'pk': items[0]}))

        return super(DownloadsManuallyFix, self).get(request, *args, **kwargs)


class DownloadsManuallyFixItem(UpdateView):
    form_class = DownloadItemManualFixForm
    success_url = reverse_lazy('downloads.manualfix')
    model = DownloadItem
    template_name = "downloads/manualfixitem.html"

    def post(self, request, *args, **kwargs):

        if 'skip' in request.POST:
            #remove from the session
            try:
                for idx, val in enumerate(self.request.session["fixitems"]):
                    if val == self.kwargs['pk']:
                        del self.request.session["fixitems"][idx]
                        self.request.session.modified = True
                        break

            except Exception as e:
                logger.exception(e)

            return HttpResponseRedirect(reverse('downloads.manualfix'))

        return super(DownloadsManuallyFixItem, self).post(request, *args, **kwargs)


    def get_object(self, queryset=None):
        obj = DownloadItem.objects.get(id=self.kwargs['pk'])
        return obj

    def form_valid(self, form):
        #Find tvdb instance
        tvdbobj = None

        #TODO: enable enter tvdbid or search by name

        try:
            tvdbobj = Tvdbcache.objects.get(id=int(form.cleaned_data['tvdbid_id']))
        except ObjectDoesNotExist:
            tvdbobj = Tvdbcache()
            tvdbobj.id = int(form.cleaned_data['tvdbid_id'])
            tvdbobj.update_from_tvdb()
            tvdbobj.save()

        if None is tvdbobj:
            raise ValidationError(
                _('Unable to find tvdb object: %(value)s'),
                code='invalid',
                params={'value':  form.cleaned_data['tvdbid_display']},
            )

        form.instance.tvdbid = tvdbobj

        #remove from the session
        try:
            for idx, val in enumerate(self.request.session["fixitems"]):
                if val == self.kwargs['pk']:
                    del self.request.session["fixitems"][idx]
                    self.request.session.modified = True
                    break

        except Exception as e:
            logger.exception(e)

        form.instance.status = DownloadItem.MOVE
        form.instance.retries = 0

        return super(DownloadsManuallyFixItem, self).form_valid(form)



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
    status = 200
    response = HttpResponse(content_type="text/plain")

    from lazy_client_core.utils.metaparser import MetaParser

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)
            series_data = MetaParser(dlitem.title, type=MetaParser.TYPE_TVSHOW)

            if series_data:
                ignoretitle = series_data.details['series'].replace(" ", ".")
                commoncore.ignore_show(ignoretitle)
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

    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            dlitem = DownloadItem.objects.get(pk=item)

            percent_complete = dlitem.get_percent_complete()

            print percent_complete

            #TODO: Fix this use dlitem retry
            if percent_complete > 99:
                dlitem.status = DownloadItem.MOVE
                dlitem.message = "Retrying extraction"
                dlitem.dlstart = None
                dlitem.retries = 2
                dlitem.save()
                response.write("Moved to extraction %s\n" % dlitem.title)
            else:
                dlitem.status = DownloadItem.QUEUE
                dlitem.message = "Retrying download"
                dlitem.retries = 2
                dlitem.dlstart = None
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

def update(request, action):

    if request.method == 'POST':
        items = request.POST.getlist('item')

        if len(items) == 0:
            return HttpResponse("Nothing selected", content_type="text/plain", status=210)
        try:
            function = common.load_button_module("lazy_client_ui.views.downloads", action)
            return function(items)
        except Exception as e:
            logger.exception(e)
            return HttpResponse("Error processing update %s" % e, content_type="text/plain", status=220)

    return HttpResponse("Invalid request", content_type="text/plain")

def downloadlog_clear(request, pk):

    response = HttpResponse(content_type="text/plain")

    try:
        obj = DownloadItem.objects.get(id=pk)
        obj.clear_log()
        response.write("Cleared log")
    except Exception as e:
        response.write("Unable to clear log.. %s" % e)

    return response