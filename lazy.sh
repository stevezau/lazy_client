#!/usr/bin/env bash
ARGS="$@"
SCRIPT=$0
pushd `dirname $0` > /dev/null
BASE_PATH=`pwd -P`
popd > /dev/null

RED='\e[0;31m'
NC='\e[0m' # No Color

PATH="$PATH:/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin"

cd $BASE_PATH

MANAGE_SCRIPT="$BASE_PATH/manage.py"
LAZY_PID="$BASE_PATH/lazy.pid"

FLEXGET_BIN="env flexget"
GIT_BIN="env git"
PIP_BIN="env pip"
FLEXGET_HOME="$HOME/.flexget/"

chmod +x $MANAGE_SCRIPT

if [ -f "/proc/sysinfo" ] && grep -q "QNAP" /proc/sysinfo; then
    export C_FORCE_ROOT="true"
    GIT_BIN="/opt/bin/git"
    FLEXGET_BIN="/opt/../Python/bin/flexget"

    FLEXGET_HOME="$BASE_PATH/.flexget"
    FLEXGET_HOME_ADMIN="/root/.flexget"
    TVDB_TMP_FOLDER="$BASE_PATH/tvdb_api-u0"
    PIP_BIN="/share/MD0_DATA/.qpkg/Python/bin/pip-2.7"
    PIP_BUILD="/tmp/pip-build"
    PIP_BUILD_TEMP="$BASE_PATH/pip-build"

    #First setup symlinks and create folders
    if [ ! -e "$FLEXGET_HOME_ADMIN" ]; then
        echo -e "ln -s $FLEXGET_HOME $FLEXGET_HOME_ADMIN"
        ln -s $FLEXGET_HOME $FLEXGET_HOME_ADMIN
    fi

    if [ ! -e "$TVDB_TMP_FOLDER" ]; then
        mkdir $TVDB_TMP_FOLDER
    fi

    if [ ! -h "/tmp/tvdb_api-u0" ]; then
        rm -rf /tmp/tvdb_api-u0
        ln -s $TVDB_TMP_FOLDER /tmp/tvdb_api-u0
    fi

    if [ ! -e "$PIP_BUILD_TEMP" ]; then
        mkdir $PIP_BUILD_TEMP
    fi

    if [ ! -h $PIP_BUILD ]; then
        rm -rf $PIP_BUILD
        ln -s $PIP_BUILD_TEMP $PIP_BUILD
    fi
fi


function upgrade {
    if [ "$2" != "-l" ]; then
        pull_git
    fi
    $MANAGE_SCRIPT migrate
    $MANAGE_SCRIPT $ARGS
}

function flexget() {
    $FLEXGET_BIN -c $FLEXGET_HOME/config-xvid.yml execute
    $FLEXGET_BIN execute --disable-tracking
}

function pull_git() {
    $GIT_BIN pull

    if [ "$?" == "0" ]; then
        echo "Pulled latest from git"
    else
        echo -e "${RED}Error pulling from git${NC}"
        exit 1
    fi

}

function setup {
    $MANAGE_SCRIPT setup
}


function start {
        echo "Starting Lazy"
        $MANAGE_SCRIPT lazy start > /dev/null 2>&1 &
}

function stop {
        $MANAGE_SCRIPT lazy stop
}

function check_pid() {
    PID_FILE=$1

    if [ -f $PID_FILE ]; then
        PID=`cat $PID_FILE`
        if [ -f /proc/$PID/exe ]; then
            PID_RUNNING="true"
        else
            PID_RUNNING="false"
        fi
    else
        PID_RUNNING="false"
    fi
}


function check_running {
    check_pid $LAZY_PID
    if [ "$PID_RUNNING" == "false" ]; then
        echo "Lazy was not running"
        start
    fi

}

case $1 in
    upgrade)
        upgrade
        ;;
    setup)
        setup
        ;;
    flexget)
        flexget
        ;;
    restart)
        stop
        start
        ;;
    check)
        check_running
        ;;
        start)
            start
        ;;
        stop)
            stop
        ;;
    *)
      echo "usage: start|stop|check|flexget|upgrade"
        ;;
esac


