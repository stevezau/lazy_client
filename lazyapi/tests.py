import datetime
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.test import TestCase
import os
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.conf import settings
from lazyapi.serializers import *

from lazycore.models import DownloadItem

class APITestsDownloadItemTestCase(TestCase):

    api_tvdb_url = reverse('tvdb_api')
    downloaditem_api = reverse('download_api')

    def do_check_download_item(self, data, expected_data, type):
        response = self.client.post(self.downloaditem_api, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, expected_data)

        created_obj = DownloadItemSerializer(data=response.data)
        self.assertTrue(created_obj.is_valid())

        imdbid = created_obj.data.get("imdbid_id")
        imdbobj = Imdbcache.objects.get(id=int(imdbid))
        self.assertTrue(imdbobj)
        imdb_img = imdbobj.posterimg
        self.assertTrue(os.path.isfile(imdb_img.name))

        if type == "tvhd":
            tvdbid = created_obj.data.get("tvdbid_id")
            tvdbobj = Tvdbcache.objects.get(id=int(tvdbid))
            self.assertTrue(tvdbobj)
            tvdb_img = tvdbobj.posterimg
            self.assertTrue(os.path.isfile(tvdb_img.name))

    def test_create_new_tvhd_downloaditem_tvdb_imdb_existing(self):
        data = {
                "ftppath": "/TVHD/Person.of.Interest.S03E11.720p.HDTV.X264-DIMENSION",
                'tvdbid_id': 248837,
                'imdbid_id': 1837642,
                'status': DownloadItem.PENDING
                }

        expected_data = {'title': 'Person.of.Interest.S03E11.720p.HDTV.X264-DIMENSION',
                'tvdbid_id': 248837,
                'imdbid_id': 1837642,
                'ftppath': '/TVHD/Person.of.Interest.S03E11.720p.HDTV.X264-DIMENSION',
                'section': 'TVHD',
                'localpath': os.path.join(settings.TVHD_TEMP, 'Person.of.Interest.S03E11.720p.HDTV.X264-DIMENSION'),
                'status': DownloadItem.PENDING
                }
        self.do_check_download_item(data, expected_data, 'tvhd')


    def test_create_new_tvhd_downloaditem_tvdb_imdb_not_existing(self):
        data = {
                "ftppath": "/TVHD/Revenge.S03E10.720p.HDTV.X264-DIMENSION",
                }

        expected_data = {'title': 'Revenge.S03E10.720p.HDTV.X264-DIMENSION',
                'tvdbid_id': 248837,
                'imdbid_id': 1837642,
                'ftppath': '/TVHD/Revenge.S03E10.720p.HDTV.X264-DIMENSION',
                'section': 'TVHD',
                'localpath': os.path.join(settings.TVHD_TEMP, 'Revenge.S03E10.720p.HDTV.X264-DIMENSION'),
                'status': DownloadItem.QUEUE,
                }

        self.do_check_download_item(data, expected_data, 'tvhd')


    def test_create_new_movie_downloaditem_with_imdb_not_existing(self):

        data = {
                "ftppath": "/HD/District.9.2009.MULTi.TRUEFRENCH.1080p.BluRay.x264-FiDELiO",
                }

        expected_data = {'title': 'District.9.2009.MULTi.TRUEFRENCH.1080p.BluRay.x264-FiDELiO',
                'tvdbid_id': None,
                'imdbid_id': 1136608,
                'ftppath': '/HD/District.9.2009.MULTi.TRUEFRENCH.1080p.BluRay.x264-FiDELiO',
                'section': 'HD',
                'localpath': os.path.join(settings.HD_TEMP, 'District.9.2009.MULTi.TRUEFRENCH.1080p.BluRay.x264-FiDELiO'),
                'status': DownloadItem.QUEUE,
                }

        self.do_check_download_item(data, expected_data, 'hd')


    def test_create_new_movie_downloaditem_with_imdb_existing(self):
        data = {
                "ftppath": "/HD/Now.You.See.Me.2013.MULTi.TRUEFRENCH.EXTENDED.1080p.BluRay.x264-FiDELiO",
                }

        expected_data = {'title': 'Now.You.See.Me.2013.MULTi.TRUEFRENCH.EXTENDED.1080p.BluRay.x264-FiDELiO',
                'tvdbid_id': None,
                'imdbid_id': 1670345,
                'ftppath': '/HD/Now.You.See.Me.2013.MULTi.TRUEFRENCH.EXTENDED.1080p.BluRay.x264-FiDELiO',
                'section': 'HD',
                'localpath': os.path.join(settings.HD_TEMP, 'Now.You.See.Me.2013.MULTi.TRUEFRENCH.EXTENDED.1080p.BluRay.x264-FiDELiO'),
                'status': DownloadItem.QUEUE,
                }

        self.do_check_download_item(data, expected_data, 'hd')