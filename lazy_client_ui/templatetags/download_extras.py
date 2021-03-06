from django import template
from django.utils import timezone

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

    seasons = dlitem.get_seasons()
    eps = dlitem.get_eps()

    if len(seasons) > 0 or len(eps) > 0:
        if len(seasons) == 1:
            text += "Season %s" % seasons[0]
        if len(seasons) > 1:
            text += "Seasons "
            for season in seasons:
                text += "%s," % season
            text.rstrip(",")

        if len(eps) == 1:
            text += " Ep %s" % eps[0]
        if len(eps) > 1:
            text += " Eps "
            for ep in eps:
                text += "%s," % ep
            text.rstrip(",")
    else:
        parser = dlitem.metaparser()
        if 'date' in parser.details:
            text += " %s" % parser.details['date'].strftime('%m.%d.%Y')

    return text

@register.inclusion_tag('manage/tvshows/tvshow_next_aired.html')
def tvshow_next_aired(tvshow):
    next_ep = tvshow.get_next_ep()

    if next_ep:
        return {"season": next_ep.season.season, "ep": next_ep.epsiode, "title": next_ep.title, "date": next_ep.aired}

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


@register.filter
def timesince2(d, now=None, reversed=False):
    import datetime
    from django.utils.html import avoid_wrapping
    from django.utils.timezone import is_aware, utc
    from django.utils.translation import ugettext, ungettext_lazy

    chunks = (
        (60 * 60 * 24 * 365, ungettext_lazy('%d year', '%d years')),
        (60 * 60 * 24 * 30, ungettext_lazy('%d month', '%d months')),
        (60 * 60 * 24 * 7, ungettext_lazy('%d week', '%d weeks')),
        (60 * 60 * 24, ungettext_lazy('%d day', '%d days')),
        (60 * 60, ungettext_lazy('%d hour', '%d hours')),
        (60, ungettext_lazy('%d minute', '%d minutes'))
    )
    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    if not now:
        now = datetime.datetime.now(utc if is_aware(d) else None)

    delta = (d - now) if reversed else (now - d)
    # ignore microseconds
    since = delta.days * 24 * 60 * 60 + delta.seconds

    if since == 0:
        return "Today"

    if since == 86400:
        return "Tomorrow"

    if since <= 0:
        # d is in the future compared to now, stop processing.
        return avoid_wrapping(ugettext('0 minutes'))
    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break
    result = avoid_wrapping(name % count)
    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        count2 = (since - (seconds * count)) // seconds2
        if count2 != 0:
            result += ugettext(', ') + avoid_wrapping(name2 % count2)
    return result

@register.filter
def timeuntil2(d, now=None):
    """
    Like timesince, but returns a string measuring the time until
    the given time.
    """
    return timesince2(d, now, reversed=True)