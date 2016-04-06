__author__ = 'steve'
from lazy_common import requests
import urlparse
import json
import logging
from requests.exceptions import *
from django.conf import settings
from requests.auth import HTTPBasicAuth

class LazyServerExcpetion(Exception):
    """ Error in search """

logger = logging.getLogger(__name__)

lazy_server_api = "http://media.stevez0.com:5050/legacy/"

default_sites = [
    'SCC',
    'SCC_0DAY',
    'SCC_ARCHIVE',
    'REVTT',
    'REVTT_PACKS',
    'HD',
#    'TL',
#    'TL_PACKS',
    ]


auth = HTTPBasicAuth(settings.LAZY_USER, settings.LAZY_PWD)


def seconds_left(dlitem):
    try:
        headers = {'Content-type': 'application/json', "Accept": "application/json"}
        data = {"title": dlitem.title, "ftppath": dlitem.ftppath}

        r = requests.post(urlparse.urljoin(lazy_server_api, "seconds_remaining/"), data=json.dumps(data), headers=headers, auth=auth)

        try:
            json_response = r.json()
            return json_response['data']
        except:
            return -1
    except:
        return -1

def download_torrents(torrents):
    old_timeout = requests.session.timeout
    requests.session.timeout = 100 #seconds

    try:
        headers = {'Content-type': 'application/json', "Accept": "application/json"}
        downloads = {"download": torrents}

        r = requests.post(urlparse.urljoin(lazy_server_api, "download_torrents/"), data=json.dumps(downloads), headers=headers, auth=auth)
        json_response = r.json()

        if 'status' in json_response and json_response['status'] == "success":
            return json_response['data']
        elif 'message' in json_response:
            raise LazyServerExcpetion(json_response['message'])
        else:
            raise LazyServerExcpetion("Invalid response from server")
    except ConnectionError as e:
        raise LazyServerExcpetion(str(e))
    except ConnectTimeout as e:
        raise LazyServerExcpetion(str(e))
    except ReadTimeout as e:
        raise LazyServerExcpetion(str(e))
    except Timeout as e:
        raise LazyServerExcpetion(str(e))
    except HTTPError as e:
        raise LazyServerExcpetion(str(e))
    finally:
        requests.session.timeout = old_timeout
def search_ftp(search):
    payload = {
        'search': search,
    }

    try:
        headers = {'Content-type': 'application/json', "Accept": "application/json"}
        r = requests.post(urlparse.urljoin(lazy_server_api, "search_ftp/"), data=json.dumps(payload), headers=headers, auth=auth)
        json_response = r.json()

        if 'status' in json_response and json_response['status'] == "success":
            return json_response['data']
        else:
            raise LazyServerExcpetion("Invalid status from server")
    except ConnectionError as e:
        raise LazyServerExcpetion(str(e))
    except ConnectTimeout as e:
        raise LazyServerExcpetion(str(e))
    except ReadTimeout as e:
        raise LazyServerExcpetion(str(e))
    except Timeout as e:
        raise LazyServerExcpetion(str(e))
    except HTTPError as e:
        raise LazyServerExcpetion(str(e))

def search_torrents(search, sites=default_sites, max_results=100):
    payload = {
        'sites': sites,
        'search': search,
        'max_results': max_results,
    }

    try:
        headers = {'Content-type': 'application/json', "Accept": "application/json"}
        r = requests.post(urlparse.urljoin(lazy_server_api, "find_torrents/"), data=json.dumps(payload), headers=headers, auth=auth)
        json_response = r.json()

        if 'status' in json_response and json_response['status'] == "success":
            return json_response['data']
        else:
            raise LazyServerExcpetion("Invalid status from server")
    except ConnectionError as e:
        raise LazyServerExcpetion(str(e))
    except ConnectTimeout as e:
        raise LazyServerExcpetion(str(e))
    except ReadTimeout as e:
        raise LazyServerExcpetion(str(e))
    except Timeout as e:
        raise LazyServerExcpetion(str(e))
    except HTTPError as e:
        raise LazyServerExcpetion(str(e))