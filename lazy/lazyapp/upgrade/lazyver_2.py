__author__ = 'steve'

def upgrade():
    from django.core.cache import cache
    cache.clear()

