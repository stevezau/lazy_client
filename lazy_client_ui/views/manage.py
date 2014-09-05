import logging
import os
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from lazy_client_core.utils import missingscanner

logger = logging.getLogger(__name__)


def tvshows(request):


    return render(request, 'manage/tvshows/index.html', {"question": "test"})