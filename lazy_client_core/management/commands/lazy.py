#!/usr/bin/env python

import os
from django.core.management.base import BaseCommand
from lazy_client_core.utils.webserver import start_server, stop_server
import atexit

CPSERVER_HELP = r"""
  Run webui

   webui start
   webui stop

"""

class Command(BaseCommand):
    help = "Start/Stop lazy server"

    def handle(self, *args, **options):

        if "help" in args:
            print CPSERVER_HELP
            return

        if "stop" in args:
            try:
                stop_server()
                print "Stopped lazy web server"
            except OSError:
                print "Error stopping web server: %s" % OSError

            return

        if "start" in args:
            #Start the webserver
            start_server()

    def usage(self, subcommand):
        return CPSERVER_HELP
