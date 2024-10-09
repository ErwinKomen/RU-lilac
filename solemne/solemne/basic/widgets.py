from django.forms.widgets import NumberInput
from django.utils.safestring import mark_safe
import os

class RangeSlider(NumberInput):
    """A range slider"""

    def render(self, name, value, attrs = None, renderer = None):
        # Initialisations
        output = []
        org_name = name

        # Change the input type
        self.input_type = "range"

        # Adapt attribute id and name
        attrs['id'] = "{}-rangeslider".format(attrs['id'])
        name = "{}-rangeslider".format(name)

        # First the regular output
        output.append(super(RangeSlider, self).render(name, value, attrs, renderer))
        # Check for none-type
        if value == None: value = ""
        # Add the visible value of the range
        output.append("<span>Value: <span class='basic-range-input'><i>(move slider)</i></span></span>")
        # Add a hidden input for text
        output.append("<div class='hidden'><input id='id_{}' type='text' name='{}' /></div>".format(org_name, org_name))
        # Combine and return
        return mark_safe('\n'.join(output))
