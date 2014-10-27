from __future__ import division
from django.core.management.base import BaseCommand
import logging
from lazy_client_core.utils.queuemanager import QueueManager
from optparse import make_option
import subprocess
import os
from importlib import import_module
import fnmatch
import pkgutil
from django.core import management
from lazy_client_core.models import Version
from django.conf import settings as djangosettings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from lazy_client_core.utils.common import green_color, fail_color, blue_color
import shutil
from django.core.cache import cache

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5 # Lock expires in 5 minutes

class Command(BaseCommand):

    base_dir = djangosettings.BASE_DIR

    queue_running = QueueManager.queue_running()

    manage_file = os.path.join(base_dir, "manage.py")
    lazysh_file = os.path.join(base_dir, "lazy.sh")

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

        #Clear cache
        cache.clear()

        # Run the setup command to sync the db etc
        call_command('setup', interactive=False)

        #stop all
        self.stop_all()

        #delete all old pyc files
        self.remove_old_pyc()

        #pull down github
        #if git:
        #    self.git_pull()

        self.upgrade_scripts()
        self.start_all()

        self.update_version()

        print blue_color("Upgrade success")

    def remove_old_pyc(self):
        print(green_color("Deleting old python files..."))

        matches = []
        for root, dirnames, filenames in os.walk(self.base_dir):
            for filename in fnmatch.filter(filenames, '*.pyc'):
                matches.append(os.path.join(root, filename))

        for f in matches:
            try:
                os.remove(f)
            except:
                pass


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
            print(green_color("Running upgrade script from version %s..." % ver))
            mod = import_module("lazy_client.upgrade.lazyver_%s" % ver)
            upgrade_fn = getattr(mod, "upgrade")
            upgrade_fn()

            #update version number so we dont re-run script
            self.update_version(ver)

    def stop_all(self):
        print(green_color("Stopping services..."))

        #Stop web_Server
        management.call_command('webui', 'stop', interactive=False)

    def run_command(self, cmd, check=False):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return_code = p.returncode

        if check:
            if return_code != 0:
                print out
                print err
                print fail_color("Error running command %s" % cmd)
                exit(1)

        return return_code, out, err

    def git_pull(self):
        import stat

        replace = False

        retries = 5

        for i in range(retries):

            if replace:
                self.run_command(['/usr/bin/env', 'git', 'reset', '--hard'], check=True)

            return_code, stdout, stderr = self.run_command(['/usr/bin/env', 'git', 'pull'])

            if "Invalid username or password" in stderr:
                print(fail_color("Invalid user/pass for Git, try again!..."))
                continue

            if "Your local changes to the following files would be overwritten by merge:" in stderr:
                print(fail_color("Appears you have edited files locally, shall i replace them?"))
                print stderr

                replace = None

                while None is replace:
                    yesno = raw_input("Replace locally edited files? [yes/no]: ")

                    if yesno.lower() == "yes":
                        replace = True

                    if yesno.lower() == "no":
                        replace = False

                continue

            if "fatal: Not a git repository" in stderr:
                return

            if return_code == 0:
                return
            else:
                print fail_color("Invalid return code, lets try again")

        print fail_color("Error unable to get latest files from GitHub")
        exit(1)

    def start_all(self):
        print(green_color("Starting services"))
        self.run_command([self.lazysh_file, 'restart'], check=True)


