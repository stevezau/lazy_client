import logging
import os
import re

from django.http import HttpResponse
from django.views.generic import TemplateView, ListView, CreateView, FormView
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.urlresolvers import reverse_lazy

from lazy_client_core.utils import common as commoncore
from lazy_client_ui import common
from lazy_client_core.models import TVShowMappings, TVShow
from lazy_client_ui.forms import AddTVMapForm, AddApprovedShow, AddIgnoreShow
from lazy_common.tvdb_api import Tvdb


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

    #TODO VAlidate mappings.. make it look better
    def form_valid(self, form):
        form.instance.tvdbid_id = form.cleaned_data['tvdbid_id']
        return super(TVMappingsCreate, self).form_valid(form)


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

            #TODO MAke a class to manage ignored items
            for line in content:
                if "    - " in line:
                    title = {}
                    title['regex'] = re.sub("    - ", "", line).strip()
                    title['title'] = re.sub("(\.|\^)", " ", title['regex']).strip().rstrip("S")
                    titles.append(title)

        context['titles'] = titles
        return context


