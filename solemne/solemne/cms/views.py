"""
Definition of views for the CMS app.
"""

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import Group
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Prefetch, Count, F, Sum
from django.db.models.functions import Lower
from django.db.models.query import QuerySet 
from django.forms import formset_factory, modelformset_factory, inlineformset_factory, ValidationError
from django.forms.models import model_to_dict
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.template import Context
from django.views.generic.detail import DetailView
from django.views.generic.base import RedirectView
from django.views.generic import ListView, View
from django.views.decorators.csrf import csrf_exempt


# General imports
from datetime import datetime
import copy
import json
import re

# ======= imports from my own application ======
from solemne.settings import APP_PREFIX, MEDIA_DIR, WRITABLE_DIR
from solemne.utils import ErrHandle, is_ajax
from solemne.cms.models import Citem, Cpage, Clocation
from solemne.cms.forms import CitemForm, CpageForm, ClocationForm
from solemne.seeker.views_utils import solemne_get_history, solemne_action_add


# ======= from RU-Basic ========================
from solemne.basic.views import BasicPart, BasicList, BasicDetails, make_search_list, add_rel_item, adapt_search, \
    app_developer, app_moderator, user_is_ingroup, user_is_superuser

# ========= OWN CMS SETTINGS ===========================
BE_RESTRICTIVE = True


# ============ SUPPORTING ROUTINES =====================
def add_cms_contents(page, context):
    """Add any available CMS contents for the indicated page"""

    oErr = ErrHandle()
    try:
        # Get all the Citem objects for this page
        qs = Citem.objects.filter(clocation__page__urlname__iexact=page)
        for obj in qs:
            # Get the htmlid for this location
            htmlid = obj.clocation.htmlid
            if not htmlid is None:
                htmlcontent = "cms_{}".format(htmlid.replace("-", "_"))
                # Get the contents value for this, translating it from markdown
                sContents = obj.get_contents_markdown()
                # Add it to the context
                context[htmlcontent] = sContents
                # allowing even empty onew
                hasid = "cms_has_{}".format(htmlid.replace("-", "_"))
                context[hasid] = True
    except:
        msg = oErr.get_error_message()
        oErr.DoError("add_cms_contents")
    return context


# ============= Cpage VIEWS ============================


class CpageEdit(BasicDetails):
    """Details and editing of a CMS content item"""

    model = Cpage
    mForm = CpageForm
    prefix = 'cpage'
    title = "Content page"
    history_button = True
    mainitems = []

    stype_edi_fields = ['name', 'urlname']
        
    # How to handle the app_moderator

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        oErr = ErrHandle()
        field_keys = ['name', 'urlname', None, None]
        try:
            may_add = user_is_ingroup(self.request, app_moderator) or user_is_ingroup(self.request, app_developer)
            # Define the main items to show and edit
            context['mainitems'] = [
                {'type': 'plain', 'label': "Page:",         'value': instance.name              },
                {'type': 'line',  'label': "Name in urls:", 'value': instance.get_urlname(True) },
                {'type': 'line',  'label': "Saved:",        'value': instance.get_saved()       },
                {'type': 'line',  'label': "Created:",      'value': instance.get_created()     },
                ]       

            # Only moderators and superusers are to be allowed to create and delete content-items
            if may_add: 
                # Allow editing
                for idx, oItem in enumerate(context['mainitems']):
                    fk = field_keys[idx]
                    if not fk is None:
                        oItem['field_key'] = fk

                # Only if this is the superuser:
                if user_is_superuser(self.request):
                    # Add one more item that allows adding locations
                    oItem = dict(type="safe", label="", value=instance.get_actions() )
                    context['mainitems'].append(oItem)

                # Signal that we have select2
                context['has_select2'] = True
            else:
                # Make sure user cannot delete
                self.no_delete = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CpageEdit/add_to_context")

        # Return the context we have made
        return context
    
    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        solemne_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return solemne_get_history(instance)


class CpageDetails(CpageEdit):
    """Just the HTML page"""
    rtype = "html"


class CpageAdd(CpageDetails):
    """Allow creating a Clocation object based on this Cpage"""

    def custom_init(self, instance):
        oErr = ErrHandle()
        try:
            # Create a new Clocation that is based on this Cpage
            item_new = Clocation.objects.create(page=instance, name="-")
            if item_new is None:
                # It wasn't successfull - redirect to the default details page of cpage
                self.redirectpage = reverse("cpage_details", kwargs={'pk': instance.id})
            else:
                # Clocation created: re-direct to this clocation
                self.redirectpage = reverse("clocation_details", kwargs={'pk': item_new.id})
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CpageAdd/custom_init")
        return None


class CpageListView(BasicList):
    """Search and list projects"""

    model = Cpage 
    listform = CpageForm
    prefix = "cpage"
    has_select2 = True
    sg_name = "Content page"     # This is the name as it appears e.g. in "Add a new XXX" (in the basic listview)
    plural_name = "Content pages"
    new_button = False
    order_cols = ['name', 'urlname', '', 'saved', 'created']
    order_default = order_cols
    order_heads = [
        {'name': 'Page',        'order': 'o=1', 'type': 'str', 'field': 'name',         'linkdetails': True,   'main': True},
        {'name': 'Name in urls','order': 'o=2', 'type': 'str', 'custom': 'urlname',     'linkdetails': True},
        {'name': 'Locations',   'order': '',    'type': 'int', 'custom': 'count',       'linkdetails': True},
        {'name': 'Saved',       'order': 'o=4', 'type': 'str', 'custom': 'saved',       'align': 'right'},
        {'name': 'Created',     'order': 'o=5', 'type': 'str', 'custom': 'created',     'align': 'right'}]
                   
    filters = [ {"name": "Page",         "id": "filter_page",     "enabled": False}
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'page',   'dbfield': 'name',         'keyS': 'page_ta'}
            ]
         } 
        ] 

    def add_to_context(self, context, initial):
        if BE_RESTRICTIVE:
            may_add = user_is_superuser(self.request)
        else:
            may_add = context['is_app_moderator'] or context['is_app_developer']
        if may_add:
            # Allow creation of new item(s)
            self.new_button = True
            context['new_button'] = self.new_button
        return context

    # hier gaat het nog niet goed
    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        oErr = ErrHandle()
        try:
            if custom == "saved":
                # Get the correctly visible date
                sBack = instance.get_saved()

            elif custom == "created":
                # Get the correctly visible date
                sBack = instance.get_created()

            elif custom == "urlname":
                sBack = instance.get_urlname(html=True)

            elif custom == "count":
                iCount = instance.get_count_locations()
                sBack = "{}".format(iCount)
            
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CpageListView/get_field_value")

        return sBack, sTitle


# ============= Clocation VIEWS ============================


class ClocationEdit(BasicDetails):
    """Details and editing of a CMS content item"""

    model = Clocation
    mForm = ClocationForm
    prefix = 'cloc'
    title = "Content location"
    history_button = True
    mainitems = []

    stype_edi_fields = ['name', 'htmlid', 'page']
        
    # How to handle the app_moderator

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        oErr = ErrHandle()
        field_keys = ['page', 'name', 'htmlid', None, None]
        try:
            may_add = user_is_ingroup(self.request, app_moderator) or user_is_ingroup(self.request, app_developer)
            # Define the main items to show and edit
            context['mainitems'] = [
                {'type': 'plain', 'label': "Page:",     'value': instance.get_page()      },
                {'type': 'line',  'label': "Location:", 'value': instance.name },
                {'type': 'line',  'label': "HTML id:",  'value': instance.htmlid    },
                {'type': 'line',  'label': "Saved:",    'value': instance.get_saved()       },
                {'type': 'line',  'label': "Created:",  'value': instance.get_created()     },
                ]       

            # Only moderators and superusers are to be allowed to create and delete content-items
            if may_add: 
                # Allow editing
                for idx, oItem in enumerate(context['mainitems']):
                    fk = field_keys[idx]
                    if not fk is None:
                        oItem['field_key'] = fk

                # Only if this is the superuser:
                if user_is_superuser(self.request):
                    # Add one more item that allows adding items
                    oItem = dict(type="safe", label="", value=instance.get_actions() )
                    context['mainitems'].append(oItem)

                # Signal that we have select2
                context['has_select2'] = True
            else:
                # Make sure user cannot delete
                self.no_delete = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Clocation/add_to_context")

        # Return the context we have made
        return context
    
    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        solemne_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return solemne_get_history(instance)


class ClocationDetails(ClocationEdit):
    """Just the HTML page"""
    rtype = "html"


class ClocationAdd(ClocationDetails):
    """Allow creating a Clocation object based on this Cpage"""

    def custom_init(self, instance):
        oErr = ErrHandle()
        try:
            # Create a new Citem that is based on this Clocation
            item_new = Citem.objects.create(clocation=instance)
            if item_new is None:
                # It wasn't successfull - redirect to the default details page of clocation
                self.redirectpage = reverse("clocation_details", kwargs={'pk': instance.id})
            else:
                # Citem created: re-direct to this citem
                self.redirectpage = reverse("citem_details", kwargs={'pk': item_new.id})
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ClocationAdd/custom_init")
        return None


class ClocationListView(BasicList):
    """Search and list projects"""

    model = Clocation 
    listform = ClocationForm
    prefix = "citem"
    has_select2 = True
    sg_name = "Content location"     # This is the name as it appears e.g. in "Add a new XXX" (in the basic listview)
    plural_name = "Content locations"
    new_button = False
    order_cols = ['page__name', 'name', 'htmlid', '', 'saved', 'created']
    order_default = order_cols
    order_heads = [
        {'name': 'Page',        'order': 'o=1', 'type': 'str', 'custom': 'page',    'linkdetails': True,   'main': True},
        {'name': 'Location',    'order': 'o=2', 'type': 'str', 'field':  'name',    'linkdetails': True},
        {'name': 'HTML id',     'order': 'o=3', 'type': 'str', 'field':  'htmlid',  'linkdetails': True },
        {'name': 'Items',       'order': '',    'type': 'int', 'custom': 'count',   'linkdetails': True},
        {'name': 'Saved',       'order': 'o=5', 'type': 'str', 'custom': 'saved',   'align': 'right'},
        {'name': 'Created',     'order': 'o=6', 'type': 'str', 'custom': 'created', 'align': 'right'}]
                   
    filters = [ {"name": "Location",         "id": "filter_location",     "enabled": False}
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'location',   'dbfield': 'name',         'keyS': 'location_ta'}
            ]
         } 
        ] 

    def add_to_context(self, context, initial):
        if context['is_app_moderator'] or context['is_app_developer']:
            ## Allow creation of new item(s)
            #self.new_button = True
            #context['new_button'] = self.new_button
            pass
        return context

    # hier gaat het nog niet goed
    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        oErr = ErrHandle()
        try:
            if custom == "saved":
                # Get the correctly visible date
                sBack = instance.get_saved()

            elif custom == "created":
                # Get the correctly visible date
                sBack = instance.get_created()

            elif custom == "page":
                sBack = instance.get_page()

            elif custom == "count":
                iCount = instance.get_count_items()
                sBack = "{}".format(iCount)
           
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ClocationListView/get_field_value")

        return sBack, sTitle


# ============= Citem VIEWS ============================


class CitemEdit(BasicDetails):
    """Details and editing of a CMS content item"""

    model = Citem
    mForm = CitemForm
    prefix = 'citem'
    title = "Content item"
    history_button = True
    mainitems = []

    stype_edi_fields = ['clocation', 'contents']
        
    # How to handle the app_moderator

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        oErr = ErrHandle()
        field_keys = [None, None, 'clocation', 'contents', None, None]
        try:
            # Define the main items to show and edit
            context['mainitems'] = [
                {'type': 'plain', 'label': "Page:",     'value': instance.get_page()      },
                {'type': 'line',  'label': "HTML id:",  'value': instance.get_htmlid()    },
                {'type': 'line',  'label': "Location:", 'value': instance.get_location(True) },
                {'type': 'line',  'label': "Contents:", 'value': instance.get_contents_markdown(retain=True)},
                {'type': 'line',  'label': "Saved:",    'value': instance.get_saved()       },
                {'type': 'line',  'label': "Created:",  'value': instance.get_created()     },
                ]       

            # Only moderators and superusers are to be allowed to create and delete content-items
            if user_is_ingroup(self.request, app_moderator) or user_is_ingroup(self.request, app_developer): 
                # Allow editing
                for idx, oItem in enumerate(context['mainitems']):
                    fk = field_keys[idx]
                    if not fk is None:
                        oItem['field_key'] = fk

                # Signal that we have select2
                context['has_select2'] = True
            else:
                # Make sure user cannot delete
                self.no_delete = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Citem/add_to_context")

        # Return the context we have made
        return context
    
    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        solemne_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return solemne_get_history(instance)


class CitemDetails(CitemEdit):
    """Just the HTML page"""
    rtype = "html"


class CitemListView(BasicList):
    """Search and list projects"""

    model = Citem 
    listform = CitemForm
    prefix = "citem"
    has_select2 = True
    sg_name = "Content item"     # This is the name as it appears e.g. in "Add a new XXX" (in the basic listview)
    plural_name = "Content items"
    new_button = False
    order_cols = ['clocation__page__name', 'clocation__htmlid', 'clocation__name', 'contents', 'saved', 'created']
    order_default = order_cols
    order_heads = [
        {'name': 'Page',        'order': 'o=1', 'type': 'str', 'custom': 'page',        'linkdetails': True},
        {'name': 'HTML id',     'order': 'o=2', 'type': 'str', 'custom': 'htmlid',      'linkdetails': True },
        {'name': 'Location',    'order': 'o=3', 'type': 'str', 'custom': 'location',    'linkdetails': True},
        {'name': 'Contents',    'order': 'o=4', 'type': 'str', 'custom': 'contents',    'linkdetails': True,   'main': True},
        {'name': 'Saved',       'order': 'o=5', 'type': 'str', 'custom': 'saved',       'align': 'right'},
        {'name': 'Created',     'order': 'o=6', 'type': 'str', 'custom': 'created',     'align': 'right'}]
                   
    filters = [ {"name": "Page",         "id": "filter_page",     "enabled": False}
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'page',   'dbfield': 'page',         'keyS': 'page_ta'}
            ]
         } 
        ] 

    def add_to_context(self, context, initial):
        if context['is_app_moderator'] or context['is_app_developer']:
            ## Allow creation of new item(s)
            #self.new_button = True
            #context['new_button'] = self.new_button
            pass
        return context

    # hier gaat het nog niet goed
    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        oErr = ErrHandle()
        try:
            if custom == "saved":
                # Get the correctly visible date
                sBack = instance.get_saved()

            elif custom == "created":
                # Get the correctly visible date
                sBack = instance.get_created()

            elif custom == "page":
                sBack = instance.get_page()

            elif custom == "htmlid":
                sBack = instance.get_htmlid()

            elif custom == "location":
                sBack = instance.get_location()

            elif custom == "contents":
                sBack = instance.get_contents_markdown(stripped=True)
                # Shorten if needed
                if len(sBack) > 100:
                    sBack = "{}...".format(sBack[:100])
            
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CitemListView/get_field_value")

        return sBack, sTitle


