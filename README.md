#INSTALL STEPS FOR LAZY

OS Config
=====
Lazy is designed to run under a user called media (this could be changed but not tested).

1. Create a new user on your os called media with the home directory of /home/media


Install Ubuntu Packages
=====
Execute the following on server


	$ sudo apt-get install apache2 libapache2-mod-wsgi lftp git python-pip supervisor unrar mysql-server phpmyadmin python-mysqldb  python-dev libpython-dev python-pycurl

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



	
Install RabbitMQ for the Backgound processor queue 
=====

	edit /etc/apt/sources.list and add following line to the bottom
	
	deb http://www.rabbitmq.com/debian/ testing main

	Then type in..
	
	$ wget http://www.rabbitmq.com/rabbitmq-signing-key-public.asc
	$ sudo apt-key add rabbitmq-signing-key-public.asc
	$ sudo apt-get update
	$ sudo apt-get install rabbitmq-server

	
Setup storage folders
=====


	$ mkdir -p /data/Videos/Movies
	$ mkdir -p /data/Videos/TVShows
	$ mkdir -p /data/Videos/_incoming/TVShows
	$ mkdir -p /data/Videos/_incoming/Requests
	$ mkdir -p /data/Videos/_incoming/Movies


Lazy Install
=====
1) Export the lazy folder from git to /home/media/lazy-repo and create a symbolic link to /home/media/lazy

	$ git clone https://github.com/rameezsadikot/Steve.git /home/media/lazy-repo
	$ ln -s /home/media/lazy-repo/lazy /home/media/lazy

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
	
8) Restarts service

	$ sudo service supervisor stop
	<wait 10 seconds>
	$ sudo service supervisor start


Setup Apache
=====

	$ sudo ln -s /home/media/lazy/serverconf/lazy-apache.conf /etc/apache2/sites-available/lazy.conf
	$ sudo a2ensite lazy
	$ sudo service apache2 restart


Conjob for Flexget
=====

Add the following cron jobs

	$ */15 * * * * /usr/local/bin/flexget -c /home/media/.flexget/config-xvid.yml  execute --cron
	$ */15 * * * * /usr/local/bin/flexget execute --cron --disable-advancement




Thats it.. go to http://serverip/lazy
