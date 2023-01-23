"""
Adaptations of the database that are called up from the (list)views in the SEEKER app.
"""

from django.db import transaction
import re
import json

# ======= imports from my own application ======
from lila.utils import ErrHandle
from lila.seeker.models import Colwit, get_crpp_date, get_current_datetime, process_lib_entries, get_searchable, get_now_time, \
    add_gold2equal, add_equal2equal, add_ssg_equal2equal, get_helptext, Information, Country, City, Author, Manuscript, \
    User, Group, Origin, Canwit, MsItem, Codhead, CanwitKeyword, CanwitAustat, NewsItem, \
    SourceInfo, AustatKeyword, ManuscriptExt, AuworkGenre, \
    ManuscriptKeyword, Action, Austat, AustatLink, Location, LocationName, LocationIdentifier, LocationRelation, LocationType, \
    ProvenanceMan, Provenance, Daterange, CollOverlap, BibRange, Feast, Comment, AustatDist, \
    Basket, BasketMan, BasketAustat, Litref, LitrefMan, LitrefCol, Report,  \
    Visit, Profile, Keyword, CanwitSignature, Status, Library, Collection, CollectionCanwit, \
    CollectionMan, Caned, UserKeyword, Template, \
    ManuscriptCorpus, ManuscriptCorpusLock, AustatCorpus, \
    Codico, OriginCodico, CodicoKeyword, ProvenanceCod, Project, ManuscriptProject, CanwitProject, \
    CollectionProject, AustatProject, \
    get_reverse_spec, LINK_EQUAL, LINK_PRT, LINK_BIDIR, LINK_PARTIAL, STYPE_IMPORTED, STYPE_EDITED, LINK_UNSPECIFIED


adaptation_list = {
    "manuscript_list": [],
    'codico_list': [],
    'canwit_list': ['lilacodefull'],
    'austat_list': ['keycodefull', 'dategenre'],
    'caned_list': ['canedftext'],
    'colwit_list': ['signatures', 'lilacode'],
    "collection_list": [] ,
    "origin_list": ['mcount']
    }


def listview_adaptations(lv):
    """Perform adaptations specific for this listview"""

    oErr = ErrHandle()
    try:
        if lv in adaptation_list:
            for adapt in adaptation_list.get(lv):
                sh_done  = Information.get_kvalue(adapt)
                if sh_done == None or sh_done != "done":
                    # Do the adaptation, depending on what it is
                    method_to_call = "adapt_{}".format(adapt)
                    bResult, msg = globals()[method_to_call]()
                    if bResult:
                        # Success
                        Information.set_kvalue(adapt, "done")
    except:
        msg = oErr.get_error_message()
        oErr.DoError("listview_adaptations")

# =========== GENERAL PURPOSE ==========================

def adapt_codicocopy(oStatus=None):
    """Create Codico's and copy Manuscript information to Codico"""
    oErr = ErrHandle()
    bResult = True
    msg = ""
    count_add = 0       # Codico layers added
    count_copy = 0      # Codico layers copied
    count_tem = 0       # Template codico changed
    oBack = dict(status="ok", msg="")

    try:
        # TODO: add code here and change to True
        bResult = False

        # Walk through all manuscripts (that are not templates)
        manu_lst = []
        for manu in Manuscript.objects.filter(mtype__iregex="man|tem"):
            # Check if this manuscript already has Codico's
            if manu.manuscriptcodicounits.count() == 0:
                # Note that Codico's must be made for this manuscript
                manu_lst.append(manu.id)
        # Status message
        oBack['total'] = "Manuscripts without codico: {}".format(len(manu_lst))
        if oStatus != None: oStatus.set("ok", oBack)
        # Create the codico's for the manuscripts
        with transaction.atomic():
            for idx, manu_id in enumerate(manu_lst):
                # Debugging message
                msg = "Checking manuscript {} of {}".format(idx+1, len(manu_lst))
                oErr.Status(msg)

                # Status message
                oBack['total'] = msg
                if oStatus != None: oStatus.set("ok", oBack)

                manu = Manuscript.objects.filter(id=manu_id).first()
                if manu != None:
                    bResult, msg = add_codico_to_manuscript(manu)
                    count_add += 1
        oBack['codico_added'] = count_add

        # Checking up on manuscripts that are imported (stype='imp') but whose Codico has not been 'fixed' yet
        manu_lst = Manuscript.objects.filter(stype="imp").exclude(itype="codico_copied")
        # Status message
        oBack['total'] = "Imported manuscripts whose codico needs checking: {}".format(len(manu_lst))
        if oStatus != None: oStatus.set("ok", oBack)
        with transaction.atomic():
            for idx, manu in enumerate(manu_lst):
                # Show what we are doing
                oErr.Status("Checking manuscript {} of {}".format(idx+1, len(manu_lst)))
                # Actually do it
                bResult, msg = add_codico_to_manuscript(manu)
                if bResult:
                    manu.itype = "codico_copied"
                    manu.save()
                    count_copy += 1
        oBack['codico_copied'] = count_copy

        # Adapt codico's for templates
        codico_name = "(No codicological definition for a template)" 
        with transaction.atomic():
            for codico in Codico.objects.filter(manuscript__mtype="tem"):
                # Make sure the essential parts are empty!!
                bNeedSaving = False
                if codico.name != codico_name : 
                    codico.name = codico_name
                    bNeedSaving = True
                if codico.notes != None: codico.notes = None ; bNeedSaving = True
                if codico.support != None: codico.support = None ; bNeedSaving = True
                if codico.extent != None: codico.extent = None ; bNeedSaving = True
                if codico.format != None: codico.format = None ; bNeedSaving = True
                if bNeedSaving:
                    codico.save()
                    count_tem += 1
        oBack['codico_template'] = count_tem

        if oStatus != None: oStatus.set("finished", oBack)

        # Note that we are indeed ready
        bResult = True
    except:
        msg = oErr.get_error_message()
        bResult = False
    return bResult, msg

def add_codico_to_manuscript(manu):
    """Check if a manuscript has a Codico, and if not create it"""

    def get_number(items, bFirst):
        """Extract the first or last consecutive number from the string"""

        number = -1
        if len(items) > 0:
            if bFirst:
                # Find the first number
                for sInput in items:
                    arNumber = re.findall(r'\d+', sInput)
                    if len(arNumber) > 0:
                        number = int(arNumber[0])
                        break
            else:
                # Find the last number
                for sInput in reversed(items):
                    arNumber = re.findall(r'\d+', sInput)
                    if len(arNumber) > 0:
                        number = int(arNumber[-1])
                        break

        return number
    
    oErr = ErrHandle()
    bResult = False
    msg = ""
    try:
        # Check if the codico exists
        codi = Codico.objects.filter(manuscript=manu).first()
        if codi == None:
            # Get first and last sermons and then their pages
            items = [x['itemsermons__locus'] for x in manu.manuitems.filter(itemsermons__locus__isnull=False).order_by(
                'order').values('itemsermons__locus')]
            if len(items) > 0:
                pagefirst = get_number(items, True)
                pagelast = get_number(items, False)
            else:
                pagefirst = 1
                pagelast = 1
            # Create the codico
            codi = Codico.objects.create(
                name=manu.name, support=manu.support, extent=manu.extent,
                format=manu.format, order=1, pagefirst=pagefirst, pagelast=pagelast,
                origin=manu.origin, manuscript=manu
                )
        else:
            # Possibly copy stuff from manu to codi
            bNeedSaving = False
            if codi.name == "SUPPLY A NAME" and manu.name != "":
                codi.name = manu.name ; bNeedSaving = True
            if codi.support == None and manu.support != None:
                codi.support = manu.support ; bNeedSaving = True
            if codi.extent == None and manu.extent != None:
                codi.extent = manu.extent ; bNeedSaving = True
            if codi.format == None and manu.format != None:
                codi.format = manu.format ; bNeedSaving = True
            if codi.order == 0:
                codi.order = 1 ; bNeedSaving = True
            if codi.origin == None and manu.origin != None:
                codi.origin = manu.origin ; bNeedSaving = True
            # Possibly save changes
            if bNeedSaving:
                codi.save()
        # Copy provenances
        if codi.codico_provenances.count() == 0:
            for mp in manu.manuscripts_provenances.all():
                obj = ProvenanceCod.objects.filter(
                    provenance=mp.provenance, codico=codi, note=mp.note).first()
                if obj == None:
                    obj = ProvenanceCod.objects.create(
                        provenance=mp.provenance, codico=codi, note=mp.note)

        # Copy keywords
        if codi.codico_kw.count() == 0:
            for mk in manu.manuscript_kw.all():
                obj = CodicoKeyword.objects.filter(
                    codico=codi, keyword=mk.keyword).first()
                if obj == None:
                    obj = CodicoKeyword.objects.create(
                        codico=codi, keyword=mk.keyword)

        # Tie all MsItems that need be to the Codico
        for msitem in manu.manuitems.all().order_by('order'):
            if msitem.codico_id == None or msitem.codico == None or msitem.codico.id != codi.id:
                msitem.codico = codi
                msitem.save()
        bResult = True
    except:
        msg = oErr.get_error_message()
        oErr.DoError("add_codico_to_manuscript")
        bResult = False
    return bResult, msg


# =========== Part of manuscript_list ==================


# =========== Part of codico_list ======================


# =========== Part of canwit_list ======================

def adapt_lilacodefull(oStatus=None):
    """Re-save Canwit objects, so that lilacodefull is calculated"""

    oErr = ErrHandle()
    bResult = True
    msg = ""
    oBack = dict(status="ok", msg="")

    try:
        # TODO: add code here and change to True
        bResult = False

        # Walk all the existing Caned items
        with transaction.atomic():
            for obj in Canwit.objects.all():
                obj.save()
        # Note that we are indeed ready
        bResult = True
    except:
        msg = oErr.get_error_message()
        bResult = False
    return bResult, msg


# =========== Part of austat_list ======================

def adapt_keycodefull(oStatus=None):
    """Create Codico's and copy Manuscript information to Codico"""
    oErr = ErrHandle()
    bResult = True
    msg = ""
    oBack = dict(status="ok", msg="")

    try:
        # TODO: add code here and change to True
        bResult = False

        # Walk all the existing Caned items
        with transaction.atomic():
            for obj in Austat.objects.all():
                # Adapt keycodefull if needed
                keycodefull = obj.get_keycode()
                if obj.keycodefull != keycodefull:
                    obj.keycodefull = keycodefull
                    obj.save()

        # Note that we are indeed ready
        bResult = True
    except:
        msg = oErr.get_error_message()
        bResult = False
    return bResult, msg

def adapt_dategenre(oStatus=None):
    """Copy the 'date' field and the 'genres' from Austat to Auwork"""

    oErr = ErrHandle()
    bResult = True
    msg = ""
    oBack = dict(status="ok", msg="")

    try:
        # Start out with 'false', until everything has been done successfully
        bResult = False

        # Walk all the existing Austat items
        for austat in Austat.objects.all():
            # Get the Auwork of this one
            auwork = austat.auwork
            # Only proceed if there is a valid auwork
            if auwork is None:
                continue

            # (1) Evaluate the 'date' field
            date_austat = austat.date
            date_auwork = auwork.date
            if not date_austat is None and date_auwork is None:
                # Copy from austat to auwork
                auwork.date = austat.date
                auwork.save()

            # (2) Evaluate the genres
            genres_austat_id = [x['id'] for x in austat.genres.all().values("id")]
            genres_auwork_id = [x['id'] for x in auwork.genres.all().values("id")]
            for genreid in genres_austat_id:
                if not genreid in genres_auwork_id:
                    # Add it to the Auwork genres
                    AuworkGenre.objects.create(auwork=auwork, genre_id=genreid)


        # Note that we are indeed ready
        bResult = True
    except:
        msg = oErr.get_error_message()
        bResult = False
    return bResult, msg


# =========== Part of caned_list ======================

def adapt_canedftext(oStatus=None):
    """Create Codico's and copy Manuscript information to Codico"""
    oErr = ErrHandle()
    bResult = True
    msg = ""
    oBack = dict(status="ok", msg="")

    try:
        # TODO: add code here and change to True
        bResult = False

        # Walk all the existing Caned items
        with transaction.atomic():
            for obj in Caned.objects.all():
                # Get the austat
                austat = obj.austat
                # Copy the ftext/ftrans from there
                if obj.ftext is None and not austat.ftext is None:
                    obj.ftext = austat.ftext
                    obj.ftrans = austat.ftrans
                    obj.srchftext = austat.srchftext
                    obj.srchftrans = austat.srchftrans
                    obj.save()

        # Note that we are indeed ready
        bResult = True
    except:
        msg = oErr.get_error_message()
        bResult = False
    return bResult, msg


# =========== Part of collection_list ==================


# =========== Part of colwit_list ======================

def adapt_signatures(oStatus=None):
    """Adapt all signatures for colwit items"""

    oErr = ErrHandle()
    bResult = True
    msg = ""
    oBack = dict(status="ok", msg="")

    try:
        # TODO: add code here and change to True
        bResult = False
        with transaction.atomic():
            for obj in Colwit.objects.all():
                obj.do_siglist()
        # Note that we are indeed ready
        bResult = True
    except:
        msg = oErr.get_error_message()
        bResult = False
    return bResult, msg

def adapt_lilacode(oStatus=None):
    """Adapt all signatures for colwit items"""

    oErr = ErrHandle()
    bResult = True
    msg = ""
    oBack = dict(status="ok", msg="")

    try:
        # TODO: add code here and change to True
        bResult = False
        with transaction.atomic():
            for obj in Colwit.objects.all():
                obj.save()
        # Note that we are indeed ready
        bResult = True
    except:
        msg = oErr.get_error_message()
        bResult = False
    return bResult, msg

# =========== Part of origin_list ======================

def adapt_mcount(oStatus=None):
    """Adapt all signatures for colwit items"""

    oErr = ErrHandle()
    bResult = True
    msg = ""
    oBack = dict(status="ok", msg="")

    try:
        # TODO: add code here and change to True
        bResult = False
        with transaction.atomic():
            for obj in Origin.objects.all():
                obj.do_mcount()
                obj.save()
        # Note that we are indeed ready
        bResult = True
    except:
        msg = oErr.get_error_message()
        bResult = False
    return bResult, msg


