#!/usr/bin/env bash

LAZY_HOME="/opt/lazy"

FLEXGET_BIN="/opt/../Python/bin/flexget"

cd $LAZY_HOME

FLEXGET_HOME="$LAZY_HOME/.flexget"
FLEXGET_HOME_ADMIN="/root/.flexget"
FLEXGET_ROOT_FOLDER="/share/homes/admin/.flexget"
TVDB_TMP_FOLDER = "$LAZY_HOME/tvdb_api-u0"

#First setup symlinks and create folders
if [ ! -e "$FLEXGET_HOME_ADMIN" ]; then
	ln -s $FLEXGET_HOME $FLEXGET_HOME_ADMIN
fi

if [ ! -e "$FLEXGET_ROOT_FOLDER" ]; then
	ln -s $FLEXGET_HOME $FLEXGET_ROOT_FOLDER
fi

if [ ! -e "$TVDB_TMP_FOLDER" ]; then
	mkdir $TVDB_TMP_FOLDER
fi

if [ ! -h "/tmp/tvdb_api-u0" ]; then
    rm -rf /tmp/tvdb_api-u0
	ln -s $TVDB_TMP_FOLDER /tmp/tvdb_api-u0
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

