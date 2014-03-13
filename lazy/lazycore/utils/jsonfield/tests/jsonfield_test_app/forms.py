from django import forms

from lazycore.utils.jsonfield.forms import JSONFormField
from .models import JSONFieldTestModel

class JSONTestForm(forms.Form):
    json_data = JSONFormField()
    optional_json_data = JSONFormField(required=False)

class JSONTestModelForm(forms.ModelForm):
    class Meta:
        model = JSONFieldTestModel
