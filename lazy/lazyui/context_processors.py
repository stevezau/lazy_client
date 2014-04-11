__author__ = 'steve'
from lazycore.utils import common

# The context processor function
def errors(request):

    errors = common.get_lazy_errors()

    if len(errors) == 0:
        errors = ""

    return {
        'lazy_errors': errors,
    }
