#INSTALL STEPS FOR LAZY

OS Config
=====
Lazy is designed to run under a user called media (this could be changed but not tested).

1. Create a new user on your os called media with the home directory of /home/media


Install Ubuntu Packages
=====
Execute the following on server


	$ sudo apt-get install apache2 libapache2-mod-wsgi lftp git python-pip supervisor

Configure flexget
=====
Flexget will watch the FTP site for new releases. It will tell lazy about any releases which meets certain criteria.

1. Install Flexget

.. code-block:: bash

	$ sudo pip install flexget

2. Copy folder flexget-conf from git and rename it to /home/media/.flexget

3. Edit the below files as required

.. code-block:: bash

	$ /home/media/.flexget/config.yml
	$ /home/media/.flexget/config-xvid.yml

	
LFTP Config. 
=====
LFTP is used to download the files from the FTP

1. Copy the lftprc file from git hub to 
.. code-block:: bash

	$ /home/media/.lftp/rc

Setup storage folders
=====
.. code-block:: bash

	$ mkdir -p /data/Videos/Movies
	$ mkdir -p /data/Videos/TVShows
	$ mkdir -p /data/Videos/_incoming/TVShows
	$ mkdir -p /data/Videos/_incoming/Requests
	$ mkdir -p /data/Videos/_incoming/Movies


Lazy Install
=====
1. Export the lazy folder from git to /home/media/lazy

2. Setup requirements for lazy

.. code-block:: bash

	$ sudo pip install -U -r /home/media/lazy/requirements.txt

3. Initial setup of database

.. code-block:: bash

	$ cd /home/media/lazy
	$ python manage.py syncdb
	
(Create a superuser for the admin section of the site when it asks)

4. Update database schema
.. code-block:: bash

	$ python manage.py migrate

5. Load menu data
.. code-block:: bash

	$ python manage.py sitetreeload --mode=replace /home/media/lazy/lazyweb/fixtures/lazyweb_initialdata.json

5. Collect static files
.. code-block:: bash

	$ python manage.py collectstatic

6. Create cache table
.. code-block:: bash

	$ python manage.py createcachetable lazy_cache

7. Setup background processor for autostartup (as media)

.. code-block:: bash

	$ mkdir /var/log/celery
	$ sudo ln -s /home/media/lazy/serverconf/lazy-supervisor.conf /etc/supervisor/conf.d/lazy.conf 
	$ sudo service supervisor restart



