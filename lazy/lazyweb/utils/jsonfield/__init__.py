import os
__version__ = open(os.path.join(os.path.dirname(__file__),'VERSION')).read().strip()

try:
    from lazyweb.utils.jsonfield.fields import JSONField
except ImportError:
    pass