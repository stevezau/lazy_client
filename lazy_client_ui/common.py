__author__ = 'steve'
from importlib import import_module
import logging

logger = logging.getLogger(__name__)

def load_button_module(package, fn):
    try:
        mod = import_module(package)
        function = getattr(mod, fn)
        return function
    except Exception as e:
        logger.exception(e)
        raise Exception(e)


