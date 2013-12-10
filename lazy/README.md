Install procedure Ubuntu Natty 11.04

#install EVRouter
wget http://debian.bedroomlan.org/debian/pool/main/e/evrouter/evrouter_0.4_amd64.deb
sudo dpkg -i evrouter_0.4_amd64.deb 

#Install Mythtv
wget http://www.mythbuntu.org/files/mythbuntu-repos.deb
sudo dpkg -i mythbuntu-repos.deb 
sudo apt-get update
sudo apt-get install mythtv-frontend mythtv-backend pwgen


#Install XBMC
##sudo add-apt-repository ppa:team-xbmc/ppa
sudo apt-add-repository ppa:nathan-renniewaldock/xbmc-stable
sudo apt-get update
sudo apt-get install xbmc

# Lazy setup
sudo apt-get install unrar cksfv python-dev python-setuptools libxml2 libxml2-dev libxslt1.1 libxslt1-dev python-formencode lftp sqlite xinit libsqlite3-0 sqlite3 
easy_install flexget IMDBpy IPy pexpect easy_extract

#Install Nvidia driver
download from net and install
http://us.download.nvidia.com/XFree86/Linux-x86_64/295.59/NVIDIA-Linux-x86_64-295.59.run

#install xrdp and others 
sudo apt-get install xrdp mingetty screen vim phpmyadmin libapache2-mod-suphp suphp-common mysql-server

#do hdd setup
mhddfs 

##################################
####Change /etc/init/tty1.conf####
##################################
# tty1 - getty
#
# This service maintains a getty on tty1 from the point the system is
# started until it is shut down again.

start on stopped rc RUNLEVEL=[2345]
stop on runlevel [!2345]

respawn
exec /sbin/mingetty --autologin xbmc tty1
#exec /sbin/getty 38400 tty1

#######################################################
####/etc/udev/rules.d/65-persistent-hauppauge.rules####
#######################################################
SUBSYSTEM=="input", KERNEL=="event*", ATTRS{idVendor}=="2040", ATTRS{idProduct}=="8400", SYMLINK+="lirc0"

#########################################
####/etc/udev/rules.d/99.input.rules ####
#########################################
KERNEL=="event*",       NAME="input/%k", MODE:="660", GROUP="input"
KERNEL=="js*",          NAME="input/%k", MODE:="664", GROUP="input"
KERNEL=="rtc0", GROUP="audio"

####################################
####SETUP FLEXGET.. ####
####################################



####################################
####xxx####
####################################




#Final step to make sure its all up-to-date
sudo apt-get update && sudo apt-get upgrade
