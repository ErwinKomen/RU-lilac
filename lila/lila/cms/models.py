# from time import clock
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import mark_safe
from markdown import markdown

import re, copy
import pytz
import lxml
import lxml.html


# From own stuff
from lila.settings import APP_PREFIX, WRITABLE_DIR, TIME_ZONE
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

def striphtml(data):
    sBack = data
    if not data is None and data != "":
        xml = lxml.html.document_fromstring(data)
        if not xml is None:
            sBack = xml.text_content()
    return sBack



# ============================ models for the CMS =================================


class Cpage(models.Model):
    """A HTML page on which the CMS works"""

    # [1] obligatory name of the page this content element pertains to
    name = models.CharField("Name", max_length=LONG_STRING)

    # [0-1] The name of the page as it occurs in 'urls.py'
    urlname = models.CharField("Name in urls", null=True, blank=True, max_length=LONG_STRING)

    # [1] And a date: the date of saving this manuscript
    created = models.DateTimeField(default=get_current_datetime)
    saved = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        sBack = self.name
        return sBack

    def get_actions(self):
        """Get HTML action buttons to allow creating a Clocation using this Cpage"""

        sBack = "-"
        oErr = ErrHandle()
        html = []
        try:
            url = reverse('cpage_add_loc', kwargs={'pk': self.id})
            html.append("<a href='{}' title='Create a CMS location within this page'>".format(url))
            html.append("<span class='badge signature ot'>Create a Location on this page</span></a>")
            # Combine response
            sBack = "\n".join(html)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Cpage/get_actions")

        return sBack

    def get_count_locations(self):
        """Get the number of locations attached to this Cpage"""

        count = self.page_locations.count()
        return count

    def get_created(self):
        sCreated = get_crpp_date(self.created, True)
        return sCreated

    def get_saved(self):
        if self.saved is None:
            self.saved = self.created
            self.save()
        sSaved = get_crpp_date(self.saved, True)
        return sSaved

    def get_urlname(self, html=False):
        sBack = "-"
        if not self.urlname is None and self.urlname != "":
            sBack = self.urlname
            if html:
                try:
                    url = reverse(sBack)
                except:
                    url = None
                if url is None:
                    sBack = "<span class='badge signature cl'>{}</span>".format(sBack)
                else:
                    sBack = "<a href='{}'><span class='badge signature cl'>{}</span></a>".format(url, sBack)
        return sBack


class Clocation(models.Model):
    """The location of a content-item on a HTML page"""

    # [1] Name of the location as a descriptive string
    name = models.TextField("Name")
    # [1] obligatory htmlid on the page
    htmlid = models.CharField("Htmlid", blank=True, null=True, max_length=LONG_STRING)

    # [1] Link to the page on which this location holds
    page = models.ForeignKey(Cpage, on_delete=models.CASCADE, related_name="page_locations")

    # [1] And a date: the date of saving this manuscript
    created = models.DateTimeField(default=get_current_datetime)
    saved = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        sBack = "-"
        if not self.page is None:
            sBack = "{}: {}".format(self.page.name, self.name)
        return sBack

    def get_actions(self):
        """Get HTML action buttons to allow creating a Citem using this Clocation"""

        sBack = "-"
        oErr = ErrHandle()
        html = []
        try:
            url = reverse('clocation_add_item', kwargs={'pk': self.id})
            html.append("<a href='{}' title='Create a CMS item within this location'>".format(url))
            html.append("<span class='badge signature ot'>Create a contents-item on this location</span></a>")
            # Combine response
            sBack = "\n".join(html)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Clocation/get_actions")

        return sBack

    def get_count_items(self):
        """Get the number of items attached to this Clocation"""

        count = self.location_items.count()
        return count

    def get_created(self):
        sCreated = get_crpp_date(self.created, True)
        return sCreated

    def get_htmlid(self):
        """Get the location HTML id"""

        sBack = "-"
        if not self.htmlid is None and self.htmlid != "":
            sBack = self.htmlid
        return sBack

    def get_location(self):
        """Get the location name"""

        sBack = "-"
        if not self.name is None and self.name != "":
            sBack = self.name
        return sBack

    def get_page(self):
        """Get the name of the page"""

        sBack = "-"
        if not self.page is None:
            sBack = self.page.name
        return sBack

    def get_saved(self):
        if self.saved is None:
            self.saved = self.created
            self.save()
        sSaved = get_crpp_date(self.saved, True)
        return sSaved


class Citem(models.Model):
    """One content item for the content management system"""

    # [1] Obligatory location of this content item
    clocation = models.ForeignKey(Clocation, on_delete=models.CASCADE, related_name="location_items")

    # [0-1] the markdown contents for the information
    contents = models.TextField("Contents", null=True, blank=True)

    # [1] And a date: the date of saving this manuscript
    created = models.DateTimeField(default=get_current_datetime)
    saved = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        sBack = "-"
        if not self.clocation is None:
            sBack = "{}: {}".format(self.clocation.page.name, self.clocation.name)
        return sBack

    def get_contents_markdown(self, stripped=False, retain=False):
        sBack = "-"
        oErr = ErrHandle()
        try:
            # sBack = self.get_contents()
            sBack = "-"
            if stripped:
                if not self.contents is None:
                    sBack = self.contents
                sBack = striphtml(markdown(sBack, safe_mode='escape', extensions=['tables']))
            else:
                sBack = self.get_contents()
                sBack = adapt_markdown(sBack)
                if retain:
                    sBack = sBack.replace("<a ", "<a class='retain' ")
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Citem/get_contents_markdown")
        return sBack

    def get_created(self):
        sCreated = get_crpp_date(self.created, True)
        return sCreated

    def get_htmlid(self):
        """Get the location HTML id"""

        sBack = "-"
        if not self.clocation is None:
            sBack = self.clocation.get_htmlid()
        return sBack

    def get_location(self):
        """Get the location name"""

        sBack = "-"
        if not self.clocation is None:
            sBack = self.clocation.get_location()
        return sBack

    def get_contents(self):
        sBack = "-"
        oErr = ErrHandle()
        try:
            if not self.contents is None:
                sBack = striphtml(self.contents)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Citem/get_contents")
        return sBack

    def get_page(self):
        """Get the name of the page"""

        sBack = "-"
        if not self.clocation is None:
            sBack = self.clocation.get_page()
        return sBack

    def get_saved(self):
        if self.saved is None:
            self.saved = self.created
            self.save()
        sSaved = get_crpp_date(self.saved, True)
        return sSaved


