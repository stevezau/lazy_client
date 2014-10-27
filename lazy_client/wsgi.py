"""
WSGI config for LazyApp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lazy_client.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

#Initalise the thead maangers
from lazy_client_core.utils import threadmanager
from lazy_client_core.utils.threadmanager import QueueManager

threadmanager.queue_manager = QueueManager()