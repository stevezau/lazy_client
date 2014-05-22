#!/usr/bin/env bash

LAZY_HOME="/opt/lazy"
FLEXGET_BIN="/share/CACHEDEV1_DATA/.qpkg/Python/bin/flexget"

cd $LAZY_HOME

FLEXGET_HOME="$LAZY_HOME/.flexget"
FLEXGET_HOME_ADMIN="/root/.flexget"
FLEXGET_ROOT_FOLDER="/share/homes/admin/.flexget"

#First setup symlinks
if [ ! -e "$FLEXGET_HOME_ADMIN" ]; then
	ln -s $FLEXGET_HOME $FLEXGET_HOME_ADMIN
fi

if [ ! -e "$FLEXGET_ROOT_FOLDER" ]; then
	ln -s $FLEXGET_HOME $FLEXGET_ROOT_FOLDER
fi


#Check lazy running
if [ "$1" == "check" ]; then
	$LAZY_HOME/lazy.sh check
fi

#Run flexget
if [ "$1" == "runflex" ]; then
	$FLEXGET_BIN -c /root/.flexget/config-xvid.yml execute --cron
	$FLEXGET_BIN execute --disable-advancement --cron
fi

