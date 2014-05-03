__author__ = 'steve'
import guessit
from django.conf import settings
import re
from flexget.utils.qualities import Quality

class MetaParser():

    TYPE_TVSHOW = 1
    TYPE_MOVIE = 2
    TYPE_UNKNOWN = 3

    title = ""
    details = []
    type = 3
    quality = None

    def __init__(self, title, type=TYPE_UNKNOWN):
        self.title = title
        self.type = type

        if self.type == self.TYPE_UNKNOWN:
            type = guessit.guess_file_info(title)
            if type['type'] == "episode":
                self.type = self.TYPE_TVSHOW
            elif type['type'] == "movie":
                self.type = self.TYPE_MOVIE

        self.details = self.get_details()
        self.quality = Quality(title)

    def get_season(self):
        seasons = self.get_seasons()

        if len(seasons) == 1:
            return seasons[0]

    def get_seasons(self):
        details = self.get_details()

        found_seasons = []

        if 'season' in details:
            found_seasons.append(int(details['season']))

        if 'seasonList' in details:
            for ep in details['seasonList']:
                found_seasons.append(int(ep))

        return found_seasons

    def get_eps(self):
        details = self.get_details()

        found_eps = []

        if 'episodeNumber' in details:
            found_eps.append(int(details['episodeNumber']))

        if 'episodeList' in details:
            for ep in details['episodeList']:
                found_eps.append(int(ep))

        return found_eps

    def get_details(self):

        from lazycore.utils import common

        if len(self.details) > 0:
            return self.details

        doco_channel = None

        #Set to TVSHOW if its a doco
        for doco_check in settings.DOCO_REGEX:
            regex = doco_check['regex']
            match = re.search(regex, self.title)

            if match:
                doco_channel = doco_check['name']
                self.type = self.TYPE_TVSHOW
                self.title = self.title.replace(match.group(1), "")
                break

        if self.type == self.TYPE_TVSHOW:
            self.details = guessit.guess_episode_info(self.title)

            if not 'special' in self.details:
                #we also need to determine if this is a season_pack
                if common.match_str_regex(settings.TVSHOW_SEASON_MULTI_PACK_REGEX, self.title):
                    self.details['type'] = "season_pack_multi"

                    for regex in settings.TVSHOW_SEASON_MULTI_PACK_REGEX:
                        multi = re.search(regex, self.title)

                        if multi:
                            #now lets get the seasons
                            start_season = int(multi.group(1))
                            end_season = int(multi.group(2))

                            seasons = []

                            for season_no in range(start_season, end_season + 1):
                                seasons.append(int(season_no))

                            self.details['seasonList'] = seasons
                            break

                elif common.match_str_regex(settings.TVSHOW_SEASON_PACK_REGEX, self.title):
                    self.details['type'] = "season_pack"

            if doco_channel:
                self.details['doco_channel'] = doco_check['name']

            return self.details

        elif self.type == self.TYPE_MOVIE:
            self.details = guessit.guess_movie_info(self.title)

            if common.match_str_regex(settings.MOVIE_PACKS_REGEX, self.title):
                self.details['type'] = "movie_pack"

            return self.details
        else:
            self.details = guessit.guess_video_info(self.title)
            return self.details
