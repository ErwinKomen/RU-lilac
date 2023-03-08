from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import mark_safe
from markdown import markdown

import re, copy


# From own stuff
from lila.utils import *

LONG_STRING=255
STANDARD_LENGTH=100

# ==================== Helper functions ====================================

def adapt_markdown(val, lowercase=False):
    """Call markdown, but perform some actions to make it a bit safer"""

    sBack = ""
    oErr = ErrHandle()
    try:
        if val != None:
            val = val.replace("***", "\*\*\*")
            sBack = mark_safe(markdown(val, safe_mode='escape', extensions=['tables']))
            sBack = sBack.replace("<p>", "")
            sBack = sBack.replace("</p>", "")
            if lowercase:
                sBack = sBack.lower()
            #print(sBack)
    except:
        msg = oErr.get_error_message()
        oErr.DoError("adapt_markdown")
    return sBack

def get_crpp_date(dtThis, readable=False):
    """Convert datetime to string"""

    if readable:
        # Convert the computer-stored timezone...
        dtThis = dtThis.astimezone(pytz.timezone(TIME_ZONE))
        # Model: yyyy-MM-dd'T'HH:mm:ss
        sDate = dtThis.strftime("%d/%B/%Y (%H:%M)")
    else:
        # Model: yyyy-MM-dd'T'HH:mm:ss
        sDate = dtThis.strftime("%Y-%m-%dT%H:%M:%S")
    return sDate

def get_current_datetime():
    """Get the current time"""
    return timezone.now()



# Create your models here.

class Citem(models.Model):
    """One content item for the content management system"""

    # [1] obligatory name of the page this content element pertains to
    page = models.CharField("Page", max_length=LONG_STRING)
    # [1] obligatory htmlid on the page
    htmlid = models.CharField("Htmlid", max_length=LONG_STRING)

    # [0-1] optional description of location in plain text
    location = models.TextField("Location", null=True, blank=True)
    # [0-1] the markdown contents for the information
    contents = models.TextField("Contents", null=True, blank=True)

    # [1] And a date: the date of saving this manuscript
    created = models.DateTimeField(default=get_current_datetime)
    saved = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        sBack = "{}:{}".format(self.page, self.htmlid)
        return sBack

    def get_contents_markdown(self):
        sBack = "-"
        oErr = ErrHandle()
        try:
            if not self.contents is None:
                sBack = adapt_markdown(sBack)
            pass
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Citem/get_contents_markdown")
        return sBack

    def get_created(self):
        sCreated = get_crpp_date(self.created, True)
        return sCreated

    def get_saved(self):
        if self.saved is None:
            self.saved = self.created
            self.save()
        sSaved = get_crpp_date(self.saved, True)
        return sSaved


