"""
Definition of typeahead views for the SEEKER app.
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

import requests
import json


# ======= imports from my own application ======
from lila.utils import ErrHandle
from lila.seeker.models import get_crpp_date, get_current_datetime, process_lib_entries, get_searchable, get_now_time, \
    add_gold2equal, add_equal2equal, add_ssg_equal2equal, get_helptext, Information, Country, City, Author, Manuscript, \
    User, Group, Origin, Canwit, MsItem, Codhead, CanwitKeyword, CanwitAustat, NewsItem, \
    SourceInfo, AustatKeyword, ManuscriptExt, \
    ManuscriptKeyword, Action, Austat, AustatLink, Location, LocationName, LocationIdentifier, LocationRelation, LocationType, \
    ProvenanceMan, Provenance, Daterange, CollOverlap, BibRange, Feast, Comment, AustatDist, \
    Basket, BasketMan, BasketSuper, Litref, LitrefMan, LitrefCol, Report, \
    Visit, Profile, Keyword, CanwitSignature, Status, Library, Collection, CollectionSerm, \
    CollectionMan, CollectionSuper, UserKeyword, Template, \
    ManuscriptCorpus, ManuscriptCorpusLock, AustatCorpus, ProjectEditor, \
    Codico, ProvenanceCod, OriginCodico, CodicoKeyword, Reconstruction, \
    Project, ManuscriptProject, CollectionProject, AustatProject, CanwitProject, \
    get_reverse_spec, LINK_EQUAL, LINK_PRT, LINK_BIDIR, LINK_PARTIAL, STYPE_IMPORTED, STYPE_EDITED, STYPE_MANUAL, LINK_UNSPECIFIED


# ============= TYPEAHEAD VIEWS ============================


@csrf_exempt
def get_countries(request):
    """Get a list of countries for autocomplete"""

    data = 'fail'
    method = "useLocation"
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sName = request.GET.get('country', '')
            if sName == "": sName = request.GET.get('country_ta', "")
            lstQ = []
            lstQ.append(Q(name__icontains=sName))
            if method == "useLocation":
                loctype = LocationType.find("country")
                lstQ.append(Q(loctype=loctype))
                countries = Location.objects.filter(*lstQ).order_by('name')
            else:
                countries = Country.objects.filter(*lstQ).order_by('name')
            results = []
            for co in countries:
                co_json = {'name': co.name, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_countries")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_cities(request):
    """Get a list of cities for autocomplete"""

    data = 'fail'
    method = "useLocation"
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            # Get the user-specified 'country' and 'city' strings
            country = request.GET.get('country', "")
            if country == "": country = request.GET.get('country_ta', "")
            city = request.GET.get("city", "")
            if city == "": city = request.GET.get('city_ta', "")

            # build the query
            lstQ = []
            if method == "useLocation":
                # Start as broad as possible: country
                qs_loc = None
                if country != "":
                    loctype_country = LocationType.find("country")
                    lstQ.append(Q(name=country))
                    lstQ.append(Q(loctype=loctype_country))
                    qs_country = Location.objects.filter(*lstQ)
                    # Fine-tune on city...
                    loctype_city = LocationType.find("city")
                    lstQ = []
                    lstQ.append(Q(name__icontains=city))
                    lstQ.append(Q(loctype=loctype_city))
                    lstQ.append(Q(relations_location__in=qs_country))
                    cities = Location.objects.filter(*lstQ)
                else:
                    loctype_city = LocationType.find("city")
                    lstQ.append(Q(name__icontains=city))
                    lstQ.append(Q(loctype=loctype_city))
                    cities = Location.objects.filter(*lstQ)
            elif method == "slowLocation":
                # First of all: city...
                loctype_city = LocationType.find("city")
                lstQ.append(Q(name__icontains=city))
                lstQ.append(Q(loctype=loctype_city))
                # Do we have a *country* specification?
                if country != "":
                    loctype_country = LocationType.find("country")
                    lstQ.append(Q(relations_location__name=country))
                    lstQ.append(Q(relations_location__loctype=loctype_country))
                # Combine everything
                cities = Location.objects.filter(*lstQ).order_by('name')
            else:
                if country != "":
                    lstQ.append(Q(country__name__icontains=country))
                lstQ.append(Q(name__icontains=city))
                cities = City.objects.filter(*lstQ).order_by('name')
            results = []
            for co in cities:
                co_json = {'name': co.name, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_cities")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)
    
@csrf_exempt
def get_libraries(request):
    """Get a list of libraries for autocomplete"""

    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            # Get the user-specified 'country' and 'city' strings
            country = request.GET.get('country', "")
            if country == "": country = request.GET.get('country_ta', "")
            city = request.GET.get("city", "")
            if city == "": city = request.GET.get('city_ta', "")
            lib = request.GET.get("library", "")
            if lib == "": lib = request.GET.get('libname_ta', "")

            # build the query
            lstQ = []
            # Start as broad as possible: country
            qs_loc = None
            if country != "":
                loctype_country = LocationType.find("country")
                lstQ.append(Q(name=country))
                lstQ.append(Q(loctype=loctype_country))
                qs_country = Location.objects.filter(*lstQ)
                # What about city?
                if city == "":
                    qs_loc = qs_country
                else:
                    loctype_city = LocationType.find("city")
                    lstQ = []
                    lstQ.append(Q(name__icontains=city))
                    lstQ.append(Q(loctype=loctype_city))
                    lstQ.append(Q(relations_location__in=qs_country))
                    qs_loc = Location.objects.filter(*lstQ)
            elif city != "":
                loctype_city = LocationType.find("city")
                lstQ.append(Q(name__icontains=city))
                lstQ.append(Q(loctype=loctype_city))
                qs_loc = Location.objects.filter(*lstQ)

            # Start out with the idea to look for a library by name:
            lstQ = []
            if lib != "": lstQ.append(Q(name__icontains=lib))
            if qs_loc != None: lstQ.append(Q(location__in=qs_loc))

            # Combine everything
            libraries = Library.objects.filter(*lstQ).order_by('name').values('name','id') 
            results = []
            for co in libraries:
                co_json = {'name': co['name'], 'id': co['id'] }
                results.append(co_json)
            data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_libraries")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_origins(request):
    """Get a list of origin names for autocomplete"""

    data = 'fail'
    if request.is_ajax():
        sName = request.GET.get('name', '')
        lstQ = []
        lstQ.append(Q(name__icontains=sName))
        origins = Origin.objects.filter(*lstQ).order_by('name')
        results = []
        for co in origins:
            co_json = {'name': co.name, 'id': co.id }
            results.append(co_json)
        data = json.dumps(results)
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_locations(request):
    """Get a list of location names for autocomplete"""

    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sName = request.GET.get('name', '')
            lstQ = []
            lstQ.append(Q(name__icontains=sName))
            locations = Location.objects.filter(*lstQ).order_by('name').values('name', 'loctype__name', 'id')
            results = []
            for co in locations:
                # name = "{} ({})".format(co['name'], co['loctype__name'])
                name = co['name']
                co_json = {'name': name, 'id': co['id'], 'loctype': co['loctype__name'] }
                results.append(co_json)
            data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_locations")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_litref(request):
    """Get ONE particular short representation of a litref"""
    
    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sId = request.GET.get('id', '')
            co_json = {'id': sId}
            lstQ = []
            lstQ.append(Q(id=sId))
            litref = Litref.objects.filter(Q(id=sId)).first()
            if litref:
                short = litref.get_short()
                co_json['name'] = short
            data = json.dumps(co_json)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_litref")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_litrefs(request):
    """Get a list of literature references for autocomplete"""
    
    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sName = request.GET.get('name', '')
            lstQ = []
            lstQ.append(Q(full__icontains=sName)|Q(short__icontains=sName))
            litrefs = Litref.objects.filter(*lstQ).order_by('short').values('full', 'short', 'id')
            results = [] 
            for co in litrefs:
                name = "{} {}".format(co['full'], co['short'])
                co_json = {'name': name, 'id': co['id'] }
                results.append(co_json)
            data = json.dumps(results)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_litrefs")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_aslink(request):
    """Get ONE particular short representation of a *link* from canwit to a Austat"""
    
    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sId = request.GET.get('id', '')
            co_json = {'id': sId}
            lstQ = []
            lstQ.append(Q(id=sId))
            ssg = CanwitAustat.objects.filter(Q(id=sId)).first()
            if ssg:
                short = ssg.get_label()
                co_json['name'] = short
            data = json.dumps(co_json)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_aslink")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_as2as(request):
    """Get ONE particular short representation of a *link* from SSG to a SSG"""
    
    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sId = request.GET.get('id', '')
            co_json = {'id': sId}
            # oErr.Status("get_as2as id={}".format(sId))
            lstQ = []
            lstQ.append(Q(id=sId))
            ssg = AustatLink.objects.filter(Q(id=sId)).first()
            if ssg:
                short = ssg.get_label()
                co_json['name'] = short
            data = json.dumps(co_json)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_as2as")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_as(request):
    """Get ONE particular short representation of an AS"""
    
    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sId = request.GET.get('id', '')
            co_json = {'id': sId}
            lstQ = []
            lstQ.append(Q(id=sId))
            ssg = Austat.objects.filter(Q(id=sId)).first()
            if ssg:
                short = ssg.get_short()
                co_json['name'] = short
            data = json.dumps(co_json)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_as")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_asdist(request):
    """Get AS distance"""
    
    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sId = request.GET.get('id', '')
            co_json = {'id': sId}
            lstQ = []
            lstQ.append(Q(id=sId))
            dist = AustatDist.objects.filter(Q(id=sId)).first()
            if dist != None:
                ssg = Austat.objects.filter(Q(id=dist.super.id)).first()
                if ssg:
                    short = ssg.get_short()
                    co_json['name'] = short
                    data = json.dumps(co_json)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_asdist")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_manuidnos(request):
    """Get a list of manuscript identifiers for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            idno = request.GET.get("name", "")
            lstQ = []
            lstQ.append(Q(idno__icontains=idno))
            items = Manuscript.objects.filter(*lstQ).order_by("idno").distinct()
            results = []
            for co in items:
                co_json = {'name': co.idno, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_authors(request):
    """Get a list of authors for autocomplete"""

    data = 'fail'
    if request.is_ajax():
        author = request.GET.get("name", "")
        lstQ = []
        lstQ.append(Q(name__icontains=author)|Q(abbr__icontains=author))
        authors = Author.objects.filter(*lstQ).order_by('name')
        results = []
        for co in authors:
            co_json = {'name': co.name, 'id': co.id }
            results.append(co_json)
        data = json.dumps(results)
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_cwftexts(request):
    """Get a list of manifestation-canwit full text for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            author = request.GET.get("name", "")
            lstQ = []
            lstQ.append(Q(srchftext__icontains=author))
            items = Canwit.objects.filter(*lstQ).values("srchftext").distinct().all().order_by('srchftext')
            results = []
            for idx, co in enumerate(items):
                val = co['srchftext']
                co_json = {'name': val, 'id': idx }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_cwftrans(request):
    """Get a list of Manifestation-canwit full-translation for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            author = request.GET.get("name", "")
            lstQ = []
            lstQ.append(Q(srchftrans__icontains=author))
            items = Canwit.objects.filter(*lstQ).values("srchftrans").distinct().all().order_by('srchftrans')
            results = []
            for idx, co in enumerate(items):
                val = co['srchftrans']
                co_json = {'name': val, 'id': idx }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_asftexts(request):
    """Get a list of manifestation-canwit full text for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            author = request.GET.get("name", "")
            lstQ = []
            lstQ.append(Q(srchftext__icontains=author))
            items = Austat.objects.filter(*lstQ).values("srchftext").distinct().all().order_by('srchftext')
            results = []
            for idx, co in enumerate(items):
                val = co['srchftext']
                co_json = {'name': val, 'id': idx }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_asftrans(request):
    """Get a list of Manifestation-canwit full-translation for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            author = request.GET.get("name", "")
            lstQ = []
            lstQ.append(Q(srchftrans__icontains=author))
            items = Austat.objects.filter(*lstQ).values("srchftrans").distinct().all().order_by('srchftrans')
            results = []
            for idx, co in enumerate(items):
                val = co['srchftrans']
                co_json = {'name': val, 'id': idx }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_srmsignatures(request):
    """Get a list of signature codes (for Canwit) for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            codename = request.GET.get("name", "")
            editype = request.GET.get("type", "")
            lstQ = []
            lstQ.append(Q(code__icontains=codename))
            if editype != "":
                lstQ.append(Q(editype=editype))
            items = CanwitSignature.objects.filter(*lstQ).order_by("code").distinct()
            results = []
            for co in items:
                co_json = {'name': co.code, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_sermosig(request):
    """Get the correct signature, given a SERMON signature"""
    
    data = 'fail'
    if request.is_ajax():
        oErr = ErrHandle()
        try:
            sId = request.GET.get('id', '')
            co_json = {'id': sId}
            sermosig = CanwitSignature.objects.filter(Q(id=sId)).first()
            if sermosig:
                short = sermosig.code
                co_json['name'] = short
            data = json.dumps(co_json)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_sermosig")
    else:
        data = "Request is not ajax"
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_keywords(request):
    """Get a list of keywords for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            # Get the complete code line, which could use semicolon-separation
            kwline = request.GET.get("name", "")
            kwlist = kwline.split(";")
            kw = "" if len(kwlist) == 0 else kwlist[-1].strip()
            lstQ = []
            lstQ.append(Q(name__icontains=kw))
            items = Keyword.objects.filter(*lstQ).order_by("name").distinct()
            results = []
            for co in items:
                co_json = {'name': co.name, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)

@csrf_exempt
def get_collections(request):
    """Get a list of collections for autocomplete"""

    oErr = ErrHandle()
    try:
        data = 'fail'
        if request.is_ajax():
            # Get the complete code line, which could use semicolon-separation
            coll_line = request.GET.get("name", "")
            coll_list = coll_line.split(";")
            col = "" if len(coll_list) == 0 else coll_list[-1].strip()
            lstQ = []
            lstQ.append(Q(name__icontains=col))
            items = Collection.objects.filter(*lstQ).order_by("name").distinct()
            results = []
            for co in items:
                co_json = {'name': co.name, 'id': co.id }
                results.append(co_json)
            data = json.dumps(results)
        else:
            data = "Request is not ajax"
    except:
        msg = oErr.get_error_message()
        data = "error: {}".format(msg)
    mimetype = "application/json"
    return HttpResponse(data, mimetype)



