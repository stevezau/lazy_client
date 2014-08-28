__author__ = 'steve'
from lazy_common import requests
import urlparse
import os
import json
import logging
from requests.exceptions import ConnectionError

class SearchException(Exception):
    """ Error in search """

logger = logging.getLogger(__name__)

lazy_server_api = "http://drifthost.com:8000/api/find_torrents/"

def search_torrents(search, sites=["REVTT", "SCC", "TL", "HD"]):
    payload = {
        'sites': sites,
        'search': search,
    }

    try:
        r = requests.post(lazy_server_api, data=payload)
        json_response = r.json()

        if 'status' in json_response and json_response['status'] == "success":
            results = json.loads(json_response)
            return results['data']
        else:
            raise SearchException("Invalid status from server")
    except ConnectionError as e:
        raise SearchException(str(e))