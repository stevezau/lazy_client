from __future__ import division
from django.core.management.base import BaseCommand
import logging
from fabric.api import *
from fabric.colors import green, red
from fabric.api import run
from fabric.tasks import execute
from lazycore.utils.queuemanager import QueueManager
from optparse import make_option
import os.path
from importlib import import_module
import pkgutil

from django.conf import settings
from lazycore.models import Version
from django.core.exceptions import ObjectDoesNotExist
import thread

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5 # Lock expires in 5 minutes

class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Lazy Auto Updater"

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list + (
                        make_option('--no-git', action='store_false',
                            dest='git',
                            default=True,
                            help='Pull from git'),
                  )


    def handle(self, *app_labels, **options):
        git = options['git']
        self.do_upgrade(git=git)

    def do_upgrade(self, git=True):
        #First stop all
        self.stop_all()

        #delete all old pyc files
        self.remove_old_pyc()

        #pull down github
        if git:
            self.git_pull()

        #now lets run any upgrade scripts
        self.install_reqs()
        self.reload_data()
        self.sync_db()
        self.upgrade_scripts()
        self.start_all()
        self.update_version()

    def remove_old_pyc(self):
        print(green("Deleting old python files..."))
        local("find /home/media/lazy -name \"*.pyc\" -exec rm -rf {} \;")

    def update_version(self, version=settings.__VERSION__):
        try:
            cur_version = Version.objects.get(id=1)
            cur_version.id = 1
            cur_version.version = version
            cur_version.save()
        except ObjectDoesNotExist:
            new_ver = Version()
            new_ver.id = 1
            new_ver.version = version
            new_ver.save()

    def upgrade_scripts(self):
        from lazyapp import upgrade
        pkgpath = os.path.dirname(upgrade.__file__)

        upgrade_scripts = []

        try:
            cur_version = Version.objects.get(id=1).version
        except ObjectDoesNotExist:
            cur_version = 1

        for _, name, _ in pkgutil.iter_modules([pkgpath]):
            if name.startswith("lazyver_"):
                version = int(name.replace("lazyver_", ""))
                if version > cur_version:
                    upgrade_scripts.append(version)

        for ver in sorted(upgrade_scripts):
            print(green("Running upgrade script from version %s..." % ver))
            mod = import_module("lazyapp.upgrade.lazyver_%s" % ver)
            upgrade_fn = getattr(mod, "upgrade")
            upgrade_fn()

            #update version number so we dont re-run script
            self.update_version(ver)

    def stop_all(self):
        print(green("Stopping services..."))
        QueueManager.stop_queue()
        local("sudo service supervisor stop")
        local("sudo service apache2 stop")

    def git_pull(self):
        print(green("Pulling master from GitHub..."))
        local('git pull')

    def install_reqs(self):
        print(green("Installing requirements..."))
        local("sudo pip install -r requirements.txt")

    def reload_data(self):
        from django.core.cache import cache
        cache.clear()

        print(green("Collecting static files..."))
        local("python manage.py collectstatic --noinput")
        print(green("Loading menu data..."))
        local('python manage.py sitetreeload --mode=replace /home/media/lazy/lazyui/fixtures/lazyui_initialdata.json')

    def sync_db(self):
        print(green("Syncing the database..."))
        local("python manage.py syncdb")
        print(green("Migrating the database..."))
        local("python manage.py migrate")

    def start_all(self):
        print(green("Starting services"))
        local("sudo service apache2 restart")
        local("sudo service supervisor start")
        QueueManager.start_queue()


