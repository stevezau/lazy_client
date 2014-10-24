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
from pure_pagination import Paginator, EmptyPage, PageNotAnInteger

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

        return super(DownloadLog, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DownloadLog, self).get_context_data(**kwargs)
        context['selectable'] = False
        logs = self.get_object().downloadlog_set.all()
        context['logs'] = logs
        return context


class DownloadsManuallyFixItemSuccess(DetailView):
    template_name = 'queue/manualfixitem_saved.html'
    model = DownloadItem


class DownloadsManuallyFixItem(UpdateView):
    form_class = DownloadItemManualFixForm
    model = DownloadItem
    template_name = "queue/manualfixitem.html"

    def get_context_data(self, **kwargs):
        context = super(DownloadsManuallyFixItem, self).get_context_data(**kwargs)
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = DownloadItemManualFixForm(download_item=self.object)
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):

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
                    tvdbobj.save()

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

        self.object.retries = 0
        self.object.save()

        return HttpResponseRedirect(reverse_lazy('queue.manualfixitem.success', kwargs={'pk': self.object.id}))


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
        context['complete'] = common.num_complete(days=7)

        context['type'] = self.type

        if self.dlget == DownloadItem.PENDING:
            context['doregroup'] = True
            context['downloads'] = sorted(self.object_list, key=self.key_function)

        #Pageinate results
        paginate = Paginator(self.object_list, 50, request=self.request)
        page = 1

        if self.request.GET and 'page' in self.request.GET:
            try:
                page = int(self.request.GET['page'])
            except:
                pass

        try:
            context['downloads'] = paginate.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page = 1
            context['downloads'] = paginate.page(page)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            page = paginate.num_pages
            context['downloads'] = paginate.page(paginate.num_pages)

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

        if self.dlget == DownloadItem.COMPLETE:
            from datetime import timedelta
            from django.utils import timezone
            some_day_last_week = timezone.now().date() - timedelta(days=14)
            return DownloadItem.objects.filter(status=DownloadItem.COMPLETE, dateadded__gt=some_day_last_week).order_by('-dateadded')
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