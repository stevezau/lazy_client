from django import forms
from lazycore.models import TVShowMappings
from django.conf import settings
import os, logging
from lazycore.models import DownloadItem

logger = logging.getLogger(__name__)

class DynamicChoiceField(forms.ChoiceField):
    def clean(self, value):
        return value


class AddTVMapForm(forms.ModelForm):
    title = forms.CharField(label="TVShow Title")
    tvdbid_display = forms.CharField(label="Search TheTVDB.com")
    tvdbid_id = forms.IntegerField(widget=forms.HiddenInput)


    class Meta:
        model = TVShowMappings
        fields = ('title', 'tvdbid_display', 'tvdbid_id')


class DownloadItemManualFixForm(forms.ModelForm):
    class Meta:
        model = DownloadItem
        fields = ('tvdbid_display', 'tvdbid_id', 'seasonoverride', 'epoverride')

    tvdbid_display = forms.CharField(label="Showname (TVDB.com)")
    tvdbid_id = forms.IntegerField(widget=forms.HiddenInput)
    seasonoverride = DynamicChoiceField(widget=forms.Select, label="Season")
    epoverride = DynamicChoiceField(widget=forms.Select, label="Ep")

    def __init__(self, *args, **kwargs):
        super(DownloadItemManualFixForm, self).__init__(*args, **kwargs)

        #First lets see if we can find the TVDBID

        if self.instance.tvdbid:
            self.fields['tvdbid_id'].initial = self.instance.tvdbid.id
            self.fields['tvdbid_display'].initial = self.instance.tvdbid.title

            #set the seasons
            try:
                tvdb_seasons = self.instance.tvdbid.get_seasons()
            except:
                return

            if len(tvdb_seasons) > 0:
                seasons = []
                seasons.append(('Select Season', 'Select Season'))

                for season in tvdb_seasons:
                    seasons.append((str(season), str(season)))

                self.fields['seasonoverride'].choices = seasons

                if self.instance.seasonoverride >= 0:
                    self.fields['seasonoverride'].initial = [self.instance.seasonoverride]

                    if self.instance.epoverride > 0:
                        #lets set the eps as well
                        tvdb_eps = self.instance.tvdbid.get_eps(int(self.instance.seasonoverride))

                        if len(tvdb_eps) > 0:
                            eps = []
                            eps.append(('Select Ep', 'Select Ep'))

                            for ep in tvdb_eps:
                                eps.append((str(ep), str(ep)))

                            self.fields['epoverride'].choices = eps
                            self.fields['epoverride'].initial = [self.instance.epoverride]



class AddApprovedShow(forms.Form):
    tvdbid_display = forms.CharField(label="Search TheTVDB.com")
    tvdbid_id = forms.IntegerField(widget=forms.HiddenInput)

    class Meta:
        fields = ('tvdbid_display', 'tvdbid_id')


class AddIgnoreShow(forms.Form):
    show_name = forms.CharField(label="Enter the full TV Show name to ignore")

    class Meta:
        fields = ('show_name')


class Find(forms.Form):
    search = forms.CharField(label="Enter item to search")

    class Meta:
        fields = ('search')


class FindMissing(forms.Form):
    tvshow = forms.ChoiceField(label="Select TV Show to find missing episodes", choices=(), widget=forms.Select(attrs={'class':'selector'}))

    def __init__(self, *args, **kwargs):
        super(FindMissing, self).__init__(*args, **kwargs)

        choices = []
        dirs = os.listdir(settings.TVHD)

        for dir in dirs:
            if os.path.isdir(os.path.join(settings.TVHD, dir)):
                choice = (dir, dir)
                choices.append(choice)

        self.fields['tvshow'].choices = choices

    class Meta:
        fields = ('search')