import datetime
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.test import TestCase
import os
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.conf import settings

from lazycore.models import DownloadItem


class DownloadViewsTestCase(TestCase):

    fixtures = ['lazyweb_views_testdata.json']

    def test_reset_download_item(self):
        dlitem = DownloadItem.objects.get(pk=2)
        dlitem.status = DownloadItem.DOWNLOADING

        dlitem.reset()

        response = self.client.post(reverse('downloads_update',
                                   args=('reset',)),
                                    {'item': dlitem.id})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(dlitem.status == DownloadItem.QUEUE)

    def test_delete_download_item(self):

        dlitem = DownloadItem.objects.get(pk=1)
        localpath = dlitem.localpath

        try:
            os.makedirs(localpath)
        except OSError:
            pass

        response = self.client.post(reverse('downloads_update',
                                   args=('delete',)),
                                    {'item': dlitem.id})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(os.path.exists(localpath))
