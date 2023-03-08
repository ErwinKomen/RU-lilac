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
from lila.settings import APP_PREFIX, MEDIA_DIR, WRITABLE_DIR
from lila.utils import ErrHandle
from lila.cms.models import Citem
from lila.cms.forms import CitemForm
from lila.seeker.views_utils import lila_get_history, lila_action_add


# ======= from RU-Basic ========================
from lila.basic.views import BasicPart, BasicList, BasicDetails, make_search_list, add_rel_item, adapt_search

# ============= Citem VIEWS ============================


class CitemEdit(BasicDetails):
    """Details and editing of a CMS content item"""

    model = Citem
    mForm = CitemForm
    prefix = 'citem'
    title = "Content item"
    history_button = True
    mainitems = []

    # How to handle the app_moderator

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        def get_singles(lst_id, clsThis, field):
            """Get a list of occurrances that have only one project id"""

            # Get all singles
            lst_singles = clsThis.objects.all().values(field).annotate(total=Count("project")).filter(total=1).values(field, "total")
            # Turn them into a dictionary - but only the singular ones
            dict_singles = { x[field]:x['total'] for x in lst_singles}
            # Count the ones that overlap: those are the singular ones
            count = 0
            attr = "{}__id".format(field)
            for oItem in lst_id:
                id = oItem[attr]
                if id in dict_singles:
                    count += 1
            return count
            
        oErr = ErrHandle()
        try:
            # Only moderators and superusers are to be allowed to create and delete project labels
            if user_is_ingroup(self.request, app_moderator) or user_is_ingroup(self.request, app_developer): 
                # Define the main items to show and edit
                context['mainitems'] = [
                    {'type': 'plain', 'label': "Name:",     'value': instance.name, 'field_key': "name"},
                    {'type': 'line',  'label': "Editors:",  'value': instance.get_editor_markdown()}
                    ]       

                # Also add a delete Warning Statistics message (see issue #485)
                lst_proj_m = ManuscriptProject.objects.filter(project=instance).values('manuscript__id')
                lst_proj_hc = CollectionProject.objects.filter(project=instance).values('collection__id')
                lst_proj_s = CanwitProject.objects.filter(project=instance).values('canwit__id')
                lst_proj_ssg = AustatProject.objects.filter(project=instance).values('equal__id')

                count_m =  len(lst_proj_m)
                count_hc =  len(lst_proj_hc)
                count_s =  len(lst_proj_s)
                count_ssg = len(lst_proj_ssg)
                single_m = get_singles(lst_proj_m, ManuscriptProject, "manuscript")
                single_hc = get_singles(lst_proj_hc, CollectionProject, "collection")
                single_s = get_singles(lst_proj_s, CanwitProject, "canwit")
                single_ssg = get_singles(lst_proj_ssg, AustatProject, "equal")
            
                local_context = dict(
                    project=instance, 
                    count_m=count_m, count_hc=count_hc, count_s=count_s, count_ssg=count_ssg,
                    single_m=single_m, single_hc=single_hc, single_s=single_s, single_ssg=single_ssg,
                    )
                context['delete_message'] = render_to_string('seeker/project_statistics.html', local_context, self.request)
            else:
                # Make sure user cannot delete
                self.no_delete = True
                # Provide minimal read-only information 
                context['mainitems'] = [
                    {'type': 'plain', 'label': "Name:",     'value': instance.name}
                    # Do not provide more information, i.e. don't give the name of the editors to the user
                    ]       
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Citem/add_to_context")

        # Return the context we have made
        return context
    
    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


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
    order_cols = ['page', 'htmlid', 'location', 'saved', 'created']
    order_default = order_cols
    order_heads = [
        {'name': 'Page',        'order': 'o=1', 'type': 'str', 'field': 'page',         'linkdetails': True,   'main': True},
        {'name': 'HTML id',     'order': 'o=2', 'type': 'str', 'field': 'htmlid',       'linkdetails': True },
        {'name': 'Location',    'order': 'o=3', 'type': 'str', 'custom': 'location',    'linkdetails': True},
        {'name': 'Saved',       'order': 'o=4', 'type': 'str', 'custom': 'saved',       'align': 'right'},
        {'name': 'Created',     'order': 'o=5', 'type': 'str', 'custom': 'created',     'align': 'right'}]
                   
    filters = [ {"name": "Page",         "id": "filter_page",     "enabled": False}
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'page',   'dbfield': 'page',         'keyS': 'page_ta'}
            ]
         } 
        ] 

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

            elif custom == "location":
                if instance.location is None or instance.location == "":
                    sBack = "-"
                else:
                    sBack = instance.location
            
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CitemListView/get_field_value")

        return sBack, sTitle


