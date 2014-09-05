from django import template
from django.template.defaultfilters import stringfilter


register = template.Library()

@register.filter(name='format_torrent_title')
def format_torrent_title(title):
    from lazy_common import metaparser
    parser = metaparser.get_parser_cache(title)

    if 'title' in parser.details:
        title = parser.details['title']

    if 'series' in parser.details:
        title = parser.details['series']

    return title

