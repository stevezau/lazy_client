#!/bin/bash
SCRIPT=$(readlink -f $0)
BASE_PATH=`dirname $SCRIPT`
MANAGE_SCRIPT="$BASE_PATH/manage.py"

chmod +x $MANAGE_SCRIPT

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

case $1 in
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
      echo "usage: start|stop [celeryd|celerybeat|webui]"
	;;
esac

