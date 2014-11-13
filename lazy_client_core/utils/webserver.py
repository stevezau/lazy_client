#!/usr/bin/env python
import logging, sys, os, signal, time, errno
from socket import gethostname
import atexit
from django.core.management.base import BaseCommand
from django.conf import settings

pidfile = settings.WEBSERVER_PIDFILE

def delpid():
    os.remove(pidfile)

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

def stop_server():
    """
    Stop process whose pid was written to supplied pidfile. 
    First try SIGTERM and if it fails, SIGKILL. If process is still running, an exception is raised.
    """

    #Shut down threads
    from lazy_client_core.utils import threadmanager
    if threadmanager.queue_manager:
        threadmanager.queue_manager.quit()
        threadmanager.queue_manager.join()

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


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def start_server():

    """
    Start CherryPy server
    """
    import cherrypy
    from django.core.handlers.wsgi import WSGIHandler as app

    # Check for a pidfile to see if the daemon already runs
    try:
        pidf = file(settings.WEBSERVER_PIDFILE)
        pid = int(pidf.read().strip())
        pidf.close()
    except IOError:
        pid = None

    if pid:
        #If its the same pid, then we are re-spawning
        if pid == os.getpid():
            pass
        else:
            if check_pid(pid):
                print "pidfile %s already exists. Web server already running?" % pidfile
                sys.exit(1)
            else:
                print "pidfile %s already exists. Web server was not found to be running, deleting pid file." % pidfile
                delpid()

    # before mounting anything
    from django.utils.daemonize import become_daemon
    #become_daemon(our_home_dir=settings.BASE_DIR)

    #cherrypy.config.update({
    #    'log.error_file': settings.WEBSERVER_ERROR_LOG,
    #    'log.access_file': settings.WEBSERVER_ACCESS_LOG,
    #})

    print 'starting server'
    atexit.register(delpid)

    # Mount the application
    cherrypy.tree.graft(app(), "/")
    cherrypy.tree.mount(None, '/static', {'/' : {
    'tools.staticdir.dir': settings.STATIC_ROOT,
    'tools.staticdir.on': True,
    }})

    # Unsubscribe the default server
    cherrypy.server.unsubscribe()
    cherrypy.engine.subscribe("stop", stop_server)

    cherrypy.config.update({'engine.autoreload.on': False})
    cherrypy.config.update({'environment': 'embedded'})

    # Instantiate a new server object
    server = cherrypy._cpserver.Server()

    # Configure the server object
    server.socket_host = settings.WEBSERVER_IP
    server.socket_port = settings.WEBSERVER_PORT
    server.thread_pool = 15

    # For SSL Support
    # server.ssl_module            = 'pyopenssl'
    # server.ssl_certificate       = 'ssl/certificate.crt'
    # server.ssl_private_key       = 'ssl/private.key'
    # server.ssl_certificate_chain = 'ssl/bundle.crt'

    fp = open(settings.WEBSERVER_PIDFILE, 'w')
    fp.write("%d\n" % os.getpid())
    fp.close()

    # Subscribe this server
    server.subscribe()

    cherrypy.engine.start()
    #Initalise the thead maangers
    from lazy_client_core.utils import threadmanager
    from lazy_client_core.utils.threadmanager import QueueManager

    threadmanager.queue_manager = QueueManager()

    cherrypy.engine.block()
