#INSTALL STEPS FOR LAZY

OS Config
=====
Lazy is designed to run under a user called media (this could be changed but not tested).

1. Create a new user on your os called media with the home directory of /home/media


Install Packages
=====
Execute the following on server

	$ sudo apt-get install git python-pip unrar mysql-server phpmyadmin python-mysqldb  python-dev libpython-dev python-pycurl



Configure flexget
=====
Flexget will watch the FTP site for new releases. It will tell lazy about any releases which meets certain criteria.

1) Install Flexget

	$ sudo pip install flexget

2) Copy folder flexget-conf from git and rename it to /home/media/.flexget

3) Edit the below files as required

	$ /home/media/.flexget/config.yml
	$ /home/media/.flexget/config-xvid.yml


	
Setup storage folders
=====


	$ mkdir -p /data/Videos/Movies
	$ mkdir -p /data/Videos/TVShows
	$ mkdir -p /data/Videos/_incoming/TVShows
	$ mkdir -p /data/Videos/_incoming/Requests
	$ mkdir -p /data/Videos/_incoming/Movies


Lazy Install
=====
1) Import Lazy_client from Git

	$ git clone https://github.com/stevezau/lazy_client.git /home/media/lazy

2) Setup requirements for lazy

	$ sudo pip install -U -r /home/media/lazy/requirements.txt

3) !!IMPORTANT!! Copy lazysettings.py.example to lazysettings.py and edit the settings

4) Initial setup

	$ ./lazy.sh setup


8) Start service

	$ ./lazy.sh start


Conjob for Flexget & Auto Lazy Startup
=====

Add the following cron jobs

	$ */15 * * * * /usr/local/bin/flexget -c /home/media/.flexget/config-xvid.yml  execute --cron
	$ */15 * * * * /usr/local/bin/flexget execute --cron --disable-advancement
	$ */5 * * * * /home/media/lazy/lazy.sh check




Thats it.. go to http://serverip/lazy
