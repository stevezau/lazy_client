__author__ = 'steve'

import json
import urllib2
from django.conf import settings
import os
from lazy_client_core.exceptions import XBMCConnectionError, InvalidXBMCURL
from datetime import datetime


xbmc_api_url = None
last_fail = None

try:
    xbmc_api_url = settings.XBMC_API_URL
except:
    pass

file_cache = {}

def send_json(method, params, api_url=xbmc_api_url):
    global last_fail

    if None is xbmc_api_url:
        raise InvalidXBMCURL("Invalid XBMC URL/IP")

    if None is not last_fail:
        now = datetime.now()
        seconds = (now-last_fail).total_seconds()

        if seconds < 60:
            raise XBMCConnectionError("Has been known to fail in past")
        pass

    data = json.dumps({
        "id": 1,
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    })

    req = urllib2.Request(api_url, data, {'Content-Type': 'application/json'})

    try:
        f = urllib2.urlopen(req)
        response = f.read()
        f.close()
        return json.loads(response)
    except Exception as e:
        last_fail = datetime.now()
        raise XBMCConnectionError(str(e))

def send_notification(title, message):

    data = {"title": title, "message": message}

    send_json("GUI.ShowNotification", data)

def add_file(f):

    #OK Lets get the path
    path = os.path.dirname(f)
    filename = os.path.basename(f)

    data = {"directory": path}

    send_notification("New Released Added", filename)
    send_json("VideoLibrary.Scan", data)

def get_file_details(f):

    if f in file_cache.keys():
        now = datetime.now()
        age = file_cache[f]['age']

        seconds = (now-age).total_seconds()

        if seconds < 900:
            return file_cache[f]

    data = {"file": f, "media": "video", "properties": ["playcount"]}

    response = send_json("Files.GetFileDetails", data)

    try:
        file_details = response['result']['filedetails']
        file_details['age'] = datetime.now()
        file_cache[f] = file_details
    except:
        pass

def get_file_playcount(f):

    file_details = get_file_details(f)

    try:
        count = file_details['playcount']
        return count
    except:
        return -1

