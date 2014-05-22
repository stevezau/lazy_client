#!/usr/bin/env bash
SCRIPT=$0
BASE_PATH=`dirname $SCRIPT`
MANAGE_SCRIPT="$BASE_PATH/manage.py"

WEBUI_PID_FILE="$BASE_PATH/lazy_web_server.pid"
CELERYD_PID_FILE="$BASE_PATH/celeryd.pid"
CELERYBEAT_PID_FILE="$BASE_PATH/celeryd_beat.pid"

export C_FORCE_ROOT="true"

chmod +x $MANAGE_SCRIPT

function upgrade {
    $MANAGE_SCRIPT upgrade
}

function setup {
    #First we need to install all the requirements
    if [ "$UID" == "0" ]; then
        /usr/bin/env pip install -r "$BASE_PATH/requirements.txt"
    else
        /usr/bin/env sudo /usr/bin/env pip install -r "$BASE_PATH/requirements.txt"
    fi

    if [ "$?" == "0" ]; then
        echo "Installed requirements"
    else
        echo "Error installing requirements"
        exit 1
    fi

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
	PID_FILE="$BASE_PATH/celeryd.pid"
	LOG_FILE="$BASE_PATH/logs/celeryd.log"
	$MANAGE_SCRIPT celeryd --loglevel=DEBUG --concurrency=4 -Ofair --pidfile=$PID_FILE  -f $LOG_FILE > /dev/null 2>&1 &
}

function stop_celeryd {
	$MANAGE_SCRIPT jobserver stop
}

function start_celerybeat {
	echo "Starting Celery Beat"
	PID_FILE="$BASE_PATH/celeryd_beat.pid"
	LOG_FILE="$BASE_PATH/logs/celery_beat.log"
	SCHEDULE_FILE="$BASE_PATH/celerybeat-schedule"
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
      echo "usage: start|stop|check [celeryd|celerybeat|webui]"
	;;
esac

