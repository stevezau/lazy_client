# -*- coding: utf-8 -*-

from __future__ import unicode_literals, division, absolute_import
from flexget.event import event
from urllib import quote
from requests.exceptions import RequestException, HTTPError
from logging import getLogger
from flexget.utils import json, requests
from flexget import plugin
from flexget import validator
from flexget.config_schema import one_or_more

import re
log = getLogger('lazy')



class PluginLazy(object):
    """
    Parse task content or url for hoster links and adds them to pyLoad.

    Example::

      pyload:
        api: http://localhost:8000/api
        request: yes
        enabled: yes

    Default values for the config elements::

      pyload:
          api: http://localhost:8000/api
          queue: no
          hoster: ALL
          parse_url: no
          multiple_hoster: yes
          enabled: yes
    """

    __author__ = 'steve'
    __version__ = '0.1'

    DEFAULT_API = 'http://localhost:8000/lazy/api'
    DEFAULT_PENDING = False
    DEFAULT_HANDLE_NO_URL_AS_FAILURE = False

    schema = {
        'type': 'object',
        'properties': {
            'api': {'type': 'string'},
            'pending': {'type': 'boolean'},
        },
    }

    def __init__(self):
        self.session = None

    def on_process_start(self, task, config):
        self.session = None

    def on_task_output(self, task, config):
        if not config.get('enabled', True):
            return
        if not task.accepted:
            return

        self.add_entries(task, config)

    def add_entries(self, task, config):
        """Adds accepted entries"""

        try:
            self.check_up(task, config)
        except IOError:
            raise plugin.PluginError('lazy not reachable', log)
        except plugin.PluginError:
            raise
        except Exception as e:
            raise plugin.PluginError('Unknown error: %s' % str(e), log)

        api_url = config.get('api', self.DEFAULT_API)
        pending = config.get('pending', self.DEFAULT_PENDING)

        for entry in task.accepted:

            log.debug("Add %s to lazy" % entry['path'])

            imdb_id = None
            tvdb_id = None

            if 'imdb_id' in entry:
                 imdb_id = int(extract_id(entry['imdb_id']))

            if 'tvdb_id' in entry:
                 tvdb_id = int(entry['tvdb_id'])

            status = 1

            if pending:
                status = 6

            try:
                post = {'ftppath': "%s" % entry['path'],
                        'imdbid_id': imdb_id,
                        'tvdbid_id': tvdb_id,
                        'status': status,
                    }

                query_api(api_url, "downloads", post)
                log.info('added entry to lazy %s' % entry['path'])

            except Exception as e:
                log.exception(e)
                entry.fail(str(e))


    def check_up(self, task, config):
        url = config.get('api', self.DEFAULT_API).rstrip("/") + "/"

        try:
            query_api(url, 'downloads')
        except HTTPError as e:
            raise plugin.PluginError('HTTP Error %s' % e, log)

def query_api(url, method, post=None):
    try:
        response = requests.request(
            'post' if post is not None else 'get',
            url.rstrip("/") + "/" + method.strip("/") + "/",
            data=post)
        response.raise_for_status()
        return response
    except RequestException as e:
        log.exception(e.response)
        if e.response.status_code == 500:
            msg = 'Internal API Error: %s %s %s %' % (method, url, post, e.message)
            raise plugin.PluginError(msg, log)
        raise

@event('plugin.register')
def register_plugin():
    plugin.register(PluginLazy, 'lazy', api_ver=2)

def extract_id(url):
    """Return IMDb ID of the given URL. Return None if not valid or if URL is not a string."""
    if not isinstance(url, basestring):
        return
    m = re.search(r'(?:nm|tt([\d]{7}))', url)
    if m:
        return m.group(1)