Installation Steps for Lazy
====

Lazy is designed to run on a linux server. Theses steps are for Ubuntu.

1. Install required packages

  #sudo apt-get install unrar cksfv python-dev python-setuptools libxml2 libxml2-dev libxslt1.1 libxslt1-dev python-formencode lftp sqlite xinit libsqlite3-0 sqlite3 

2. Install required python packages

  #sudo easy_install flexget IMDBpy IPy pexpect easy_extract


3. Install lazy. Download the lazy egg.

  #sudo easy_install lazy-x.egg
  

Configuration of Lazy
====

Lazy is now installed. We now need to configure it.

1. Create ~/.lazy folder in your home folder (User that lazy will run as. Don't use root!)

2. Install the config.cfg file and change the required values


Configuration of Flexget
====

Flexget will watch the FTP site for new releases. It will tell lazy about any releases which meets certian criteria. 

1. Copy the examples as shown below.
  
    flexget-config.yml to ~/home/.flexget/config.yml
    flexget-config-xvid.yml to ~/home/.flexget/config-xvid.yml

2. Edit required valuse in the config files.

Setup Conjobs
====

The follow cronjobs are required. Make sure you edit the paths to reflect your server.

*/15 * * * * /usr/local/bin/flexget --cron -c /home/media/.flexget/config-xvid.yml
*/15 * * * * /usr/local/bin/flexget --cron --disable-advancement
*/2 * * * * /usr/local/bin/lazy queuemanager -q update &> /dev/null
*/10 * * * * /usr/local/bin/lazy moverls &> /dev/null





That's it, your done. I'd also recommend installing Lazy-UI as its a full frontned UI to lazy.
