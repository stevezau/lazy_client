import os
import sys

path = '/home/media/lazy'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'lazy_client.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()