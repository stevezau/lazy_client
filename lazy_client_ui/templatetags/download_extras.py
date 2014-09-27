from django import template
from django.template.defaultfilters import stringfilter


register = template.Library()

@register.filter(name='progressbar_color')
def progressbar_color(percent):
    if percent > 90:
        return "danger"
    if percent > 70:
        return "warning"

    return "success"

@register.filter(name='progressbar_reverse_color')
def progressbar_reverse_color(percent):

    if percent > 85:
        return "success"
    if percent > 60:
        return "warning"

    return "danger"


@register.filter(name='get_ep_season')
def get_ep_season(dlitem):

    text = ""

    season = dlitem.get_season()
    eps = dlitem.get_eps()

    if season > 0 and len(eps) > 0:
        text += "Season %s ep" % season

        for ep in eps:
            text += " %s" % ep
    else:
        parser = dlitem.metaparser()
        if 'date' in parser.details:
            text += " %s" % parser.details['date'].strftime('%m.%d.%Y')

    return text


@register.filter(name='format_torrent_title')
def format_torrent_title(title):
    from lazy_common import metaparser
    parser = metaparser.get_parser_cache(title)

    title = ""

    series = False

    if 'doco_channel' in parser.details:
        title += "%s: " % parser.details['doco_channel']

    if 'series' in parser.details:
        title += parser.details['series']
        series = True

    if 'title' in parser.details:
        if series:
            title += ": %s" % parser.details['title']
        else:
            title += " %s" % parser.details['title']

    if 'date' in parser.details:
        title += " %s" % parser.details['date'].strftime('%m.%d.%Y')

    return title


@register.filter
def truncatesmart(value, limit=80):
    """
    Truncates a string after a given number of chars keeping whole words.

    Usage:
        {{ string|truncatesmart }}
        {{ string|truncatesmart:50 }}
    """

    try:
        limit = int(limit)
    # invalid literal for int()
    except ValueError:
        # Fail silently.
        return value

    # Make sure it's unicode
    value = unicode(value)

    # Return the string itself if length is smaller or equal to the limit
    if len(value) <= limit:
        return value

    # Cut the string
    value = value[:limit]

    # Break into words and remove the last
    words = value.split(' ')[:-1]

    # Join the words and return
    return ' '.join(words) + '...'