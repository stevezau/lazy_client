Lazy-UI Installation
====

1. First you need to install the following packages

  sudo apt-get install apache2 libapache2-mod-suphp sqlite libapache2-mod-php5 php-pear php5-curl php5-sqlite php5-mysql 

2. Install the following pear packages
  
  sudo pear install config_lite-0.2.1

3. Install the Lazy Web-UI

  Extract the lazy-ui.tar.gz file into /var/www/media
  
4. Change owner to media:media

  sudo chown -R media:media /var/www/media
  

Lazy-UI Configuration
====

First make sure the config file is correct

1. Edit /var/www/media/includes/functions.php and change $config::loadConfig to the right lazy config file.

2. Enable suPhp

  sudo a2enmod suphp
  


Thats it your done.. now go to http://serverip/media
