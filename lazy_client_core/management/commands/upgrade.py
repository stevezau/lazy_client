from __future__ import division
from django.core.management.base import BaseCommand
import logging
from fabric.api import *
from fabric.colors import green, red
from fabric.operations import prompt
from lazy_client_core.utils.queuemanager import QueueManager
from optparse import make_option
import os
from importlib import import_module
import pkgutil
from fabric.api import settings
from lazy_client_core.models import Version
from django.conf import settings as djangosettings
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5 # Lock expires in 5 minutes

class Command(BaseCommand):

    queue_running = QueueManager.queue_running()

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

        if os.path.exists("lazysettings.bk"):
            local("mv lazysettings.bk lazysettings.py")

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

    def update_version(self, version=djangosettings.__VERSION__):
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
        from lazy_client import upgrade
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
            mod = import_module("lazy_client.upgrade.lazyver_%s" % ver)
            upgrade_fn = getattr(mod, "upgrade")
            upgrade_fn()

            #update version number so we dont re-run script
            self.update_version(ver)

    def stop_all(self):
        print(green("Stopping services..."))

        if self.queue_running:
            QueueManager.stop_queue()

        local("sudo service supervisor stop")
        local("sudo service apache2 stop")

    def git_pull(self):

        replace = False

        with settings(warn_only=True):

            retries = 5

            for i in range(retries):

                up_to = retries - i

                if replace:
                    local("mv lazysettings.py lazysettings.bk")
                    local("git stash")
                    local("git stash drop")
                    local("mv lazysettings.bk lazysettings.py")
                    local("chmod +x manage.py")
                    result = local('git pull', capture=True)
                else:
                    result = local('git pull', capture=True)


                if "Invalid username or password" in result.stderr:
                    print(red("Invalid user/pass for Git, try again!..."))
                    continue

                if "Your local changes to the following files would be overwritten by merge:" in result.stderr:
                    print(red("Appears you have edited files locally, shall i replace them?"))
                    print result.stderr
                    replace = prompt("Replace locally edit files?", default="yes", validate=r'yes|no')

                    if replace == "yes":
                        replace == True

                    continue

                if result.return_code == 0:
                    return
                else:
                   print(red("Invalid return code, lets try again"))

            raise SystemExit("ERROR: Unable to get latest files from GitHub")

    def install_reqs(self):
        print(green("Installing requirements..."))
        local("sudo pip install -r requirements.txt")

    def reload_data(self):
        from django.core.cache import cache
        cache.clear()

        print(green("Collecting static files..."))
        local("python manage.py collectstatic --noinput")
        print(green("Loading menu data..."))
        local('python manage.py sitetreeload --mode=replace /home/media/lazy/lazy_client_ui/fixtures/lazyui_initialdata.json')

    def sync_db(self):
        print(green("Syncing the database..."))
        local("python manage.py syncdb")
        print(green("Migrating the database..."))
        local("python manage.py migrate")

    def start_all(self):
        print(green("Starting services"))
        local("sudo service apache2 restart")
        local("sudo service supervisor start")

        if self.queue_running:
            QueueManager.start_queue()

