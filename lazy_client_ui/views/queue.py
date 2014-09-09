import logging

from django.utils.translation import ugettext as _
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import TemplateView, ListView, DetailView, UpdateView
from django.core.exceptions import ObjectDoesNotExist
from django.forms import ValidationError
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.conf import settings
from django.db.models import Q
from lazy_client_core.models import DownloadItem, TVShow, Movie
from lazy_client_ui.forms import DownloadItemManualFixForm


logger = logging.getLogger(__name__)


class QueueIndex(TemplateView):
    template_name = 'queue/index.html'
    model = DownloadItem


class DownloadLog(DetailView):
    model = DownloadItem
    template_name = "queue/log.html"

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
    template_name = "queue/manualfix.html"

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
    template_name = "queue/manualfixitem.html"

    def get_context_data(self, **kwargs):
        context = super(DownloadsManuallyFixItem, self).get_context_data(**kwargs)
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        video_files = self.object.video_files

        form = DownloadItemManualFixForm(download_item=self.object)

        return self.render_to_response(self.get_context_data(form=form))

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

        self.object = self.get_object()
        form = DownloadItemManualFixForm(request.POST or None, download_item=self.object)

        #Lets do the validation
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_object(self, queryset=None):
        obj = DownloadItem.objects.get(id=self.kwargs['pk'])
        return obj

    def form_valid(self, form):
        from lazy_common import metaparser

        self.object = self.get_object()

        video_files = self.object.video_files

        i = 0

        for vid_fields in form.get_vid_fields():
            #lets save it
            type_dict_name = "%i_type" % i
            video_file_type = int(form.cleaned_data[type_dict_name])

            if video_file_type == metaparser.TYPE_TVSHOW:
                tvdbobj = None
                tvdbid_dict_name = '%s_tvdbid_id' % i
                tvdb_id = int(form.cleaned_data[tvdbid_dict_name])

                try:
                    tvdbobj = TVShow.objects.get(id=tvdb_id)
                except ObjectDoesNotExist:
                    tvdbobj = TVShow()
                    tvdbobj.id = tvdb_id
                    tvdbobj.update_from_tvdb()

                if None is tvdbobj:
                    raise ValidationError(
                        _('Unable to find tvdb object: %(value)s'),
                        code='invalid',
                        params={'value':  form.cleaned_data['%s_tvdbid_display' % i]},
                    )

                video_files[i]['season_override'] = form.cleaned_data['%s_tvdbid_season_override' % i]
                video_files[i]['ep_override'] = form.cleaned_data['%s_tvdbid_ep_override' % i]
                video_files[i]['tvdbid_id'] = int(form.cleaned_data['%s_tvdbid_id' % i])

                #If this is a single tvshow then lets update the whole download_item
                parser = self.object.metaparser()
                if parser.details['type'] == "episode":
                    self.object.tvdbid = tvdbobj

            if video_file_type == metaparser.TYPE_MOVIE:
                imdbobj = None
                imdbid_dict_name = '%s_imdbid_id' % i
                imdbid_id = int(form.cleaned_data[imdbid_dict_name])

                try:
                    imdbobj = Movie.objects.get(id=imdbid_id)
                except ObjectDoesNotExist:
                    imdbobj = Movie()
                    imdbobj.id = imdbid_id
                    imdbobj.update_from_imdb()

                video_files[i]['imdbid_id'] = imdbid_id

                if None is imdbobj:
                    raise ValidationError(
                        _('Unable to find imdb object: %(value)s'),
                        code='invalid',
                        params={'value':  form.cleaned_data['%s_tvdbid_display' % i]},
                    )

                #If this is a single movie then lets update the whole download_item
                parser = self.object.metaparser()
                if parser.details['type'] == "movie":
                    self.object.imdbid = imdbobj

            i += 1


        #remove from the session
        for idx, val in enumerate(self.request.session["fixitems"]):
            if val == self.kwargs['pk']:
                del self.request.session["fixitems"][idx]
                self.request.session.modified = True
                break

        self.object.retries = 0
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class QueueManage(ListView):
    template_name = 'queue/index.html'
    model = DownloadItem

    type = None
    dlget = DownloadItem.DOWNLOADING

    def get_context_data(self, **kwargs):
        context = super(QueueManage, self).get_context_data(**kwargs)

        from lazy_client_ui import common
        context['downloading'] = common.num_downloading()
        context['extracting'] = common.num_extracting()
        context['queue'] = common.num_queue()
        context['pending'] = common.num_pending()
        context['errors'] = common.num_error()

        context['type'] = self.type

        if self.dlget == DownloadItem.PENDING:
            context['doregroup'] = True
            queryset = self.get_queryset()

            # Sort by class and grade descending, case insensitive
            from operator import attrgetter
            from lazy_common import utils

            get_date = utils.compose(attrgetter('dateadded'))
            get_tvdbid = utils.compose(attrgetter('tvdbid_id'))

            context['object_list_regroup'] = utils.multikeysort(queryset, ['-dateadded', 'tvdbid'],{'tvdbid':get_tvdbid,'dateadded':get_date})

        return context


    def get_queryset(self):
        self.type = self.kwargs.get('type')

        if self.type.lower() == "error":
            self.dlget = 99
        else:
            #convert type to int
            for dlint in DownloadItem.STATUS_CHOICES:
                if dlint[1].lower() == self.type.lower():
                    self.dlget = dlint[0]

        #only get a max of 10 for
        if self.dlget == DownloadItem.COMPLETE:
           return DownloadItem.objects.all().filter(status=self.dlget).order_by('-id').filter()[0:30]
        elif self.dlget == DownloadItem.QUEUE:
            return DownloadItem.objects.all().filter(retries__lte=settings.DOWNLOAD_RETRY_COUNT, status=self.dlget).order_by('priority','id')
        elif self.dlget == 99:
            return DownloadItem.objects.filter(~Q(status=DownloadItem.COMPLETE), retries__gt=settings.DOWNLOAD_RETRY_COUNT).order_by('priority','id')
        else:
            return DownloadItem.objects.all().filter(status=self.dlget, retries__lte=settings.DOWNLOAD_RETRY_COUNT)

    def key_function(self, dlitem):
        try:
            if dlitem.tvdbid is None:
                return (dlitem.id, None)
            else:
                return (dlitem.tvdbid.id, dlitem.id)
        except:
            return (dlitem.id, None)




def downloadlog_clear(request, pk):

    response = HttpResponse(content_type="text/plain")

    try:
        obj = DownloadItem.objects.get(id=pk)
        obj.clear_log()
        response.write("Cleared log")
    except Exception as e:
        response.write("Unable to clear log.. %s" % e)

    return response