#!/usr/bin/env bash
ARGS="$@"
SCRIPT=$0
BASE_PATH=`dirname $SCRIPT`
RED='\e[0;31m'
NC='\e[0m' # No Color

cd $BASE_PATH

MANAGE_SCRIPT="$BASE_PATH/manage.py"
WEBUI_PID_FILE="lazy_web_server.pid"
CELERYD_PID_FILE="celeryd.pid"
CELERYBEAT_PID_FILE="celeryd_beat.pid"

export C_FORCE_ROOT="true"

chmod +x $MANAGE_SCRIPT

function upgrade {
    pull_git
    upgrade_reqs
    $MANAGE_SCRIPT $ARGS
}

function pull_git() {
    /usr/bin/env git pull

    if [ "$?" == "0" ]; then
        echo "Pulled latest from git"
    else
        echo -e "${RED}Error pulling from git${NC}"
        exit 1
    fi

}

function upgrade_reqs() {
    #First we need to install all the requirements
    if [ "$UID" == "0" ]; then
        /usr/bin/env pip install -r "requirements.txt"
        /usr/bin/env easy_install --upgrade http://drifthost.com/lazy_common-0.1-py2.7.egg
    else
        /usr/bin/env sudo /usr/bin/env pip install -r "requirements.txt"
        /usr/bin/env sudo /usr/bin/env easy_install --upgrade http://drifthost.com/lazy_common-0.1-py2.7.egg
    fi

    if [ "$?" == "0" ]; then
        echo "Installed requirements"
    else
        echo -e "${RED}Error installing requirements${NC}"
        exit 1
    fi

}

function setup {
    upgrade_reqs
    $MANAGE_SCRIPT setup
}

function start_all {
	start_lazy_webui
	start_celeryd
	start_celerybeat
}

function stop_all {
	stop_lazy_webui
	stop_celeryd
	stop_celerybeat
}

function start_lazy_webui {
	echo "Starting Lazy WebUI"
	$MANAGE_SCRIPT webui start > /dev/null 2>&1 &
}

function stop_lazy_webui {
	$MANAGE_SCRIPT webui stop
}

function start_celeryd {
	echo "Starting Celeryd"
	PID_FILE="celeryd.pid"
	LOG_FILE="logs/celeryd.log"
	$MANAGE_SCRIPT celeryd --loglevel=DEBUG --concurrency=4 -Ofair --pidfile=$PID_FILE  -f $LOG_FILE > /dev/null 2>&1 &
}

function stop_celeryd {
	$MANAGE_SCRIPT jobserver stop
}

function start_celerybeat {
	echo "Starting Celery Beat"
	PID_FILE="celeryd_beat.pid"
	LOG_FILE="logs/celery_beat.log"
	SCHEDULE_FILE="celerybeat-schedule"
	$MANAGE_SCRIPT celerybeat --pidfile=$PID_FILE  -f $LOG_FILE --schedule=$SCHEDULE_FILE > /dev/null 2>&1 &
}

function stop_celerybeat {
	$MANAGE_SCRIPT jobserver stop_beat
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
    #First lets check if WebUI is running
    check_pid $WEBUI_PID_FILE
    if [ "$PID_RUNNING" == "false" ]; then
        echo "WebUI was not running"
        start_lazy_webui
    fi

    #second lets check if celerybeat is running
    check_pid $CELERYBEAT_PID_FILE
    if [ "$PID_RUNNING" == "false" ]; then
        echo "Celery Beat was not running"
        start_celerybeat
    fi


    #third lets check if celeryd is running
    check_pid $CELERYD_PID_FILE
    if [ "$PID_RUNNING" == "false" ]; then
        echo "CeleryD was not running"
        start_celeryd
    fi

}

case $1 in
    upgrade)
        upgrade
        ;;
    setup)
        setup
        ;;
    restart)
        stop_all
        start_all
        ;;
    check)
        check_running
        ;;
	start)
		case $2 in
			celeryd)
				start_celeryd
				;;
			celerybeat)
				start_celerybeat
				;;
			webui)
				start_lazy_webui
				;;
			*)
				start_all
 				;;
        	esac
      	;;
	stop)
		case $2 in
			celeryd)
				stop_celeryd
				;;
			celerybeat)
				stop_celerybeat
				;;
			webui)
				stop_lazy_webui
				;;
			*)
				stop_all
   				;;
		esac
	;;
    *)
      echo "usage: start|stop|check|upgrade [celeryd|celerybeat|webui]"
	;;
esac


