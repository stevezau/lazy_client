from django.views.generic import TemplateView, FormView, ListView, DetailView
import logging
import os
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from lazyui import common
from lazyapp.forms import Find, FindMissing
from lazycore.utils import ftpmanager
from lazycore.models import DownloadItem, Job
from lazycore.utils.missingscanner import MissingScanner


logger = logging.getLogger(__name__)


class JobIndexView(TemplateView):
    template_name = 'other/jobs/index.html'

class JobListView(ListView):
    template_name = 'other/jobs/job_list.html'
    model = Job

class JobDetailView(DetailView):
    template_name = 'other/jobs/report.html'
    model = Job

    def get_context_data(self, **kwargs):
        context = super(JobDetailView, self).get_context_data(**kwargs)
        context['selectable'] = False
        report = self.get_object().report
        context['report'] = report
        return context


class FindMissingIndexView(FormView):
    template_name = 'other/findmissing/index.html'
    form_class = FindMissing

    def form_valid(self, form):
        print form.cleaned_data['tvshow']
        return HttpResponseRedirect(reverse('other.findmissing.report', kwargs={'tvshow': form.cleaned_data['tvshow']}))


class FindMissingReport(TemplateView):
    template_name = 'other/findmissing/report.html'

    def get_context_data(self, **kwargs):
        context = super(FindMissingReport, self).get_context_data(**kwargs)
        context['tvshow'] = self.kwargs.get('tvshow')
        return context


class FindMissingReportContent(TemplateView):
    template_name = 'other/findmissing/report_content.html'

    def get_context_data(self, **kwargs):
        context = super(FindMissingReportContent, self).get_context_data(**kwargs)
        context['selectable'] = True
        scanner = MissingScanner()
        tvshow = search = kwargs.get("tvshow")
        tvshow_path = os.path.join(settings.TVHD, tvshow)

        report = scanner.show_report(tvshow_path)
        context['report'] = report

        return context


class FindIndexView(FormView):
    template_name = 'other/find/index.html'
    form_class = Find

    def form_valid(self, form):
        print form.cleaned_data['search']
        return HttpResponseRedirect(reverse('other.find.search', kwargs={'search': form.cleaned_data['search']}))

class SearchIndexView(TemplateView):
    template_name = 'other/find/search.html'

    def get_context_data(self, **kwargs):
        context = super(SearchIndexView, self).get_context_data(**kwargs)
        context['search'] = self.kwargs.get('search')
        return context

class FindListView(TemplateView):
    template_name = 'other/find/find_content.html'


    def get_context_data(self, **kwargs):
        context = super(FindListView, self).get_context_data(**kwargs)

        try:
            search = kwargs.get("search")

            if not search or search == "":
                raise Exception("You didn't enter anything to search!")

            results = ftpmanager.search_torrents(search)
        except Exception as e:
            results = {}
            res_global = {}
            results['global'] = res_global

            errors = [e]
            res_global['errors'] = errors

        context['search_results'] = results
        return context

def fix_missing_seasons(items):

    status = 200
    response = HttpResponse(content_type="text/plain")
    scanner = MissingScanner()

    #figure out what we are trying to fix
    fix = {}

    for item in items:
        try:
            season, __, tvshow_name = item.partition("~")

            if tvshow_name not in fix:
                fix[tvshow_name] = []
            fix[tvshow_name].append(season)

        except:
            pass

    for tvshow_name, seasons in fix.items():
        try:
            showpath = os.path.join(settings.TVHD, tvshow_name)

            if showpath and not showpath == "":

                int_seasons = []

                for season_no in seasons:
                    int_seasons.append(int(season_no))

                #lets do the fixing
                scanner.fix_show.delay(showpath, int_seasons)
                response.write("Launched job to try fix %s with seasons %s" % (showpath, int_seasons))

            else:
                #TODO: What is this doing?
                response.write("Unable to download %s as it was not found" % tvshow_name)

        except Exception as e:
            status = 210
            response.write("Unable to download %s as %s" % (item, e))

    response.status_code = status
    return response

def delete_report(items):

    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            job = Job.objects.get(id=item)
            job.delete()

            response.write("Deleted job %s" % item)

        except Exception as e:
            status = 210
            response.write("Unable to delete job as it was not found" % item)

    response.status_code = status
    return response


def fix_all(request):

    response = HttpResponse(content_type="text/plain")

    try:
        scanner = MissingScanner()
        scanner.fix_all.delay()

        response.write("Fixing all TVShows. This can take a while so i've launched a job, please check the status of the job in the jobs menu")
    except Exception as e:
        response.write("Error launching job due to %s" % e)

    return response



def report_all(request):

    response = HttpResponse(content_type="text/plain")

    try:
        scanner = MissingScanner()
        scanner.report_all.delay()

        response.write("Checking all TVShows. This can take a while so i've launched a job, please check the status of the job in the jobs menu")
    except Exception as e:
        response.write("Error launching job due to %s" % e)

    return response

def download_torrent(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            #TODO: More error checking here..
            #lets figure out what site this is for
            site, __, torrent = item.partition("~")

            path = ftpmanager.download_torrent(site, torrent)

            if path and not path == "":
                response.write("Downloading to %s" % path)

                #Now add it to the queue
                new_download_item = DownloadItem()
                new_download_item.status = DownloadItem.QUEUE
                new_download_item.ftppath = path
                new_download_item.requested = True
                new_download_item.save()

            else:
                response.write("Unable to download %s as it was not found") % torrent

        except Exception as e:
            status = 210
            response.write("Unable to download %s as %s" % (item, e))

    response.status_code = status
    return response


def update(request, type):

    if request.method == 'POST':

        items = request.POST.getlist('item')

        if len(items) == 0:
            return HttpResponse("Nothing selected", content_type="text/plain", status=210)
        try:
            function = common.load_button_module("lazyui.views.other", type)
            return function(items)
        except Exception as e:
            logger.exception(e)
            return HttpResponse("Error processing update %s" % e, content_type="text/plain", status=220)

    return HttpResponse("Invalid request", content_type="text/plain")
