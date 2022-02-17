"""
Definition of EXCEL views for the SEEKER app.
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
import io, sys, os
import openpyxl, json
from openpyxl.utils.cell import get_column_letter
from openpyxl.cell import Cell
from openpyxl import Workbook
from io import StringIO
import csv
import requests

# ======= imports from my own application ======
from lila.settings import APP_PREFIX, MEDIA_DIR
from lila.utils import ErrHandle

from lila.seeker.models import Manuscript, Canwit, Profile, Report, Codico, Location, LocationType, Library
from lila.seeker.views import app_editor
from lila.reader.views import ReaderImport
from lila.reader.forms import UploadFileForm



class ManuscriptUploadExcel(ReaderImport):
    """Specific parameters for importing manuscripts from Excel"""

    import_type = "excel"
    sourceinfo_url = "https://www.ru.nl/english/people/boodts-s/"

    def process_files(self, request, source, lResults, lHeader):
        file_list = []
        oErr = ErrHandle()
        bOkay = True
        code = ""
        oStatus = self.oStatus
        try:
            # Make sure we have the username
            username = self.username
            profile = Profile.get_user_profile(username)
            team_group = app_editor
            kwargs = {'profile': profile, 'username': username, 'team_group': team_group}

            # Get the contents of the imported file
            files = request.FILES.getlist('files_field')
            if files != None:
                for data_file in files:
                    filename = data_file.name
                    file_list.append(filename)

                    # Set the status
                    oStatus.set("reading", msg="file={}".format(filename))

                    # Get the source file
                    if data_file == None or data_file == "":
                        self.arErr.append("No source file specified for the selected project")
                    else:
                        # Check the extension
                        arFile = filename.split(".")
                        extension = arFile[len(arFile)-1]

                        lst_manual = []
                        lst_read = []

                        # Further processing depends on the extension
                        oResult = {'status': 'ok', 'count': 0, 'sermons': 0, 'msg': "", 'user': username}

                        if extension == "xlsx":
                            # This is an Excel file: read the file using openpyxl
                            # Write data temporarily to the WRITABLE dir, but with a temporary filename
                            tmp_path = os.path.abspath(os.path.join( MEDIA_DIR, filename))
                            with io.open(tmp_path, "wb") as f:
                                sData = data_file.read()
                                f.write(sData)

                            # Read string file
                            wb = openpyxl.load_workbook(tmp_path, read_only=True)
                            sheetnames = wb.sheetnames
                            ws_manu = None
                            ws_sermo = None
                            for sname in sheetnames:
                                if "manu" in sname.lower():
                                    ws_manu = wb[sname]
                                elif "sermo" in sname.lower():
                                    ws_sermo = wb[sname]
                            # Do we have a manuscript worksheet?
                            if ws_manu != None:
                                # Process the manuscript-proper details: columns Name and Value
                                oManu = {}
                                row_num = 1
                                if ws_manu.cell(row=row_num, column=1).value.lower() == "field" and \
                                   ws_manu.cell(row=row_num, column=2).value.lower() == "value":
                                    # we can skip the first row
                                    row_num += 1
                                bStop = False
                                while not bStop:
                                    k = ws_manu.cell(row=row_num, column=1).value
                                    v = ws_manu.cell(row=row_num, column=2).value
                                    if k == "" or k == None:
                                        bStop = True
                                    else:
                                        row_num += 1
                                        k = k.lower()
                                        oManu[k] = v
                                # We have an object with key/value pairs: process it
                                manu = Manuscript.custom_add(oManu, **kwargs)

                                # Now get the codicological unit that has been automatically created and adapt it
                                codico = manu.manuscriptcodicounits.first()
                                if codico != None:
                                    oManu['manuscript'] = manu
                                    codico = Codico.custom_add(oManu, **kwargs)

                                oResult['count'] += 1
                                oResult['obj'] = manu
                                oResult['name'] = manu.idno

                                # Check if there is a "Sermon" worksheet
                                if ws_sermo != None:
                                    # Get the column names
                                    row_num = 1
                                    column = 1
                                    header = []
                                    v = ws_sermo.cell(row=row_num, column=column).value
                                    while v != None and v != "" and v != "-":                                        
                                        header.append(v.lower())
                                        column += 1
                                        v = ws_sermo.cell(row=row_num, column=column).value
                                    # Process the sermons in this sheet
                                    canwit_list = []
                                    column = 1
                                    row_num += 1
                                    v = ws_sermo.cell(row=row_num, column=column).value
                                    while v != "" and v != None:
                                        # ==== DEBUG ====
                                        oErr.Status("Upload excel row_num={}".format(row_num))
                                        # ===============

                                        # Create a new sermon object
                                        oSermon = {}
                                        # Process this row
                                        for idx, col_name in enumerate(header):
                                            column = idx + 1
                                            oSermon[col_name] = ws_sermo.cell(row=row_num, column=column).value
                                        # Process this sermon
                                        order = oSermon['order']
                                        sermon = Canwit.custom_add(oSermon, manu, order)

                                        oResult['sermons'] += 1

                                        # Get parent, firstchild, next
                                        parent = oSermon['parent']
                                        firstchild = oSermon['firstchild']
                                        nextone = oSermon['next']
                                        # Add to list
                                        canwit_list.append({'order': order, 'parent': parent, 'firstchild': firstchild,
                                                            'next': nextone, 'sermon': sermon})
                                        # GO to the next row for the next sermon
                                        row_num += 1
                                        column = 1
                                        v = ws_sermo.cell(row=row_num, column=column).value

                                    # Now process the parent/firstchild/next items
                                    with transaction.atomic():
                                        for oSermo in canwit_list:
                                            # Get the p/f/n numbers
                                            parent_id = oSermo['parent']
                                            firstchild_id = oSermo['firstchild']
                                            next_id = oSermo['next']
                                            # Process parent
                                            if parent_id != '' and parent_id != None:
                                                # parent_id = str(parent_id)
                                                parent = next((obj['sermon'] for obj in canwit_list if obj['order'] == parent_id), None)
                                                oSermo['sermon'].msitem.parent = parent.msitem
                                                oSermo['sermon'].msitem.save()
                                            # Process firstchild
                                            if firstchild_id != '' and firstchild_id != None:
                                                # firstchild_id = str(firstchild_id)
                                                firstchild = next((obj['sermon'] for obj in canwit_list if obj['order'] == firstchild_id), None)
                                                oSermo['sermon'].msitem.firstchild = firstchild.msitem
                                                oSermo['sermon'].msitem.save()
                                            # Process next
                                            if next_id != '' and next_id != None:
                                                # next_id = str(next_id)
                                                nextone = next((obj['sermon'] for obj in canwit_list if obj['order'] == next_id), None)
                                                oSermo['sermon'].msitem.next = nextone.msitem
                                                oSermo['sermon'].msitem.save()


                        # Create a report and add it to what we return
                        oContents = {'headers': lHeader, 'list': lst_manual, 'read': lst_read}
                        oReport = Report.make(username, "ixlsx", json.dumps(oContents))
                                
                        # Determine a status code
                        statuscode = "error" if oResult == None or oResult['status'] == "error" else "completed"
                        if oResult == None:
                            self.arErr.append("There was an error. No manuscripts have been added")
                        else:
                            lResults.append(oResult)
            code = "Imported using the [import_excel] function on this filew: {}".format(", ".join(file_list))
        except:
            bOkay = False
            code = oErr.get_error_message()
        return bOkay, code


class ManuscriptUploadJson(ReaderImport):
    import_type = "json"
    sourceinfo_url = "https://www.ru.nl/lila/upload_json"


    def process_files(self, request, source, lResults, lHeader):
        file_list = []
        oErr = ErrHandle()
        bOkay = True
        code = ""
        oStatus = self.oStatus
        try:
            # Make sure we have the username
            username = self.username
            profile = Profile.get_user_profile(username)
            team_group = app_editor
            kwargs = {'profile': profile, 'username': username, 'team_group': team_group, 'keyfield': 'path'}

            # Get the contents of the imported file
            files = request.FILES.getlist('files_field')
            if files != None:
                for data_file in files:
                    filename = data_file.name
                    file_list.append(filename)

                    # Set the status
                    oStatus.set("reading", msg="file={}".format(filename))

                    # Get the source file
                    if data_file == None or data_file == "":
                        self.arErr.append("No source file specified for the selected project")
                    else:
                        # Check the extension
                        arFile = filename.split(".")
                        extension = arFile[len(arFile)-1]

                        lst_manual = []
                        lst_read = []

                        # Further processing depends on the extension
                        oResult = {'status': 'ok', 'count': 0, 'sermons': 0, 'msg': "", 'user': username}

                        if extension == "json":
                            # This is a JSON file: Load the file into a variable
                            sData = data_file.read()
                            lst_manu = json.loads( sData.decode(encoding="utf8"))

                            # Check if this is a dictionary or a list
                            if isinstance(lst_manu, dict):
                                # It is a dictionary: turn it into a list
                                oManuList = lst_manu
                                lst_manu = [v for k,v in oManuList.items()]

                            # Walk through the manuscripts
                            for oManu in lst_manu:
                                # Each manuscript has some stuff of its own
                                # We have an object with key/value pairs: process it
                                manu = Manuscript.custom_add(oManu, **kwargs)

                                # Now get the codicological unit that has been automatically created and adapt it
                                codico = manu.manuscriptcodicounits.first()
                                if codico != None:
                                    oManu['manuscript'] = manu
                                    codico = Codico.custom_add(oManu, **kwargs)

                                oResult['count'] += 1
                                oResult['obj'] = manu
                                oResult['name'] = manu.idno

                                # Process all the MsItems into a list of sermons
                                canwit_list = []
                                for oMsItem in oManu['msitems']:
                                    # Get the sermon object
                                    oSermon = oMsItem['sermon']
                                    order = oMsItem['order']
                                    sermon = Canwit.custom_add(oSermon, manu, order, **kwargs)

                                    # Keep track of the number of sermons read
                                    oResult['sermons'] += 1

                                    # Get parent, firstchild, next
                                    parent = oMsItem['parent']
                                    firstchild = oMsItem['firstchild']
                                    nextone = oMsItem['next']

                                    # Add to list
                                    canwit_list.append({'order': order, 'parent': parent, 'firstchild': firstchild,
                                                        'next': nextone, 'sermon': sermon})

                                # Now process the parent/firstchild/next items
                                with transaction.atomic():
                                    for oSermo in canwit_list:
                                        # Get the p/f/n numbers
                                        parent_id = oSermo['parent']
                                        firstchild_id = oSermo['firstchild']
                                        next_id = oSermo['next']
                                        # Process parent
                                        if parent_id != '' and parent_id != None:
                                            # parent_id = str(parent_id)
                                            parent = next((obj['sermon'] for obj in canwit_list if obj['order'] == parent_id), None)
                                            oSermo['sermon'].msitem.parent = parent.msitem
                                            oSermo['sermon'].msitem.save()
                                        # Process firstchild
                                        if firstchild_id != '' and firstchild_id != None:
                                            # firstchild_id = str(firstchild_id)
                                            firstchild = next((obj['sermon'] for obj in canwit_list if obj['order'] == firstchild_id), None)
                                            oSermo['sermon'].msitem.firstchild = firstchild.msitem
                                            oSermo['sermon'].msitem.save()
                                        # Process next
                                        if next_id != '' and next_id != None:
                                            # next_id = str(next_id)
                                            nextone = next((obj['sermon'] for obj in canwit_list if obj['order'] == next_id), None)
                                            oSermo['sermon'].msitem.next = nextone.msitem
                                            oSermo['sermon'].msitem.save()


                        # Create a report and add it to what we return
                        oContents = {'headers': lHeader, 'list': lst_manual, 'read': lst_read}
                        oReport = Report.make(username, "ixlsx", json.dumps(oContents))
                                
                        # Determine a status code
                        statuscode = "error" if oResult == None or oResult['status'] == "error" else "completed"
                        if oResult == None:
                            self.arErr.append("There was an error. No manuscripts have been added")
                        else:
                            lResults.append(oResult)

            code = "Imported using the [import_json] function on this file list: {}".format(", ".join(file_list))
        except:
            bOkay = False
            code = oErr.get_error_message()
        return bOkay, code


class ManuscriptUploadGalway(ReaderImport):
    """Specific parameters for importing manuscripts from https://elmss.nuigalway.ie/"""

    import_type = "nuigalway"
    sourceinfo_url = "https://elmss.nuigalway.ie/"

    def process_files(self, request, source, lResults, lHeader):
        file_list = []
        oErr = ErrHandle()
        bOkay = True
        code = ""
        oStatus = self.oStatus
        # The list of headers to be shown
        lHeader = ['status', 'msg', 'name', 'daterange', 'library', 'idno', 'url']

        def add_manu(lst_manual, lst_read, status="", msg="", user="", name="", url="", daterange="", 
                     library="", filename="", sermons="", idno=""):
            oInfo = {}
            oInfo['status'] = status
            oInfo['msg'] = msg
            oInfo['user'] = user
            oInfo['name'] = name
            oInfo['url'] = url
            oInfo['daterange'] = daterange
            oInfo['library'] = library
            oInfo['idno'] = idno
            oInfo['filename'] = filename
            oInfo['sermons'] = sermons
            if status == "error":
                lst_manual.append(oInfo)
            else:
                lst_read.append(oInfo)
            return True

        try:
            # Make sure we have the username
            username = self.username
            profile = Profile.get_user_profile(username)
            team_group = app_editor
            kwargs = {'profile': profile, 'username': username, 'team_group': team_group, 'source': source}

            # Get the contents of the imported file
            files = request.FILES.getlist('files_field')
            if files != None:
                for data_file in files:
                    filename = data_file.name
                    file_list.append(filename)

                    # Set the status
                    oStatus.set("reading", msg="file={}".format(filename))

                    # Get the source file
                    if data_file == None or data_file == "":
                        self.arErr.append("No source file specified for the selected project")
                    else:
                        # Check the extension
                        arFile = filename.split(".")
                        extension = arFile[len(arFile)-1]

                        lst_manual = []
                        lst_read = []

                        # Further processing depends on the extension
                        oResult = {'status': 'ok', 'count': 0, 'sermons': 0, 'msg': "", 'user': username, 'filename': filename}

                        if extension == "csv":
                            # This is a CSV file. We expect the catalogue id's to be in the leftmost column

                            # Write data temporarily to the WRITABLE dir, but with a temporary filename
                            tmp_path = os.path.abspath(os.path.join( MEDIA_DIR, filename))
                            with io.open(tmp_path, "wb") as f:
                                sData = data_file.read()
                                f.write(sData)

                            # Read the CSV file with a reader
                            with open(tmp_path, "r", encoding="utf-8") as f:
                                reader = csv.reader(f, delimiter=",", dialect='excel')
                                # Read the header cells and make a header row in the worksheet
                                headers = next(reader)
                                row_num = 1
                                column = 1
                                lCsv = []
                                for row in reader:
                                    # Keep track of the EXCEL row we are in
                                    row_num += 1
                                    # Get the ID
                                    cell_value = row[0]
                                    if cell_value != None and cell_value != "":
                                        # Get the catalogue id
                                        catalogue_id = int(cell_value)

                                        # Set the status
                                        oStatus.set("reading", msg="catalogue id={}".format(catalogue_id))

                                        # Clear the galway and codico objects
                                        oGalway = None
                                        oCodico = None

                                        # Read the manuscript object from the Galway site
                                        oGalway = self.get_galway(catalogue_id)
                                        # Extract Manuscript information and Codico information from [oGalway]
                                        oManu, oCodico = self.get_manucodico(oGalway)

                                        if oManu != None and oCodico != None:
                                            libname = "{}, {}, {}".format(oManu['country_name'], oManu['city_name'], oManu['library_name'])

                                            # Add manuscript (if not yet there)
                                            manu = Manuscript.custom_add(oManu, **kwargs)

                                            if manu.library == None:
                                                # Log that the library is not recognized
                                                oErr.Status("Library not recognized: {}".format(libname))
                                                # Also add this in the notes
                                                notes = "" if manu.notes == None else manu.notes
                                                manu.notes = "Library not found: {}  \n{}".format(libname, notes)

                                            # Make sure to add the source and the RAW data
                                            manu.source = source
                                            manu.raw = json.dumps(oGalway, indent=2)
                                            manu.save()

                                            # Now get the codicological unit that has been automatically created and adapt it
                                            codico = manu.manuscriptcodicounits.first()
                                            if codico != None:
                                                oCodico['manuscript'] = manu
                                                codico = Codico.custom_add(oCodico, **kwargs)

                                            # Process results
                                            add_manu(lst_manual, lst_read, status=oResult['status'], user=oResult['user'],
                                                            name=codico.name, daterange=oCodico['date ranges'],
                                                            library=libname, filename=manu.idno, sermons=0,
                                                            idno=manu.idno)

                                            oResult['count'] += 1
                                            #oResult['obj'] = manu
                                            #oResult['name'] = manu.idno

                                            oResultManu = dict(name=manu.idno, filename=oManu['url'], sermons=0)
                                            lResults.append(oResultManu)


                        # Create a report and add it to what we return
                        oContents = {'headers': lHeader, 'list': lst_manual, 'read': lst_read}
                        oReport = Report.make(username, "xlsx", json.dumps(oContents))
                                
                        # Determine a status code
                        statuscode = "error" if oResult == None or oResult['status'] == "error" else "completed"
                        if oResult == None:
                            self.arErr.append("There was an error. No manuscripts have been added")
                        else:
                            lResults.append(oResult)
            
            # Make sure we have a success message available
            code = "Imported using the [import_galway] function on this file: {}".format(", ".join(file_list))

            # Indicate we are ready
            oStatus.set("ready")
        except:
            bOkay = False
            code = oErr.get_error_message()
        return bOkay, code

    def get_galway(self, catalogue_id):
        # Read the manuscript with the indicated id

        oBack = None
        bResult = False
        oErr = ErrHandle()
        try:
            url = "https://elmss.nuigalway.ie/api/v1/catalogue/{}".format(catalogue_id)
            try:
                r = requests.get(url)
            except:
                sMsg = oErr.get_error_message()
                oErr.DoError("Request problem")
                return False, sMsg
            if r.status_code == 200:
                # Read the response
                sText = r.text
                oBack = json.loads(sText)
                bResult = True
            else:
                bResult = False
                sResult = "download_file received status {} for {}".format(r.status_code, url)
                oErr.Status("get_galway reading error: {}".format(sResult))
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_galway")
            oBack = None

        return oBack

    def get_manucodico(self, oGalway):
        # Convert a Galway object into a processable Manu and Codico object

        oManu = None
        oCodico = None
        oErr = ErrHandle()
        try:
            # Initialisations
            oManu = {}
            oCodico = {}
            oGalwayItem = oGalway['item']
            city = None
            country = None
            library = None

            loctype_country = LocationType.objects.filter(name="country").first()
            loctype_city= LocationType.objects.filter(name="city").first()

            # Start with admin notes
            oManu['notes'] = oGalwayItem['admin_notes']

            # Check for shelf marks
            shelf_history = ""
            shelfmark = None
            oLibrary = None
            for oShelfmark in oGalwayItem['shelfmarks']:
                shelfmark = oShelfmark['shelfmark']
                oLibrary = oShelfmark['library']
                if oLibrary != "" and oLibrary != None:
                    country = oLibrary['country']
                    city = oLibrary['city']
                    library = oLibrary['library']
                    shelfmark = "{}, {}, {}, {}".format(country, city, library, shelfmark)
                shelf_history = "{}  \nshelfmark: {}".format(shelf_history, shelfmark)
            shelfcount = len(oGalwayItem['shelfmarks'])
            if shelfcount > 1:
                # Add the history to notes
                oManu['notes'] = "{}  \n{}".format(oManu['notes'], shelf_history)

            # Load the values of the *LAST* shelfmark
            if shelfmark != None and oLibrary != None:
                # Set the final shelf mark
                oManu['shelf mark'] = shelfmark

                # derive country/city/library
                oManu['country_name'] = oLibrary['country']
                oManu['city_name'] = oLibrary['city']
                oManu['library_name'] = oLibrary['library']

                # Try get the country id
                country = Location.objects.filter(loctype=loctype_country, name__iexact=oManu['country_name']).first()
                if country != None: 
                    oManu['country id'] = country.id

                    # Try to get the city, restricted to the country
                    city = Location.objects.filter(loctype=loctype_city,
                                                   name__iexact=oManu['city_name'],
                                                   lcountry=country).first()
                    if city != None:
                        oManu['city id'] = city.id

                        # Try to get the library, restricted to city
                        library = Library.objects.filter(name__iexact = oManu['library_name'],
                                                          lcountry=country, lcity=city).first()
                        if library != None:
                            oManu['library id'] = library.id

            oManu['notes'] = "{}  \nScript commentary: {}".format(oManu['notes'],
               oGalwayItem['script_commentary'])
            oManu['url'] = oGalwayItem['public_url']
            oManu['external id'] = oGalwayItem['id']
            lExternal = []
            dataurl = oManu.get('url')
            facsimile = oGalwayItem.get('facsimile_url')
            if dataurl != None and dataurl != "": lExternal.append(dataurl)
            if facsimile != None and facsimile != "": lExternal.append(facsimile)
            oManu['external links'] = lExternal

            # Load the codico values
            oCodico['title'] = oGalwayItem['contents']
            oCodico['date ranges'] = "{}-{}".format(oGalwayItem['numerical_date_start'], oGalwayItem['numerical_date_end'])
            oCodico['support'] = oGalwayItem['support']
            oCodico['provenances'] = oGalwayItem['provenance']

            # Note: extent and format are not provided:
            #oCodico['extent'] = oGalwayItem['']
            #oCodico['format'] = oGalwayItem['']

            # Debugging
            provenances_txt = oCodico['provenances']
            # oErr.Status("document [{}] provenances: {}".format(oManu['shelf mark'], oCodico['provenances']))
        except:
            msg = oErr.get_error_message()
            oErr.DoError("get_manucodico")
            oManu = None

        return oManu, oCodico

