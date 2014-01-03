from django import forms
from lazyweb.models import TVShowMappings
from django.conf import settings
import os

class AddTVMapForm(forms.ModelForm):
    title = forms.CharField(label="TVShow Title")
    tvdbid_display = forms.CharField(label="Search TheTVDB.com")
    tvdbid_id = forms.IntegerField(widget=forms.HiddenInput)


    class Meta:
        model = TVShowMappings
        fields = ('title', 'tvdbid_display', 'tvdbid_id')


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