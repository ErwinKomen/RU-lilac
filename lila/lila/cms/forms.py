"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelMultipleChoiceField, ModelChoiceField
from django.forms.widgets import *
from django.db.models import F, Case, Value, When, IntegerField
from django_select2.forms import ModelSelect2Mixin, Select2MultipleWidget, ModelSelect2MultipleWidget, \
    ModelSelect2TagWidget, ModelSelect2Widget, HeavySelect2Widget


# ============ from own application
from lila.basic.widgets import RangeSlider
from lila.cms.models import *


# ================= WIDGETS =====================================


#class AuthorOneWidget(ModelSelect2Widget):
#    model = Author
#    search_fields = [ 'name__icontains']

#    def label_from_instance(self, obj):
#        return obj.name

#    def get_queryset(self):
#        return Author.objects.all().order_by('name').distinct()


#class AuthorWidget(ModelSelect2MultipleWidget):
#    model = Author
#    search_fields = [ 'name__icontains']

#    def label_from_instance(self, obj):
#        return obj.name

#    def get_queryset(self):
#        return Author.objects.all().order_by('name').distinct()




# ================= FORMS =======================================

class CitemForm(forms.ModelForm):
    """Keyword list and edit"""

    page_ta = forms.CharField(label=_("Page"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching input-sm', 'placeholder': 'Page...', 'style': 'width: 100%;'}))
    #kwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
    #            widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = []

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Citem
        fields = ['page', 'htmlid', 'location', 'contents']
        widgets={
            'page':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
            'htmlid':      forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
            'location': forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'Location of this item (descriptive)...'}),
            'contents': forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'Contents (use markdown to enter)...'})
            }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CitemForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['page'].required = False
            self.fields['htmlid'].required = False
            self.fields['location'].required = False
            self.fields['contents'].required = False

            # self.fields['kwlist'].queryset = Keyword.objects.all().order_by('name')

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']

                # self.fields['visibility'].initial = instance.visibility
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CitemForm/init")

        # We do not really return anything from the init
        return None

