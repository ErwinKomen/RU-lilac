"""
Definition of views for the SEEKER app.
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
from lxml import etree as ET

# General imports
from datetime import datetime
import operator 
from operator import itemgetter
from functools import reduce
from pyzotero import zotero
from time import sleep 
import fnmatch
import sys, os
import base64
import copy
import json
import csv, re
import requests
import openpyxl
from openpyxl.utils.cell import get_column_letter
import sqlite3
from io import StringIO
from itertools import chain

# ======== imports for PDF creation ==========
import io  
from markdown import markdown 
from reportlab.lib.units import inch 
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle 
from reportlab.lib.units import inch 
from reportlab.pdfgen import canvas 
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Frame, PageBreak   
from reportlab.rl_config import defaultPageSize  

# ======= imports from my own application ======
from lila.settings import APP_PREFIX, MEDIA_DIR, WRITABLE_DIR
from lila.utils import ErrHandle
from lila.seeker.forms import SearchCollectionForm, SearchManuscriptForm, SearchManuForm, SearchSermonForm, LibrarySearchForm, SignUpForm, \
    AuthorSearchForm, UploadFileForm, UploadFilesForm, ManuscriptForm, CanwitForm, CommentForm, \
    AuthorEditForm, BibRangeForm, FeastForm, LitrefForm, \
    CanwitSuperForm, SearchUrlForm, GenreForm, AuworkForm, \
    CanwitSignatureForm, AustatLinkForm, AuworkEditionForm, \
    ReportEditForm, SourceEditForm, ManuscriptProvForm, LocationForm, LocationRelForm, OriginForm, \
    LibraryForm, ManuscriptExtForm, ManuscriptLitrefForm, CanwitKeywordForm, KeywordForm, \
    ManuscriptKeywordForm, DaterangeForm, ProjectForm, CanwitCollectionForm, CollectionForm, \
    AustatForm, ManuscriptCollectionForm, CollectionLitrefForm, \
    SuperSermonGoldCollectionForm, ProfileForm, UserKeywordForm, ProvenanceForm, ProvenanceManForm, \
    TemplateForm, TemplateImportForm, ManuReconForm,  ManuscriptProjectForm, \
    CodicoForm, CodicoProvForm, ProvenanceCodForm, OriginCodForm, CodicoOriginForm
from lila.seeker.models import get_crpp_date, get_current_datetime, process_lib_entries, get_searchable, get_now_time, \
    add_gold2equal, add_equal2equal, add_ssg_equal2equal, get_helptext, Information, Country, City, Author, Manuscript, \
    User, Group, Origin, Canwit, MsItem, Codhead, CanwitKeyword, CanwitAustat, NewsItem, \
    SourceInfo, AustatKeyword, ManuscriptExt, AuworkGenre, AuworkKeyword,  \
    ManuscriptKeyword, Action, Austat, AustatLink, Location, LocationName, LocationIdentifier, LocationRelation, LocationType, \
    ProvenanceMan, Provenance, Daterange, CollOverlap, BibRange, Feast, Comment, AustatDist, \
    Basket, BasketMan, BasketAustat, Litref, LitrefMan, LitrefCol, Report, \
    Visit, Profile, Keyword, CanwitSignature, Status, Library, Collection, CollectionCanwit, \
    CollectionMan, Caned, UserKeyword, Template, Genre, Auwork, EdirefWork, \
    ManuscriptCorpus, ManuscriptCorpusLock, AustatCorpus, ProjectEditor, \
    Codico, ProvenanceCod, OriginCodico, CodicoKeyword, Reconstruction, \
    Project, ManuscriptProject, CollectionProject, AustatProject, CanwitProject, \
    get_reverse_spec, LINK_EQUAL, LINK_PRT, LINK_BIDIR, LINK_PARTIAL, STYPE_IMPORTED, STYPE_EDITED, STYPE_MANUAL, LINK_UNSPECIFIED
from lila.reader.views import reader_uploads
from lila.bible.models import Reference
from lila.seeker.adaptations import listview_adaptations, adapt_codicocopy, add_codico_to_manuscript
from lila.seeker.views_utils import lila_action_add, lila_get_history

# ======= from RU-Basic ========================
from lila.basic.views import BasicPart, BasicList, BasicDetails, make_search_list, add_rel_item, adapt_search


# Some constants that can be used
paginateSize = 20
paginateSelect = 15
paginateValues = (100, 50, 20, 10, 5, 2, 1, )

# Global debugging 
bDebug = False

cnrs_url = "http://medium-avance.irht.cnrs.fr"

def get_application_name():
    """Try to get the name of this application"""

    # Walk through all the installed apps
    for app in apps.get_app_configs():
        # Check if this is a site-package
        if "site-package" not in app.path:
            # Get the name of this app
            name = app.name
            # Take the first part before the dot
            project_name = name.split(".")[0]
            return project_name
    return "unknown"
# Provide application-specific information
PROJECT_NAME = get_application_name()
app_uploader = "{}_uploader".format(PROJECT_NAME.lower())
app_editor = "{}_editor".format(PROJECT_NAME.lower())
app_userplus = "{}_userplus".format(PROJECT_NAME.lower())
app_developer = "{}_developer".format(PROJECT_NAME.lower())
app_moderator = "{}_moderator".format(PROJECT_NAME.lower())

def get_usercomments(type, instance, profile):
    """Get a HTML list of comments made by this user and possible users in the same group"""

    html = []
    lstQ = []
    if not username_is_ingroup(profile.user, app_editor):
        # App editors have permission to see *all* comments from all users
        lstQ.append(Q(profile=profile))
    if type != "":
        lstQ.append(Q(otype=type))

    # Calculate the list
    qs = instance.comments.filter(*lstQ).order_by("-created")

    # REturn the list
    return qs

def get_application_context(request, context):
    context['is_authenticated'] = user_is_authenticated(request)
    context['authenticated'] = context['is_authenticated'] 
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)
    context['is_app_moderator'] = user_is_superuser(request) or user_is_ingroup(request, app_moderator)
    return context

def treat_bom(sHtml):
    """REmove the BOM marker except at the beginning of the string"""

    # Check if it is in the beginning
    bStartsWithBom = sHtml.startswith(u'\ufeff')
    # Remove everywhere
    sHtml = sHtml.replace(u'\ufeff', '')
    # Return what we have
    return sHtml

def adapt_m2m(cls, instance, field1, qs, field2, extra = [], extrargs = {}, qfilter = {}, 
              related_is_through = False, userplus = None, added=None, deleted=None):
    """Adapt the 'field' of 'instance' to contain only the items in 'qs'
    
    The lists [added] and [deleted] (if specified) will contain links to the elements that have been added and deleted
    If [deleted] is specified, then the items will not be deleted by adapt_m2m(). Caller needs to do this.
    """

    errHandle = ErrHandle()
    try:
        # Get current associations
        lstQ = [Q(**{field1: instance})]
        for k,v in qfilter.items(): lstQ.append(Q(**{k: v}))
        through_qs = cls.objects.filter(*lstQ)
        if related_is_through:
            related_qs = through_qs
        else:
            related_qs = [getattr(x, field2) for x in through_qs]
        # make sure all items in [qs] are associated
        if userplus == None or userplus:
            for obj in qs:
                if obj not in related_qs:
                    # Add the association
                    args = {field1: instance}
                    if related_is_through:
                        args[field2] = getattr(obj, field2)
                    else:
                        args[field2] = obj
                    for item in extra:
                        # Copy the field with this name from [obj] to 
                        args[item] = getattr(obj, item)
                    for k,v in extrargs.items():
                        args[k] = v
                    # cls.objects.create(**{field1: instance, field2: obj})
                    new = cls.objects.create(**args)
                    if added != None:
                        added.append(new)

        # Remove from [cls] all associations that are not in [qs]
        # NOTE: do not allow userplus to delete
        for item in through_qs:
            if related_is_through:
                obj = item
            else:
                obj = getattr(item, field2)
            if obj not in qs:
                if deleted == None:
                    # Remove this item
                    item.delete()
                else:
                    deleted.append(item)
        # Return okay
        return True
    except:
        msg = errHandle.get_error_message()
        return False

def adapt_m2o(cls, instance, field, qs, link_to_obj = None, **kwargs):
    """Adapt the instances of [cls] pointing to [instance] with [field] to only include [qs] """

    errHandle = ErrHandle()
    try:
        # Get all the [cls] items currently linking to [instance]
        lstQ = [Q(**{field: instance})]
        linked_qs = cls.objects.filter(*lstQ)
        if link_to_obj != None:
            linked_through = [getattr(x, link_to_obj) for x in linked_qs]
        # make sure all items in [qs] are linked to [instance]
        for obj in qs:
            if (obj not in linked_qs) and (link_to_obj == None or obj not in linked_through):
                # Create new object
                oNew = cls()
                setattr(oNew, field, instance)
                # Copy the local fields
                for lfield in obj._meta.local_fields:
                    fname = lfield.name
                    if fname != "id" and fname != field:
                        # Copy the field value
                        setattr(oNew, fname, getattr(obj, fname))
                for k, v in kwargs.items():
                    setattr(oNew, k, v)
                # Need to add an object link?
                if link_to_obj != None:
                    setattr(oNew, link_to_obj, obj)
                oNew.save()
        # Remove links that are not in [qs]
        for obj in linked_qs:
            if obj not in qs:
                # Remove this item
                obj.delete()
        # Return okay
        return True
    except:
        msg = errHandle.get_error_message()
        return False

def adapt_m2o_sig(instance, qs):
    """Adapt the instances of [CanwitSignature] pointing to [instance] to only include [qs] 
    
    Note: convert CanwitSignature into (Gold) Signature
    """

    errHandle = ErrHandle()
    try:
        # Get all the [CanwitSignature] items currently linking to [instance]
        linked_qs = CanwitSignature.objects.filter(sermon=instance)
        # make sure all items in [qs] are linked to [instance]
        bRedo = False
        for obj in qs:
            # Get the CanwitSignature equivalent for Gold signature [obj]
            sermsig = instance.get_sermonsig(obj)
            if sermsig not in linked_qs:
                # Indicate that we need to re-query
                bRedo = True
        # Do we need to re-query?
        if bRedo: 
            # Yes we do...
            linked_qs = CanwitSignature.objects.filter(sermon=instance)
        # Remove links that are not in [qs]
        for obj in linked_qs:
            # Get the gold-signature equivalent of this sermon signature
            gsig = obj.get_goldsig()
            # Check if the gold-sermon equivalent is in [qs]
            if gsig not in qs:
                # Remove this item
                obj.delete()
        # Return okay
        return True
    except:
        msg = errHandle.get_error_message()
        return False

def is_empty_form(form):
    """Check if the indicated form has any cleaned_data"""

    if "cleaned_data" not in form:
        form.is_valid()
    cleaned = form.cleaned_data
    return (len(cleaned) == 0)

def user_is_authenticated(request):
    # Is this user authenticated?
    username = request.user.username
    user = User.objects.filter(username=username).first()
    response = False if user == None else user.is_authenticated
    return response

def user_is_ingroup(request, sGroup):
    # Is this user part of the indicated group?
    user = User.objects.filter(username=request.user.username).first()
    response = username_is_ingroup(user, sGroup)
    return response

def username_is_ingroup(user, sGroup):
    # glist = user.groups.values_list('name', flat=True)

    # Only look at group if the user is known
    if user == None:
        glist = []
    else:
        glist = [x.name for x in user.groups.all()]

        # Only needed for debugging
        if bDebug:
            ErrHandle().Status("User [{}] is in groups: {}".format(user, glist))
    # Evaluate the list
    bIsInGroup = (sGroup in glist)
    return bIsInGroup

def user_is_superuser(request):
    bFound = False
    # Is this user part of the indicated group?
    username = request.user.username
    if username != "":
        user = User.objects.filter(username=username).first()
        if user != None:
            bFound = user.is_superuser
    return bFound

def user_is_in_team(request):
    bResult = False
    username = request.user.username
    team_group = app_editor
    # Validate
    if username and team_group and username != "" and team_group != "":
        # First filter on owner
        owner = Profile.get_user_profile(username)
        # Now check for permissions
        bResult = (owner.user.groups.filter(name=team_group).first() != None)
    return bResult

def add_visit(request, name, is_menu):
    """Add the visit to the current path"""

    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous":
        Visit.add(username, name, request.path, is_menu)

def action_model_changes(form, instance):
    field_values = model_to_dict(instance)
    changed_fields = form.changed_data
    exclude = []
    if hasattr(form, 'exclude'):
        exclude = form.exclude
    changes = {}
    for item in changed_fields: 
        if item in field_values:
            changes[item] = field_values[item]
        elif item not in exclude:
            # It is a form field
            try:
                representation = form.cleaned_data[item]
                if isinstance(representation, QuerySet):
                    # This is a list
                    rep_list = []
                    for rep in representation:
                        rep_str = str(rep)
                        rep_list.append(rep_str)
                    representation = json.dumps(rep_list)
                elif isinstance(representation, str) or isinstance(representation, int):
                    representation = representation
                elif isinstance(representation, object):
                    representation = str(representation)
                changes[item] = representation
            except:
                changes[item] = "(unavailable)"
    return changes

def has_string_value(field, obj):
    response = (field != None and field in obj and obj[field] != None and obj[field] != "")
    return response

def has_list_value(field, obj):
    response = (field != None and field in obj and obj[field] != None and len(obj[field]) > 0)
    return response

def has_obj_value(field, obj):
    response = (field != None and field in obj and obj[field] != None)
    return response

def make_ordering(qs, qd, order_default, order_cols, order_heads):

    oErr = ErrHandle()

    try:
        bAscending = True
        sType = 'str'
        order = []
        colnum = ""
        # reset 'used' feature for all heads
        for item in order_heads: item['used'] = None
        if 'o' in qd and qd['o'] != "":
            colnum = qd['o']
            if '=' in colnum:
                colnum = colnum.split('=')[1]
            if colnum != "":
                order = []
                iOrderCol = int(colnum)
                bAscending = (iOrderCol>0)
                iOrderCol = abs(iOrderCol)

                # Set the column that it is in use
                order_heads[iOrderCol-1]['used'] = 1
                # Get the type
                sType = order_heads[iOrderCol-1]['type']
                for order_item in order_cols[iOrderCol-1].split(";"):
                    if order_item != "":
                        if sType == 'str':
                            order.append(Lower(order_item).asc(nulls_last=True))
                        else:
                            order.append(F(order_item).asc(nulls_last=True))
                if bAscending:
                    order_heads[iOrderCol-1]['order'] = 'o=-{}'.format(iOrderCol)
                else:
                    # order = "-" + order
                    order_heads[iOrderCol-1]['order'] = 'o={}'.format(iOrderCol)

                # Reset the sort order to ascending for all others
                for idx, item in enumerate(order_heads):
                    if idx != iOrderCol - 1:
                        # Reset this sort order
                        order_heads[idx]['order'] = order_heads[idx]['order'].replace("-", "")
        else:
            for order_item in order_default[0].split(";"):
                if order_item != "":
                    order.append(Lower(order_item))
           #  order.append(Lower(order_cols[0]))
        if sType == 'str':
            if len(order) > 0:
                qs = qs.order_by(*order)
        else:
            qs = qs.order_by(*order)
        # Possibly reverse the order
        if not bAscending:
            qs = qs.reverse()
    except:
        msg = oErr.get_error_message()
        oErr.DoError("seeker/views/make_ordering")
        lstQ = []

    return qs, order_heads, colnum

def process_visit(request, name, is_menu, **kwargs):
    """Process one visit and return updated breadcrumbs"""

    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous" and request.user.username != "":
        # Add the visit
        Visit.add(username, name, request.get_full_path(), is_menu, **kwargs)
        # Get the updated path list
        p_list = Profile.get_stack(username)
    else:
        p_list = []
        p_list.append({'name': 'Home', 'url': reverse('home')})
    # Return the breadcrumbs
    # return json.dumps(p_list)
    return p_list

def get_breadcrumbs(request, name, is_menu, lst_crumb=[], **kwargs):
    """Process one visit and return updated breadcrumbs"""

    # Initialisations
    p_list = []
    p_list.append({'name': 'Home', 'url': reverse('home')})
    # Find out who this is
    username = "anonymous" if request.user == None else request.user.username
    if username != "anonymous" and request.user.username != "":
        # Add the visit
        currenturl = request.get_full_path()
        Visit.add(username, name, currenturl, is_menu, **kwargs)
        # Set the full path, dependent on the arguments we get
        for crumb in lst_crumb:
            if len(crumb) == 2:
                p_list.append(dict(name=crumb[0], url=crumb[1]))
            else:
                pass
        # Also add the final one
        p_list.append(dict(name=name, url=currenturl))
    # Return the breadcrumbs
    return p_list



# ================ OTHER VIEW HELP FUNCTIONS ============================

def search_generic(s_view, cls, form, qd, username=None, team_group=None):
    """Generic queryset generation for searching"""

    qs = None
    oErr = ErrHandle()
    bFilter = False
    genForm = None
    oFields = {}
    try:
        bHasFormset = (len(qd) > 0)

        if bHasFormset:
            # Get the formset from the input
            lstQ = []
            prefix = s_view.prefix
            filters = s_view.filters
            searches = s_view.searches
            lstExclude = []

            if s_view.use_team_group:
                genForm = form(qd, prefix=prefix, username=username, team_group=team_group)
            else:
                genForm = form(qd, prefix=prefix)

            if genForm.is_valid():

                # Process the criteria from this form 
                oFields = genForm.cleaned_data

                # Adapt the search for empty lila codes
                if 'codetype' in oFields:
                    codetype = oFields['codetype']
                    if codetype == "non":
                        lstExclude = []
                        lstExclude.append(Q(equal__isnull=False))
                    elif codetype == "spe":
                        lstExclude = []
                        lstExclude.append(Q(equal__isnull=True))
                    # Reset the codetype
                    oFields['codetype'] = ""  
                    
                # Adapt search for soperator/scount
                if 'soperator' in oFields:
                    if not 'scount' in oFields or oFields['soperator'] == "-":
                        oFields.pop('soperator') 

                # Adapt search for mtype, if that is not specified
                if 'mtype' in oFields and oFields['mtype'] == "":
                    # Make sure we only select MAN and not TEM (template)
                    oFields['mtype'] = "man"
                                 
                # Create the search based on the specification in searches
                filters, lstQ, qd, lstExclude = make_search_list(filters, oFields, searches, qd, lstExclude)

                # Calculate the final qs
                if len(lstQ) == 0:
                    # No filter: Just show everything
                    qs = cls.objects.all()
                else:
                    # There is a filter: apply it
                    qs = cls.objects.filter(*lstQ).distinct()
                    bFilter = True
            else:
                # TODO: communicate the error to the user???

                # Just show NOTHING
                qs = cls.objects.none()

        else:
            # Just show everything
            qs = cls.objects.all().distinct()
    except:
        msg = oErr.get_error_message()
        oErr.DoError("search_generic")
        qs = None
        bFilter = False
    # Return the resulting filtered and sorted queryset
    return filters, bFilter, qs, qd, oFields

def search_collection(request):
    """Search for a collection"""

    # Set defaults
    template_name = "seeker/collection.html"

    # Get a link to a form
    searchForm = SearchCollectionForm()

    # Other initialisations
    currentuser = request.user
    authenticated = currentuser.is_authenticated

    # Create context and add to it
    context = dict(title="Search collection",
                   authenticated=authenticated,
                   searchForm=searchForm)
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Create and show the result
    return render(request, template_name, context)

def get_short_edit(short):
    # Strip off the year of the short reference in Litref, keep only first part (abbr and seriesnumber)

    result = None
    arResult = short.split("(")
    if len(arResult) > 1:
        result = arResult[0].strip()
    elif len(arResult) == 1:
        result = arResult[0].strip()
    return result

#def lila_action_add(view, instance, details, actiontype):
#    """User can fill this in to his/her liking"""

#    oErr = ErrHandle()
#    try:
#        # Check if this needs processing
#        stype_edi_fields = getattr(view, "stype_edi_fields", None)
#        if stype_edi_fields and not instance is None:
#            # Get the username: 
#            username = view.request.user.username
#            # Process the action
#            cls_name = instance.__class__.__name__
#            Action.add(username, cls_name, instance.id, actiontype, json.dumps(details))

#            # -------- DEBGGING -------
#            # print("lila_action_add type={}".format(actiontype))
#            # -------------------------

#            # Check the details:
#            if 'changes' in details:
#                changes = details['changes']
#                if 'stype' not in changes or len(changes) > 1:
#                    # Check if the current STYPE is *not* 'Edited*
#                    stype = getattr(instance, "stype", "")
#                    if stype != STYPE_EDITED:
#                        bNeedSaving = False
#                        key = ""
#                        if 'model' in details:
#                            bNeedSaving = details['model'] in stype_edi_fields
#                        if not bNeedSaving:
#                            # We need to do stype processing, if any of the change fields is in [stype_edi_fields]
#                            for k,v in changes.items():
#                                if k in stype_edi_fields:
#                                    bNeedSaving = True
#                                    key = k
#                                    break

#                        if bNeedSaving:
#                            # Need to set the stype to EDI
#                            instance.stype = STYPE_EDITED
#                            # Adapt status note
#                            snote = json.loads(instance.snote)
#                            snote.append(dict(date=get_crpp_date(get_current_datetime()), username=username, status=STYPE_EDITED, reason=key))
#                            instance.snote = json.dumps(snote)
#                            # Save it
#                            instance.save()
#    except:
#        msg = oErr.get_error_message()
#        oErr.DoError("lila_action_add")
#    # Now we are ready
#    return None

#def lila_get_history(instance):
#    lhtml= []
#    lhtml.append("<table class='table'><thead><tr><td><b>User</b></td><td><b>Date</b></td><td><b>Description</b></td></tr></thead><tbody>")
#    # Get the history for this item
#    lHistory = Action.get_history(instance.__class__.__name__, instance.id)
#    for obj in lHistory:
#        description = ""
#        if obj['actiontype'] == "new":
#            description = "Create New"
#        elif obj['actiontype'] == "add":
#            description = "Add"
#        elif obj['actiontype'] == "delete":
#            description = "Delete"
#        elif obj['actiontype'] == "change":
#            description = "Changes"
#        elif obj['actiontype'] == "import":
#            description = "Import Changes"
#        if 'changes' in obj:
#            lchanges = []
#            for key, value in obj['changes'].items():
#                lchanges.append("<b>{}</b>=<code>{}</code>".format(key, value))
#            changes = ", ".join(lchanges)
#            if 'model' in obj and obj['model'] != None and obj['model'] != "":
#                description = "{} {}".format(description, obj['model'])
#            description = "{}: {}".format(description, changes)
#        lhtml.append("<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(obj['username'], obj['when'], description))
#    lhtml.append("</tbody></table>")

#    sBack = "\n".join(lhtml)
#    return sBack

def get_pie_data():
    """Fetch data for a particular type of pie-chart for the home page
    
    Current types: 'canwit', 'austat', 'manu'
    """

    oErr = ErrHandle()
    red = 0
    orange = 0
    green = 0
    combidata = {}
    ptypes = ['canwit', 'austat', 'manu']
    try:
        for ptype in ptypes:
            qs = None
            if ptype == "canwit":
                qs = Canwit.objects.filter(msitem__isnull=False).order_by('stype').values('stype')
            elif ptype == "austat":
                qs = Austat.objects.filter(moved__isnull=True).order_by('stype').values('stype')
            elif ptype == "manu":
                qs = Manuscript.objects.filter(mtype='man').order_by('stype').values('stype')
            # Calculate the different stype values
            if qs != None:
                app = sum(x['stype'] == "app" for x in qs)  # Approved
                edi = sum(x['stype'] == "edi" for x in qs)  # Edited
                imp = sum(x['stype'] == "imp" for x in qs)  # Imported
                man = sum(x['stype'] == "man" for x in qs)  # Manually created
                und = sum(x['stype'] == "-" for x in qs)    # Undefined
                red = imp + und + man
                orange = edi
                green = app
            total = red + green + orange
            if total == 0:
                total = 100
                red = 20
                orange = 20
                green = 60
            # Create a list of data
            data = []
            data.append({'name': 'Initial', 'value': red, 'total': total})
            data.append({'name': 'Edited', 'value': orange, 'total': total})
            data.append({'name': 'Approved', 'value': green, 'total': total})
            combidata[ptype] = data
    except:
        msg = oErr.get_error_message()
        combidata['msg'] = msg
        combidata['status'] = "error"
    return combidata 




# ================= STANDARD views =====================================

def home(request, errortype=None):
    """Renders the home page."""

    assert isinstance(request, HttpRequest)
    # Specify the template
    template_name = 'index.html'
    # Define the initial context
    context =  {'title':'RU-lila',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)
    context['is_app_moderator'] = user_is_superuser(request) or user_is_ingroup(request, app_moderator)

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "Home", True)

    # See if this is the result of a particular error
    if errortype != None:
        if errortype == "404":
            context['is_404'] = True

    # Check the newsitems for validity
    NewsItem.check_until()

    # Create the list of news-items
    lstQ = []
    lstQ.append(Q(status='val'))
    newsitem_list = NewsItem.objects.filter(*lstQ).order_by('-created', '-saved')
    context['newsitem_list'] = newsitem_list

    # Gather the statistics
    context['count_canwit'] = Canwit.objects.exclude(mtype="tem").count()
    context['count_manu'] = Manuscript.objects.exclude(mtype="tem").count()

    # Gather pie-chart data
    context['pie_data'] = get_pie_data()

    # Render and return the page
    return render(request, template_name, context)

def view_404(request, *args, **kwargs):
    return home(request, "404")

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'Contact',
                'message':'Sven Meeder',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "Contact", True)

    return render(request,'contact.html', context)

def more(request):
    """Renders the more page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'More',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "More", True)

    return render(request,'more.html', context)

def technical(request):
    """Renders the technical information page."""
    assert isinstance(request, HttpRequest)
    # Specify the template
    template_name = 'technical.html'
    context =  {'title':'Technical',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)
    context['is_app_moderator'] = user_is_superuser(request) or user_is_ingroup(request, app_moderator)

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "Technical", True)

    return render(request,template_name, context)

def guide(request):
    """Renders the user-manual (guide) page."""
    assert isinstance(request, HttpRequest)
    # Specify the template
    template_name = 'guide.html'
    context =  {'title':'User manual',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)
    context['is_app_moderator'] = user_is_superuser(request) or user_is_ingroup(request, app_moderator)

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "Guide", True)

    return render(request,template_name, context)

def bibliography(request):
    """Renders the more page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'Bibliography',
                'year':datetime.now().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Add the edition references (abreviated and full)



    # Create empty list for the editions
    edition_list = []
    
    # Retrieve all records from the Zotero database (user for now)
    zot = zotero.Zotero('5802673', 'user', 'oVBhIJH5elqA8zxrJGwInwWd')
    
    # Store only the records from the Edition collection (key: from URL 7HQU3AY8)
    zot_editions = zot.collection_items('7HQU3AY8')
   
    for item in zot_editions:
        creators_ed = item['data']['creators']
        creator_list_ed = []
        for creator in creators_ed:
            first_name = creator['firstName']
            last_name = creator['lastName']
            creator_list_ed.append(first_name + " " + last_name)
        edition_list.append({'abbr': item['data']['extra'] + ", " + item['data']['pages'], 'full': item['data']['title'], 'creators': ", ".join(creator_list_ed)})
   
    context['edition_list'] = edition_list    
    
    # Add the literature references from zotero, data extra 
        
    # Create empty list for the literature
    
    reference_list = [] 
    
    # Retrieve all records from the Zotero database (user for now)
    zot = zotero.Zotero('5802673', 'user', 'oVBhIJH5elqA8zxrJGwInwWd')
    
    # Store only the records in the Literature collection,  (key: from URL FEPVSGVX)
    zot_literature = zot.collection_items('FEPVSGVX')
        
    
    for item in zot_literature:
        creators = item['data']['creators']
        creator_list = []
        for creator in creators:
            first_name = creator['firstName']
            last_name = creator['lastName']
            creator_list.append(first_name + " " + last_name)
        reference_list.append({'abbr':creator['lastName'] + ", " + item['data']['extra'] + " " + item['data']['volume'] + " (" + item['data']['date']+ ")"+", "+item['data']['pages'], 'full': item['data']['title'], 'creators': ", ".join(creator_list)})
    context['reference_list'] = reference_list

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "Bibliography", True)

    return render(request,'bibliography.html', context)

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    context =  {'title':'About',
                'message':'Radboud University lila utility.',
                'year':get_current_datetime().year,
                'pfx': APP_PREFIX,
                'site_url': admin.site.site_url}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)

    # Calculate statistics
    sites = {}
    people = {}
    for obj in SourceInfo.objects.all().order_by('url', 'collector'):
        if obj.url == None or obj.url == "":
            # Look at PEOPLE
            collector = obj.collector
            if collector != None and collector != "":
                if not collector in people:
                    people[collector] = obj.sourcemanuscripts.filter(mtype='man').count()
                else:
                    people[collector] += obj.sourcemanuscripts.filter(mtype='man').count()
        elif obj.url != None and obj.url != "":
            # Look at SITES
            collector = obj.url
            if collector != None and collector != "":
                if not collector in sites:
                    sites[collector] = obj.sourcemanuscripts.filter(mtype='man').count()
                else:
                    sites[collector] += obj.sourcemanuscripts.filter(mtype='man').count()
    context['sites'] = [{"url": k, "count": v} for k,v in sites.items()]
    people_lst = [{"count": v, "person": k} for k,v in people.items()]
    people_lst = sorted(people_lst, key = lambda x: x['count'], reverse=True)
    context['people'] = people_lst

    # Process this visit
    context['breadcrumbs'] = get_breadcrumbs(request, "About", True)

    return render(request,'about.html', context)

def short(request):
    """Renders the page with the short instructions."""

    assert isinstance(request, HttpRequest)
    template = 'short.html'
    context = {'title': 'Short overview',
               'message': 'Radboud University lila short intro',
               'year': get_current_datetime().year}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    return render(request, template, context)

def nlogin(request):
    """Renders the not-logged-in page."""
    assert isinstance(request, HttpRequest)
    context =  {    'title':'Not logged in', 
                    'message':'Radboud University lila utility.',
                    'year':get_current_datetime().year,}
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    return render(request,'nlogin.html', context)

def login_as_user(request, user_id):
    assert isinstance(request, HttpRequest)

    # Find out who I am
    supername = request.user.username
    super = User.objects.filter(username__iexact=supername).first()
    if super == None:
        return nlogin(request)

    # Make sure that I am superuser
    if super.is_staff and super.is_superuser:
        user = User.objects.filter(username__iexact=user_id).first()
        if user != None:
            # Perform the login
            login(request, user)
            return HttpResponseRedirect(reverse("home"))

    return home(request)

def signup(request):
    """Provide basic sign up and validation of it """

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Save the form
            form.save()
            # Create the user
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            # also make sure that the user gets into the STAFF,
            #      otherwise he/she may not see the admin pages
            user = authenticate(username=username, 
                                password=raw_password,
                                is_staff=True)
            user.is_staff = True
            user.save()
            # Add user to the "lila_user" group
            gQs = Group.objects.filter(name="lila_user")
            if gQs.count() > 0:
                g = gQs[0]
                g.user_set.add(user)
            # Log in as the user
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

# ============= MYLILA ====================================

def mylila(request):
    """Renders the MyLila page (=PRE)."""
    
    oErr = ErrHandle()
    try:
        # Get the request right
        assert isinstance(request, HttpRequest)

        # Double check: the person must have been logged-in
        if not user_is_authenticated(request):
            # Indicate that use must log in
            return nlogin(request)

        # Specify the template
        template_name = 'mylila.html'
        context =  {'title':'My Lila',
                    'year':get_current_datetime().year,
                    'pfx': APP_PREFIX,
                    'site_url': admin.site.site_url}
        context = get_application_context(request, context)

        profile = Profile.get_user_profile(request.user.username)
        context['profile'] = profile
        context['rset_count'] = 0   # ResearchSet.objects.filter(profile=profile).count()
        context['dct_count'] = 0    # SetDef.objects.filter(researchset__profile=profile).count()
        context['count_datasets'] = Collection.objects.filter(settype="pd", owner=profile).count()

        # Figure out any editing rights
        qs = profile.projects.all()
        context['edit_projects'] = "(none)"
        if context['is_app_editor'] and qs.count() > 0:
            html = []
            for obj in qs:
                url = reverse('project_details', kwargs={'pk': obj.id})
                html.append("<span class='project'><a href='{}'>{}</a></span>".format(url, obj.name))
            context['edit_projects'] = ",".join(html)

        # Figure out which projects this editor may handle
        if context['is_app_editor']:
            qs = profile.project_editor.filter(status="incl")
            if qs.count() == 0:
                sDefault = "(none)"
            else:
                html = []
                for obj in qs:
                    project = obj.project
                    url = reverse('project_details', kwargs={'pk': project.id})
                    html.append("<span class='project'><a href='{}'>{}</a></span>".format(url, project.name))
                sDefault = ", ".join(html)
            context['default_projects'] = sDefault

        # Process this visit
        context['breadcrumbs'] = get_breadcrumbs(request, "My Lila", True)
    except:
        msg = oErr.get_error_message()
        oErr.DoError("mylila")

    return render(request,template_name, context)


# ============= Other SUPPORT functions ===================

def get_cnrs_manuscripts(city, library):
    """Get the manuscripts held in the library"""

    oErr = ErrHandle()
    sBack = ""
    try:
        # Get the code of the city
        obj = City.objects.filter(name__iexact=city.name).first()
        if obj != None:
            # Get the code of the city
            idVille = obj.idVilleEtab
            # Build the query
            url = "{}/Manuscrits/manuscritforetablissement".format(cnrs_url)
            data = {"idEtab": library, "idVille": idVille}
            try:
                r = requests.post(url, data=data)
            except:
                sMsg = oErr.get_error_message()
                oErr.DoError("Request problem")
                return "Request problem: {}".format(sMsg)
            # Decypher the response
            if r.status_code == 200:
                # Return positively
                sText = r.text.replace("\t", " ")
                reply = json.loads(sText)
                if reply != None and "items" in reply:
                    results = []
                    for item in reply['items']:
                        if item['name'] != "":
                            results.append(item['name'])

                    # Interpret the results
                    lst_manu = []
                    for item in results:
                        lst_manu.append("<span class='manuscript'>{}</span>".format(item))
                    sBack = "\n".join(lst_manu)
    except:
        msg = oErr.get_error_message()
        sBack = "Error: {}".format(msg)
        oErr.DoError("get_cnrs_manuscripts")
    return sBack




# ============= LOCATION VIEWS ============================


class LocationListView(BasicList):
    """Listview of locations"""

    model = Location
    listform = LocationForm
    paginate_by = 15
    prefix = "loc"
    has_select2 = True
    order_cols = ['name', 'loctype__name', '', '']
    order_default = order_cols
    order_heads = [{'name': 'Name',         'order': 'o=1', 'type': 'str', 'custom': 'location', 'linkdetails': True, 'main': True},
                   {'name': 'Type',         'order': 'o=2', 'type': 'str', 'custom': 'loctype',  'linkdetails': True},
                   {'name': 'Part of...',   'order': '',    'type': 'str', 'custom': 'partof'},
                   {'name': '',             'order': '',    'type': 'str', 'custom': 'manulink' }]
    filters = [ {"name": "Name",    "id": "filter_location",    "enabled": False},
                {"name": "Type",    "id": "filter_loctype",     "enabled": False},
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'location', 'dbfield': 'name',       'keyS': 'location_ta', 'keyList': 'locchooser', 'infield': 'name' },
            {'filter': 'loctype',  'fkfield': 'loctype',    'keyList': 'loctypechooser', 'infield': 'name' }]}
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        if custom == "location":
            html.append(instance.name)
        elif custom == "loctype":
            sLocType = "-"
            if instance.loctype != None:
                sLocType = instance.loctype.name
            html.append(sLocType)
        elif custom == "partof":
            sName = instance.get_partof_html()
            if sName == "": sName = "<i>(part of nothing)</i>"
            html.append(sName)
        elif custom == "manulink":
            # This is currently unused
            pass
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle


class LocationEdit(BasicDetails):
    model = Location
    mForm = LocationForm
    prefix = "loc"
    title = "Location details"
    history_button = True
    mainitems = []

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",                     'value': instance.name,         'field_key': "name"},
            {'type': 'line',  'label': "Location type:",            'value': instance.loctype.name, 'field_key': 'loctype'},
            {'type': 'line',  'label': "This location is part of:", 'value': instance.get_partof_html(),   
             'field_list': "locationlist"}
            ]

        # Signal that we have select2
        context['has_select2'] = True

        # Return the context we have made
        return context

    def after_save(self, form, instance):
        """This is for processing items from the list of available ones"""

        msg = ""
        bResult = True
        oErr = ErrHandle()
        
        try:
            # Process many-to-many changes: Add and remove relations in accordance with the new set passed on by the user
            if getattr(form, 'cleaned_data') != None:
                # (1) 'locations'
                locationlist = form.cleaned_data['locationlist']
                adapt_m2m(LocationRelation, instance, "contained", locationlist, "container")
            
        except:
            msg = oErr.get_error_message()
            bResult = False
        return bResult, msg

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class LocationDetails(LocationEdit):
    """Like Location Edit, but then html output"""
    rtype = "html"
    

# ============= ORIGIN VIEWS ============================


class OriginListView(BasicList):
    """Listview of origins"""

    model = Origin
    listform = OriginForm
    prefix = "prj"
    has_select2 = True
    paginate_by = 15
    page_function = "ru.lila.seeker.search_paged_start"
    order_cols = ['name', 'location', 'note', '']
    order_default = order_cols
    order_heads = [{'name': 'Name',     'order': 'o=1', 'type': 'str', 'custom': 'origin', 'main': True, 'linkdetails': True},
                   {'name': 'Location', 'order': 'o=2', 'type': 'str', 'custom': 'location'},
                   {'name': 'Note',     'order': 'o=3', 'type': 'str', 'custom': 'note'},
                   {'name': '',         'order': '',    'type': 'str', 'custom': 'manulink' }]
    filters = [ {"name": "Location",        "id": "filter_location",    "enabled": False},
                {"name": "Shelfmark",       "id": "filter_manuid",      "enabled": False, "head_id": "filter_other"},
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'location', 'dbfield': 'name', 'keyS': 'location_ta', 'keyList': 'locationlist', 'infield': 'name' }]}
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        if custom == "manulink":
            # Link to manuscripts in this project
            count = instance.origin_manuscripts.all().count()
            url = reverse('manuscript_list')
            if count > 0:
                html.append("<a href='{}?manu-origin={}'><span class='badge jumbo-3 clickable' title='{} manuscripts with this origin'>{}</span></a>".format(
                    url, instance.id, count, count))
        elif custom == "location":
            sLocation = ""
            if instance.location:
                sLocation = instance.location.name
            html.append(sLocation)
        elif custom == "note":
            sNote = "" if not instance.note else instance.note
            html.append(sNote)
        elif custom == "origin":
            sName = instance.name
            if sName == "": sName = "<i>(unnamed)</i>"
            html.append(sName)
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle


class OriginEdit(BasicDetails):
    """The details of one origin"""

    model = Origin
    mForm = OriginForm
    prefix = "org"
    title = "Origin" 
    rtype = "json"
    basic_name = "origin"
    history_button = True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",             'value': instance.name,         'field_key': "name"},
            {'type': 'line',  'label': "Origin note:",      'value': instance.note,         'field_key': 'note'},
            {'type': 'plain', 'label': "Origin location:",  'value': instance.get_location(),   'field_key': "location"}
            ]

        # Signal that we have select2
        context['has_select2'] = True

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class OriginDetails(OriginEdit):
    """Like Origin Edit, but then html output"""
    rtype = "html"
    

class OriginCodEdit(BasicDetails):
    """The details of one 'origin'"""

    model = OriginCodico
    mForm = OriginCodForm
    prefix = 'cori'
    title = "CodicoOrigin"
    history_button = False # True
    # rtype = "json"
    # mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'safe',  'label': "Origin:",   'value': instance.get_origin()},
            {'type': 'plain', 'label': "Note:",         'value': instance.note,   'field_key': 'note'     },
            ]

        # Signal that we have select2
        context['has_select2'] = True

        context['listview'] = reverse("codico_details", kwargs={'pk': instance.codico.id})

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class OriginCodDetails(OriginCodEdit):
    """Like OriginCodico Edit, but then html output"""
    rtype = "html"
        

# ============= EDITOR PROVIDED GENRE VIEWS ============================


class GenreEdit(BasicDetails):
    """The details of one genre"""

    model = Genre
    mForm = GenreForm
    prefix = 'gnr'
    title = "GenreEdit"
    rtype = "json"
    history_button = True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",       'value': instance.name,                     'field_key': 'name'},
            {'type': 'plain', 'label': "Description:",'value': instance.description,              'field_key': 'description'}
            ]
        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class GenreDetails(GenreEdit):
    """Like Genre Edit, but then html output"""
    rtype = "html"
    

class GenreListView(BasicList):
    """Search and list genres"""

    model = Genre
    listform = GenreForm
    prefix = "gnr"
    has_select2 = True
    in_team = False
    order_cols = ['name', '']
    order_default = order_cols
    order_heads = [{'name': 'Genre',     'order': 'o=1', 'type': 'str', 'field': 'name', 'default': "(unnamed)", 'main': True, 'linkdetails': True},
                   {'name': 'Frequency', 'order': '', 'type': 'str', 'custom': 'links'}]
    filters = [ {"name": "Genre",         "id": "filter_genre",     "enabled": False},
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'genre',    'dbfield': 'name',   'keyS': 'genre_ta', 'keyList': 'kwlist', 'infield': 'name' },
            ]}
        ]

    def initializations(self):
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "links":
            html = []
            # Get the HTML code for the links of this instance
            #number = instance.freqcanwit()
            #if number > 0:
            #    url = reverse('canwit_list')
            #    html.append("<a href='{}?sermo-genrelist={}'>".format(url, instance.id))
            #    html.append("<span class='badge jumbo-1 clickable' title='Frequency in manifestation sermons'>{}</span></a>".format(number))
            #number = instance.freqmanu()
            #if number > 0:
            #    url = reverse('manuscript_list')
            #    html.append("<a href='{}?manu-genrelist={}'>".format(url, instance.id))
            #    html.append("<span class='badge jumbo-3 clickable' title='Frequency in manuscripts'>{}</span></a>".format(number))
            number = instance.freqsuper()
            if number > 0:
                url = reverse('austat_list')
                html.append("<a href='{}?as-genrelist={}'>".format(url, instance.id))
                html.append("<span class='badge jumbo-4 clickable' title='Frequency in manuscripts'>{}</span></a>".format(number))
            # Combine the HTML code
            sBack = "\n".join(html)

        return sBack, sTitle


# ============= EDITOR PROVIDED LITREF VIEWS ============================


class LitrefEdit(BasicDetails):
    """The details of one litref"""

    model = Litref
    mForm = LitrefForm
    prefix = 'lit'
    title = "Litref Details"
    rtype = "json"
    no_delete = True
    permission = "readonly"
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show 
        # NOTE: do *NOT* allow editing. That should take place within Zotero
        context['mainitems'] = [
            {'type': 'safe',  'label': "Short:",    'value': instance.get_short_markdown()   },
            {'type': 'safe',  'label': "Full:",     'value': instance.get_full_markdown()    },
            {'type': 'plain', 'label': "Created:",  'value': instance.get_created() },
            {'type': 'plain', 'label': "Saved:",    'value': instance.get_saved()   }
            ]
        # Return the context we have made
        return context


class LitrefDetails(LitrefEdit):
    """Like Litref Edit, but then html output"""
    rtype = "html"
    

class LitrefListView(BasicList):
    """Search and list litrefs"""

    model = Litref
    listform = LitrefForm
    prefix = "lit"
    has_select2 = True
    in_team = False
    new_button = False
    bUseFilter = True
    order_cols = ['short', 'full', 'saved']
    order_default = order_cols
    order_heads = [
        {'name': 'Short',   'order': 'o=1', 'type': 'str', 'field': 'short', 'linkdetails': True},
        {'name': 'Full',    'order': 'o=2', 'type': 'str', 'custom': 'full', 'linkdetails': True, 'main': True},
        {'name': 'Date',    'order': 'o=3', 'type': 'str', 'custom': 'date', 'linkdetails': True,
         'title':   'Date when this literature reference has been last updated'}]
    filters = [ 
        {"name": "Full",    "id": "filter_full",     "enabled": False},
        ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'full',    'dbfield': 'full',   'keyS': 'full_ta'   },
            ]}
        ]

    def initializations(self):
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "full":
            sBack = instance.get_full_markdown()
        elif custom == "date":
            sBack = instance.get_saved()

        return sBack, sTitle

    def adapt_search(self, fields):
        lstExclude=None
        qAlternative = None

        # Make sure empty references are not shown
        lstExclude = [ Q(short__isnull=True) | Q(short="") ]      
       
        return fields, lstExclude, qAlternative


# ============= AUWORK VIEWS ============================================


class AuworkEdit(BasicDetails):
    """The details of one genre"""

    model = Auwork
    mForm = AuworkForm
    prefix = 'wrk'
    title = "WorkEdit"
    rtype = "json"
    prefix_type = "simple"
    history_button = True
    mainitems = []

    WediFormSet = inlineformset_factory(Auwork, EdirefWork,
                                         form = AuworkEditionForm, min_num=0,
                                         fk_name = "auwork",
                                         extra=0, can_delete=True, can_order=False)

    formset_objects = [{'formsetClass': WediFormSet,  'prefix': 'wedi',  'readonly': False, 'noinit': True, 'linkfield': 'auwork'}]

    stype_edi_fields = ['key', 'opus', 'work', 'date', 'full',
                        'EdirefWork', 'edilist']

    def custom_init(self, instance):
        # Check if there is a 'key' parameter
        if instance is None:
            key = self.qd.get("wrk-key")
            if not key is None:
                self.object = Auwork.objects.create(key=key)
        return None
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        oErr = ErrHandle()
        try:
            # Define the main items to show and edit
            context['mainitems'] = [
                {'type': 'plain', 'label': "Key code:",         'value': instance.key,  'field_key': 'key'},
                {'type': 'plain', 'label': "Opus:",             'value': instance.opus, 'field_key': 'opus'},
                {'type': 'plain', 'label': "Work:",             'value': instance.work, 'field_key': 'work'},
                {'type': 'plain', 'label': "Date:",             'value': instance.date, 'field_key': 'date'},
                {'type': 'plain', 'label': "Full description:", 'value': instance.full, 'field_key': 'full'},
                {'type': 'line',  'label': "Genre(s):",         'value': instance.get_genres_markdown(),   'field_list': 'genrelist'},
                {'type': 'line',  'label': "Keywords:",         'value': instance.get_keywords_markdown(), 'field_list': 'kwlist'},
                {'type': 'line',  'label': "Editions:",         'value': instance.get_edirefs_markdown(),
                 'multiple': True, 'field_list': 'edilist', 'fso': self.formset_objects[0], 'template_selection': 'ru.lila.litref_template'}
                ]

            # Signal that we have select2
            context['has_select2'] = True

        except:
            msg = oErr.get_error_message()
            oErr.DoError("AuworkEdit/add_to_context")

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def after_save(self, form, instance):
        msg = ""
        bResult = True
        oErr = ErrHandle()
                
        try:
            # Process many-to-many changes: Add and remove relations in accordance with the new set passed on by the user
            # (1) 'editions'
            edilist = form.cleaned_data['edilist']
            adapt_m2m(EdirefWork, instance, "auwork", edilist, "reference", extra=['pages'], related_is_through = True)

            # (2) 'genres'
            genrelist = form.cleaned_data['genrelist']
            adapt_m2m(AuworkGenre, instance, "auwork", genrelist, "genre")

            # (3) 'keywords'
            kwlist = form.cleaned_data['kwlist']
            adapt_m2m(AuworkKeyword, instance, "auwork", kwlist, "keyword")

        except:
            msg = oErr.get_error_message()
            bResult = False
        return bResult, msg

    def get_history(self, instance):
        return lila_get_history(instance)

    def process_formset(self, prefix, request, formset):

        errors = []
        bResult = True
        instance = formset.instance
        for form in formset:
            if form.is_valid():
                cleaned = form.cleaned_data

                if prefix == "wedi":
                    # Edition processing
                    newpages = ""
                    if 'newpages' in cleaned and cleaned['newpages'] != "":
                        newpages = cleaned['newpages']
                    # Also get the litref
                    if 'oneref' in cleaned:
                        litref = cleaned['oneref']
                        # Check if all is in order
                        if litref:
                            form.instance.reference = litref
                            if newpages:
                                form.instance.pages = newpages
                    # Note: it will get saved with form.save()
            else:
                errors.append(form.errors)
                bResult = False
        return None


class AuworkDetails(AuworkEdit):
    """Like Auwork Edit, but then html output"""
    rtype = "html"

    def add_to_context(self, context, instance):
        # First get the 'standard' context from AuworkEdit
        context = super(AuworkDetails, self).add_to_context(context, instance)

        context['sections'] = []

        oErr = ErrHandle()
        try:

            # Lists of related objects
            related_objects = []
            resizable = True
            index = 1
            sort_start = '<span class="sortable"><span class="fa fa-sort sortshow"></span>&nbsp;'
            sort_start_int = '<span class="sortable integer"><span class="fa fa-sort sortshow"></span>&nbsp;'
            sort_end = '</span>'

            # List of Sermons that link to this feast (with an FK)
            austats = dict(title="Authorative statements with this work", prefix="austat")
            if resizable: austats['gridclass'] = "resizable"

            rel_list =[]
            qs = Austat.objects.filter(auwork=instance).order_by('keycode')
            for item in qs:
                # Fields: author, keycode, full text

                url = reverse('austat_details', kwargs={'pk': item.id})
                rel_item = []

                # S: Order number for this austat
                add_rel_item(rel_item, index, False, align="right")
                index += 1

                # Author
                author_txt = item.get_author()
                add_rel_item(rel_item, author_txt, False, main=False, link=url)

                # Key code
                keycode_txt = item.get_keycode()
                add_rel_item(rel_item, keycode_txt, False, main=False, link=url)

                # Work
                work_txt = item.get_work()
                add_rel_item(rel_item, work_txt, False, main=True, link=url)


                # Add this line to the list
                rel_list.append(dict(id=item.id, cols=rel_item))

            austats['rel_list'] = rel_list

            austats['columns'] = [
                '{}<span>#</span>{}'.format(sort_start_int, sort_end), 
                '{}<span>Author</span>{}'.format(sort_start, sort_end), 
                '{}<span>Key code</span>{}'.format(sort_start, sort_end), 
                '{}<span>Work</span>{}'.format(sort_start_int, sort_end)
                ]
            related_objects.append(austats)

            # Add all related objects to the context
            context['related_objects'] = related_objects
        except:
            msg = oErr.get_error_message()
            oErr.DoError("AuworkDetails/get_field_value")

        # Return the context we have made
        return context
    

class AuworkListView(BasicList):
    """Search and list genres"""

    model = Auwork
    listform = AuworkForm
    prefix = "wrk"
    has_select2 = True
    in_team = False
    order_cols = ['key', 'work', 'opus', 'date', '']
    order_default = order_cols
    order_heads = [
        {'name': 'Key code',  'order': 'o=1', 'type': 'str', 'field': 'key',  'linkdetails': True},
        {'name': 'Work',      'order': 'o=2', 'type': 'str', 'field': 'work', 'linkdetails': True, 'main': True},
        {'name': 'Opus',      'order': 'o=3', 'type': 'str', 'field': 'opus', 'linkdetails': True},
        {'name': 'Date',      'order': 'o=4', 'type': 'str', 'field': 'date', 'linkdetails': True},
        {'name': 'Frequency', 'order': '',    'type': 'str', 'custom': 'links'},
        ]
    filters = [ 
        {"name": "Key code",    "id": "filter_keycode", "enabled": False},
        {"name": "Work",        "id": "filter_work",    "enabled": False},
        {"name": "Opus",        "id": "filter_opus",    "enabled": False},
        ]
    searches = [
        {'section': '', 'filterlist': [
            #{'filter': 'keycode',   'dbfield': 'key',   'keyS': 'keycode_ta', 'keyList': 'keylist',  'infield': 'name' },
            #{'filter': 'work',      'dbfield': 'work',  'keyS': 'work_ta',    'keyList': 'worklist', 'infield': 'name' },
            #{'filter': 'opus',      'dbfield': 'opus',  'keyS': 'opus_ta',    'keyList': 'opuslist', 'infield': 'name' },
            {'filter': 'keycode',   'dbfield': 'key',   'keyS': 'key_ta'},
            {'filter': 'work',      'dbfield': 'work',  'keyS': 'work_ta' },
            {'filter': 'opus',      'dbfield': 'opus',  'keyS': 'opus_ta' },
            ]}
        ]

    def initializations(self):
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "links":
            # Get the number of Austat linked to this Work
            html = []
            number = Austat.objects.filter(auwork=instance).count()
            if number > 0:
                url = reverse('austat_list')
                html.append("<a href='{}?as-worklist={}'>".format(url, instance.id))
                html.append("<span class='badge jumbo-4 clickable' title='Frequency in Authoritative Statements'>{}</span></a>".format(number))
            # Combine the HTML code
            sBack = "\n".join(html)

        return sBack, sTitle


# ============= EDITOR PROVIDED KEYWORD VIEWS ============================


class KeywordEdit(BasicDetails):
    """The details of one keyword"""

    model = Keyword
    mForm = KeywordForm
    prefix = 'kw'
    title = "KeywordEdit"
    rtype = "json"
    history_button = True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",       'value': instance.name,                     'field_key': 'name'},
            {'type': 'plain', 'label': "Visibility:", 'value': instance.get_visibility_display(), 'field_key': 'visibility'},
            {'type': 'plain', 'label': "Description:",'value': instance.description,              'field_key': 'description'}
            ]
        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class KeywordDetails(KeywordEdit):
    """Like Keyword Edit, but then html output"""
    rtype = "html"
    

class KeywordListView(BasicList):
    """Search and list keywords"""

    model = Keyword
    listform = KeywordForm
    prefix = "kw"
    paginate_by = 20
    # template_name = 'seeker/keyword_list.html'
    has_select2 = True
    in_team = False
    page_function = "ru.lila.seeker.search_paged_start"
    order_cols = ['name', 'visibility', '']
    order_default = order_cols
    order_heads = [{'name': 'Keyword',    'order': 'o=1', 'type': 'str', 'field': 'name', 'default': "(unnamed)", 'main': True, 'linkdetails': True},
                   {'name': 'Visibility', 'order': 'o=2', 'type': 'str', 'custom': 'visibility'},
                   {'name': 'Frequency', 'order': '', 'type': 'str', 'custom': 'links'}]
    filters = [ {"name": "Keyword",         "id": "filter_keyword",     "enabled": False},
                {"name": "Visibility",      "id": "filter_visibility",  "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'keyword',    'dbfield': 'name',         'keyS': 'keyword_ta', 'keyList': 'kwlist', 'infield': 'name' },
            {'filter': 'visibility', 'dbfield': 'visibility',   'keyS': 'visibility' }]}
        ]

    def initializations(self):
        # Check out who I am
        in_team = user_is_in_team(self.request)
        self.in_team = in_team
        if in_team:
            self.order_cols = ['name', 'visibility', '']
            self.order_default = self.order_cols
            self.order_heads = [
                {'name': 'Keyword',    'order': 'o=1', 'type': 'str', 'field': 'name', 'default': "(unnamed)", 'main': True, 'linkdetails': True},
                {'name': 'Visibility', 'order': 'o=2', 'type': 'str', 'custom': 'visibility'},
                {'name': 'Frequency', 'order': '', 'type': 'str', 'custom': 'links'}]
            self.filters = [ {"name": "Keyword",         "id": "filter_keyword",     "enabled": False},
                             {"name": "Visibility",      "id": "filter_visibility",  "enabled": False}]
            self.searches = [
                {'section': '', 'filterlist': [
                    {'filter': 'keyword',    'dbfield': 'name',         'keyS': 'keyword_ta', 'keyList': 'kwlist', 'infield': 'name' },
                    {'filter': 'visibility', 'dbfield': 'visibility',   'keyS': 'visibility' }]}
                ]
            self.bUseFilter = False
        else:
            self.order_cols = ['name', '']
            self.order_default = self.order_cols
            self.order_heads = [
                {'name': 'Keyword',    'order': 'o=1', 'type': 'str', 'field': 'name', 'default': "(unnamed)", 'main': True, 'linkdetails': True},
                {'name': 'Frequency', 'order': '', 'type': 'str', 'custom': 'links'}]
            self.filters = [ {"name": "Keyword",         "id": "filter_keyword",     "enabled": False}]
            self.searches = [
                {'section': '', 'filterlist': [
                    {'filter': 'keyword',    'dbfield': 'name',         'keyS': 'keyword_ta', 'keyList': 'kwlist', 'infield': 'name' }]},
                {'section': 'other', 'filterlist': [
                    {'filter': 'visibility', 'dbfield': 'visibility',   'keyS': 'visibility' }
                    ]}
                ]
            self.bUseFilter = True
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "links":
            html = []
            # Get the HTML code for the links of this instance
            number = instance.freqcanwit()
            if number > 0:
                url = reverse('canwit_list')
                html.append("<a href='{}?sermo-kwlist={}'>".format(url, instance.id))
                html.append("<span class='badge jumbo-1 clickable' title='Frequency in manifestation sermons'>{}</span></a>".format(number))
            number = instance.freqmanu()
            if number > 0:
                url = reverse('manuscript_list')
                html.append("<a href='{}?manu-kwlist={}'>".format(url, instance.id))
                html.append("<span class='badge jumbo-3 clickable' title='Frequency in manuscripts'>{}</span></a>".format(number))
            number = instance.freqsuper()
            if number > 0:
                url = reverse('austat_list')
                html.append("<a href='{}?ssg-kwlist={}'>".format(url, instance.id))
                html.append("<span class='badge jumbo-4 clickable' title='Frequency in manuscripts'>{}</span></a>".format(number))
            # Combine the HTML code
            sBack = "\n".join(html)
        elif custom == "visibility":
            sBack = instance.get_visibility_display()
        return sBack, sTitle

    def adapt_search(self, fields):
        lstExclude=None
        qAlternative = None
        if not self.in_team:
            # restrict access to "all" marked ons
            fields['visibility'] = "all"

        return fields, lstExclude, qAlternative


# ============= USER-SPECIFIED KEYWORD VIEWS ============================


class UserKeywordEdit(BasicDetails):
    """The details of one 'user-keyword': one that has been linked by a user"""

    model = UserKeyword
    mForm = UserKeywordForm
    prefix = 'ukw'
    title = "UserKeywordEdit"
    rtype = "json"
    history_button = True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "User:",     'value': instance.get_profile_markdown(),    },
            {'type': 'plain', 'label': "Keyword:",  'value': instance.keyword.name,     },
            {'type': 'plain', 'label': "Type:",     'value': instance.get_type_display()},
            {'type': 'plain', 'label': "Link:",     'value': self.get_link(instance)},
            {'type': 'plain', 'label': "Proposed:", 'value': instance.created.strftime("%d/%b/%Y %H:%M")}
            ]

        if context['is_app_editor']:
            lhtml = []
            lbuttons = [dict(href="{}?approvelist={}".format(reverse('userkeyword_list'), instance.id), 
                             label="Approve Keyword", 
                             title="Approving this keyword attaches it to the target and removes it from the list of user keywords.")]
            lhtml.append("<div class='row'><div class='col-md-12' align='right'>")
            for item in lbuttons:
                lhtml.append("  <a role='button' class='btn btn-xs jumbo-3' title='{}' href='{}'>".format(item['title'], item['href']))
                lhtml.append("     <span class='glyphicon glyphicon-ok'></span>{}</a>".format(item['label']))
            lhtml.append("</div></div>")
            context['after_details'] = "\n".join(lhtml)

        # Return the context we have made
        return context

    def get_link(self, instance):
        details = ""
        value = ""
        url = ""
        sBack = ""
        if instance.type == "manu" and instance.manu: 
            # Manuscript: shelfmark
            url = reverse('manuscript_details', kwargs = {'pk': instance.manu.id})
            value = instance.manu.idno
            sBack = "<span class='badge signature ot'><a href='{}'>{}</a></span>".format(url, value)
        elif instance.type == "sermo" and instance.sermo: 
            # Sermon (manifestation): Gryson/Clavis + shelf mark (of M)
            sig = instance.sermo.get_eqsetsignatures_markdown("first")
            # Sermon identification
            url = reverse('canwit_details', kwargs = {'pk': instance.sermo.id})
            # value = "{}/{}".format(instance.sermo.order, instance.sermo.manu.manusermons.all().count())
            value = "{}/{}".format(instance.sermo.order, instance.sermo.manu.get_canwit_count())
            sermo = "<span><a href='{}'>sermon {}</a></span>".format(url, value)
            # Manuscript shelfmark
            url = reverse('manuscript_details', kwargs = {'pk': instance.sermo.manu.id})
            manu = "<span class='badge signature ot'><a href='{}'>{}</a></span>".format(url, instance.sermo.manu.idno)
            # Combine
            sBack = "{} {} {}".format(sermo, manu, sig)
        elif instance.type == "austat" and instance.austat: 
            # Get signatures
            sig = instance.austat.get_goldsigfirst()
            # Get Gold URL
            url = reverse('austat_details', kwargs = {'pk': instance.austat.id})
            # Combine
            sBack = "<span class='badge signature ot'><a href='{}'>{}</a></span> {}".format(url, "austat", sig)
        return sBack

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class UserKeywordDetails(UserKeywordEdit):
    """Like UserKeyword Edit, but then html output"""
    rtype = "html"
    

class UserKeywordListView(BasicList):
    """Search and list keywords"""

    model = UserKeyword
    listform = UserKeywordForm
    prefix = "ukw"
    paginate_by = 20
    has_select2 = True
    in_team = False
    new_button = False
    order_cols = ['profile__user__username', 'keyword__name',  'type', '', 'created', '']
    order_default = order_cols
    order_heads = [{'name': 'User',     'order': 'o=1', 'type': 'str', 'custom': 'profile'},
                   {'name': 'Keyword',  'order': 'o=2', 'type': 'str', 'custom': 'keyword', 'main': True, 'linkdetails': True},
                   {'name': 'Type',     'order': 'o=3', 'type': 'str', 'custom': 'itemtype'},
                   {'name': 'Link',     'order': '',    'type': 'str', 'custom': 'link'},
                   {'name': 'Proposed', 'order': 'o=5', 'type': 'str', 'custom': 'date'},
                   {'name': 'Approve',  'order': '',    'type': 'str', 'custom': 'approve', 'align': 'right'}]
    filters = [ {"name": "Keyword",     "id": "filter_keyword", "enabled": False},
                {"name": "User",        "id": "filter_profile", "enabled": False},
                {"name": "Type",        "id": "filter_type",    "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'keyword',   'fkfield': 'keyword', 'keyFk': 'id', 'keyList': 'kwlist',      'infield': 'id' },
            {'filter': 'profile',   'fkfield': 'profile', 'keyFk': 'id', 'keyList': 'profilelist', 'infield': 'id' },
            {'filter': 'type',      'dbfield': 'type',    'keyS': 'type' }]}
        ]
    custombuttons = [{"name": "approve_keywords", "title": "Approve currently filtered keywords", 
                      "icon": "music", "template_name": "seeker/approve_keywords.html" }]

    def initializations(self):
        if self.request.user:
            username = self.request.user.username
            # See if there is a list of approved id's
            qd = self.request.GET if self.request.method == "GET" else self.request.POST
            approvelist = qd.get("approvelist", None)
            if approvelist != None:
                # See if this needs translation
                if approvelist[0] == "[":
                    approvelist = json.loads(approvelist)
                else:
                    approvelist = [ approvelist ]
                # Does this user have the right privilages?
                if user_is_superuser(self.request) or user_is_ingroup(self.request, app_editor):
                    # Get the profile
                    profile = Profile.get_user_profile(username)

                    # Approve the UserKeyword stated here
                    for ukw_id in approvelist:
                        obj = UserKeyword.objects.filter(profile=profile, id=ukw_id).first()
                        if obj != None:
                            obj.moveup()
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "keyword":
            sBack = instance.keyword.name
        elif custom == "profile":
            username = instance.profile.user.username
            url = reverse("profile_details", kwargs = {'pk': instance.profile.id})
            sBack = "<a href='{}'>{}</a>".format(url, username)
        elif custom == "itemtype":
            sBack = instance.get_type_display()
        elif custom == "link":
            sBack = self.get_link(instance)
        elif custom == "date":
            sBack = instance.created.strftime("%d/%b/%Y %H:%M")
        elif custom == "approve":
            url = "{}?approvelist={}".format(reverse("userkeyword_list"), instance.id)
            sBack = "<a class='btn btn-xs jumbo-2' role='button' href='{}' title='Approve this keyword'><span class='glyphicon glyphicon-thumbs-up'></span></a>".format(url)
        return sBack, sTitle

    def get_link(self, instance):
        details = ""
        value = ""
        url = ""
        sBack = ""
        if instance.type == "manu" and instance.manu: 
            # Manuscript: shelfmark
            url = reverse('manuscript_details', kwargs = {'pk': instance.manu.id})
            value = instance.manu.idno
            sBack = "<span class='badge signature ot'><a href='{}'>{}</a></span>".format(url, value)
        elif instance.type == "sermo" and instance.sermo: 
            # Sermon (manifestation): Gryson/Clavis + shelf mark (of M)
            sig = instance.sermo.get_eqsetsignatures_markdown("first")
            # Sermon identification
            url = reverse('canwit_details', kwargs = {'pk': instance.sermo.id})
            manu_obj = instance.sermo.get_manuscript()
            value = "{}/{}".format(instance.sermo.order, manu_obj.get_canwit_count())
            sermo = "<span><a href='{}'>sermon {}</a></span>".format(url, value)
            # Manuscript shelfmark
            url = reverse('manuscript_details', kwargs = {'pk': manu_obj.id})
            manu = "<span class='badge signature ot'><a href='{}'>{}</a></span>".format(url, manu_obj.idno)
            # Combine
            sBack = "{} {} {}".format(sermo, manu, sig)
        elif instance.type == "austat" and instance.austat: 
            # Get signatures
            sig = instance.austat.get_goldsigfirst()
            # Get Gold URL
            url = reverse('austat_details', kwargs = {'pk': instance.austat.id})
            # Combine
            sBack = "<span class='badge signature ot'><a href='{}'>{}</a></span> {}".format(url, "austat", sig)
        return sBack

    def add_to_context(self, context, initial):
        # Make sure to add a list of the currently filtered keywords
        if self.qs != None:
            lst_ukw = [x.id for x in self.qs]
            context['ukw_selection'] = lst_ukw
            context['ukw_list'] = reverse("userkeyword_list")
        return context


# ============= PROVENANCE VIEWS ============================


class ProvenanceEdit(BasicDetails):
    """The details of one 'provenance'"""

    model = Provenance
    mForm = ProvenanceForm
    prefix = 'prov'
    title = "Provenance"
    rtype = "json"
    history_button = True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",         'value': instance.name,             'field_key': "name"},
            {'type': 'plain', 'label': "Location:",     'value': instance.get_location(),   'field_key': 'location'     },
            ]

        # Signal that we have select2
        context['has_select2'] = True

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)

    def get_manuscripts(self, instance):
        # find the shelfmark
        manu = instance.manu
        if manu != None:
            # Get the URL to the manu details
            url = reverse("manuscript_details", kwargs = {'pk': manu.id})
            shelfmark = manu.idno[:20]
            sBack = "<span class='badge signature cl'><a href='{}'>{}</a></span>".format(url, manu.idno)
        #lManu = []
        #for obj in instance.manuscripts_provenances.all():
        #    # Add the shelfmark of this one
        #    manu = obj.manuscript
        #    url = reverse("manuscript_details", kwargs = {'pk': manu.id})
        #    shelfmark = manu.idno[:20]
        #    lManu.append("<span class='badge signature cl'><a href='{}'>{}</a></span>".format(url, manu.idno))
        #sBack = ", ".join(lManu)
        return sBack


class ProvenanceDetails(ProvenanceEdit):
    """Like Provenance Edit, but then html output"""
    rtype = "html"

    def add_to_context(self, context, instance):
        # First get the 'standard' context
        context = super(ProvenanceDetails, self).add_to_context(context, instance)

        context['sections'] = []

        # Lists of related objects
        related_objects = []
        resizable = True
        index = 1
        sort_start = '<span class="sortable"><span class="fa fa-sort sortshow"></span>&nbsp;'
        sort_start_int = '<span class="sortable integer"><span class="fa fa-sort sortshow"></span>&nbsp;'
        sort_end = '</span>'

        # List of Manuscripts that use this provenance
        manuscripts = dict(title="Manuscripts with this provenance", prefix="mprov")
        if resizable: manuscripts['gridclass'] = "resizable"

        rel_list =[]
        qs = instance.manuscripts_provenances.all().order_by('manuscript__idno')
        for item in qs:
            manu = item.manuscript
            url = reverse('manuscript_details', kwargs={'pk': manu.id})
            url_pm = reverse('provenanceman_details', kwargs={'pk': item.id})
            rel_item = []

            # S: Order number for this manuscript
            add_rel_item(rel_item, index, False, align="right")
            index += 1

            # Manuscript
            manu_full = "{}, {}, <span class='signature'>{}</span> {}".format(manu.get_city(), manu.get_library(), manu.idno, manu.name)
            add_rel_item(rel_item, manu_full, False, main=False, link=url)

            # Note for this provenance
            note = "(none)" if item.note == None or item.note == "" else item.note
            add_rel_item(rel_item, note, False, nowrap=False, main=True, link=url_pm,
                         title="Note for this provenance-manuscript relation")

            # Add this line to the list
            rel_list.append(dict(id=item.id, cols=rel_item))

        manuscripts['rel_list'] = rel_list

        manuscripts['columns'] = [
            '{}<span>#</span>{}'.format(sort_start_int, sort_end), 
            '{}<span>Manuscript</span>{}'.format(sort_start, sort_end), 
            '{}<span>Note</span>{}'.format(sort_start, sort_end)
            ]
        related_objects.append(manuscripts)

        # List of Codicos that use this provenance
        codicos = dict(title="codicological unites with this provenance", prefix="mcodi")
        if resizable: codicos['gridclass'] = "resizable"

        rel_list =[]
        qs = instance.codico_provenances.all().order_by('codico__manuscript__idno', 'codico__order')
        for item in qs:
            codico = item.codico
            manu = codico.manuscript
            url = reverse('manuscript_details', kwargs={'pk': manu.id})
            url_c = reverse('codico_details', kwargs={'pk': codico.id})
            url_pc = reverse('provenancecod_details', kwargs={'pk': item.id})
            rel_item = []

            # S: Order number for this manuscript
            add_rel_item(rel_item, index, False, align="right")
            index += 1

            # Manuscript
            manu_full = "{}, {}, <span class='signature'>{}</span> {}".format(manu.get_city(), manu.get_library(), manu.idno, manu.name)
            add_rel_item(rel_item, manu_full, False, main=False, link=url)

            # Codico
            codico_full = "<span class='badge signature ot'>{}</span>".format(codico.order)
            add_rel_item(rel_item, codico_full, False, main=False, link=url_c)

            # Note for this provenance
            note = "(none)" if item.note == None or item.note == "" else item.note
            add_rel_item(rel_item, note, False, nowrap=False, main=True, link=url_pc,
                         title="Note for this provenance-codico relation")

            # Add this line to the list
            rel_list.append(dict(id=item.id, cols=rel_item))

        codicos['rel_list'] = rel_list

        codicos['columns'] = [
            '{}<span>#</span>{}'.format(sort_start_int, sort_end), 
            '{}<span>Manuscript</span>{}'.format(sort_start, sort_end), 
            '{}<span>codicological unit</span>{}'.format(sort_start, sort_end), 
            '{}<span>Note</span>{}'.format(sort_start, sort_end)
            ]
        related_objects.append(codicos)

        # Add all related objects to the context
        context['related_objects'] = related_objects

        # Return the context we have made
        return context
    

class ProvenanceListView(BasicList):
    """Search and list provenances"""

    model = Provenance
    listform = ProvenanceForm
    prefix = "prov"
    has_select2 = True
    new_button = True   # Provenances are added in the Manuscript view; each provenance belongs to one manuscript
                        # Issue #289: provenances are to be added *HERE*
    order_cols = ['location__name', 'name']
    order_default = order_cols
    order_heads = [
        {'name': 'Location',    'order': 'o=1', 'type': 'str', 'custom': 'location', 'linkdetails': True},
        {'name': 'Name',        'order': 'o=2', 'type': 'str', 'field':  'name', 'main': True, 'linkdetails': True},
        # Issue #289: remove this note from here
        # {'name': 'Note',        'order': 'o=3', 'type': 'str', 'custom': 'note', 'linkdetails': True},
        {'name': 'Manuscript',  'order': 'o=4', 'type': 'str', 'custom': 'manuscript'}
        ]
    filters = [ {"name": "Name",        "id": "filter_name",    "enabled": False},
                {"name": "Location",    "id": "filter_location","enabled": False},
                {"name": "Manuscript",  "id": "filter_manuid",  "enabled": False},
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'name',      'dbfield': 'name', 'keyS': 'name'},
            {'filter': 'location',  'fkfield': 'location', 'keyS': 'location_ta', 'keyId': 'location', 'keyFk': "name", 'keyList': 'locationlist', 'infield': 'id' },
            {'filter': 'manuid',    'fkfield': 'manuscripts_provenances__manuscript', 'keyFk': 'idno', 'keyList': 'manuidlist', 'infield': 'id' }
            # Issue #289: innovation below turned back to the original above
            # {'filter': 'manuid',    'fkfield': 'manu', 'keyFk': 'idno', 'keyList': 'manuidlist', 'infield': 'id' }
            ]}
        ]

    def initializations(self):
        """Perform some initializations"""

        oErr = ErrHandle()
        try:

            # ======== One-time adaptations ==============
            listview_adaptations("provenance_list")

        except:
            msg = oErr.get_error_message()
            oErr.DoError("ProvenanceListView/initializations")

        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "manuscript":
            # Multiple connections possible
            # One provenance may be connected to any number of manuscripts!
            lManu = []
            for obj in instance.manuscripts_provenances.all():
                # Add the shelfmark of this one
                manu = obj.manuscript
                url = reverse("manuscript_details", kwargs = {'pk': manu.id})
                shelfmark = manu.idno[:20]
                lManu.append("<span class='badge signature cl'><a href='{}'>{}</a></span>".format(url, manu.idno))
            sBack = ", ".join(lManu)
            # Issue #289: the innovation below is turned back to the original above
            ## find the shelfmark
            #manu = instance.manu
            #if manu != None:
            #    # Get the URL to the manu details
            #    url = reverse("manuscript_details", kwargs = {'pk': manu.id})
            #    shelfmark = manu.idno[:20]
            #    sBack = "<span class='badge signature cl'><a href='{}'>{}</a></span>".format(url, manu.idno)
        elif custom == "location":
            sBack = ""
            if instance.location:
                sBack = instance.location.name
        #elif custom == "note":
        #    sBack = ""
        #    if instance.note:
        #        sBack = instance.note[:40]
        return sBack, sTitle

    def adapt_search(self, fields):
        lstExclude=None
        qAlternative = None
        x = fields
        return fields, lstExclude, qAlternative


class ProvenanceManEdit(BasicDetails):
    """The details of one 'provenance'"""

    model = ProvenanceMan
    mForm = ProvenanceManForm
    prefix = 'mprov'
    title = "ManuscriptProvenance"
    rtype = "json"
    history_button = False # True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'safe',  'label': "Provenance:",   'value': instance.get_provenance()},
            {'type': 'plain', 'label': "Note:",         'value': instance.note,   'field_key': 'note'     },
            ]

        # Signal that we have select2
        context['has_select2'] = True

        context['listview'] = reverse("manuscript_details", kwargs={'pk': instance.manuscript.id})

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class ProvenanceManDetails(ProvenanceManEdit):
    """Like ProvenanceMan Edit, but then html output"""
    rtype = "html"
        

class ProvenanceCodEdit(BasicDetails):
    """The details of one 'provenance'"""

    model = ProvenanceCod
    mForm = ProvenanceCodForm
    prefix = 'cprov'
    title = "CodicoProvenance"
    rtype = "json"
    history_button = False # True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'safe',  'label': "Provenance:",   'value': instance.get_provenance()},
            {'type': 'plain', 'label': "Note:",         'value': instance.note,   'field_key': 'note'     },
            ]

        # Signal that we have select2
        context['has_select2'] = True

        context['listview'] = reverse("codico_details", kwargs={'pk': instance.codico.id})

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class ProvenanceCodDetails(ProvenanceCodEdit):
    """Like ProvenanceCod Edit, but then html output"""
    rtype = "html"
        

# ============= BIBLE RANGE VIEWS ============================


class BibRangeEdit(BasicDetails):
    """The details of one 'user-keyword': one that has been linked by a user"""

    model = BibRange
    mForm = BibRangeForm
    prefix = 'brng'
    title = "Bible references"
    title_sg = "Bible reference"
    rtype = "json"
    history_button = False # True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Book:",         'value': instance.get_book(),   'field_key': 'book', 'key_hide': True },
            {'type': 'plain', 'label': "Abbreviations:",'value': instance.get_abbr()                        },
            {'type': 'plain', 'label': "Chapter/verse:",'value': instance.chvslist,     'field_key': 'chvslist', 'key_hide': True },
            {'type': 'line',  'label': "Intro:",        'value': instance.intro,        'field_key': 'intro'},
            {'type': 'line',  'label': "Extra:",        'value': instance.added,        'field_key': 'added'},
            {'type': 'plain', 'label': "Sermon:",       'value': self.get_sermon(instance)                  },
            {'type': 'plain', 'label': "Manuscript:",   'value': self.get_manuscript(instance)              }
            ]

        # Signal that we have select2
        context['has_select2'] = True

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)

    def get_manuscript(self, instance):
        # find the shelfmark via the sermon
        manu = instance.sermon.msitem.manu
        url = reverse("manuscript_details", kwargs = {'pk': manu.id})
        sBack = "<span class='badge signature cl'><a href='{}'>{}</a></span>".format(url, manu.get_full_name())
        return sBack

    def get_sermon(self, instance):
        # Get the sermon
        sermon = instance.sermon
        url = reverse("canwit_details", kwargs = {'pk': sermon.id})
        title = "{}: {}".format(sermon.msitem.manu.idno, sermon.locus)
        sBack = "<span class='badge signature gr'><a href='{}'>{}</a></span>".format(url, title)
        return sBack


class BibRangeDetails(BibRangeEdit):
    """Like BibRange Edit, but then html output"""
    rtype = "html"
    

class BibRangeListView(BasicList):
    """Search and list provenances"""

    model = BibRange
    listform = BibRangeForm
    prefix = "brng"
    has_select2 = True
    sg_name = "Bible reference"
    plural_name = "Bible references"
    new_button = False  # BibRanges are added in the Manuscript view; each provenance belongs to one manuscript
    order_cols = ['book__idno', 'chvslist', 'intro', 'added', 'sermon__msitem__manu__idno;sermon__locus']
    order_default = order_cols
    order_heads = [
        {'name': 'Book',            'order': 'o=1', 'type': 'str', 'custom': 'book', 'linkdetails': True},
        {'name': 'Chapter/verse',   'order': 'o=2', 'type': 'str', 'field': 'chvslist', 'main': True, 'linkdetails': True},
        {'name': 'Intro',           'order': 'o=3', 'type': 'str', 'custom': 'intro', 'linkdetails': True},
        {'name': 'Extra',           'order': 'o=4', 'type': 'str', 'custom': 'added', 'linkdetails': True},
        {'name': 'Sermon',          'order': 'o=5', 'type': 'str', 'custom': 'sermon'}
        ]
    filters = [ 
        {"name": "Bible reference", "id": "filter_bibref",      "enabled": False},
        {"name": "Intro",           "id": "filter_intro",       "enabled": False},
        {"name": "Extra",           "id": "filter_added",       "enabled": False},
        {"name": "Manuscript...",   "id": "filter_manuscript",  "enabled": False, "head_id": "none"},
        {"name": "Shelfmark",       "id": "filter_manuid",      "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Country",         "id": "filter_country",     "enabled": False, "head_id": "filter_manuscript"},
        {"name": "City",            "id": "filter_city",        "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Library",         "id": "filter_library",     "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Origin",          "id": "filter_origin",      "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Provenance",      "id": "filter_provenance",  "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Date from",       "id": "filter_datestart",   "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Date until",      "id": "filter_datefinish",  "enabled": False, "head_id": "filter_manuscript"},
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'bibref',    'dbfield': '$dummy',    'keyS': 'bibrefbk'},
            {'filter': 'bibref',    'dbfield': '$dummy',    'keyS': 'bibrefchvs'},
            {'filter': 'intro',     'dbfield': 'intro',     'keyS': 'intro'},
            {'filter': 'added',     'dbfield': 'added',     'keyS': 'added'}
            ]},
        {'section': 'manuscript', 'filterlist': [
            {'filter': 'manuid',        'fkfield': 'sermon__msitem__manu',                    'keyS': 'manuidno',     'keyList': 'manuidlist', 'keyFk': 'idno', 'infield': 'id'},
            {'filter': 'country',       'fkfield': 'sermon__msitem__manu__library__lcountry', 'keyS': 'country_ta',   'keyId': 'country',     'keyFk': "name"},
            {'filter': 'city',          'fkfield': 'sermon__msitem__manu__library__lcity',    'keyS': 'city_ta',      'keyId': 'city',        'keyFk': "name"},
            {'filter': 'library',       'fkfield': 'sermon__msitem__manu__library',           'keyS': 'libname_ta',   'keyId': 'library',     'keyFk': "name"},
            {'filter': 'origin',        'fkfield': 'sermon__msitem__manu__origin',            'keyS': 'origin_ta',    'keyId': 'origin',      'keyFk': "name"},
            {'filter': 'provenance',    'fkfield': 'sermon__msitem__manu__provenances',       'keyS': 'prov_ta',      'keyId': 'prov',        'keyFk': "name"},
            {'filter': 'datestart',     'dbfield': 'sermon__msitem__codico__codico_dateranges__yearstart__gte',    'keyS': 'date_from'},
            {'filter': 'datefinish',    'dbfield': 'sermon__msitem__codico__codico_dateranges__yearfinish__lte',   'keyS': 'date_until'},
            ]},
        {'section': 'other', 'filterlist': [
            {'filter': 'bibref',     'dbfield': 'id',    'keyS': 'bibref'}
            ]}
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "sermon":
            sermon = instance.sermon
            # find the shelfmark
            manu = sermon.msitem.manu
            url = reverse("canwit_details", kwargs = {'pk': sermon.id})
            sBack = "<span class='badge signature cl'><a href='{}'>{}: {}</a></span>".format(url, manu.idno, sermon.locus)
        elif custom == "book":
            sBack = instance.book.name
        elif custom == "intro":
            sBack = " "
            if instance.intro != "":
                sBack = instance.intro
        elif custom == "added":
            sBack = " "
            if instance.added != "":
                sBack = instance.added
        return sBack, sTitle

    def adapt_search(self, fields):
        lstExclude=None
        qAlternative = None

        # Adapt the bible reference list
        bibrefbk = fields.get("bibrefbk", "")
        if bibrefbk != None and bibrefbk != "":
            bibrefchvs = fields.get("bibrefchvs", "")

            # Get the start and end of this bibref
            start, einde = Reference.get_startend(bibrefchvs, book=bibrefbk)
 
            # Find out which sermons have references in this range
            lstQ = []
            lstQ.append(Q(bibrangeverses__bkchvs__gte=start))
            lstQ.append(Q(bibrangeverses__bkchvs__lte=einde))
            sermonlist = [x.id for x in BibRange.objects.filter(*lstQ).order_by('id').distinct()]

            fields['bibrefbk'] = Q(id__in=sermonlist)

        return fields, lstExclude, qAlternative


# ============= FEAST VIEWS ============================


class FeastEdit(BasicDetails):
    """The details of one Christian Feast"""

    model = Feast
    mForm = FeastForm
    prefix = 'fst'
    title = "Feast"
    title_sg = "Feast"
    rtype = "json"
    history_button = False # True
    mainitems = []
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",         'value': instance.name,         'field_key': 'name'     },
            {'type': 'plain', 'label': "Latin name:",   'value': instance.get_latname(),'field_key': 'latname'  },
            {'type': 'plain', 'label': "Feast date:",   'value': instance.get_date(),   'field_key': 'feastdate' },
            #{'type': 'plain', 'label': "Sermon:",       'value': self.get_sermon(instance)                  },
            #{'type': 'plain', 'label': "Manuscript:",   'value': self.get_manuscript(instance)              }
            ]

        # Signal that we have select2
        context['has_select2'] = True

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)

    def get_manuscript(self, instance):
        html = []
        # find the shelfmark via the sermon
        for manu in Manuscript.objects.filter(manuitems__itemsermons__feast=instance).order_by("idno"):
            url = reverse("manuscript_details", kwargs = {'pk': manu.id})
            html.append("<span class='badge signature cl'><a href='{}'>{}</a></span>".format(url, manu.get_full_name()))
        sBack = ", ".join(html)
        return sBack

    def get_sermon(self, instance):
        html = []
        # Get the sermons
        for sermon in Canwit.objects.filter(feast=instance).order_by("msitem__manu__idno", "locus"):
            url = reverse("canwit_details", kwargs = {'pk': sermon.id})
            title = "{}: {}".format(sermon.msitem.manu.idno, sermon.locus)
            html.append("<span class='badge signature gr'><a href='{}'>{}</a></span>".format(url, title))
        sBack = ", ".join(html)
        return sBack


class FeastDetails(FeastEdit):
    """Like Feast Edit, but then html output"""
    rtype = "html"

    def add_to_context(self, context, instance):
        # First get the 'standard' context from TestsetEdit
        context = super(FeastDetails, self).add_to_context(context, instance)

        context['sections'] = []

        # Lists of related objects
        related_objects = []
        resizable = True
        index = 1
        sort_start = '<span class="sortable"><span class="fa fa-sort sortshow"></span>&nbsp;'
        sort_start_int = '<span class="sortable integer"><span class="fa fa-sort sortshow"></span>&nbsp;'
        sort_end = '</span>'

        # List of Sermons that link to this feast (with an FK)
        sermons = dict(title="Manuscripts with sermons connected to this feast", prefix="tunit")
        if resizable: sermons['gridclass'] = "resizable"

        rel_list =[]
        qs = instance.feastsermons.all().order_by('msitem__manu__idno', 'locus')
        for item in qs:
            manu = item.msitem.manu
            url = reverse('canwit_details', kwargs={'pk': item.id})
            url_m = reverse('manuscript_details', kwargs={'pk': manu.id})
            rel_item = []

            # S: Order number for this sermon
            add_rel_item(rel_item, index, False, align="right")
            index += 1

            # Manuscript
            manu_full = "{}, {}, <span class='signature'>{}</span> {}".format(manu.get_city(), manu.get_library(), manu.idno, manu.name)
            add_rel_item(rel_item, manu_full, False, main=True, link=url_m)

            # Locus
            locus = "(none)" if item.locus == None or item.locus == "" else item.locus
            add_rel_item(rel_item, locus, False, main=True, link=url, 
                         title="Locus within the manuscript (links to the sermon)")

            # Origin/provenance
            or_prov = "{} ({})".format(manu.get_origin(), manu.get_provenance_markdown())
            add_rel_item(rel_item, or_prov, False, main=True, 
                         title="Origin (if known), followed by provenances (between brackets)")

            # Date
            daterange = "{}-{}".format(manu.yearstart, manu.yearfinish)
            add_rel_item(rel_item, daterange, False, link=url_m, align="right")

            # Add this line to the list
            rel_list.append(dict(id=item.id, cols=rel_item))

        sermons['rel_list'] = rel_list

        sermons['columns'] = [
            '{}<span>#</span>{}'.format(sort_start_int, sort_end), 
            '{}<span>Manuscript</span>{}'.format(sort_start, sort_end), 
            '{}<span>Locus</span>{}'.format(sort_start, sort_end), 
            '{}<span title="Origin/Provenance">or./prov.</span>{}'.format(sort_start, sort_end), 
            '{}<span>date</span>{}'.format(sort_start_int, sort_end)
            ]
        related_objects.append(sermons)

        # Add all related objects to the context
        context['related_objects'] = related_objects

        # Return the context we have made
        return context
    

class FeastListView(BasicList):
    """Search and list Christian feasts"""

    model = Feast
    listform = FeastForm
    prefix = "fst"
    has_select2 = True
    sg_name = "Feast"
    plural_name = "Feasts"
    new_button = True  # Feasts can be added from the listview
    order_cols = ['name', 'latname', 'feastdate', '']   # feastsermons__msitem__manu__idno;feastsermons__locus
    order_default = order_cols
    order_heads = [
        {'name': 'Name',    'order': 'o=1', 'type': 'str', 'field': 'name',     'linkdetails': True},
        {'name': 'Latin',   'order': 'o=2', 'type': 'str', 'field': 'latname',  'linkdetails': True},
        {'name': 'Date',    'order': 'o=3', 'type': 'str', 'field': 'feastdate','linkdetails': True, 'main': True},
        {'name': 'Sermons', 'order': '',    'type': 'str', 'custom': 'sermons'}
        ]
    filters = [ 
        {"name": "Name",            "id": "filter_engname",     "enabled": False},
        {"name": "Latin",           "id": "filter_latname",     "enabled": False},
        {"name": "Date",            "id": "filter_feastdate",   "enabled": False},
        {"name": "Manuscript...",   "id": "filter_manuscript",  "enabled": False, "head_id": "none"},
        {"name": "Shelfmark",       "id": "filter_manuid",      "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Country",         "id": "filter_country",     "enabled": False, "head_id": "filter_manuscript"},
        {"name": "City",            "id": "filter_city",        "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Library",         "id": "filter_library",     "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Origin",          "id": "filter_origin",      "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Provenance",      "id": "filter_provenance",  "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Date from",       "id": "filter_datestart",   "enabled": False, "head_id": "filter_manuscript"},
        {"name": "Date until",      "id": "filter_datefinish",  "enabled": False, "head_id": "filter_manuscript"},
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'engname',   'dbfield': 'name',      'keyS': 'name'},
            {'filter': 'latname',   'dbfield': 'latname',   'keyS': 'latname'},
            {'filter': 'feastdate', 'dbfield': 'feastdate', 'keyS': 'feastdate'}
            ]},
        {'section': 'manuscript', 'filterlist': [
            {'filter': 'manuid',        'fkfield': 'feastsermons__msitem__manu',                    'keyS': 'manuidno',     'keyList': 'manuidlist', 'keyFk': 'idno', 'infield': 'id'},
            {'filter': 'country',       'fkfield': 'feastsermons__msitem__manu__library__lcountry', 'keyS': 'country_ta',   'keyId': 'country',     'keyFk': "name"},
            {'filter': 'city',          'fkfield': 'feastsermons__msitem__manu__library__lcity',    'keyS': 'city_ta',      'keyId': 'city',        'keyFk': "name"},
            {'filter': 'library',       'fkfield': 'feastsermons__msitem__manu__library',           'keyS': 'libname_ta',   'keyId': 'library',     'keyFk': "name"},
            {'filter': 'origin',        'fkfield': 'feastsermons__msitem__manu__origin',            'keyS': 'origin_ta',    'keyId': 'origin',      'keyFk': "name"},
            {'filter': 'provenance',    'fkfield': 'feastsermons__msitem__manu__provenances',       'keyS': 'prov_ta',      'keyId': 'prov',        'keyFk': "name"},
            {'filter': 'datestart',     'dbfield': 'feastsermons__msitem__codico__codico_dateranges__yearstart__gte',    'keyS': 'date_from'},
            {'filter': 'datefinish',    'dbfield': 'feastsermons__msitem__codico__codico_dateranges__yearfinish__lte',   'keyS': 'date_until'},
            ]}
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "sermon":
            html = []
            for sermon in instance.feastsermons.all().order_by('feast__name'):
                # find the shelfmark
                manu = sermon.msitem.manu
                url = reverse("canwit_details", kwargs = {'pk': sermon.id})
                html.append("<span class='badge signature cl'><a href='{}'>{}: {}</a></span>".format(url, manu.idno, sermon.locus))
            sBack = ", ".join(html)
        elif custom == "sermons":
            sBack = "{}".format(instance.feastsermons.count())
        return sBack, sTitle


# ============= MANUSCRIPT TEMPLATE VIEWS ============================


class TemplateEdit(BasicDetails):
    """The details of one 'user-keyword': one that has been linked by a user"""

    model = Template
    mForm = TemplateForm
    prefix = 'tmpl'
    title = "TemplateEdit"
    rtype = "json"
    history_button = True
    use_team_group = True
    mainitems = []

    stype_edi_fields = ['name', 'description']
        
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",         'value': instance.name,             'field_key': "name"},
            {'type': 'line',  'label': "Description:",  'value': instance.description,      'field_key': 'description'},
            {'type': 'plain', 'label': "Items:",        'value': instance.get_count()},
            {'type': 'plain', 'label': "Owner:",        'value': instance.get_username()},
            {'type': 'plain', 'label': "Manuscript:",   'value': instance.get_manuscript_link()}
            ]

        # Signal that we have select2
        context['has_select2'] = True

        # Make sure 'authenticated' is adapted to only include EDITORS
        if context['authenticated']:
            if not context['is_app_editor'] and not user_is_superuser(self.request): context['permission'] = False

        # Return the context we have made
        return context

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)


class TemplateDetails(TemplateEdit):
    """Like Template Edit, but then html output"""
    rtype = "html"

    def before_save(self, form, instance):
        bStatus = True
        msg = ""
        if instance == None or instance.id == None:
            # See if we have the profile id
            profile = Profile.get_user_profile(self.request.user.username)
            form.instance.profile = profile
            # See if we have the 'manubase' item
            manubase = self.qd.get("manubase", None)
            if manubase != None:
                # Find out which manuscript this is
                manu = Manuscript.objects.filter(id=manubase).first()
                if manu != None:
                    # Create a 'template-copy' of this manuscript
                    manutemplate = manu.get_manutemplate_copy()
                    instance.manu = manutemplate
        return bStatus, msg
    

class TemplateApply(TemplateDetails):
    """Create a new manuscript that is based on this template"""

    def custom_init(self, instance):
        # Find out who I am
        profile = Profile.get_user_profile(self.request.user.username)
        # Get the manuscript
        manu_template = instance.manu
        # Create a new manuscript that is based on this one
        manu_new = manu_template.get_manutemplate_copy("man", profile, instance)
        # Re-direct to this manuscript
        self.redirectpage = reverse("manuscript_details", kwargs={'pk': manu_new.id})
        return None


class TemplateImport(TemplateDetails):
    """Import manuscript sermons from a template"""

    initRedirect = True

    def initializations(self, request, pk):
        oErr = ErrHandle()
        try:
            # Find out who I am
            profile = Profile.get_user_profile(request.user.username)

            # Get the parameters
            self.qd = request.POST
            self.object = None
            manu_id = self.qd.get("manu_id", "")
            if manu_id != "":
                instance = Manuscript.objects.filter(id=manu_id).first()

            # The default redirectpage is just this manuscript
            self.redirectpage = reverse("manuscript_details", kwargs = {'pk': instance.id})
            # Get the template to be used as import
            template_id = self.qd.get("template", "")
            if template_id != "":
                template = Template.objects.filter(id=template_id).first()
                if template != None:
                    # Set my own object
                    self.object = template

                    # Import this template into the manuscript
                    instance.import_template(template, profile)
            # Getting here means all went well
        except:
            msg = oErr.get_error_message()
            oErr.DoError("TemplateImport/initializations")
        return None


class TemplateListView(BasicList):
    """Search and list templates"""

    model = Template
    listform = TemplateForm
    prefix = "tmpl"
    has_select2 = True
    new_button = False  # Templates are added in the Manuscript view; each template belongs to one manuscript
    use_team_group = True
    order_cols = ['profile__user__username', 'name', '']
    order_default = order_cols
    order_heads = [
        {'name': 'Owner',       'order': 'o=1', 'type': 'str', 'custom': 'owner'},
        {'name': 'Name',        'order': 'o=2', 'type': 'str', 'field': 'name', 'main': True, 'linkdetails': True},
        {'name': 'Items',       'order': '',    'type': 'str', 'custom': 'items', 'linkdetails': True},
        {'name': 'Manuscript',  'order': '',    'type': 'str', 'custom': 'manuscript'}
        ]
    filters = [
        ]
    searches = [
        ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "owner":
            # find the owner
            username = instance.get_username()
            sBack = "<span class='template_owner'>{}</span>".format(username)
        elif custom == "items":
            # The number of sermons (items) part of this manuscript
            sBack = "{}".format(instance.get_count())
        elif custom == "manuscript":
            url = reverse('template_apply', kwargs={'pk': instance.id})
            sBack = "<a href='{}' title='Create a new manuscript based on this template'><span class='glyphicon glyphicon-open'></span></a>".format(url)
        return sBack, sTitle

    def add_to_context(self, context, initial):
        # Make sure 'authenticated' is adapted to only include EDITORS
        if context['authenticated']:
            context['permission'] = context['is_app_editor'] or user_is_superuser(self.request)
            # if not context['is_app_editor'] and not user_is_superuser(self.request): context['permission'] = False
        return context


# ============= USER PROFILE VIEWS ============================


class ProfileEdit(BasicDetails):
    """Details view of profile"""

    model = Profile
    mForm = ProfileForm
    prefix = "prof"
    title = "ProfileEdit"
    rtype = "json"
    has_select2 = True
    history_button = True
    no_delete = True
    mainitems = []

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "User",          'value': instance.user.id, 'field_key': "user", 'empty': 'idonly'},
            {'type': 'plain', 'label': "Username:",     'value': instance.user.username, },
            {'type': 'plain', 'label': "Email:",        'value': instance.user.email, },
            {'type': 'plain', 'label': "First name:",   'value': instance.user.first_name, },
            {'type': 'plain', 'label': "Last name:",    'value': instance.user.last_name, },
            {'type': 'plain', 'label': "Is staff:",     'value': instance.user.is_staff, },
            {'type': 'plain', 'label': "Is superuser:", 'value': instance.user.is_superuser, },
            {'type': 'plain', 'label': "Date joined:",  'value': instance.user.date_joined.strftime("%d/%b/%Y %H:%M"), },
            {'type': 'plain', 'label': "Last login:",   'value': instance.user.last_login.strftime("%d/%b/%Y %H:%M"), },
            {'type': 'plain', 'label': "Groups:",       'value': instance.get_groups_markdown(), },
            {'type': 'plain', 'label': "Status:",       'value': instance.get_ptype_display(),          'field_key': 'ptype'},
            {'type': 'line',  'label': "Afiliation:",   'value': instance.affiliation,                  'field_key': 'affiliation'},
            {'type': 'line',  'label': "Project approval rights:", 'value': instance.get_projects_markdown(),    'field_list': 'projlist'}
            ]
        # Return the context we have made
        return context

    def after_save(self, form, instance):
        msg = ""
        bResult = True
        oErr = ErrHandle()
        
        try:
            # (6) 'projects'
            projlist = form.cleaned_data['projlist']
            adapt_m2m(ProjectEditor, instance, "profile", projlist, "project")
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ProfileEdit/after_save")
            bResult = False
        return bResult, msg

    def get_history(self, instance):
        return lila_get_history(instance)


class ProfileDetails(ProfileEdit):
    """Like Profile Edit, but then html output"""
    rtype = "html"


class ProfileListView(BasicList):
    """List user profiles"""

    model = Profile
    listform = ProfileForm
    prefix = "prof"
    new_button = False      # Do not allow adding new ones here
    order_cols = ['user__username', '', 'ptype', 'affiliation', '', '']
    order_default = order_cols
    order_heads = [
        {'name': 'Username',    'order': 'o=1', 'type': 'str', 'custom': 'name', 'default': "(unnamed)", 'linkdetails': True},
        {'name': 'Email',       'order': '',    'type': 'str', 'custom': 'email', 'linkdetails': True},
        {'name': 'Status',      'order': 'o=3', 'type': 'str', 'custom': 'status', 'linkdetails': True},
        {'name': 'Affiliation', 'order': 'o=4', 'type': 'str', 'custom': 'affiliation', 'main': True, 'linkdetails': True},
        {'name': 'Project Approver',    'order': '',    'type': 'str', 'custom': 'projects'},
        {'name': 'Groups',      'order': '',    'type': 'str', 'custom': 'groups'}]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "name":
            sBack = instance.user.username
        elif custom == "email":
            sBack = instance.user.email
        elif custom == "status":
            sBack = instance.get_ptype_display()
        elif custom == "affiliation":
            sBack = "-" if instance.affiliation == None else instance.affiliation
        elif custom == "projects":
            lHtml = []
            for g in instance.projects.all():
                name = g.name
                lHtml.append("<span class='badge signature cl'>{}</span>".format(name))
            sBack = ", ".join(lHtml)
        elif custom == "groups":
            lHtml = []
            for g in instance.user.groups.all():
                name = g.name.replace("lila_", "")
                lHtml.append("<span class='badge signature gr'>{}</span>".format(name))
            sBack = ", ".join(lHtml)
        return sBack, sTitle


class DefaultEdit(BasicDetails):
    """User-definable defaults for this user-profile"""

    model = Profile
    mForm = ProfileForm
    prefix = "def"
    title = "DefaultEdit"
    titlesg = "Default"
    basic_name = "default"
    has_select2 = True
    history_button = False
    no_delete = True
    mainitems = []

    def custom_init(self, instance):
        self.listview = reverse('mylila')

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "User",              'value': instance.user.id, 'field_key': "user", 'empty': 'idonly'},
            {'type': 'plain', 'label': "Username:",         'value': instance.user.username, },
            {'type': 'line',  'label': "Editing rights:",   'value': instance.get_projects_markdown()},
            {'type': 'line',  'label': 'Default projects:', 'value': instance.get_defaults_markdown(), 'field_list': 'deflist'}
            ]
        # Return the context we have made
        return context

    def after_save(self, form, instance):
        msg = ""
        bResult = True
        oErr = ErrHandle()
        
        try:
            # (6) 'default projects'
            deflist = form.cleaned_data['deflist']
            instance.defaults_update(deflist)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("DefaultEdit/after_save")
            bResult = False
        return bResult, msg


class DefaultDetails(DefaultEdit):
    """Like Default Edit, but then html output"""

    rtype = "html"


# ============= PROJECT VIEWS ============================


class ProjectEdit(BasicDetails):
    """Details and editing of a project (nov 2021 version)"""

    model = Project
    mForm = ProjectForm
    prefix = 'proj'
    title = "Project"
    # no_delete = True
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
            oErr.DoError("Project/add_to_context")

        # Return the context we have made
        return context
    
    def get_history(self, instance):
        return lila_get_history(instance)


class ProjectDetails(ProjectEdit):
    """Just the HTML page"""
    rtype = "html"


class ProjectListView(BasicList):
    """Search and list projects"""

    model = Project 
    listform = ProjectForm
    prefix = "proj"
    has_select2 = True
    paginate_by = 20
    sg_name = "Project"     # This is the name as it appears e.g. in "Add a new XXX" (in the basic listview)
    plural_name = "Projects"
    # page_function = "ru.lila.seeker.search_paged_start"
    order_cols = ['name', '']
    order_default = order_cols
    order_heads = [
        {'name': 'Project',                  'order': 'o=1', 'type': 'str', 'custom': 'project',   'main': True, 'linkdetails': True},
        {'name': 'Manuscripts',              'order': 'o=2', 'type': 'str', 'custom': 'manulink',  'align': 'right' },
        {'name': 'Sermons',                  'order': 'o=3', 'type': 'str', 'custom': 'sermolink', 'align': 'right'},
        {'name': 'Authoritative statements', 'order': 'o=4', 'type': 'str', 'custom': 'ssglink',   'align': 'right'},
        {'name': 'Historical collections',   'order': 'o=5', 'type': 'str', 'custom': 'hclink',    'align': 'right'}]
                   
    filters = [ {"name": "Project",         "id": "filter_project",     "enabled": False},
                {"name": "Shelfmark",       "id": "filter_manuid",      "enabled": False, "head_id": "filter_other"},
               ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'project',   'dbfield': 'name',         'keyS': 'project_ta', 'keyList': 'projlist', 'infield': 'name' }]} 
            #{'filter': 'project',   'fkfield': 'projects',    'keyFk': 'name', 'keyList': 'projlist', 'infield': 'name'}]},
        ] 

    # hier gaat het nog niet goed
    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        html = []
        oErr = ErrHandle()
        try:
            if custom == "manulink":
                # Link to the manuscripts in this project
                count = instance.project_manuscripts.exclude(mtype="tem").count()
                url = reverse('manuscript_list')
                if count > 0:
                 #   html.append("<a href='{}?manu-prjlist={}'><span class='badge jumbo-3 clickable' title='{} manuscripts in this project'>{}</span></a>".format(
                 #       url, instance.id, count, count)) 
                    html.append("<a href='{}?manu-projlist={}'><span class='badge jumbo-3 clickable' title='{} manuscripts in this project'>{}</span></a>".format(
                        url, instance.id, count, count))

            elif custom == "sermolink":
                # Link to the sermons in this project
                count = instance.project_canwits.count() 
                url = reverse('canwit_list')
                if count > 0:                 
                    html.append("<a href='{}?sermo-projlist={}'><span class='badge jumbo-3 clickable' title='{} sermons in this project'>{}</span></a>".format(
                        url, instance.id, count, count))
            
            elif custom == "ssglink":
                # Link to the Authoritative statements in this project
                count = instance.project_austat.count() 
                url = reverse('austat_list')
                if count > 0:                 
                    html.append("<a href='{}?ssg-projlist={}'><span class='badge jumbo-3 clickable' title='{} Authoritative statements in this project'>{}</span></a>".format(
                        url, instance.id, count, count))

            elif custom == "hclink":
                # Link to the historical collections in this project
                count = instance.project_collection.exclude(settype="pd").count() # Nog expliciet met HC rekening houden?
                url = reverse('collhist_list')
                if count > 0:                 
                    html.append("<a href='{}?hist-projlist={}'><span class='badge jumbo-3 clickable' title='{} historical collections in this project'>{}</span></a>".format(
                        url, instance.id, count, count))

            elif custom == "project":
                sName = instance.name
                if sName == "": sName = "<i>(unnamed)</i>"
                html.append(sName)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ProjectListView/get_field_value")
        # Combine the HTML code
        sBack = "\n".join(html)
        return sBack, sTitle



# ============= EDITOR COMMENT VIEWS ============================


class CommentSend(BasicPart):
    """Receive a comment from a user"""

    MainModel = Comment
    template_name = 'seeker/comment_add.html'

    def add_to_context(self, context):

        url_names = {"manu": "manuscript_details", "sermo": "canwit_details",
                     "austat": "austat_details",   "codi": "codico_details"}
        obj_names = {"manu": "Manuscript", "sermo": "Sermon",
                     "austat": "Authoritative statement",
                     "codi": "codicological unit"}
        def get_object(otype, objid):
            obj = None
            if otype == "manu":
                obj = Manuscript.objects.filter(id=objid).first()
            elif otype == "sermo":
                obj = Canwit.objects.filter(id=objid).first()
            elif otype == "austat":
                obj = Austat.objects.filter(id=objid).first()
            elif otype == "codi":
                obj = Codico.objects.filter(id=objid).first()
            return obj

        if self.add:
            # Get the form
            form = CommentForm(self.qd, prefix="com")
            if form.is_valid():
                cleaned = form.cleaned_data
                # Yes, we are adding something new - check what we have
                profile = cleaned.get("profile")
                otype = cleaned.get("otype")
                objid = cleaned.get("objid")
                content = cleaned.get("content")
                if content != None and content != "":
                    # Yes, there is a remark
                    comment = Comment.objects.create(profile=profile, content=content, otype=otype)
                    obj = get_object(otype, objid)
                    # Add a new object for this user
                    obj.comments.add(comment)

                    # Send this comment by email
                    objurl = reverse(url_names[otype], kwargs={'pk': obj.id})
                    context['objurl'] = self.request.build_absolute_uri(objurl)
                    context['objname'] = obj_names[otype]
                    context['comdate'] = comment.get_created()
                    context['user'] = profile.user
                    context['objcontent'] = content
                    contents = render_to_string('seeker/comment_mail.html', context, self.request)
                    comment.send_by_email(contents)

                    # Get a list of comments by this user for this item
                    context['comment_list'] = get_usercomments(otype, obj, profile)
                    # Translate this list into a valid string
                    comment_list = render_to_string('seeker/comment_list.html', context, self.request)
                    # And then pass on this string in the 'data' part of the POST response
                    #  (this is done using the BasicPart POST handling)
                    context['data'] = dict(comment_list=comment_list)


        # Send the result
        return context


class CommentEdit(BasicDetails):
    """The details of one comment"""

    model = Comment
    mForm = None        # We are not using a form here!
    prefix = 'com'
    new_button = False
    # no_delete = True
    permission = "readonly"
    mainitems = []

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        oErr = ErrHandle()
        try:
            # Define the main items to show and edit
            context['mainitems'] = [
                {'type': 'plain', 'label': "Timestamp:",    'value': instance.get_created(),    },
                {'type': 'plain', 'label': "User name:",    'value': instance.profile.user.username,     },
                {'type': 'plain', 'label': "Comment:",      'value': instance.content,     },
                {'type': 'plain', 'label': "Item type:",    'value': instance.get_otype()},
                {'type': 'safe', 'label': "Link:",          'value': self.get_link(instance)}
                ]

        except:
            msg = oErr.get_error_message()
            oErr.DoError("CommentEdit/add_to_context")

        # Return the context we have made
        return context

    def get_link(self, instance):
        url = ""
        label = ""
        sBack = ""
        if instance.otype == "manu":
            obj = instance.comments_manuscript.first()
            url = reverse("manuscript_details", kwargs={'pk': obj.id})
            label = "manu_{}".format(obj.id)
        elif instance.otype == "sermo":
            obj = instance.comments_sermon.first()
            url = reverse("canwit_details", kwargs={'pk': obj.id})
            label = "sermo_{}".format(obj.id)
        elif instance.otype == "austat":
            obj = instance.comments_super.first()
            url = reverse("austat_details", kwargs={'pk': obj.id})
            label = "super_{}".format(obj.id)
        if url != "":
            sBack = "<span class='badge signature gr'><a href='{}'>{}</a></span>".format(url, label)
 
        return sBack


class CommentDetails(CommentEdit):
    """Like Comment Edit, but then html output"""
    rtype = "html"
    

class CommentListView(BasicList):
    """Search and list comments"""

    model = Comment
    listform = CommentForm
    prefix = "com"
    paginate_by = 20
    has_select2 = True
    order_cols = ['created', 'profile__user__username', 'otype', '']
    order_default = order_cols
    order_heads = [
        {'name': 'Timestamp',   'order': 'o=1', 'type': 'str', 'custom': 'created', 'main': True, 'linkdetails': True},
        {'name': 'User name',   'order': 'o=2', 'type': 'str', 'custom': 'username'},
        {'name': 'Item Type',   'order': 'o=3', 'type': 'str', 'custom': 'otype'},
        {'name': 'Link',        'order': '',    'type': 'str', 'custom': 'link'},
        ]
    filters = [ {"name": "Item type",   "id": "filter_otype",       "enabled": False},
                {"name": "User name",   "id": "filter_username",    "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'otype',    'dbfield': 'otype',   'keyS': 'otype',           'keyList': 'otypelist' },
            {'filter': 'username', 'fkfield': 'profile', 'keyFk': 'user__username', 'keyList': 'profilelist', 'infield': 'id'}
            ]
         }
        ]
    
    def initializations(self):
        """Perform some initializations"""

        # Check if otype has already been taken over
        comment_otype = Information.get_kvalue("comment_otype")
        if comment_otype == None or comment_otype != "done":
            # Get all the comments that have no o-type filled in yet
            qs = Comment.objects.filter(otype="-")
            with transaction.atomic():
                for obj in qs:
                    # Figure out where it belongs to
                    if obj.comments_manuscript.count() > 0:
                        obj.otype = "manu"
                    elif obj.comments_sermon.count() > 0:
                        obj.otype = "sermo"
                    elif obj.comments_super.count() > 0:
                        obj.otype = "austat"
                    elif obj.comments_codi.count() > 0:
                        obj.otype = "codi"
                    obj.save()
            # Success
            Information.set_kvalue("comment_otype", "done")

        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        oErr = ErrHandle()
        try:
            if custom == "username":
                sBack = instance.profile.user.username
            elif custom == "created":
                sBack = instance.get_created()
            elif custom == "otype":
                sBack = instance.get_otype()
            elif custom == "link":
                url = ""
                label = ""
                if instance.otype == "manu":
                    obj = instance.comments_manuscript.first()
                    if not obj is None:
                        url = reverse("manuscript_details", kwargs={'pk': obj.id})
                        label = "manu_{}".format(obj.id)
                    else:
                        iStop = 1
                elif instance.otype == "sermo":
                    obj = instance.comments_sermon.first()
                    if obj is None:
                        iStop = 1
                    else:
                        url = reverse("canwit_details", kwargs={'pk': obj.id})
                        label = "sermo_{}".format(obj.id)
                elif instance.otype == "austat":
                    obj = instance.comments_super.first()
                    if obj is None:
                        iStop = 1
                    else:
                        url = reverse("austat_details", kwargs={'pk': obj.id})
                        label = "super_{}".format(obj.id)
                elif instance.otype == "codi":
                    obj = instance.comments_codi.first()
                    if obj is None:
                        iStop = 1
                    else:
                        url = reverse("codico_details", kwargs={'pk': obj.id})
                        label = "codi_{}".format(obj.id)
                if url != "":
                    sBack = "<span class='badge signature gr'><a href='{}'>{}</a></span>".format(url, label)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CommentListView/get_field_value")
        return sBack, sTitle



# ===================== AUTHOR VIEWS AND OPERATIONS ========================


class AuthorEdit(BasicDetails):
    """The details of one author"""

    model = Author
    mForm = AuthorEditForm
    prefix = 'author'
    title = "Author"
    mainitems = []

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",         'value': instance.name,     'field_key': "name" },
            {'type': 'plain', 'label': "Abbreviation:", 'value': instance.abbr,     'field_key': 'abbr' },
            {'type': 'plain', 'label': "Number:",       'value': instance.number, 
             'title': "The author number is automatically assigned" },
            {'type': 'plain', 'label': "Editable:",     "value": instance.get_editable()                }
            ]

        # Signal that we have select2
        context['has_select2'] = True

        # Return the context we have made
        return context


class AuthorDetails(AuthorEdit):
    """Html variant of AuthorEdit"""

    rtype = "html"


class AuthorListView(BasicList):
    """Search and list authors"""

    model = Author
    listform = AuthorSearchForm
    has_select2 = True
    prefix = "auth"
    paginate_by = 20
    delete_line = True
    page_function = "ru.lila.seeker.search_paged_start"
    order_cols = ['abbr', 'number', 'name', '', '']
    order_default = ['name', 'abbr', 'number', '', '']
    order_heads = [{'name': 'Abbr',        'order': 'o=1', 'type': 'str', 
                    'title': 'Abbreviation of this name (used in standard literature)', 'field': 'abbr', 'default': ""},
                   {'name': 'Number',      'order': 'o=2', 'type': 'int', 'title': 'lila author number', 'field': 'number', 'default': 10000, 'align': 'right'},
                   {'name': 'Author name', 'order': 'o=3', 'type': 'str', 'field': "name", "default": "", 'main': True, 'linkdetails': True},
                   {'name': 'Links',       'order': '',    'type': 'str', 'title': 'Number of links from Sermon Descriptions and Gold Sermons', 'custom': 'links' },
                   {'name': '',            'order': '',    'type': 'str', 'options': ['delete']}]
    filters = [ {"name": "Author",  "id": "filter_author",  "enabled": False}]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'author', 'dbfield': 'name', 'keyS': 'author_ta', 'keyList': 'authlist', 'infield': 'name' }
            ]}
        ]
    downloads = [{"label": "Excel", "dtype": "xlsx", "url": 'author_results'},
                 {"label": "csv (tab-separated)", "dtype": "csv", "url": 'author_results'},
                 {"label": None},
                 {"label": "json", "dtype": "json", "url": 'author_results'}]
    uploads = [{"url": "import_authors", "label": "Authors (csv/json)", "msg": "Specify the CSV file (or the JSON file) that contains the lila authors"}]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "links":
            html = []
            # Get the HTML code for the links of this instance
            number = instance.author_sermons.count()
            if number > 0:
                url = reverse('canwit_list')
                html.append("<span class='badge jumbo-1' title='linked sermon descriptions'>")
                html.append(" <a href='{}?sermo-author={}'>{}</a></span>".format(url, instance.id, number))
            # Combine the HTML code
            sBack = "\n".join(html)
        return sBack, sTitle


class AuthorListDownload(BasicPart):
    MainModel = Author
    template_name = "seeker/download_status.html"
    action = "download"
    dtype = "csv"       # downloadtype

    def custom_init(self):
        """Calculate stuff"""
        
        dt = self.qd.get('downloadtype', "")
        if dt != None and dt != '':
            self.dtype = dt

    def get_queryset(self, prefix):

        # Get parameters
        name = self.qd.get("name", "")

        # Construct the QS
        lstQ = []
        if name != "": lstQ.append(Q(name__iregex=adapt_search(name)))
        qs = Author.objects.filter(*lstQ).order_by('name')

        return qs

    def get_data(self, prefix, dtype, response=None):
        """Gather the data as CSV, including a header line and comma-separated"""

        # Initialize
        lData = []
        sData = ""

        if dtype == "json":
            # Loop
            for author in self.get_queryset(prefix):
                row = {"id": author.id, "name": author.name}
                lData.append(row)
            # convert to string
            sData = json.dumps(lData)
        else:
            # Create CSV string writer
            output = StringIO()
            delimiter = "\t" if dtype == "csv" else ","
            csvwriter = csv.writer(output, delimiter=delimiter, quotechar='"')
            # Headers
            headers = ['id', 'name']
            csvwriter.writerow(headers)
            # Loop
            for author in self.get_queryset(prefix):
                row = [author.id, author.name]
                csvwriter.writerow(row)

            # Convert to string
            sData = output.getvalue()
            output.close()

        return sData


# ====================== LIBRARY VIEWS AND OPERATIONS ===================

class LibraryListView(BasicList):
    """Listview of libraries in countries/cities"""

    model = Library
    listform = LibrarySearchForm
    has_select2 = True
    prefix = "lib"
    plural_name = "Libraries"
    sg_name = "Library"
    order_cols = ['lcountry__name', 'lcity__name', 'name', 'idLibrEtab', 'mcount', '']
    order_default = order_cols
    order_heads = [
        {'name': 'Country',     'order': 'o=1', 'type': 'str', 'custom': 'country', 'default': "", 'linkdetails': True},
        {'name': 'City',        'order': 'o=2', 'type': 'str', 'custom': 'city',    'default': "", 'linkdetails': True},
        {'name': 'Library',     'order': 'o=3', 'type': 'str', 'field':  "name",    "default": "", 'main': True, 'linkdetails': True},
        {'name': 'CNRS',        'order': 'o=4', 'type': 'int', 'custom': 'cnrs',    'align': 'right' },
        {'name': 'Manuscripts', 'order': 'o=5', 'type': 'int', 'custom': 'manuscripts'},
        {'name': 'type',        'order': '',    'type': 'str', 'custom': 'libtype'},
        # {'name': '',            'order': '',    'type': 'str', 'custom': 'links'}
        ]
    filters = [ 
        {"name": "Country", "id": "filter_country", "enabled": False},
        {"name": "City",    "id": "filter_city",    "enabled": False},
        {"name": "Library", "id": "filter_library", "enabled": False}
        ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'country',   'fkfield': 'lcountry',  'keyList': 'countrylist',    'infield': 'name' },
            {'filter': 'city',      'fkfield': 'lcity',     'keyList': 'citylist',       'infield': 'name' },
            {'filter': 'library',   'dbfield': 'name',      'keyList': 'librarylist',    'infield': 'name', 'keyS': 'library_ta' }
            ]
         }
        ]
    downloads = [{"label": "Excel", "dtype": "xlsx", "url": 'library_results'},
                 {"label": "csv (tab-separated)", "dtype": "csv", "url": 'library_results'},
                 {"label": None},
                 {"label": "json", "dtype": "json", "url": 'library_results'}]

    def initializations(self):
        oErr = ErrHandle()
        try:
            # Check if signature adaptation is needed
            mcounting = Information.get_kvalue("mcounting")
            if mcounting == None or mcounting != "done":
                # Perform adaptations
                with transaction.atomic():
                    for lib in Library.objects.all():
                        mcount = lib.library_manuscripts.count()
                        if lib.mcount != mcount:
                            lib.mcount = mcount
                            lib.save()
                # Success
                Information.set_kvalue("mcounting", "done")

        except:
            msg = oErr.get_error_message()
            oErr.DoError("LibraryListView/initializations")
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "country":
            if instance.lcountry != None:
                sBack = instance.lcountry.name
        elif custom == "city":
            if instance.lcity != None:
                sBack = instance.lcity.name
        elif custom == "cnrs":
            if instance.idLibrEtab >= 0:
                sBack = instance.idLibrEtab
        elif custom == "manuscripts":
            count = instance.num_manuscripts()
            if count == 0:
                sBack = "-"
            else:
                html = []
                html.append("<span>{}</span>".format(count))
                # Create the URL
                url = "{}?manu-library={}".format(reverse('manuscript_list'), instance.id)
                # Add a link to them
                html.append('<a role="button" class="btn btn-xs jumbo-3" title="Go to these manuscripts" ')
                html.append(' href="{}"><span class="glyphicon glyphicon-chevron-right"></span></a>'.format(url))
                sBack = "\n".join(html)
        elif custom == "libtype":
            if instance.libtype != "":
                sTitle = instance.get_libtype_display()
                sBack = instance.libtype

        return sBack, sTitle


class LibraryListDownload(BasicPart):
    MainModel = Library
    template_name = "seeker/download_status.html"
    action = "download"
    dtype = "csv"       # downloadtype

    def custom_init(self):
        """Calculate stuff"""
        
        dt = self.qd.get('downloadtype', "")
        if dt != None and dt != '':
            self.dtype = dt

    def add_to_context(self, context):
        # Provide search URL and search name
        #context['search_edit_url'] = reverse("seeker_edit", kwargs={"object_id": self.basket.research.id})
        #context['search_name'] = self.basket.research.name
        return context

    def get_queryset(self, prefix):

        # Get parameters
        country = self.qd.get("country", "")
        city = self.qd.get("city", "")
        library = self.qd.get("library", "")

        # Construct the QS
        lstQ = []
        loc_qs = None

        # if country != "": lstQ.append(Q(country__name__iregex=adapt_search(country)))
        # if city != "": lstQ.append(Q(city__name__iregex=adapt_search(city)))

        if country != "":
            lstQ = []
            lstQ.append(Q(name__iregex=adapt_search(country)))
            lstQ.append(Q(loctype__name="country"))
            country_qs = Location.objects.filter(*lstQ)
            if city == "":
                loc_qs = country_qs
            else:
                lstQ = []
                lstQ.append(Q(name__iregex=adapt_search(city)))
                lstQ.append(Q(loctype__name="city"))
                loc_qs = Location.objects.filter(*lstQ)
        elif city != "":
            lstQ = []
            lstQ.append(Q(name__iregex=adapt_search(city)))
            lstQ.append(Q(loctype__name="city"))
            loc_qs = Location.objects.filter(*lstQ)

        lstQ = []
        if library != "": lstQ.append(Q(name__iregex=adapt_search(library)))
        if loc_qs != None: lstQ.append(Q(location__in=loc_qs))

        qs = Library.objects.filter(*lstQ).order_by('country__name', 'city__name', 'name')

        return qs

    def get_data(self, prefix, dtype, response=None):
        """Gather the data as CSV, including a header line and comma-separated"""

        # Initialize
        lData = []
        sData = ""

        if dtype == "json":
            # Loop
            with transaction.atomic():
                for lib in self.get_queryset(prefix):
                    country = ""
                    city = ""
                    if lib.country: country = lib.country.name
                    if lib.city: city = lib.city.name
                    row = {"id": lib.id, "country": lib.get_country_name(), "city": lib.get_city_name(), "library": lib.name, "libtype": lib.libtype}
                    lData.append(row)

            ## Loop
            #for oLib in self.get_queryset(prefix).values('id', 'lcountry__name', 'lcity__name', 'name', 'libtype'):
            #    country = ""
            #    city = ""
            #    if lib.country: country = lib.country.name
            #    if lib.city: city = lib.city.name
            #    row = {"id": lib.id, "country": lib.get_country_name(), "city": lib.get_city_name(), "library": lib.name, "libtype": lib.libtype}
            #    lData.append(row)
            # convert to string
            sData = json.dumps(lData)
        else:
            # Create CSV string writer
            output = StringIO()
            delimiter = "\t" if dtype == "csv" else ","
            csvwriter = csv.writer(output, delimiter=delimiter, quotechar='"')
            # Headers
            headers = ['id', 'country', 'city', 'library', 'libtype']
            csvwriter.writerow(headers)
            qs = self.get_queryset(prefix)
            if qs.count() > 0:
                # Loop
                with transaction.atomic():
                    for lib in qs:
                        row = [lib.id, lib.get_country_name(), lib.get_city_name(), lib.name, lib.libtype]
                        csvwriter.writerow(row)

            # Convert to string
            sData = output.getvalue()
            output.close()

        return sData


class LibraryEdit(BasicDetails):
    model = Library
    mForm = LibraryForm
    prefix = 'lib'
    prefix_type = "simple"
    title = "LibraryDetails"
    rtype = "json"
    history_button = True
    mainitems = []
    stype_edi_fields = ['idLibrEtab', 'name', 'libtype', 'location', 'lcity', 'lcountry']
    
    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Name:",                 'value': instance.name,                     'field_key': "name"},
            {'type': 'plain', 'label': "Library type:",         'value': instance.get_libtype_display(),    'field_key': 'libtype'},
            {'type': 'plain', 'label': "CNRS library id:",      'value': instance.idLibrEtab,               'field_key': "idLibrEtab"},
            {'type': 'plain', 'label': "Library location:",     "value": instance.get_location_markdown(),  'field_key': "location"},
            {'type': 'plain', 'label': "City of library:",      "value": instance.get_city_name()},
            {'type': 'plain', 'label': "Country of library: ",  "value": instance.get_country_name()}
            ]

        # Signal that we have select2
        context['has_select2'] = True

        # Return the context we have made
        return context

    def before_save(self, form, instance):
        bNeedSaving = False
        # Check whether the location has changed
        if 'location' in form.changed_data:
            # Get the new location
            location = form.cleaned_data['location']
            if location != None:
                # Get the hierarchy including myself
                hierarchy = location.hierarchy()
                for item in hierarchy:
                    if item.loctype.name == "city":
                        instance.lcity = item
                        bNeedSaving = True
                    elif item.loctype.name == "country":
                        instance.lcountry = item
                        bNeedSaving = True

        return True, ""

    def action_add(self, instance, details, actiontype):
        """User can fill this in to his/her liking"""
        lila_action_add(self, instance, details, actiontype)

    def get_history(self, instance):
        return lila_get_history(instance)
    

class LibraryDetails(LibraryEdit):
    """The full HTML version of the edit, together with French library contents"""

    rtype = "html"

    def add_to_context(self, context, instance):
        # First make sure we have the 'default' context from LibraryEdit
        context = super(LibraryDetails, self).add_to_context(context, instance)

        # Do we have a city and a library?
        city = instance.lcity
        library = instance.name
        if city != None and library != None:
            # Go and find out if there are any French connections
            sLibList = get_cnrs_manuscripts(city, library)
            sLibList = sLibList.strip()
            # Add this to 'after details'
            if sLibList != "":
                lhtml = []
                lhtml.append("<h4>Available in the CNRS library</h4>")
                lhtml.append("<div>{}</div>".format(sLibList))
                context['after_details'] = "\n".join(lhtml)

        # Return the adapted context
        return context


# ================= REPORTS ON UPLOADS =================================

class ReportListView(BasicList):
    """Listview of reports"""

    model = Report
    listform = ReportEditForm
    has_select2 = True
    bUseFilter = True
    new_button = False
    basic_name = "report"
    order_cols = ['created', 'user', 'reptype', '']
    order_default = ['-created', 'user', 'reptype']
    order_heads = [{'name': 'Date', 'order': 'o=1', 'type': 'str', 'custom': 'date', 'align': 'right', 'linkdetails': True},
                   {'name': 'User', 'order': 'o=2', 'type': 'str', 'custom': 'user', 'linkdetails': True},
                   {'name': 'Type', 'order': 'o=3', 'type': 'str', 'custom': 'reptype', 'main': True, 'linkdetails': True},
                   {'name': 'Size', 'order': '',    'type': 'str', 'custom': 'size'}]
    filters = [ {"name": "User",       "id": "filter_user",      "enabled": False} ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'user', 'fkfield': 'user', 'keyFk': 'username', 'keyList': 'userlist', 'infield': 'id'}
            ]}
         ]

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "date":
            sBack = instance.created.strftime("%d/%b/%Y %H:%M")
        elif custom == "user":
            sBack = instance.user.username
        elif custom == "reptype":
            sBack = instance.get_reptype_display()
        elif custom == "size":
            # Get the total number of downloaded elements
            iSize = 0
            rep = instance.contents
            if rep != None and rep != "" and rep[0] == "{":
                oRep = json.loads(rep)
                if 'list' in oRep:
                    iSize = len(oRep['list'])
            sBack = "{}".format(iSize)
        return sBack, sTitle


class ReportEdit(BasicDetails):
    model = Report
    mForm = ReportEditForm
    prefix = "rpt"
    title = "ReportDetails"
    no_delete = True            # Don't allow users to remove a report
    mainitems = []

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Created:",      'value': instance.get_created()         },
            {'type': 'line',  'label': "User:",         'value': instance.user.username         },
            {'type': 'line',  'label': "Report type:",  'value': instance.get_reptype_display() },
            # {'type': 'safe',  'label': "Download:",     'value': self.get_download_html(instance)},
            {'type': 'safe',  'label': "Raw data:",     'value': self.get_raw(instance)}
            ]

        # Signal that we do have select2
        context['has_select2'] = True

        # Return the context we have made
        return context

    def get_download_html(self, instance):
        """Get HTML representation of the report download buttons"""

        sBack = ""
        template_name = "seeker/report_download.html"
        oErr = ErrHandle()
        try:
            context = dict(report=instance)
            sBack = render_to_string(template_name, context, self.request)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ReportEdit/get_download_html")
        return sBack

    def get_raw(self, instance):
        """Get HTML representation of the report details"""

        sBack = ""
        if instance.contents != None and instance.contents != "" and instance.contents[0] == "{":
            # There is a real report
            sContents = "-" if instance.contents == None else instance.contents
            sBack = "<textarea rows='1' style='width: 100%;'>{}</textarea>".format(sContents)
        return sBack


class ReportDetails(ReportEdit):
    """HTML output for a Report"""

    rtype = "html"

    def add_to_context(self, context, instance):
        context = super(ReportDetails, self).add_to_context(context, instance)

        context['after_details'] = self.get_download_html(instance)

        return context


class ReportDownload(BasicPart):
    MainModel = Report
    template_name = "seeker/download_status.html"
    action = "download"
    dtype = "csv"       # Download Type

    def custom_init(self):
        """Calculate stuff"""
        
        dt = self.qd.get('downloadtype', "")
        if dt != None and dt != '':
            self.dtype = dt

    def get_data(self, prefix, dtype, response=None):
        """Gather the data as CSV, including a header line and comma-separated"""

        # Initialize
        lData = []

        # Unpack the report contents
        sData = self.obj.contents

        if dtype == "json":
            # no need to do anything: the information is already in sData
            pass
        else:
            # Convert the JSON to a Python object
            oContents = json.loads(sData)
            # Get the headers and the list
            headers = oContents['headers']

            # Create CSV string writer
            output = StringIO()
            delimiter = "\t" if dtype == "csv" else ","
            csvwriter = csv.writer(output, delimiter=delimiter, quotechar='"')

            # Write Headers
            csvwriter.writerow(headers)

            # Two lists
            todo = [oContents['list'], oContents['read'] ]
            for lst_report in todo:

                # Loop
                for item in lst_report:
                    row = []
                    for key in headers:
                        if key in item:
                            row.append(item[key].replace("\r", " ").replace("\n", " "))
                        else:
                            row.append("")
                    csvwriter.writerow(row)

            # Convert to string
            sData = output.getvalue()
            output.close()

        return sData


# ================ INFORMATION SOURCE ==================================

class SourceListView(BasicList):
    """Listview of sources"""

    model = SourceInfo
    listform = SourceEditForm
    has_select2 = True
    bUseFilter = True
    prefix = "src"
    new_button = False
    basic_name = "source"
    order_cols = ['created', 'collector', 'url', '']
    order_default = ['-created', 'collector', 'url']
    order_heads = [{'name': 'Date',           'order': 'o=1','type': 'str', 'custom': 'date', 'align': 'right', 'linkdetails': True},
                   {'name': 'Collector',      'order': 'o=2', 'type': 'str', 'field': 'collector', 'linkdetails': True},
                   {'name': 'Collected from', 'order': 'o=3', 'type': 'str', 'custom': 'from', 'main': True},
                   {'name': 'Manuscripts',    'order': '',    'type': 'int', 'custom': 'manucount'}]
    filters = [ {"name": "Collector",       "id": "filter_collector",      "enabled": False} ]
    searches = [
        {'section': '', 'filterlist': [
            {'filter': 'collector', 'fkfield': 'profile', 'keyS': 'profile_ta', 'keyFk': 'user__username', 'keyList': 'profilelist', 'infield': 'id'}
            ]}
         ]

    def initializations(self):
        # Remove SourceInfo's that are not tied to a Manuscript anymore
        remove_id = []
        for obj in SourceInfo.objects.all():
            m_count = obj.sourcemanuscripts.count()
            if m_count == 0:
                remove_id.append(obj.id)
        # Remove them
        if len(remove_id) > 0:
            SourceInfo.objects.filter(id__in=remove_id).delete()
        # Find out if any manuscripts need source info
        with transaction.atomic():
            for obj in Manuscript.objects.filter(source__isnull=True):
                # Get the snote info
                snote = obj.snote
                if snote != None and snote != "" and snote[0] == "[":
                    snote_lst = json.loads(snote)
                    if len(snote_lst)>0:
                        snote_first = snote_lst[0]
                        if 'username' in snote_first:
                            username = snote_first['username']
                            profile = Profile.get_user_profile(username)
                            created = obj.created
                            source = SourceInfo.objects.create(
                                code="Manually created",
                                created=created,
                                collector=username, 
                                profile=profile)
                            obj.source = source
                            obj.save()
        # Are there still manuscripts without source?
        if Manuscript.objects.filter(source__isnull=True).count() > 0:
            # Make the NEW button available
            self.new_button = True
        return None

    def get_field_value(self, instance, custom):
        sBack = ""
        sTitle = ""
        if custom == "date":
            sBack = instance.created.strftime("%d/%b/%Y %H:%M")
        elif custom == "from":
            if instance.url != None:
                sBack = instance.url
            elif instance.code != None:
                sBack = instance.code
        elif custom == "manucount":
            count_m = instance.sourcemanuscripts.filter(mtype='man').count()
            qs_t = instance.sourcemanuscripts.filter(mtype='tem')
            count_t = qs_t.count()
            if count_m == 0:
                if count_t == 0:
                    sBack = "&nbsp;"
                    sTitle = "No manuscripts are left from this source"
                elif count_t == 1:
                    # Get the id of the manuscript
                    manu = qs_t.first()
                    # Get the ID of the template with this manuscript
                    obj_t = Template.objects.filter(manu=manu).first()
                    url = reverse("template_details", kwargs={'pk': obj_t.id})
                    sBack = "<a href='{}' title='One template manuscript'><span class='badge jumbo-2 clickable'>{}</span></a>".format(
                        url, count_t)
                else:
                    url = reverse('template_list')
                    sBack = "<a href='{}?tmp-srclist={}' title='Template manuscripts'><span class='badge jumbo-1 clickable'>{}</span></a>".format(
                        url, instance.id, count_t)
            else:
                url = reverse('manuscript_list')
                sBack = "<a href='{}?manu-srclist={}' title='Manuscripts'><span class='badge jumbo-3 clickable'>{}</span></a>".format(
                    url, instance.id, count_m)
        return sBack, sTitle

    def add_to_context(self, context, initial):
        SourceInfo.init_profile()
        return context


class SourceEdit(BasicDetails):
    model = SourceInfo
    mForm = SourceEditForm
    prefix = 'source'
    prefix_type = "simple"
    basic_name = 'source'
    title = "SourceInfo"
    mainitems = []

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        # Define the main items to show and edit
        context['mainitems'] = [
            {'type': 'plain', 'label': "Created:",      'value': instance.get_created()     },
            {'type': 'line',  'label': "Collector:",    'value': instance.get_username()    },
            {'type': 'line',  'label': "URL:",          'value': instance.url,              'field_key': 'url'  },
            {'type': 'line',  'label': "Code:",         'value': instance.get_code_html(),  'field_key': 'code' },
            {'type': 'safe',  'label': "Manuscript:",   'value': instance.get_manu_html(),  
             'field_list': 'manulist' }
            ]

        # Signal that we do have select2
        context['has_select2'] = True

        # Return the context we have made
        return context

    def before_save(self, form, instance):
        # Determine the user
        if self.request.user != None:
            profile = Profile.get_user_profile(self.request.user.username)
            form.instance.profile = profile
            # Check if a manuscript has been given
            manulist = form.cleaned_data.get('manulist', None)
            if manulist != None:
                #  manuscript has been added
                manu = Manuscript.objects.filter(id=manulist.id).first()
                if manu != None:
                    manu.source = instance
                    manu.save()
        return True, ""


class SourceDetails(SourceEdit):
    """The HTML variant of [SourceEdit]"""

    rtype = "html"
    

# ================= LITERATURE REFERENCES ===============================

class LitRefListView(ListView):
    """Listview of edition and literature references"""
       
    model = Litref
    paginate_by = 2000
    template_name = 'seeker/literature_list.html'
    entrycount = 0    
    entrycount_collection = 0
    qd = None
    # EK: nee dus, dit zijn geen projecten. plural_name = "Projects"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(LitRefListView, self).get_context_data(**kwargs)

        oErr = ErrHandle()
        try:
            # Get the parameters passed on with the GET or the POST request
            initial = self.request.GET if self.request.method == "GET" else self.request.POST

            # Determine the count for literature references
            context['entrycount'] = self.entrycount # self.get_queryset().count()
        
            # Set the prefix
            context['app_prefix'] = APP_PREFIX

            # Make sure the paginate-values are available
            context['paginateValues'] = paginateValues

            if 'paginate_by' in initial:
                context['paginateSize'] = int(initial['paginate_by'])
            else:
                context['paginateSize'] = paginateSize

            # Set the title of the application
            context['title'] = "LiLaC literature info"

            # Change name of the qs for collection references 
            context['collection_list'] = self.get_collectionset() 

            # Determine the count for collection references
            context['entrycount_collection'] = self.entrycount_collection

            # Add the standard authenticated, uploader,editor and moderator groups
            context = get_application_context(self.request, context)

            # Process this visit and get the new breadcrumbs object
            prevpage = reverse('home')
            context['prevpage'] = prevpage
            context['breadcrumbs'] = get_breadcrumbs(self.request, "Literature references", True)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("LitRefListView/get_context_data")

        # Return the calculated context
        return context
    
    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in default class property value.
        """
        return self.paginate_by
    
    def get_queryset(self):
        """Get queryset literature references"""

        qs = None
        oErr = ErrHandle()
        try:

            # Calculate the final qs for the manuscript litrefs
            litref_ids = [x['reference'] for x in LitrefMan.objects.all().values('reference')]

            # Combine the two qs into one and filter
            qs = Litref.objects.filter(id__in=litref_ids).order_by('short')

            # Determine the length
            self.entrycount = qs.count()

        except:
            msg = oErr.get_error_message()
            oErr.DoError("LitRefListView/get_queryset")
        # Return the resulting filtered and sorted queryset
        return qs

    def get_collectionset(self):
        """Get Queryset collection references"""

        qs = None
        oErr = ErrHandle()
        try:
            # Calculate the final qs for the litrefs between an edition item and a SG
            ediref_ids = [x['reference'] for x in LitrefCol.objects.all().values('reference')]
       
            # Sort and filter all editions
            qs = Litref.objects.filter(id__in=ediref_ids).order_by('full')

            # Determine the length
            self.entrycount_collection = qs.count()

        except:
            msg = oErr.get_error_message()
            oErr.DoError("LitRefListView/get_collectionset")
        # Return the resulting filtered and sorted queryset
        return qs


# =================== CANWITHAUSTAT combinations ========================

class CanwitAustatEdit(BasicDetails):
    """Details view of the combination CanwitAustat"""

    model = CanwitAustat
    mForm = CanwitSuperForm
    prefix = 'cwau'
    prefix_type = 'simple'
    basic_name = 'canwitaustat'
    title = "Austat link"
    listform = None
    mainitems = []

    def add_to_context(self, context, instance):
        """Add to the existing context"""

        oErr = ErrHandle()
        try:
            # Define the main items to show and edit
            context['mainitems'] = [
                {'type': 'safe',  'label': "Canon witness:",            'value': instance.get_canwit_html(),        'field_view': 'canwit'  },
                {'type': 'safe',  'label': "Manuscript:",               'value': instance.get_manu_html()},
                {'type': 'safe',  'label': "Authoritative statement:",  'value': instance.get_austat_html(),        'field_view': 'austat'  },
                {'type': 'plain', 'label': "FONS type:",                'value': instance.get_fonstype_display()                            },
                {'type': 'plain', 'label': "Note:",                     'value': instance.note,                     'field_key': 'newnote'  }
                ]

            # Signal that we do have select2
            context['has_select2'] = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CanwitAustatEdit/add_to_context")

        # Return the context we have made
        return context

    def after_save(self, form, instance):
        # Process a change from [newnote] to [note]

        oErr = ErrHandle()
        try:
            cleaned = form.cleaned_data
            newnote = cleaned.get("newnote")
            if not newnote is None:
                # Compare with existing note
                if instance.note != newnote:
                    instance.note = newnote
                    instance.save()
        except:
            msg = oErr.get_error_message()
            pass

        return True, ""


class CanwitAustatDetails(CanwitAustatEdit):
    """The HTML variant of [CanwitAustatEdit]"""

    rtype = "html"









# =========================================================================





