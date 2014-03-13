__author__ = 'steve'

import json
import urllib2
from django.conf import settings

xbmc_urls = []

try:
    xbmc_urls = settings.XBMC_API_URLS
except:
    pass

def send_json(method, params):

    data = json.dumps({
        "id": 1,
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    })

    for api_url in xbmc_urls:
        req = urllib2.Request(api_url, data, {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()

def send_notification(title, message):

    data = {"title": title, "message": message}

    send_json("GUI.ShowNotification", data)

def update_path(path):

    data = {"directory": path}

    send_json("VideoLibrary.Scan", data)
