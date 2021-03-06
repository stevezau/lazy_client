import os
import logging

from django import forms
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from lazy_client_core.models import TVShowMappings
from lazy_common import metaparser
from lazy_client_core.models import TVShow
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, MultiField
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions, StrictButton
from crispy_forms.bootstrap import InlineField


logger = logging.getLogger(__name__)

TYPE_CHOICES = (
    (metaparser.TYPE_UNKNOWN, "Select Type"),
    (metaparser.TYPE_TVSHOW, 'TVShow'),
    (metaparser.TYPE_MOVIE, 'Movie'),
)

class DynamicChoiceField(forms.ChoiceField):
    def clean(self, value):
        return value

def validate_ep_season(self, value):
    int_field = forms.IntegerField()
    int_field.validate(value)


class AddTVMapForm(forms.ModelForm):
    title = forms.CharField(label="TVShow Title")
    tvdbid_display = forms.CharField(label="Search TheTVDB.com")
    tvdbid_id = forms.IntegerField(widget=forms.HiddenInput)


    class Meta:
        model = TVShowMappings
        fields = ('title', 'tvdbid_display', 'tvdbid_id')


class DownloadItemManualFixForm(forms.Form):

    current_field_i = 0

    #TODO Improve this
    def is_valid(self):

        i = 0
        #Remove invalid fields
        for vid_fields in self.get_vid_fields():
            type_dict_name = '%s_type' % i

            if type_dict_name in self.data:
                type = self.data[type_dict_name]

                self.fields[type_dict_name].validate(type)

                int_type = int(type)

                if int_type == metaparser.TYPE_TVSHOW:
                    #lets remove all imdb fields..
                    for name in vid_fields:
                        if 'imdbid' in name:
                            #lets remove it
                            del_name = "%s_%s" % (i, name)
                            del self.fields[del_name]

                elif int_type == metaparser.TYPE_MOVIE:
                    for name in vid_fields:
                        if 'tvdbid' in name:
                            #lets remove it
                            del_name = "%s_%s" % (i, name)
                            del self.fields[del_name]
            i += 1

        return super(DownloadItemManualFixForm, self).is_valid()

    def get_vid_fields(self):

        vid_fields = []
        i = 0

        for vid_file in self.object.video_files:
            vid_fields_current = {}

            for name in self.fields:
                if name.startswith('%s_' % i):
                    vid_fields_current[name.replace("%s_" % i, "")] = self[name]

            vid_fields.append(vid_fields_current)
            i += 1

        return vid_fields

    def __init__(self, *args, **kwargs):
        self.object = kwargs.pop('download_item')
        super(DownloadItemManualFixForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_class = 'form-inline manualfix'
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.error_text_inline = True
        self.helper.help_text_inline = False
        self.helper.form_method = "POST"
        self.helper.form_show_labels = False

        type = self.object.get_type()

        video_files = self.object.video_files

        self.helper.layout = Layout()

        if video_files:
            for i, video_file in enumerate(video_files):
                self.fields['%s_type' % i] = forms.ChoiceField(choices=TYPE_CHOICES)
                self.fields['%s_video_file' % i] = forms.CharField(widget=forms.HiddenInput)

                self.fields['%s_video_file' % i].initial = os.path.basename(video_file['file'])
                self.fields['%s_type' % i].initial = type

                #TVShow Fields
                self.fields['%s_tvdbid_id' % i] = forms.CharField(widget=forms.HiddenInput)
                self.fields['%s_tvdbid_display' % i] = forms.CharField()
                self.fields['%s_tvdbid_display' % i].label = None
                self.fields['%s_tvdbid_season_override' % i] = DynamicChoiceField(validators=[validate_ep_season])
                self.fields['%s_tvdbid_ep_override' % i] = DynamicChoiceField(validators=[validate_ep_season])

                #Movie Fields
                self.fields['%s_imdbid_id' % i] = forms.CharField(widget=forms.HiddenInput)
                self.fields['%s_imdbid_display' % i] = forms.CharField()

                self.helper.layout.extend([
                    Div(
                        HTML("<div class='panel-heading'><strong>File:</strong> %s</div>" % video_file['file'].replace(self.object.localpath, "").lstrip("/")),
                        Div(
                            '%s_type' % i,
                            '%s_video_file' % i,
                            '%s_tvdbid_id' % i,
                            Field('%s_tvdbid_display' % i, placeholder="Enter TVShow Name"),
                            '%s_tvdbid_season_override' % i,
                            '%s_tvdbid_ep_override' % i,
                            '%s_imdbid_id' % i,
                            Field('%s_imdbid_display' % i, placeholder="Enter Movie Name"),
                            css_class="panel-body",
                        ),
                        css_class="panel panel-info",
                        css_id="file_%s" % i
                    )
                ])

            self.helper.layout.extend([
                Div(
                    Submit('Submit', 'Submit'),
                    Button('Back', 'Back', css_class="btn-primary", onclick="window.history.back()"),
                    css_class="center-block text-center"
                )
            ])

            parser = self.object.metaparser()

            #Pre-populate movie fields
            if 'type' in parser.details and parser.details['type'] == "movie" and self.object.imdbid:
                for i, video_file in enumerate(video_files):
                    self.fields['%s_imdbid_id' % i].initial = self.object.imdbid.id
                    self.fields['%s_imdbid_display' % i].initial = self.object.imdbid.title

            #Pre-populate tvshow fields
            if self.object.tvdbid:
                if 'type' in parser.details and parser.details['type'] == "episode":
                    self.fields['%s_tvdbid_id' % i].initial = self.object.tvdbid.id
                    self.fields['%s_tvdbid_display' % i].initial = self.object.tvdbid.title

                for i, video_file in enumerate(video_files):
                    self.fields['%s_tvdbid_id' % i].initial = self.object.tvdbid.id
                    self.fields['%s_tvdbid_display' % i].initial = self.object.tvdbid.title

                    if 'tvdbid_id' in video_file:
                        try:
                            tvdb_obj = TVShow.objects.get(id=int(video_file['tvdbid_id']))

                            self.fields['%s_tvdbid_id' % i].initial = tvdb_obj.id
                            self.fields['%s_tvdbid_display' % i].initial = tvdb_obj.title
                        except ObjectDoesNotExist:
                            pass

                    #set the seasons
                    tvdb_seasons = self.object.tvdbid.get_seasons()

                    if len(tvdb_seasons) > 0:
                        seasons = []
                        seasons.append(('Select Season', 'Select Season'))

                        for season_obj in tvdb_seasons:
                            if season_obj.season == 0:
                                seasons.append((str(season_obj.season), "Specials"))
                            else:
                                seasons.append((str(season_obj.season), "Season %s" % season_obj.season))

                        self.fields['%s_tvdbid_season_override' % i].choices = seasons

                        if 'season_override' in video_file and video_file['season_override'] >= 0:
                            season = video_file['season_override']
                            self.fields['%s_tvdbid_season_override' % i].initial = season

                            if 'ep_override' in video_file and video_file['ep_override'] >= 0:
                                #lets set the eps as well
                                ep_override = video_file['ep_override']
                                tvdb_eps = self.object.tvdbid.get_eps(int(season), xem=False)

                                if len(tvdb_eps) > 0:
                                    eps = []
                                    eps.append(('Select Ep', 'Select Ep'))

                                    for ep in tvdb_eps:
                                        eps.append((str(ep), "Ep - %s " % ep))

                                    self.fields['%s_tvdbid_ep_override' % i].choices = eps
                                    self.fields['%s_tvdbid_ep_override' % i].initial = ep_override

class AddApprovedShow(forms.Form):
    tvdbid_display = forms.CharField(label="Search TheTVDB.com")
    tvdbid_id = forms.IntegerField(widget=forms.HiddenInput)

    class Meta:
        fields = ('tvdbid_display', 'tvdbid_id')


class AddIgnoreShow(forms.Form):
    show_name = forms.CharField(label="Enter the full TV Show name to ignore")

    class Meta:
        fields = ('show_name')



class FindMissing(forms.Form):
    tvshow = forms.ChoiceField(label="Select TV Show to find missing episodes", choices=(), widget=forms.Select(attrs={'class':'selector'}))

    def __init__(self, *args, **kwargs):
        super(FindMissing, self).__init__(*args, **kwargs)

        choices = []
        dirs = os.listdir(settings.TV_PATH)

        for dir in dirs:
            if os.path.isdir(os.path.join(settings.TV_PATH, dir)):
                choice = (dir, dir)
                choices.append(choice)

        self.fields['tvshow'].choices = choices

    class Meta:
        fields = ('search')


class Find(forms.Form):

    def __init__(self, *args, **kwargs):
        super(Find, self).__init__(*args, **kwargs)
        # Uni-form
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.error_text_inline = True
        self.helper.help_text_inline = False
        self.helper.form_method = "GET"
        self.helper.layout = Layout(
            'search',
            StrictButton('Search', type="submit", spinner="tiny", css_class='btn-primary'),
        )

    search = forms.CharField(label="Search", max_length=200)

class FindTVShow(forms.Form):

    def __init__(self, *args, **kwargs):
        super(FindTVShow, self).__init__(*args, **kwargs)
        # Uni-form
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.error_text_inline = True
        self.helper.form_method = "GET"
        self.helper.help_text_inline = False
        self.helper.layout = Layout(
            'search',
            StrictButton('Search', type="submit", spinner="tiny", css_class='btn-primary'),
        )

    search = forms.CharField(max_length=200)

class FindMovie(forms.Form):

    def __init__(self, *args, **kwargs):
        super(FindMovie, self).__init__(*args, **kwargs)
        # Uni-form
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.field_template = 'bootstrap3/layout/inline_field.html'
        self.helper.error_text_inline = True
        self.helper.form_method = "GET"
        self.helper.help_text_inline = False
        self.helper.layout = Layout(
            'search',
            StrictButton('Search', type="submit", spinner="tiny", css_class='btn-primary'),
        )

    search = forms.CharField(max_length=200)