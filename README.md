#INSTALL STEPS FOR LAZY

OS Config
=====
Lazy is designed to run under a user called media (this could be changed but not tested).

1. Create a new user on your os called media with the home directory of /home/media


Install Ubuntu Packages
=====
Execute the following on server


	$ sudo apt-get install apache2 libapache2-mod-wsgi lftp git python-pip supervisor mysql-server phpmyadmin python-mysqldb 

Setup Mysql
=====

1) Create database in mysql called lazy

	
Configure flexget
=====
Flexget will watch the FTP site for new releases. It will tell lazy about any releases which meets certain criteria.

1) Install Flexget

	$ sudo pip install flexget

2) Copy folder flexget-conf from git and rename it to /home/media/.flexget

3) Edit the below files as required

	$ /home/media/.flexget/config.yml
	$ /home/media/.flexget/config-xvid.yml

	
LFTP Config. 
=====
LFTP is used to download the files from the FTP

1) Copy the lftprc file from git hub to 


	$ /home/media/.lftp/rc

Setup storage folders
=====


	$ mkdir -p /data/Videos/Movies
	$ mkdir -p /data/Videos/TVShows
	$ mkdir -p /data/Videos/_incoming/TVShows
	$ mkdir -p /data/Videos/_incoming/Requests
	$ mkdir -p /data/Videos/_incoming/Movies


Lazy Install
=====
1) Export the lazy folder from git to /home/media/lazy

2) Setup requirements for lazy

	$ sudo pip install -U -r /home/media/lazy/requirements.txt

3) !!IMPORTANT!! Edit the settings in file /home/media/lazy/lazysettings.py


4) Initial setup of database

	$ cd /home/media/lazy
	$ mkdir -p static/media
	$ python manage.py syncdb
	$ python manage.py createcachetable lazy_cache
	$ python manage.py migrate

	(Create a superuser for the admin section of the site when it asks)

5) Load menu data

	$ python manage.py sitetreeload --mode=replace /home/media/lazy/lazyweb/fixtures/lazyweb_initialdata.json

6) Collect static files

	$ python manage.py collectstatic

	
7) Setup background processor for autostartup (as media)

	$ sudo mkdir /var/log/celery
	$ sudo chown media:media /var/log/celery
	$ sudo ln -s /home/media/lazy/serverconf/lazy-supervisor.conf /etc/supervisor/conf.d/lazy.conf 
	$ sudo service supervisor restart
	


Setup Apache
=====

	$ sudo ln -s /home/media/lazy/serverconf/lazy-apache.conf /etc/apache2/sites-available/lazy.conf
	$ sudo a2ensite lazy
	$ sudo service apache2 restart


Conjob for Flexget
=====

Add the following cron jobs

	$ */15 * * * * /usr/local/bin/flexget --cron -c /home/media/.flexget/config-xvid.yml
	$ */15 * * * * /usr/local/bin/flexget --cron --disable-advancement




Thats it.. go to http://serverip/lazy
