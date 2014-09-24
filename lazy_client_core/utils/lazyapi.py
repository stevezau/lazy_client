__author__ = 'steve'
from lazy_common import requests
import urlparse
import os
import json
import logging
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError

class LazyServerExcpetion(Exception):
    """ Error in search """

logger = logging.getLogger(__name__)

lazy_server_api = "http://drifthost.com:8000/api/"

default_sites = [
    'SCC',
    'SCC_0DAY',
    'SCC_ARCHIVE',
    'REVTT',
    'HD',
    'TL',
    'TL_PACKS',
    ]

def download_torrents(torrents):
    try:
        headers = {'Content-type': 'application/json', "Accept": "application/json"}
        downloads = {"download": torrents}
        r = requests.post(urlparse.urljoin(lazy_server_api, "download_torrents/"), data=json.dumps(downloads), headers=headers)
        json_response = r.json()

        if 'status' in json_response and json_response['status'] == "success":
            return json_response['data']
        elif 'message' in json_response:
            raise LazyServerExcpetion(json_response['message'])
        else:
            raise LazyServerExcpetion("Invalid response from server")
    except ConnectionError as e:
        raise LazyServerExcpetion(str(e))
    except HTTPError as e:
        raise LazyServerExcpetion(str(e))

def search_ftp(search):
    payload = {
        'search': search,
    }

    try:
        headers = {'Content-type': 'application/json', "Accept": "application/json"}
        r = requests.post(urlparse.urljoin(lazy_server_api, "search_ftp/"), data=json.dumps(payload), headers=headers)
        json_response = r.json()

        if 'status' in json_response and json_response['status'] == "success":
            return json_response['data']
        else:
            raise LazyServerExcpetion("Invalid status from server")
    except ConnectionError as e:
        raise LazyServerExcpetion(str(e))
    except HTTPError as e:
        raise LazyServerExcpetion(str(e))


def search_torrents(search, sites=default_sites):
    payload = {
        'sites': sites,
        'search': search,
    }

    try:
        headers = {'Content-type': 'application/json', "Accept": "application/json"}
        r = requests.post(urlparse.urljoin(lazy_server_api, "find_torrents/"), data=json.dumps(payload), headers=headers)
        json_response = r.json()

        if 'status' in json_response and json_response['status'] == "success":
            return json_response['data']
        else:
            raise LazyServerExcpetion("Invalid status from server")
    except ConnectionError as e:
        raise LazyServerExcpetion(str(e))
    except HTTPError as e:
        raise LazyServerExcpetion(str(e))