from django.http import HttpResponse
from lazyweb.models import TVShowMappings, Tvdbcache
from django.views.generic import TemplateView, ListView, CreateView, FormView
from django.core.exceptions import ObjectDoesNotExist
from lazyweb import utils
from django.conf import settings
import logging
from lazyweb.forms import AddTVMapForm, AddApprovedShow, AddIgnoreShow
import os, signal, shutil, re
from django.core.urlresolvers import reverse_lazy
from lazyweb.utils.tvdb_api import Tvdb
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


class TVMappingsIndexView(TemplateView):
    template_name = 'config/tvmap/index.html'
    model = TVShowMappings


class TVMappingsListView(ListView):
    template_name = 'config/tvmap/tvmap_content.html'
    model = TVShowMappings


class TVMappingsCreate(CreateView):
    form_class = AddTVMapForm
    model = TVShowMappings
    template_name = 'config/tvmap/add.html'
    success_url = reverse_lazy('config.tvmap.index')

    def form_valid(self, form):
        form.instance.tvdbid_id = form.cleaned_data['tvdbid_id']
        return super(TVMappingsCreate, self).form_valid(form)


class ApprovedIndexView(TemplateView):
    template_name = 'config/approved/index.html'


class ApprovedListView(TemplateView):
    template_name = 'config/approved/approved_content.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ApprovedListView, self).get_context_data(**kwargs)

        tvdbapi = Tvdb()
        tvdbfavs = tvdbapi.get_favs()

        favs = []

        #now lets sort them all out
        if tvdbfavs and len(tvdbfavs) > 0:
            for tvdbfav in tvdbfavs:
                try:
                    tvcache_obj = Tvdbcache.objects.get(id=int(tvdbfav))
                    favs.append(tvcache_obj)

                except ObjectDoesNotExist:
                    #not found, lets add it
                    new_tvcache = Tvdbcache()
                    new_tvcache.id = int(tvdbfav)
                    new_tvcache.update_from_tvdb()
                    new_tvcache.save()
                    favs.append(new_tvcache)

        context['favs'] = favs
        return context


class ApprovedCreate(FormView):
    template_name = 'config/approved/add.html'
    form_class = AddApprovedShow
    success_url = reverse_lazy('config.approved.index')

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        tvdbapi = Tvdb()
        tvdbapi.add_fav(form.cleaned_data['tvdbid_id'])

        #also create a folder
        try:
            tvdbobj = Tvdbcache.objects.get(id=int(form.cleaned_data['tvdbid_id']))
            dst = os.path.join(settings.TVHD, tvdbobj.title)
            dst = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", dst)
            dst = dst.strip()
            tvdbobj.localpath = dst
            tvdbobj.save()
            os.mkdir(dst)
        except ObjectDoesNotExist:
            new_tvdbcache = Tvdbcache()
            new_tvdbcache.id = int(form.cleaned_data['tvdbid_id'])
            new_tvdbcache.update_from_tvdb()

            dst = os.path.join(settings.TVHD, new_tvdbcache.title)
            dst = re.sub(settings.ILLEGAL_CHARS_REGEX, " ", dst)
            dst = dst.strip()
            logger.debug(dst)
            os.mkdir(dst)

            new_tvdbcache.localpath = dst
            new_tvdbcache.save()
            pass

        return super(ApprovedCreate, self).form_valid(form)


class IgnoredIndexView(TemplateView):
    template_name = 'config/ignore/index.html'


class IgnoredListView(TemplateView):
    template_name = 'config/ignore/ignore_content.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(IgnoredListView, self).get_context_data(**kwargs)

        titles = []

        if os.path.exists(settings.FLEXGET_IGNORE):

            with open(settings.FLEXGET_IGNORE) as f:
                content = f.readlines()

            for line in content:
                if "    - " in line:
                    title = {}
                    title['regex'] = re.sub("    - ", "", line).strip()
                    title['title'] = re.sub("(\.|\^)", " ", title['regex']).strip().rstrip("S")
                    titles.append(title)

        context['titles'] = titles
        return context


class IgnoredCreate(FormView):
    template_name = 'config/ignore/add.html'
    form_class = AddIgnoreShow
    success_url = reverse_lazy('config.ignore.index')

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        if not form.cleaned_data['show_name'] == "":
            utils.ignore_show(form.cleaned_data['show_name'])
        return super(IgnoredCreate, self).form_valid(form)




def delete_mapping(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        try:
            tvmapping = TVShowMappings.objects.get(pk=item)
            tvmapping.delete()
            response.write("Deleted %s\n" % tvmapping.title)
        except ObjectDoesNotExist:
            status = 210
            response.write("Unable to delete %s as it was not found") % item

    response.status_code = status
    return response

def delete_ignore(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    for item in items:
        utils.remove_ignore(item)
        response.write("Deleted %s\n" % item)


    response.status_code = status
    return response


def delete_fav(items):
    status = 200
    response = HttpResponse(content_type="text/plain")

    tvdbapi = Tvdb()

    for item in items:
        tvdbapi.del_fav(item)
        response.write("Deleted %s\n" % item)


    response.status_code = status
    return response


def update(request, type):

    if request.method == 'POST':
        items = request.POST.getlist('item')

        if len(items) == 0:
            return HttpResponse("Nothing selected", content_type="text/plain", status=210)
        try:
            function = utils.load_button_module("lazyweb.views.config", type)
            return function(items)
        except Exception as e:
            logger.exception(e)
            return HttpResponse("Error processing update %s" % e, content_type="text/plain", status=220)

    return HttpResponse("Invalid request", content_type="text/plain")
