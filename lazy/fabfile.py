from fabric.api import *
from fabric.colors import green, red
from fabric.contrib import django

django.project('lazyapp')

from lazycore.utils.queuemanager import QueueManager

#first lets set the local path to ~/home/lazy

def upgrade():
    #First stop all
    stop_all()

    #pull down github
    #git_pull()

    #now lets run any upgrade scripts


    install_reqs()
    collect_static()
    sync_db()

    start_all()

    update_version()

def update_version():
    pass


def stop_all():
    print(green("Stopping services..."))
    QueueManager.stop_queue()
    local("sudo service supervisor stop")
    local("sudo service apache2 stop")

def restart():
    local('python manage.py sitetreeload --mode=replace /home/media/lazy/lazyweb/fixtures/lazyweb_initialdata.json')
    local('python manage.py collectstatic')


def git_pull():
    print(green("Pulling master from GitHub..."))
    local('git pull')


def install_reqs():
    print(green("Installing requirements..."))
    local("sudo pip install -r requirements.txt")


def collect_static():
    print(green("Collecting static files..."))
    local("python manage.py collectstatic --noinput")


def sync_db():
    print(green("Syncing the database..."))
    local("python manage.py syncdb")
    print(green("Migrating the database..."))
    local("python manage.py migrate")


def start_all():
    print(green("Starting services"))
    local("sudo service apache2 restart")
    local("sudo service supervisor start")
    QueueManager.start_queue()