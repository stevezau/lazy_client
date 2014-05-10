__author__ = 'steve'

import json
import urllib2
from django.conf import settings
import os

xbmc_api_urls = []

try:
    xbmc_api_urls = settings.XBMC_API_URLS
except:
    pass

def send_json(api_url, method, params):

    data = json.dumps({
        "id": 1,
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    })

    req = urllib2.Request(api_url, data, {'Content-Type': 'application/json'})
    f = urllib2.urlopen(req)
    response = f.read()
    f.close()

def send_notification(api_url, title, message):

    data = {"title": title, "message": message}

    try:
        send_json(api_url, "GUI.ShowNotification", data)
    except:
        pass

def add_file(f):

    #OK Lets get the path
    path = os.path.dirname(f)
    filename = os.path.basename(f)

    for xbmc_api_url in xbmc_api_urls:
        try:
            data = {"directory": path}
            send_notification(xbmc_api_url, "New Released Added", filename)
            send_json(xbmc_api_url, "VideoLibrary.Scan", data)
        except:
            pass
            



