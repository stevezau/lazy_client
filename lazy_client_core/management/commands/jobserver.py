#!/usr/bin/env python

import time
import errno
import os
from django.core.management.base import BaseCommand
from lazy_client_core.utils.webserver import start_server, stop_server
from django.core import management
from django.conf import settings
import signal

HELP = r"""
  Run webui

   jobserver stop

"""

def poll_process(pid):
    """
    Poll for process with given pid up to 10 times waiting .25 seconds in between each poll.
    Returns False if the process no longer exists otherwise, True.
    """
    for n in range(10):
        time.sleep(0.25)
        try:
            # poll the process state
            os.kill(pid, 0)
        except OSError, e:
            if e[0] == errno.ESRCH:
                # process has died
                return False
            else:
                raise Exception
    return True

def stop_server(pidfile):
    """
    Stop process whose pid was written to supplied pidfile.
    First try SIGTERM and if it fails, SIGKILL. If process is still running, an exception is raised.
    """

    if os.path.exists(pidfile):
        pid = int(open(pidfile).read())
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError: #process does not exist
            os.remove(pidfile)
            return
        if poll_process(pid):
            #process didn't exit cleanly, make one last effort to kill it
            os.kill(pid, signal.SIGKILL)
            if poll_process(pid):
                raise OSError, "Process %s did not stop."
        os.remove(pidfile)


class Command(BaseCommand):
    help = "Start/Stop background job server"

    def handle(self, *args, **options):

        if "help" in args:
            print HELP
            return

        if "stop_beat" in args:

            pidfile = settings.CELERY_BEAT_PID_FILE

            if os.path.exists(pidfile):
                pid = int(open(pidfile).read())
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError: #process does not exist
                    os.remove(pidfile)
                    return
                if poll_process(pid):
                    #process didn't exit cleanly, make one last effort to kill it
                    os.kill(pid, signal.SIGKILL)
                    if poll_process(pid):
                        print "Error stopping web server"
                        return

                try:
                    os.remove(pidfile)
                except:
                    pass

                print "Stopped job server"
            else:
                print "job server was not running"

        if "stop" in args:

            from lazy_client_core.utils.queuemanager import QueueManager
            QueueManager.stop_jobs()

            pidfile = settings.CELERYD_PID_FILE

            if os.path.exists(pidfile):
                pid = int(open(pidfile).read())
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError: #process does not exist
                    os.remove(pidfile)
                    return
                if poll_process(pid):
                    #process didn't exit cleanly, make one last effort to kill it
                    os.kill(pid, signal.SIGKILL)
                    if poll_process(pid):
                        print "Error stopping web server"
                        return

                try:
                    os.remove(pidfile)
                except:
                    pass

                print "Stopped job server"
            else:
                print "job server was not running"

    def usage(self, subcommand):
        return HELP
