#!/usr/bin/python2.7
import argparse
import logging
import sys

from lazy.includes.exceptions import LazyError
from lazy.includes.manager import Manager
from lazy.includes import functions

logger = logging.getLogger('lazy')

# Parser
parser = argparse.ArgumentParser(add_help=False, conflict_handler='resolve')

# Args
parser.add_argument('-v', action='store_true', dest='debug', help='Run debug logging')
parser.add_argument('-l', action='store', dest='logFile', help='Log file')
parser.add_argument('-c', action='store', dest='configFile', help='Config file')
parser.add_argument('-h', action='store_true', dest='helpAction', help='Display help, include action for help on action')
parser.add_argument('action',  nargs='?', action='store',  help='Program to run')
parser.add_argument('--list', action='store_true', dest='listActions', help='List Actions')
parser.add_argument('--database', action='store', dest='database', help='Database file')


def main():
    # First lets parse the command line args
    resultArgs = parser.parse_known_args()

    mainArgs = resultArgs[0]
    actionArgs = resultArgs[1]

    # Check a few things
    if mainArgs.action:
        action = mainArgs.action.lower()
    else:
        parser.print_help()
        sys.exit(1)

    #Now check if compoment exists
    try:
        manager = Manager(mainArgs)
        logger.debug("trying to load module: " + action)
        module = __import__('actions.' + action, globals(), locals(), [action])
        actionClass = getattr(module, action)
        logger.debug("Loaded module: " + action)
    except (LazyError) as e:
        logger.exception(e)
        sys.exit(e.id)
    except (ImportError, AttributeError) as e:
        logger.exception(e)
        logger.error(e.message)
        sys.exit(1)

    # Setup action object and check parms
    logger.debug("Starting action: " + action)
    actionObj = actionClass(parser)

    #Offload rest of processing to the action object
    try:
        actionObj.execute()
        functions.removePidFile(action)
    except LazyError as e:
        logger.error(e.message)
        sys.exit(e.id)
