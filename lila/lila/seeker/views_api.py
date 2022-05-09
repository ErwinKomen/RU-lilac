"""
Definition of API views for the SEEKER app.
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

# ======= imports from my own application ======
from lila.utils import ErrHandle
from lila.seeker.models import get_crpp_date, get_current_datetime, process_lib_entries, get_searchable, get_now_time, \
    add_gold2equal, add_equal2equal, add_ssg_equal2equal, get_helptext, Information, Country, City, Author, Manuscript, \
    User, Group, Origin, Canwit, MsItem, Codhead, CanwitKeyword, CanwitAustat, NewsItem, \
    SourceInfo, AustatKeyword, ManuscriptExt, \
    ManuscriptKeyword, Action, Austat, AustatLink, Location, LocationName, LocationIdentifier, LocationRelation, LocationType, \
    ProvenanceMan, Provenance, Daterange, CollOverlap, BibRange, Feast, Comment, AustatDist, \
    Basket, BasketMan, BasketAustat, Litref, LitrefMan, LitrefCol, Report, \
    Visit, Profile, Keyword, CanwitSignature, Status, Library, Collection, CollectionCanwit, \
    CollectionMan, CollectionAustat, UserKeyword, Template, \
    ManuscriptCorpus, ManuscriptCorpusLock, AustatCorpus, ProjectEditor, \
    Codico, ProvenanceCod, OriginCodico, CodicoKeyword, Reconstruction, \
    Project, ManuscriptProject, CollectionProject, AustatProject, CanwitProject, \
    get_reverse_spec, LINK_EQUAL, LINK_PRT, LINK_BIDIR, LINK_PARTIAL, STYPE_IMPORTED, STYPE_EDITED, STYPE_MANUAL, LINK_UNSPECIFIED


# ============= API VIEWS ============================

@csrf_exempt
def import_authors(request):
    """Import a CSV file or a JSON file that contains author names"""


    # Initialisations
    # NOTE: do ***not*** add a breakpoint until *AFTER* form.is_valid
    arErr = []
    error_list = []
    transactions = []
    data = {'status': 'ok', 'html': ''}
    template_name = 'seeker/import_authors.html'
    obj = None
    data_file = ""
    bClean = False
    username = request.user.username

    # Check if the user is authenticated and if it is POST
    if not request.user.is_authenticated  or request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            # NOTE: from here a breakpoint may be inserted!
            print('valid form')
            # Get the contents of the imported file
            data_file = request.FILES['file_source']
            filename = data_file.name

            # Get the source file
            if data_file == None or data_file == "":
                arErr.append("No source file specified for the selected project")
            else:
                # Check the extension
                arFile = filename.split(".")
                extension = arFile[len(arFile)-1]

                # Further processing depends on the extension
                if extension == "json":
                    # This is a JSON file
                    oResult = Author.read_json(username, data_file, arErr)
                else:
                    # Read the list of authors as CSV
                    oResult = Author.read_csv(username, data_file, arErr)

                # Determine a status code
                statuscode = "error" if oResult == None or oResult['status'] == "error" else "completed"
                if oResult == None:
                    arErr.append("There was an error. No authors have been added")

            # Get a list of errors
            error_list = [str(item) for item in arErr]

            # Create the context
            context = dict(
                statuscode=statuscode,
                results=oResult,
                error_list=error_list
                )

            if len(arErr) == 0:
                # Get the HTML response
                data['html'] = render_to_string(template_name, context, request)
            else:
                data['html'] = "Please log in before continuing"


        else:
            data['html'] = 'invalid form: {}'.format(form.errors)
            data['status'] = "error"
    else:
        data['html'] = 'Only use POST and make sure you are logged in'
        data['status'] = "error"
 
    # Return the information
    return JsonResponse(data)

def do_create_pdf_lit(request):
    """"This definition creates the input for the pdf with all used literature (full) references."""
         
    # Store title, and pageinfo (for at the bottom of the page) 
    Title = "Literature references used in lila:"
    pageinfo = "Literature lila"
       
    # Store name of the file    
    filename = "Lit_ref_lila.pdf"
    
    # Calculate the final qs for the manuscript litrefs
    litref_ids = [x['reference'] for x in LitrefMan.objects.all().values('reference')]
    
    # Hier worden short en full opgehaald?
    qs = Litref.objects.filter(id__in=litref_ids).order_by('short') 
    
    # Create a list of objects 
    pdf_list = []
    for obj in qs:
        item = {}
        item = obj.full
        pdf_list.append(item)
        
    # Call create_pdf_lila function with arguments  
    response  = create_pdf_lila(Title, pageinfo, filename, pdf_list)
       
    # And return the pdf
    return response

def do_create_pdf_edi(request):
    response = None

    # TODO: overnemen van PASSIMs

    # And return the pdf
    return response

def create_pdf_lila(Title, pageinfo, filename, pdf_list):
    """This definition creates a pdf for all lila requests."""
     
    # Define sizes of the pages in the pdf
    PAGE_HEIGHT=defaultPageSize[1]; PAGE_WIDTH=defaultPageSize[0]
    
    # Store text and current date for information on date of the download
    today = datetime.today()
    today.strftime('%Y-%m-%d')
       
    # Set buffer   
    buffer = io.BytesIO()

    # Set the first page
    def myFirstPage(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica-Bold',22)
        canvas.drawCentredString(PAGE_WIDTH/2.0, PAGE_HEIGHT-80, Title)
        canvas.setFont('Helvetica',10)
        canvas.drawString(75,730, "Downloaded on: ")
        canvas.drawString(150,730, today.strftime('%d-%m-%Y'))
        canvas.setFont('Helvetica',9)
        canvas.drawString(inch, 0.75 * inch, "Page 1 / %s" % pageinfo)
        canvas.restoreState()
    
    # Set the second and later pages
    def myLaterPages(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica',9)
        canvas.drawString(inch, 0.75 * inch, "Page %d %s" % (doc.page, pageinfo))
        canvas.restoreState()

    # Create the HttpResponse object with the appropriate PDF headers. 
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
               
    # Define style of the pdf
    styles = getSampleStyleSheet()
        
    doc = SimpleDocTemplate(buffer)
    Story = [Spacer(1,1.05*inch)]
    style = styles["Normal"]
    # Dit tzt afhankelijk maken van lit en edi, niet van manuscript TH: hier nog met Erwin over hebben

    for line in pdf_list:
        line_2 = markdown(line)
        line_3 = line_2.replace("<em>", "<i>")
        line_4 = line_3.replace("</em>", "</i>")
        line_5 = markdown(line_4)
          
        lit_ref = (line_5) *1 
        p = Paragraph(lit_ref, style, '-')
        Story.append(p)
        Story.append(Spacer(1,0.2*inch))
    doc.build(Story, onFirstPage=myFirstPage, onLaterPages=myLaterPages)
    
    # Write the buffer to the PDF
    response.write(buffer.getvalue())
    # Close the buffer cleanly, and we're done.
    buffer.close()
       
    # And return the pdf
    return response

def do_create_pdf_manu(request):
    """This definition creates the input for the pdf with all manuscripts in the lila database."""
  
    # Store title, and pageinfo (for at the bottom of each page) 
    Title = "Manuscripts listed in lila:"
    pageinfo = "Manuscripts lila"
             
    # Store name of the pdf file 
    filename = "Manu_list_lila.pdf"

    # Which method needs to be used
    method = "msitem"   # "canwit"

    # Calculate the qs for the manuscripts       
    qs = Manuscript.objects.all()
    
    # Create temporary list and add relevant fields to the list
    pdf_list_temp = []
    for obj in qs:
        # Count all (Canwit) items for each manuscript
        count = obj.get_canwit_count()
        
        # Handle empty origin fields
        origin = None if obj.origin == None else obj.origin.name
        
        # Retrieve all provenances for each manuscript
        qs_prov = obj.manuscripts_provenances.all()
        
        # Iterate through the queryset, place name and location 
        # for each provenance together 
        prov_texts = []
        for prov in qs_prov:
            prov = prov.provenance
            # Issue #289: innovation turned back to the above
            prov_text = prov.name
            if prov.location:
                prov_text = "{} ({})".format(prov_text, prov.location.name)
            prov_texts.append(prov_text)
        # Join all provenances together
        provenance = ", ".join(prov_texts)
        
        # Store all relevant items in a dictionary and append to the list TH: let op, link lib and city
        name = "" if obj.name == None else obj.name         
        idno = "" if obj.idno == None else obj.idno
        yearstart = "" if obj.yearstart == None else obj.yearstart
        yearfinish = "" if obj.yearfinish == None else obj.yearfinish
        libname = "" if obj.library == None else obj.library.name
        city = "" if obj.library == None or obj.library.city == None else obj.library.city.name
        
        item = dict(name=name, idno=idno, yearstart=yearstart, yearfinish=yearfinish,
                stype=obj.get_stype_display(), libname=libname, city=city, origin=origin, provenance=provenance,
                count=count)
        pdf_list_temp.append(item)
             
    # Sort the list on city and yearstart
    pdf_list_sorted = sorted(pdf_list_temp, key=itemgetter('city', 'yearstart')) 
        
    # Create five strings and add to pdf_list (to be processed in create_pdf_lila)
    pdf_list=[]
    for dict_item in pdf_list_sorted:
       
       # The first string contains the name of the city, library and id code of the manuscript     
       string_1 = dict_item['city'] + ", "+ dict_item['libname'] + ", "+ dict_item['idno']
       
       # The second string contains the start and end year of the manuscript and the number of items of the manuscript
       string_2 = 'Date: ' + str(dict_item['yearstart']) + "-" + str(dict_item['yearfinish']) + ', items: ' + str(dict_item['count'])
       
       # The third string contains the status of the manuscript: manual, imported or edited
       string_3 = 'Status: ' + dict_item['stype']
       
       # The fourth string contains the origin of the manuscript
       if dict_item['origin'] == None:
          origin = ""
       else:
          origin = dict_item['origin']
              
       string_4 = 'Origin: ' + origin
        
       # The fifth string contains the provenances of the manuscript
       if dict_item['provenance'] == None:
          provenance = ""
       else:
          provenance = dict_item['provenance']

       string_5 = 'Provenances: '+ provenance
       
       # The strings are combined into one with markddown line breaks so that each string is placed on a new line in the pdf
       combined = string_1 + "<br />" + string_2 + "<br />" + string_3 + "<br />" + string_4 + "<br />" + string_5
       
       # The new combined strings are placed in a new list, to be used in the create_pdf_lila function.        
       pdf_list.append(combined)

    # Call create_pdf_lila function with arguments  
    response = create_pdf_lila(Title, pageinfo, filename, pdf_list)
  
    # And return the pdf
    return response

def sync_lila(request):
    """-"""
    assert isinstance(request, HttpRequest)

    # Gather info
    context = {'title': 'Synclila',
               'message': 'Radboud University lila'
               }
    template_name = 'seeker/synclila.html'
    context['is_app_uploader'] = user_is_ingroup(request, app_uploader)
    context['is_app_editor'] = user_is_ingroup(request, app_editor)
    context['is_enrich_editor'] = user_is_ingroup(request, enrich_editor)
    context['is_app_moderator'] = user_is_superuser(request) or user_is_ingroup(request, app_moderator)
    context['is_superuser'] = user_is_superuser(request)

    # Add the information in the 'context' of the web page
    return render(request, template_name, context)

def sync_start(request):
    """Synchronize information"""

    oErr = ErrHandle()
    data = {'status': 'starting'}
    try:
        # Get the user
        username = request.user.username
        # Authentication
        if not user_is_ingroup(request, app_editor):
            return redirect('home')

        # Get the synchronization type
        get = request.GET
        synctype = ""
        force = False
        if 'synctype' in get:
            synctype = get['synctype']
        if 'force' in get:
            force = get['force']
            force = (force == "true" or force == "1" )

        if synctype == '':
            # Formulate a response
            data['status'] = 'no sync type specified'

        else:
            # Remove previous status objects for this combination of user/type
            qs = Status.objects.filter(user=username, type=synctype)
            qs.delete()

            # Create a status object for this combination of synctype/user
            oStatus = Status(user=username, type=synctype, status="preparing")
            oStatus.save()

            # Formulate a response
            data['status'] = 'done'

            if synctype == "entries":
                # Use the synchronisation object that contains all relevant information
                oStatus.set("loading")

                # Update the models with the new information
                oResult = process_lib_entries(oStatus)
                if oResult == None or oResult['result'] == False:
                    data.status = 'error'
                elif oResult != None:
                    data['count'] = oResult

            elif synctype == "zotero":
                # Use the synchronisation object that contains all relevant information
                oStatus.set("loading")

                # Update the models with the new information
                oResult, msg = Litref.sync_zotero(force=force, oStatus=oStatus)

                if oResult != None and 'status' in oResult:
                    data['count'] = oResult
                else:
                    data['status'] = 'error {}'.format(msg)

            elif synctype == "codico":
                # Use the synchronisation object that contains all relevant information
                oStatus.set("loading")

                # Perform the adaptation
                bResult, msg = adapt_codicocopy(oStatus=oStatus)
                
                if bResult:
                    data['count'] = 1
                else:
                    data['status'] = "error {}".format(msg) 

    except:
        oErr.DoError("sync_start error")
        data['status'] = "error"

    # Return this response
    return JsonResponse(data)

def sync_progress(request):
    """Get the progress on the /crpp synchronisation process"""

    oErr = ErrHandle()
    data = {'status': 'preparing'}

    try:
        # Get the user
        username = request.user.username
        # Get the synchronization type
        get = request.GET
        synctype = ""
        if 'synctype' in get:
            synctype = get['synctype']

        if synctype == '':
            # Formulate a response
            data['status'] = 'error'
            data['msg'] = "no sync type specified" 

        else:
            # Formulate a response
            data['status'] = 'UNKNOWN'

            # Get the appropriate status object
            # sleep(1)
            oStatus = Status.objects.filter(user=username, type=synctype).first()

            # Check what we received
            if oStatus == None:
                # There is no status object for this type
                data['status'] = 'error'
                data['msg'] = "Cannot find status for {}/{}".format(
                    username, synctype)
            else:
                # Get the last status information
                data['status'] = oStatus.status
                data['msg'] = oStatus.msg
                data['count'] = oStatus.count

        # Return this response
        return JsonResponse(data)
    except:
        oErr.DoError("sync_start error")
        data = {'status': 'error'}

    # Return this response
    return JsonResponse(data)

def redo_zotero(request):
    oErr = ErrHandle()
    data = {'status': 'preparing'}

    try:
        if request.method == 'GET':
            oBack, msg = Litref.sync_zotero(True)
        if oBack != None and 'status' in oBack:
            data['status'] = "ok"
            data['count'] = oBack
        else:
            data['status'] = "error"
            data['msg'] = msg
            data['html'] = msg
    except:
        oErr.DoError("redo_zotero error")
        data = {'status': 'error'}

    # Return this response
    return JsonResponse(data)


