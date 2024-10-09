"""Models for the LICT app.

LICT = Lilac Comparative Table
"""
from django.apps.config import AppConfig
from django.apps import apps
from django.db import models, transaction
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.query import QuerySet 
from django.urls import reverse


from markdown import markdown
import json, copy

# Take from my own app
from solemne.utils import ErrHandle, is_ajax
from solemne.settings import TIME_ZONE
from solemne.seeker.models import get_current_datetime, get_crpp_date, build_abbr_list, COLLECTION_SCOPE, \
    Collection, Manuscript, Profile, Caned, CanwitKeyword

STANDARD_LENGTH=255
ABBR_LENGTH = 5

SETLIST_TYPE = "lict.setlisttype"

def get_lilacode(austatu_id, austatu_code):
    code = austatu_code if austatu_code and austatu_code != "" else "(nocode_{})".format(austatu_id)
    return code

def get_list_matches(oPMlist, oAustatList):
    """Calculate the number of matches between the two lists"""

    matches = 0
    for oPm in oPMlist['auslist']:
        austat = oPm['austat']
        # Check how manu times this Austat appears in [oAustatList]
        for oAustat in oAustatList['auslist']:
            if austat == oAustat['austat']:
                matches += 1
    return matches


class ResearchSet(models.Model):
    """One research set
    
    A research set is a user-curated collection of source-lists.
    It can be used as the basis for creating a DCT, a dynamic comparison table
    """

    # [1] obligatory name
    name = models.CharField("Name", max_length=STANDARD_LENGTH)
    # [1] a research set belongs to a particular user's profilee
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="profile_researchsets")

    # [0-1] Optional notes for this set
    notes = models.TextField("Notes", blank=True, null=True)

    # [1] A list of all the DCT parameters for this DCT
    contents = models.TextField("Contents", default="[]")

    # [1] The scope of this collection: who can view it?
    #     E.g: private, team, global - default is 'private'
    scope = models.CharField("Scope", choices=build_abbr_list(COLLECTION_SCOPE), default="priv", max_length=5)

    # [1] And a date: the date of saving this manuscript
    created = models.DateTimeField(default=get_current_datetime)
    saved = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """Just return the name"""
        return self.name

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        # Adapt the save date
        self.saved = get_current_datetime()
        response = super(ResearchSet, self).save(force_insert, force_update, using, update_fields)

        # If there is no DCT definition yet, create a default one
        SetDef.check_default(self, self.profile.user.username)

        # Return the response when saving
        return response

    def adapt_order(self):
        """Re-calculate the order and adapt where needed"""

        qs = self.researchset_setlists.all().order_by("order")
        order = 1
        with transaction.atomic():
            # Walk all the SetList objects
            for obj in qs:
                # Check if the order is as it should be
                if obj.order != order:
                    #No: adapt the order
                    obj.order = order
                    # And save it
                    obj.save()
                # Keep track of how the order should be
                order += 1
        return None

    def calculate_matches(self, auslists):
        """Calculate the number of pm-matches for each list from auslists"""

        oErr = ErrHandle()
        lBack = []
        try:
            # Preparation: create a list of SSG ids per list
            for oItem in auslists:
                oItem['austatid'] = [x['austat'] for x in oItem['auslist']]
                oItem['unique_matches'] = 0

            # Calculate the number of matches for each Austatlist
            for idx_list in range(len(auslists)):
                # Take this as the possible pivot list
                lPivot = auslists[idx_list]['austatid']

                # Walk all lists that are not this pivot and count matches
                lUnique = []
                oMatches = {}
                if 'matchset' in auslists[idx_list]['title']:
                    oMatches = auslists[idx_list]['title']['matchset']
                for idx, setlist in enumerate(auslists):
                    if idx != idx_list:
                        # Get this auslist
                        lAustatId = setlist['austatid']

                        # Start calculating the number of matches this list has with the currently suggested PM
                        sKey = str(auslists[idx]['title']['order'])
                        lMatches = []

                        # Consider all ssg id's in this list
                        for austat_id in lAustatId:
                            # Global unique matches
                            if austat_id in lPivot and not austat_id in lUnique:
                                lUnique.append(austat_id)
                            # Calculation with respect to the currently suggested PM
                            if austat_id in lPivot: # and not austat_id in lMatches:
                                lMatches.append(austat_id)
                        # Keep track of the matches (for sorting)
                        oMatches[sKey] = len(lMatches)
                # Store the between-list matches
                auslists[idx_list]['title']['matchset'] = oMatches

                # Store the number of matches for this list
                unique_matches = len(lUnique)
                auslists[idx_list]['unique_matches'] = unique_matches

            # What we return
            lBack = auslists
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ResearchSet/calculate_matches")
            lBack = None
        # Return the status
        return lBack

    def calculate_pm(self):
        """Calculate the Pivot Manuscript/item for this research set"""

        oErr = ErrHandle()
        iBack = -1
        try:
            # Get the lists that we have made
            ssglists = self.get_austatlists()

            # Calculate the matches
            ssglists = self.calculate_matches(ssglists)

            # Figure out what the first best list is
            idx_pm = -1
            max_matches = -1
            min_order = len(ssglists) + 2
            min_year_start = 3000
            min_year_finish = 3000
            for idx, oListItem in enumerate(ssglists):
                unique_matches = oListItem['unique_matches']
                year_start = oListItem['title']['yearstart']
                year_finish = oListItem['title']['yearfinish']
                order = oListItem['title']['order']

                # Check which is the best so far
                bTakeThis = False
                bTakeThis = (unique_matches > max_matches)
                if not bTakeThis and unique_matches == max_matches:
                    bTakeThis = (year_start < min_year_start)
                    if not bTakeThis and year_start == min_year_start:
                        bTakeThis = (year_finish < min_year_finish)
                        if not bTakeThis and year_finish == min_year_finish:
                            bTakeThis = (order < min_order)

                # Adapt if this is the one
                if bTakeThis:
                    max_matches = unique_matches
                    min_year_start = year_start
                    min_year_finish = year_finish
                    min_order = order
                    idx_pm = idx

            # What we return is the 'order' value of the best matching list
            iBack = ssglists[idx_pm]['title']['order']

        except:
            msg = oErr.get_error_message()
            oErr.DoError("ResearchSet/calculate_pm")
            iBack = -1
        # Return the PM that we have found
        return iBack

    def get_created(self):
        """REturn the creation date in a readable form"""

        # sDate = self.created.strftime("%d/%b/%Y %H:%M")
        sDate = get_crpp_date(self.created, True)
        return sDate

    def get_notes_html(self):
        """Convert the markdown notes"""

        sNotes = "-"
        if self.notes != None:
            sNotes = markdown(self.notes)
        return sNotes

    def get_saved(self):
        """REturn the saved date in a readable form"""

        # sDate = self.saved.strftime("%d/%b/%Y %H:%M")
        sDate = get_crpp_date(self.saved, True)
        return sDate

    def get_size_markdown(self):
        """Get a markdown representation of the size of this set"""

        size = 0
        lHtml = []
        size = self.researchset_setlists.count()
        if size > 0:
            # Create a display for this topic
            lHtml.append("<span class='badge signature gr'>{}</span>".format(size))
        else:
            lHtml.append("0")
        sBack = ", ".join(lHtml)
        return sBack

    def get_austatlists(self, recalculate=False):
        """Get the set of lists for this particular ResearchSet"""

        oErr = ErrHandle()
        lBack = None
        try:
            if self.contents != "" and self.contents[0] == "[":
                lst_contents = json.loads(self.contents)
            else:
                lst_contents = []
            if not recalculate and len(lst_contents) > 0:
                # Should the unique_matches be re-calculated?
                if not 'unique_matches' in lst_contents[0]:
                    # Yes, re-calculate
                    lst_contents = self.calculate_matches(lst_contents)
                    # And make sure this gets saved!
                    self.contents = json.dumps(lst_contents)
                    self.save()
                lBack = lst_contents
            else:
                # Re-calculate the lists
                self.update_austatlists()
                # Get the result
                lBack = json.loads(self.contents)

        except:
            msg = oErr.get_error_message()
            oErr.DoError("ResearchSet/get_austatlists")
        return lBack

    def update_austatlists(self, force = False):
        """Re-calculate the set of lists for this particular ResearchSet"""

        oErr = ErrHandle()
        bResult = True
        lst_ssglists = []
        try:
            oPMlist = None
            # Get the lists of SSGs for each list in the set
            for idx, setlist in enumerate(self.researchset_setlists.all().order_by('order')):
                # Check for the contents
                if force or setlist.contents == "" or len(setlist.contents) < 3 or setlist.contents[0] == "[":
                    setlist.calculate_contents()

                # Retrieve the SSG-list from the contents
                oSsgList = json.loads(setlist.contents)

                # If this is not the *first* setlist, calculate the number of matches with the first
                if idx == 0:
                    oPMlist = copy.copy(oSsgList)
                else:
                    # Calculate the matches
                    oSsgList['title']['matches'] = get_list_matches(oPMlist, oSsgList)
                # Always pass on the default order
                oSsgList['title']['order'] = idx + 1

                # Add the list object to the list
                lst_ssglists.append(oSsgList)

            # Calculate the unique_matches for each list
            lst_ssglists = self.calculate_matches(lst_ssglists)

            # Put it in the ResearchSet and save it
            self.contents = json.dumps(lst_ssglists)
            self.save()

            # All related SetDef items should be warned
            with transaction.atomic():
                for obj in SetDef.objects.filter(researchset=self.id):
                    contents = json.loads(obj.contents)
                    contents['recalc'] = True
                    obj.contents = json.dumps(contents)
                    obj.save()

            # Return this list of lists
            bResult = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ResearchSet/update_austatlists")
            bResult = False
        return bResult


class SetList(models.Model):
    """A setlist belongs to a research set"""

    # [1] A setlist just belongs to a research set
    researchset = models.ForeignKey(ResearchSet, on_delete=models.CASCADE, related_name="researchset_setlists")
    # [1] The lists must be ordered (and they can be re-ordered by the user)
    order = models.IntegerField("Order", default=0)
    # [1] Each setlist must be of a particular type
    setlisttype = models.CharField("Setlist type", choices=build_abbr_list(SETLIST_TYPE), max_length=5)

    # [0-1] A user-defined name, if this is a SSGD type
    name = models.CharField("Setlist name", max_length=STANDARD_LENGTH, blank=True, null=True)

    # [1] For convenience and faster operation: keep a JSON list of the SSGs in this setlist
    contents = models.TextField("Contents", default="{}")

    # Depending on the type of setlist, there is a pointer to the actual list of SSGs
    # [0-1] Manuscript pointer
    manuscript = models.ForeignKey(Manuscript, blank=True, null=True, on_delete=models.SET_NULL, related_name="manuscript_setlists")
    # [0-1] Collection pointer (that can be HC, public or personal collection
    collection = models.ForeignKey(Collection, blank=True, null=True, on_delete=models.SET_NULL, related_name="collection_setlists")

    def __str__(self):
        """Combine the name and the order"""
        sBack = "{}: {}".format(self.researchset.name, self.order)
        return sBack

    def calculate_contents(self):
        oSsgList = {}
        # Add the name object for this list
        oSsgList['title'] = self.get_title_object()
        # Get the list of SSGs for this list
        oSsgList['auslist'] = self.get_ssg_list()
        # Add this contents and save myself
        self.contents = json.dumps(oSsgList)
        self.save()
        return True

    def get_ssg_list(self):
        """Create a list of SSGs,depending on the type I am"""

        oErr = ErrHandle()
        lBack = None
        collection_types = ['hist', 'ssgd']
        try:
            if self.setlisttype == "manu":
                # Create a list of SSG's from the manuscript
                lBack = self.ssgs_manuscript(self.manuscript)
            elif self.setlisttype in collection_types:
                lBack = self.ssgs_collection(self.collection)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("SetList/get_ssg_list")
        return lBack

    def get_title_object(self):
        """Depending on the setlisttype, this provides the title of the setlist
        
        The title is stored in an object, to facilitate template rendering
        """

        oBack = {"main": "", "size": 0, "yearstart": 0, "yearfinish": 3000, "matches": 0}
        if self.setlisttype == "manu":
            # This is a manuscript
            oBack = self.manuscript.get_full_name_html(field1="top", field2="middle", field3="main")
            oBack['size'] = self.manuscript.get_sermon_count()
            oBack['url'] = reverse('manuscript_details', kwargs={'pk': self.manuscript.id})
            oBack['yearstart'] = self.manuscript.yearstart
            oBack['yearfinish'] = self.manuscript.yearfinish
        elif self.setlisttype == "hist":
            # Historical collection
            oBack['top'] = "hc"
            oBack['main'] = self.collection.name
            oBack['size'] = self.collection.freqsuper()
            oBack['url'] = reverse('collhist_details', kwargs={'pk': self.collection.id})
        elif self.setlisttype == "ssgd":
            # Personal collection
            oBack['top'] = "pd"
            if self.name == None or self.name == "":
                oBack['main'] = self.collection.name
            else:
                oBack['main'] = self.name
            oBack['size'] = self.collection.freqsuper()
            oBack['url'] = reverse('collpriv_details', kwargs={'pk': self.collection.id})
        else:
            # No idea what this is
            oBack['top'] = "UNKNOWN"
            oBack['main'] = self.setlisttype
        # Return the result
        return oBack

    def ssgs_collection(self, bDebug = False):
        """Get the ordered list of SSGs in the [super] type collection"""

        oErr = ErrHandle()
        lBack = None
        code = None
        try:
            coll = self.collection
            # Get the list of SSGs inside this collection
            # Per issue #402 additional info needs to be there:
            #   author, 
            #   PASSIM code, 
            #   incipit, explicit, HC (if the SSG is part of a historical collection), 
            #   number of SGs contained in the equality set, 
            #   number of links to other SSGs
            # HC/PD specific:
            #   name
            #   description
            #   size
            # HC-specific:
            #   literature
            qs = Caned.objects.filter(collection=coll).order_by('order').values(
                'order', 'collection__name', 'collection__descrip', 'collection__settype', 
                'super', 'super__code', 'super__author__name',
                'super__incipit', 'super__explicit', 'super__sgcount', 'super__ssgcount')
            lBack = []
            with transaction.atomic():
                for obj in qs:
                    # Get the order number
                    order = obj['order']
                    # Get the collection-specific information
                    name = obj['collection__name']
                    descr = obj['collection__descrip']
                    settype = obj['collection__settype']
                    # Get the SSG
                    super = obj['super']
                    code = obj['super__code']
                    authorname = obj['super__author__name']
                    incipit = obj['super__incipit']
                    explicit = obj['super__explicit']
                    sgcount = obj['super__sgcount']
                    ssgcount = obj['super__ssgcount']
                    # Get the name(s) of the HC
                    lst_hc = Caned.objects.filter(super=super, collection__settype="hc").values(
                        'collection__id', 'collection__name')
                    hcs = ", ".join( [x['collection__name'] for x in lst_hc])
                    # ======== DEBUGGING ============
                    if hcs != "":
                        iStop = 1
                    # ===============================
                    # Get a URL for this ssg
                    url = reverse('equalgold_details', kwargs={'pk': super})

                    ## Treat signatures for this SSG
                    #sigbest = get_goldsig_dct(super)
                    #if sigbest == "":
                    #    sigbest = "ssg_{}".format(super)
                    ## Signatures for this SSG: get the full list
                    #siglist = get_goldsiglist_dct(super)
                    ## Put into object
                    #oItem = dict(super=super, sig=sigbest, siglist=siglist,
                    #             name=name, descr=descr, type=settype,
                    #             order=order, code=code, url=url, author=authorname,
                    #             incipit=incipit, explicit=explicit, sgcount=sgcount, 
                    #             ssgcount=ssgcount, hcs=hcs)
                    # Add to list
                    lBack.append(oItem)

            # Debugging: print the list
            if bDebug and not code is None:
                print("Collection id={}".format(coll.id))
                for oItem in lBack:
                    order = oItem.get("order")
                    austat = oItem.get("super")
                    sig = oItem.get("sig")
                    code = get_lilacode(austat, code)
                    print("sermon {}: ssg={} sig=[{}]".format(order, code, sig))

        except:
            msg = oErr.get_error_message()
            oErr.DoError("ssgs_collection")
        return lBack

    def ssgs_manuscript(self, bDebug = False):
        """Get the ordered list of SSGs related to a manuscript"""

        oErr = ErrHandle()
        lBack = None
        try:
            manu = self.manuscript
            # Get a list of SSGs to which the sermons in this manuscript point
            # Per issue #402 additional info needs to be there:
            #   author, 
            #   PASSIM code, 
            #   incipit, explicit, HC (if the SSG is part of a historical collection), 
            #   number of SGs contained in the equality set, 
            #   number of links to other SSGs
            # Per issue #402, phase 2, even more info needs to be added:
            #   for MANUSCRIPT source-lists, there should be an option for the user 
            #       to select additional SERMON manifestation details fields to be shown 
            #       (options: attributed author, section title, lectio, title, incipit, explicit, 
            #       postscriptum, feast, bible reference, cod. notes, notes, keywords)
            qs = manu.sermondescr_super.all().order_by('sermon__msitem__order').values(
                'sermon', 'sermon__msitem__order', 'super', 'super__code', 'super__author__name',
                'super__incipit', 'super__explicit', 'super__sgcount', 'super__ssgcount',
                'sermon__author__name', 'sermon__sectiontitle', 'sermon__quote', 'sermon__title', 
                'sermon__incipit', 'sermon__explicit', 'sermon__postscriptum', 'sermon__feast__name', 
                'sermon__bibleref', 'sermon__additional', 'sermon__note')
            # NOTE: the 'keywords' for issue #402 are a bit more cumbersome to collect...
            lBack = []
            with transaction.atomic():
                for obj in qs:
                    # Get the order number
                    order = obj['sermon__msitem__order']
                    # Get the SSG and all its characteristics
                    super = obj['super']
                    code = obj['super__code']
                    authorname = obj['super__author__name']
                    incipit = obj['super__incipit']
                    explicit = obj['super__explicit']
                    sgcount = obj['super__sgcount']
                    ssgcount = obj['super__ssgcount']
                    # Sermon characteristics
                    sermon = obj['sermon']
                    srm_author = obj['sermon__author__name']
                    srm_sectiontitle = obj['sermon__sectiontitle']
                    srm_lectio = obj['sermon__quote']
                    srm_title = obj['sermon__title']
                    srm_incipit = obj['sermon__incipit']
                    srm_explicit = obj['sermon__explicit']
                    srm_postscriptum = obj['sermon__postscriptum']
                    srm_feast = obj['sermon__feast__name']
                    srm_bibleref = obj['sermon__bibleref']
                    srm_codnotes = obj['sermon__additional']
                    srm_notes = obj['sermon__note']

                    # Get the name(s) of the HC
                    lst_hc = Caned.objects.filter(super=super, collection__settype="hc").values(
                        'collection__id', 'collection__name')
                    hcs = ", ".join( [x['collection__name'] for x in lst_hc])
                    # ======== DEBUGGING ============
                    if hcs != "":
                        iStop = 1
                    # ===============================

                    # TODO: Get the keywords
                    lst_kw = CanwitKeyword.objects.filter(canwit=sermon).values(
                        'keyword__name')
                    kws = ", ".join( [x['keyword__name'] for x in lst_kw])

                    # Get a URL for this ssg
                    url = reverse('equalgold_details', kwargs={'pk': super})

                    ## Treat signatures for this SSG: get the best for showing
                    #sigbest = get_goldsig_dct(super)
                    #if sigbest == "":
                    #    sigbest = "ssg_{}".format(super)
                    ## Signatures for this SSG: get the full list
                    #siglist = get_goldsiglist_dct(super)

                    # Put into object
                    oItem = dict(super=super, hcs=hcs, kws=kws,                                              # sig=sigbest, siglist=siglist
                                 order=order, code=code, url=url, author=authorname, type='ms',
                                 incipit=incipit, explicit=explicit, sgcount=sgcount, ssgcount=ssgcount,
                                 srm_author=srm_author, srm_sectiontitle=srm_sectiontitle, srm_lectio=srm_lectio,
                                 srm_title=srm_title, srm_incipit=srm_incipit, srm_explicit=srm_explicit,
                                 srm_postscriptum=srm_postscriptum, srm_feast=srm_feast, 
                                 srm_bibleref=srm_bibleref, srm_codnotes=srm_codnotes, srm_notes=srm_notes)
                    # Add to list
                    lBack.append(oItem)

            # Debugging: print the list
            if bDebug:
                print("Manuscript id={}".format(manu.id))
                for oItem in lBack:
                    order = oItem.get("order")
                    super = oItem.get("super")
                    sig = oItem.get("sig")
                    code = get_lilacode(super, code)
                    print("sermon {}: ssg={} sig=[{}]".format(order, code, sig))

        except:
            msg = oErr.get_error_message()
            oErr.DoError("ssgs_manuscript")
        return lBack
    

class SetDef(models.Model):
    """THe definition of a DCT"""

    # [1] obligatory name
    name = models.CharField("Name", max_length=STANDARD_LENGTH)
    # [1] A setlist just belongs to a research set
    researchset = models.ForeignKey(ResearchSet, on_delete=models.CASCADE, related_name="researchset_setdefs")
    # [1] order number of this DCT (assigned automatically)
    order = models.IntegerField("Order", default = 0)

    # [0-1] Optional notes for this definition
    notes = models.TextField("Notes", blank=True, null=True)

    # [1] A list of all the DCT parameters for this DCT
    contents = models.TextField("Contents", default="{}")

    # [1] And a date: the date of saving this manuscript
    created = models.DateTimeField(default=get_current_datetime)
    saved = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """Just return the name"""
        return self.name

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        # Adapt the save date
        self.saved = get_current_datetime()

        # Need any name or notes fixed?
        if self.name == None or self.name == "":
            # Calculate the proper order
            last = SetDef.objects.filter(researchset=self.researchset).order_by("-order", "-saved").first()
            if last == None:
                order = 1
            else:
                order = last.order + 1
            self.order = order
            # Automatically assign a name
            default_name = "{}_DCT_{:06}".format(self.researchset.profile.user.username, order)
            self.name = default_name
            self.notes = "Automatically created"
        # Initial saving
        response = super(SetDef, self).save(force_insert, force_update, using, update_fields)

        # Return the response when saving
        return response

    def check_default(rset, username):
        """Create a default SetDef for this research set"""

        # Are there any setdefs?
        if SetDef.objects.filter(researchset=rset).count() == 0:
            # Make sure to create at least one (with overall default values)
            obj = SetDef.objects.create(researchset=rset)
        return True

    def get_created(self):
        """REturn the creation date in a readable form"""

        # sDate = self.created.strftime("%d/%b/%Y %H:%M")
        sDate = get_crpp_date(self.created, True)
        return sDate

    def get_contents(self, pivot_id=None, recalculate=False):
        """Get the set of lists for this particular DCT"""

        oErr = ErrHandle()
        oBack = None
        try:
            # Get the SSGlists from the research set
            ssglists = self.researchset.get_austatlists(recalculate)

            # Possibly get (stored) parameters from myself
            params = {}
            if self.contents != "" and self.contents[0] == "{":
                params = json.loads(self.contents)
            
            # Return the parameters and the lists
            oBack = dict(params=params, ssglists=ssglists)

        except:
            msg = oErr.get_error_message()
            oErr.DoError("SetDef/get_contents")
        return oBack

    def get_notes_html(self):
        """Convert the markdown notes"""

        sNotes = "-"
        if self.notes != None:
            sNotes = markdown(self.notes)
        return sNotes

    def get_saved(self):
        """REturn the saved date in a readable form"""

        # sDate = self.saved.strftime("%d/%b/%Y %H:%M")
        sDate = get_crpp_date(self.saved, True)
        return sDate

    def get_setlist(self, pivot_id=None):
        """Get the set of lists for this particular DCT"""

        oErr = ErrHandle()
        oBack = None
        try:
            # Get to the research set
            id_list = [x['id'] for x in self.researchset.researchset_setlists.all().order_by('order').values("id")]
            lst_rset = []
            if pivot_id != None and pivot_id in id_list:
                lst_rset.append(pivot_id)
            # Add the remaining ID's
            for id in id_list:
                if not id in lst_rset: lst_rset.append(id)

            # Check the number of lists in the research set
            if lst_rset == None or len(lst_rset) < 2:
                oErr.Status("Not enough SSG-lists to compare")
                return None

            # We have enough lists: Get the lists of SSGs for each 
            lst_ssglists = []
            for setlist_id in lst_rset:
                # Get the actual setlist
                setlist = SetList.objects.filter(id=setlist_id).first()
                if setlist != None:
                    # Create an empty SSG-list
                    oSsgList = {}
                    # Add the object itself
                    oSsgList['obj'] = setlist
                    # Add the name object for this list
                    oSsgList['title'] = setlist.get_title_object()
                    # Get the list of SSGs for this list
                    oSsgList['auslist'] = setlist.get_ssg_list()
                    # Add the list object to the list
                    lst_ssglists.append(oSsgList)
            
            # Return this list of lists
            oBack = dict(ssglists=lst_ssglists)
            # Prepare and create an appropriate table = list of rows
            rows = []
            # Create header row
            oRow = []
            oRow.append('Gr/Cl/Ot')
            for oSsgList in lst_ssglists:
                # Add the title *object*
                oRow.append(oSsgList['title'])
            rows.append(oRow)

            # Start out with the pivot: the *first* one in 'auslist'
            lst_pivot = lst_ssglists[0]
            for oPivot in lst_pivot['auslist']:
                # Create a row based on this pivot
                oRow = []
                # (1) row header
                oRow.append(oPivot['sig'])
                # (2) pivot SSG number
                oRow.append(oPivot['order'])
                # (3) SSG number in all other manuscripts
                ssg_id = oPivot['super']
                for lst_this in lst_ssglists[1:]:
                    bFound = False
                    order = ""
                    for oItem in lst_this['auslist']:
                        if ssg_id == oItem['super']:
                            # Found it!
                            order = oItem['order']
                            bFound = True
                            break
                    oRow.append(order)
                # (4) add the row to the list
                rows.append(oRow)
            # Make sure we return the right information
            oBack['setlist'] = rows
        except:
            msg = oErr.get_error_message()
            oErr.DoError("SetDef/get_setlist")
        return oBack


