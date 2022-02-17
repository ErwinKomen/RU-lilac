"""
Definition of views for the READER app.
"""

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Prefetch, Count, F
from django.db.models.functions import Lower
from django.db.models.query import QuerySet 
from django.forms import formset_factory, modelformset_factory, inlineformset_factory, ValidationError
from django.forms.models import model_to_dict
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template.loader import render_to_string
from django.template import Context
from django.views.generic.detail import DetailView
from django.views.generic.base import RedirectView
from django.views.generic import ListView, View
from django.views.decorators.csrf import csrf_exempt

# General imports
from datetime import datetime
import operator 
from operator import itemgetter
from functools import reduce
from time import sleep 
import fnmatch
import sys, os
import base64
import json
import csv, re
import requests
import demjson
import openpyxl
from openpyxl.utils.cell import get_column_letter
from io import StringIO
from itertools import chain

# Imports needed for working with XML and other file formats
from xml.dom import minidom
# See: http://effbot.org/zone/celementtree.htm
import xml.etree.ElementTree as ElementTree
 
# ======= imports from my own application ======
from lila.settings import APP_PREFIX, MEDIA_DIR, WRITABLE_DIR
from lila.utils import ErrHandle
from lila.reader.forms import UploadFileForm, UploadFilesForm
from lila.seeker.models import Manuscript, Canwit, Status, SourceInfo, ManuscriptExt, Provenance, ProvenanceMan, \
    Library, Location, CanwitSignature, Author, Feast, Daterange, Comment, Profile, MsItem, Canhead, Origin, \
    Report, Keyword, ManuscriptKeyword, ManuscriptProject, STYPE_IMPORTED, get_current_datetime

# ======= from RU-Basic ========================
from lila.basic.views import BasicList, BasicDetails, BasicPart

# =================== This is imported by seeker/views.py ===============
reader_uploads = [
    {"title": "ecodex", "label": "e-codices", "url": "import_ecodex", "type": "multiple",
     "msg": "Upload e-codices XML files (n), using default project assignment defined in Mylila"},
    {"title": "ead",    "label": "EAD",       "url": "import_ead",    "type": "multiple",
     "msg": "Upload 'Archives et Manuscripts' XML files, using default project assignment defined in Mylila"}
    ]
# Global debugging 
bDebug = False


# =============== Helper functions ======================================

def getText(nodeStart):
    # Iterate all Nodes aggregate TEXT_NODE
    rc = []
    for node in nodeStart.childNodes:
        if node.nodeType == node.TEXT_NODE:
            sText = node.data.strip(' \t\n')
            if sText != "":
                rc.append(sText)
        else:
            # Recursive
            rc.append(getText(node))
    return ' '.join(rc)

def download_file(url):
    """Download a file from the indicated URL"""

    bResult = True
    sResult = ""
    errHandle = ErrHandle()
    # Get the filename from the url
    name = url.split("/")[-1]
    # Set the output directory
    outdir = os.path.abspath(os.path.join(MEDIA_DIR, "e-codices"))
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    # Create a filename where we can store it
    filename = os.path.abspath(os.path.join(outdir, name))
    try:
        r = requests.get(url)
    except:
        sMsg = errHandle.get_error_message()
        errHandle.DoError("Request problem")
        return False, sMsg
    if r.status_code == 200:
        # Read the response
        sText = r.text
        # Write away
        with open(filename, "w", encoding="utf-8") as f:
            f.write(sText)
        sResult = filename
    else:
        bResult = False
        sResult = "download_file received status {} for {}".format(r.status_code, url)
    # Return the result
    return bResult, sResult

def user_is_ingroup(request, sGroup):
    # Is this user part of the indicated group?
    username = request.user.username
    user = User.objects.filter(username=username).first()
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

def get_user_profile(username):
        # Sanity check
        if username == "":
            # Rebuild the stack
            return None
        # Get the user
        user = User.objects.filter(username=username).first()
        # Get to the profile of this user
        profile = Profile.objects.filter(user=user).first()
        return profile



class ReaderImport(View):
    # Initialisations
    arErr = []
    error_list = []
    transactions = []
    data = {'status': 'ok', 'html': ''}
    template_name = 'reader/import_manuscripts.html'
    obj = None
    oStatus = None
    data_file = ""
    bClean = False
    import_type = "undefined"
    sourceinfo_url = "undefined"
    username = ""
    mForm = UploadFilesForm
    
    def post(self, request, pk=None):
        # A POST request means we are trying to SAVE something
        self.initializations(request, pk)

        # Explicitly set the status to OK
        self.data['status'] = "ok"

        username = request.user.username
        self.username = username

        if self.checkAuthentication(request):
            # Remove previous status object for this user
            Status.objects.filter(user=username).delete()
            # Create a status object
            oStatus = Status(user=username, type=self.import_type, status="preparing")
            oStatus.save()
            # Make sure the status is available
            self.oStatus = oStatus

            form = self.mForm(request.POST, request.FILES)
            lResults = []
            if form.is_valid():
                # NOTE: from here a breakpoint may be inserted!
                print('import_{}: valid form'.format(self.import_type))
                oErr = ErrHandle()
                try:
                    # The list of headers to be shown
                    lHeader = ['status', 'msg', 'name', 'yearstart', 'yearfinish', 'library', 'idno', 'filename', 'url']

                    # Get profile 
                    profile = Profile.get_user_profile(username) 
                    
                    # Create a SourceInfo object for this extraction
                    source = SourceInfo.objects.create(url=self.sourceinfo_url, collector=username, profile = profile)

                    # Process the request
                    bOkay, code = self.process_files(request, source, lResults, lHeader)

                    if bOkay:
                        # Adapt the 'source' to tell what we did 
                        source.code = code
                        oErr.Status(code)
                        source.save()
                        # Indicate we are ready
                        oStatus.set("readyclose")
                        # Get a list of errors
                        error_list = [str(item) for item in self.arErr]

                        statuscode = "error" if len(error_list) > 0 else "completed"

                        # Create the context
                        context = dict(
                            statuscode=statuscode,
                            results=lResults,
                            error_list=error_list
                            )
                    else:
                        self.arErr.append(code)

                    if len(self.arErr) == 0:
                        # Get the HTML response
                        self.data['html'] = render_to_string(self.template_name, context, request)
                    else:
                        lHtml = []
                        for item in self.arErr:
                            lHtml.append(item)
                        self.data['html'] = "There are errors: {}".format("\n".join(lHtml))
                except:
                    msg = oErr.get_error_message()
                    oErr.DoError("import_{}".format(self.import_type))
                    self.data['html'] = msg
                    self.data['status'] = "error"

            else:
                self.data['html'] = 'invalid form: {}'.format(form.errors)
                self.data['status'] = "error"
        
            # NOTE: do ***not*** add a breakpoint until *AFTER* form.is_valid
        else:
            self.data['html'] = "Please log in before continuing"

        # Return the information
        return JsonResponse(self.data)

    def initializations(self, request, object_id):
        # Clear errors
        self.arErr = []
        # COpy the request
        self.request = request

        # Get the parameters
        if request.POST:
            self.qd = request.POST
        else:
            self.qd = request.GET
        # ALWAYS: perform some custom initialisations
        self.custom_init()

    def custom_init(self):
        pass    

    def checkAuthentication(self,request):
        # first check for authentication
        if not request.user.is_authenticated:
            # Provide error message
            self.data['html'] = "Please log in to work on this project"
            return False
        elif not user_is_ingroup(request, 'lila_uploader'):
            # Provide error message
            self.data['html'] = "Sorry, you do not have the rights to upload anything"
            return False
        else:
            return True

    def add_manu(self, lst_manual, lst_read, status="", msg="", user="", name="", url="", yearstart="", yearfinish="",
                    library="", idno="", filename=""):
        oInfo = {}
        oInfo['status'] = status
        oInfo['msg'] = msg
        oInfo['user'] = user
        oInfo['name'] = name
        oInfo['url'] = url
        oInfo['yearstart'] = yearstart
        oInfo['yearfinish'] = yearfinish
        oInfo['library'] = library
        oInfo['idno'] = idno
        oInfo['filename'] = filename
        if status == "error":
            lst_manual.append(oInfo)
        else:
            lst_read.append(oInfo)
        return True

    def process_files(self, request, source, lResults, lHeader):
        bOkay = True
        code = ""
        return bOkay, code





