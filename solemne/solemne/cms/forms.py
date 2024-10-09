"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from django.forms import ModelMultipleChoiceField, ModelChoiceField
from django.forms.widgets import *
from django.db.models import F, Case, Value, When, IntegerField
from django_select2.forms import ModelSelect2Mixin, Select2MultipleWidget, ModelSelect2MultipleWidget, \
    ModelSelect2TagWidget, ModelSelect2Widget, HeavySelect2Widget


# ============ from own application
from solemne.basic.widgets import RangeSlider
from solemne.cms.models import *


# ================= WIDGETS =====================================


class CpageOneWidget(ModelSelect2Widget):
    model = Cpage
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Cpage.objects.all().order_by('name').distinct()


class CpageWidget(ModelSelect2MultipleWidget):
    model = Cpage
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Cpage.objects.all().order_by('name').distinct()


class ClocationOneWidget(ModelSelect2Widget):
    model = Clocation
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Clocation.objects.all().order_by('page__name', 'name').distinct()


class ClocationWidget(ModelSelect2MultipleWidget):
    model = Clocation
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Clocation.objects.all().order_by('page__name', 'name').distinct()




# ================= FORMS =======================================

class CpageForm(forms.ModelForm):
    """Content Page list and edit"""

    page_ta = forms.CharField(label=_("Page"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching input-sm', 'placeholder': 'Page...', 'style': 'width: 100%;'}))
    typeaheads = []

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Cpage
        fields = ['name', 'urlname']
        widgets={
            'name':     forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
            'urlname':  forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'})
            }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CpageForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['name'].required = False
            self.fields['urlname'].required = False

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CpageForm/init")

        # We do not really return anything from the init
        return None


class ClocationForm(forms.ModelForm):
    """Content location list and edit"""

    location_ta = forms.CharField(label=_("Location"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching input-sm', 'placeholder': 'Location...', 'style': 'width: 100%;'}))
    typeaheads = []

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Clocation
        fields = ['name', 'htmlid', 'page']
        widgets={
            'name':     forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
            'htmlid':   forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
            'page':     CpageOneWidget(attrs={'data-placeholder': 'Select a page...', 'style': 'width: 100%;'})
            }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ClocationForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['name'].required = False
            self.fields['htmlid'].required = False
            self.fields['page'].required = False

            self.fields['page'].queryset = Cpage.objects.all().order_by('name')

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']

        except:
            msg = oErr.get_error_message()
            oErr.DoError("ClocationForm/init")

        # We do not really return anything from the init
        return None


class CitemForm(forms.ModelForm):
    """Keyword list and edit"""

    #page_ta = forms.CharField(label=_("Page"), required=False,
    #            widget=forms.TextInput(attrs={'class': 'typeahead searching input-sm', 'placeholder': 'Page...', 'style': 'width: 100%;'}))
    #kwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
    #            widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = []

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Citem
        fields = ['clocation', 'contents']
        widgets={
            'clocation': ClocationOneWidget(attrs={'data-placeholder': 'Select a location...', 'style': 'width: 100%;'}),
            'contents': forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'Contents (use markdown to enter)...'})
            }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CitemForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['clocation'].required = False
            self.fields['contents'].required = False

            self.fields['clocation'].queryset = Clocation.objects.all().order_by('page__name', 'name')

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']

                # self.fields['visibility'].initial = instance.visibility
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CitemForm/init")

        # We do not really return anything from the init
        return None

