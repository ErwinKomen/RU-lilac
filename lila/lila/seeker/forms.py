"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _
from django.forms import ModelMultipleChoiceField, ModelChoiceField
from django.forms.widgets import *
from django.db.models import F, Case, Value, When, IntegerField
from django_select2.forms import ModelSelect2Mixin, Select2MultipleWidget, ModelSelect2MultipleWidget, ModelSelect2TagWidget, ModelSelect2Widget, HeavySelect2Widget
from lila.seeker.models import *
from lila.basic.widgets import RangeSlider

def init_choices(obj, sFieldName, sSet, use_helptext=True, maybe_empty=False, bUseAbbr=False, exclude=None):
    if (obj.fields != None and sFieldName in obj.fields):
        if bUseAbbr:
            obj.fields[sFieldName].choices = build_abbr_list(sSet, maybe_empty=maybe_empty, exclude=exclude)
        else:
            obj.fields[sFieldName].choices = build_choice_list(sSet, maybe_empty=maybe_empty)
        if use_helptext:
            obj.fields[sFieldName].help_text = get_help(sSet)

def user_is_in_team(username, team_group, userplus=None):
    bResult = False
    # Validate
    if username and team_group and username != "" and team_group != "":
        # First filter on owner
        owner = Profile.get_user_profile(username)
        # Now check for permissions
        bResult = (owner.user.groups.filter(name=team_group).first() != None)
        # If the user has no permission, perhaps he is a 'userplus'?
        if not bResult and userplus:
            bResult = (owner.user.groups.filter(name=userplus).first() != None)
    return bResult

CODE_TYPE = [('-', 'Irrelevant'), ('spe', 'Part of a Super Sermon Gold'), ('non', 'Loner: not part of a SSG')]
AUTHOR_TYPE = [('', 'All'), ('spe', 'Author defined'), ('non', 'No author defined')]
SCOUNT_OPERATOR = [('', '(make a choice)'), ('lt', 'Less than'), ('lte', 'Less then or equal'),('exact', 'Equals'), 
                   ('gte', 'Greater than or equal'), ('gt', 'Greater than')]


# ================= WIDGETS =====================================


class AuthorOneWidget(ModelSelect2Widget):
    model = Author
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Author.objects.all().order_by('name').distinct()


class AuthorWidget(ModelSelect2MultipleWidget):
    model = Author
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Author.objects.all().order_by('name').distinct()


class BibrefWidget(ModelSelect2MultipleWidget):
    model = BibRange
    search_fields = ['book__name__icontains', 'book__latname__icontains']
    addonly = False

    def label_from_instance(self, obj):
        # Provide a suitable reference label
        return obj.get_ref_latin()

    def get_queryset(self):
        if self.addonly:
            qs = BibRange.objects.none()
        else:
            qs = BibRange.objects.all().order_by('book__idno', 'chvslist').distinct()
        return qs


class BibrefAddonlyWidget(BibrefWidget):
    """Variation on BibRefWidget"""
    addonly = True


class BookWidget(ModelSelect2Widget):
    model = Book
    search_fields = [ 'name__icontains', 'latname__icontains', 'abbr__icontains', 'latabbr__icontains' ]

    def label_from_instance(self, obj):
        # Provide both the Latin as well as the English name
        full = "{} ({})".format(obj.latname, obj.name)
        # Determine here what to return...
        return full

    def get_queryset(self):
        return Book.objects.all().order_by('idno').distinct()


class CheckboxString(CheckboxInput):

    def value_from_datadict(self, data, files, name):
        sBack = "true" if name in data else "false"
        return sBack


class CityOneWidget(ModelSelect2Widget):
    model = Location
    search_fields = [ 'name__icontains' ]
    dependent_fields = {}   # E.G: {'lcity': 'lcity', 'lcountry': 'lcountry'}

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        loc_city = LocationType.objects.filter(name="city").first()
        return Location.objects.filter(loctype=loc_city).order_by('name').distinct()


class CityMonasteryOneWidget(ModelSelect2Widget):
    model = Location
    search_fields = [ 'name__icontains' ]
    dependent_fields = {}   # E.G: {'lcity': 'lcity', 'lcountry': 'lcountry'}

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        level = 8   # Level 8 is city, lower than that is village, library, monastery
        #loc_id = LocationType.objects.filter(Q(name="city")|Q(name="village")|Q(name="monastery")).first()
        #return Location.objects.filter(loctype=loc_city).order_by('name').distinct()
        return Location.objects.filter(loctype__level__lte=level).order_by('name').distinct()


class CityWidget(ModelSelect2MultipleWidget):
    model = Location
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        loctype = LocationType.objects.filter(name__iexact="city").first()
        if loctype != None:
            level = loctype.level
            qs = Location.objects.filter(loctype__level__lte=level).order_by('name').distinct()
        else:
            qs = Location.objects.all().order_by('name').distinct()
        return qs


class CodeWidget(ModelSelect2MultipleWidget):
    # lila codes defined in Austat instances
    model = Austat
    search_fields = [ 'code__icontains' ]

    def label_from_instance(self, obj):
        return obj.get_code()

    def get_queryset(self):
        return Austat.objects.filter(moved__isnull=True, atype='acc').order_by('code').distinct()


class CodicoOneWidget(ModelSelect2Widget):
    """Select one Codico"""

    model = Codico
    search_fields = [ 
        'manuscript__lcity__name__icontains', 
        'manuscript__library__name__icontains',
        'manuscript__idno__icontains', 
        #'name__icontains', 
        'order__icontains']

    def label_from_instance(self, obj):
        # The name is the MS's [idno] plus credentials of the codico
        return obj.get_identification()

    def get_queryset(self):
        return Codico.objects.filter(manuscript__mtype='man').order_by(
            'manuscript__idno', 'order').distinct()


class CollectionWidget(ModelSelect2MultipleWidget):
    model = Collection
    search_fields = [ 'name__icontains' ]
    type = None

    def label_from_instance(self, obj):
        if obj.name and obj.owner:
            return "{} ({})".format( obj.name, obj.owner.user.username)
        else:
            return "coll_{}".format(obj.id)

    def get_queryset(self):
        username = self.attrs.pop('username', '')
        team_group = self.attrs.pop('team_group', '')
        settype = self.attrs.pop('settype', '')
        scope = self.attrs.pop('scope', '')
        if self.type:
            qs = Collection.get_scoped_queryset(self.type, username, team_group, settype=settype, scope=scope)
        else:
            qs = Collection.get_scoped_queryset(None, username, team_group, settype=settype, scope=scope)
        #if settype:
        #    qs = qs.filter(settype=settype)
        return qs


class CollectionManuWidget(CollectionWidget):
    """Like Collection, but then for: Manuscript"""
    type = "manu"


class CollectionCanwitWidget(CollectionWidget):
    """Like Collection, but then for: Sermon"""
    type = "sermo"


class CollectionAustatWidget(CollectionWidget):
    """Like Collection, but then for: Austat = super sermon gold"""
    type = "austat"


class CollectionOneWidget(ModelSelect2Widget):
    model = Collection
    search_fields = [ 'name__icontains' ]


    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        oErr = ErrHandle()
        qs = None
        try:
            qs = Collection.objects.all().order_by('name')
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CollectionOneWidget")
        return qs


class CollectionWidget(ModelSelect2MultipleWidget):
    model = Collection
    search_fields = [ 'name__icontains' ]


    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        oErr = ErrHandle()
        qs = None
        try:
            qs = Collection.objects.all().order_by('name')
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CollectionWidget")
        return qs


class CollOneWidget(ModelSelect2Widget):
    model = Collection
    search_fields = [ 'name__icontains' ]
    type = None
    settype = "pd"

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        oErr = ErrHandle()
        qs = None
        try:
            username = self.attrs.pop('username', '')
            team_group = self.attrs.pop('team_group', '')
            if self.type:
                qs = Collection.get_scoped_queryset(self.type, username, team_group, settype=self.settype)
            else:
                qs = Collection.get_scoped_queryset(None, username, team_group, settype=self.settype)
            #lstQ = []
            #if self.type != None: lstQ.append(Q(type=self.type))
            #if self.settype != None: lstQ.append(Q(settype=self.settype))
            #return Collection.objects.filter(*lstQ).order_by('name').distinct()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CollOneWidget")
        return qs


class CollOneManuWidget(CollOneWidget):
    """Like CollOne, but then for: Manuscript"""
    type = "manu"
    settype = "pd"


class CollOneSermoWidget(CollOneWidget):
    """Like CollOne, but then for: Sermon"""
    type = "sermo"
    settype = "pd"


class CollOneSuperWidget(CollOneWidget):
    """Like CollOne, but then for: Austat = super sermon gold"""
    type = "austat"
    settype = "pd"


class CollOneHistWidget(CollOneWidget):
    """Like CollOne, but then for: Austat = super sermon gold"""
    type = "austat"
    settype = "hc"


class CountryWidget(ModelSelect2MultipleWidget):
    model = Location
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        loctype = LocationType.objects.filter(name__iexact="country").first()
        if loctype != None:
            qs = Location.objects.filter(loctype=loctype).order_by('name').distinct()
        else:
            qs = Location.objects.all().order_by('name').distinct()
        return qs


class CountryOneWidget(ModelSelect2Widget):
    model = Location
    search_fields = [ 'name__icontains' ]
    dependent_fields = {'lcity': 'lcity_locations'}
    # Note: k = form field, v = model field

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        loc_country = LocationType.objects.filter(name="country").first()
        return Location.objects.filter(loctype=loc_country).order_by('name').distinct()


class DaterangeWidget(ModelSelect2MultipleWidget):
    model = Daterange
    search_fields = [ 'yearstart__icontains', 'yearfinish__icontains' ]
    addonly = False
    codico = None

    def label_from_instance(self, obj):
        if obj.yearstart == obj.yearfinish:
            years = "{}".format(obj.yearstart)
        else:
            years = "{}-{}".format(obj.yearstart, obj.yearfinish)
        return years

    def get_queryset(self):
        if self.addonly:
            if self.codico is None:
                qs = Daterange.objects.none()
            else:
                qs = self.codico.codico_dateranges.all()
        else:
            qs = Daterange.objects.all().order_by('yearstart').distinct()
        return qs


class AustatMultiWidget(ModelSelect2MultipleWidget):
    model = Austat
    search_fields = ['code__icontains', 'id__icontains', 'author__name__icontains']
    addonly = False

    def label_from_instance(self, obj):
        # sLabel = obj.get_label(do_incexpl = False)
        sLabel = obj.get_code()
        return sLabel

    def get_queryset(self):
        if self.addonly:
            qs = Austat.objects.none()
        else:
            qs = Austat.objects.filter(code__isnull=False, moved__isnull=True, atype='acc').order_by('code').distinct()
        return qs


class AustatLinkAddOnlyWidget(AustatMultiWidget):
    model = AustatLink
    search_fields = ['dst__code__icontains', 'dst__id__icontains', 'dst__author__name__icontains']
    addonly = True

    def label_from_instance(self, obj):
        sLabel = obj.get_label(do_incexpl = True)
        return sLabel

    def get_queryset(self):
        if self.addonly:
            qs = AustatLink.objects.none()
        else:
            qs = AustatLink.objects.all().order_by('dst__code', 'dst__firstsig').distinct()
        return qs


class AustatWidget(ModelSelect2Widget):
    model = Austat
    search_fields = [ 'code__icontains', 'author__name__icontains', 'srchftext__icontains', 'srchftrans__icontains' ]
    addonly = False
    order = [F('code').asc(nulls_last=True), 'firstsig']
    exclude = None

    def label_from_instance(self, obj):
        # Determine the full text
        full = obj.get_text()
        # Determine here what to return...
        return full

    def get_queryset(self):
        if self.addonly:
            qs = Austat.objects.none()
        else:
            # qs = Austat.objects.all().order_by('code', 'firstsig').distinct()
            if self.exclude == None:
                qs = Austat.objects.filter(moved__isnull=True, atype='acc').order_by(*self.order).distinct()
            else:
                qs = Austat.objects.filter(moved__isnull=True, atype='acc').exclude(id=self.exclude).order_by(*self.order).distinct()
        return qs


class AuworkWidget(ModelSelect2MultipleWidget):
    model = Auwork
    search_fields = [ 'key__icontains', 'work__icontains' ]

    def label_from_instance(self, obj):
        return obj.key

    def get_queryset(self):
        qs = Auwork.objects.all().order_by('key').distinct()
        return qs


class AuworkOneWidget(ModelSelect2Widget):
    model = Auwork
    search_fields = [ 'key__icontains', 'work__icontains' ]

    def label_from_instance(self, obj):
        return obj.key

    def get_queryset(self):
        qs = Auwork.objects.all().order_by('key').distinct()
        return qs


class CodheadOneWidget(ModelSelect2Widget):
    model = Codhead
    search_fields = [ 'locus__icontains', 'title__icontains' ]

    def label_from_instance(self, obj):
        return obj.locus

    def get_queryset(self):
        qs = Codhead.objects.all().order_by('locus').distinct()
        return qs


class FeastOneWidget(ModelSelect2Widget):
    model = Feast
    search_fields = [ 'name__icontains', 'latname__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Feast.objects.all().order_by('name').distinct()


class FeastWidget(ModelSelect2MultipleWidget):
    model = Feast
    search_fields = [ 'name__icontains', 'latname__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Feast.objects.all().order_by('name').distinct()


class FreeWidget(ModelSelect2MultipleWidget):
    model = Free
    search_fields = ['name__icontains', 'field__icontains']
    main = ""

    def label_from_instance(self, obj):
        # Provide a suitable reference label
        return obj.name

    def get_queryset(self):
        qs = Free.objects.filter(main=self.main).order_by("name")
        return qs


class KeycodeMultiWidget(ModelSelect2MultipleWidget):
    model = Austat
    search_fields = ['auwork__key__icontains', 'keycode__icontains']
    addonly = False

    def label_from_instance(self, obj):
        sLabel = obj.get_keycode()
        return sLabel

    def get_queryset(self):
        if self.addonly:
            qs = Austat.objects.none()
        else:
            qs = Austat.objects.filter(keycode__isnull=False, moved__isnull=True, atype='acc').order_by('auwork__key', 'keycode').distinct()
        return qs


class GenreWidget(ModelSelect2MultipleWidget):
    model = Keyword
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        qs = Genre.objects.all().order_by('name').distinct()
        return qs


class KeywordWidget(ModelSelect2MultipleWidget):
    model = Keyword
    search_fields = [ 'name__icontains' ]
    is_team = True

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        if self.is_team:
            qs = Keyword.objects.all().order_by('name').distinct()
        else:
            qs = Keyword.objects.exclude(visibility="edi").order_by('name').distinct()
        return qs


class KeywordAllWidget(KeywordWidget):
    """All keywords"""
    is_team = False


class KeywordOneWidget(ModelSelect2Widget):
    model = Keyword
    search_fields = [ 'name__icontains' ]
    is_team = True

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        if self.is_team:
            qs = Keyword.objects.all().order_by('name').distinct()
        else:
            qs = Keyword.objects.exclude(visibility="edi").order_by('name').distinct()
        return qs


class LitrefWidget(ModelSelect2Widget):
    model = Litref
    search_fields = [ 'full__icontains' ]

    def label_from_instance(self, obj):
        # The label only gives the SHORT version!!
        short = obj.get_short()
        full = obj.full
        # Determine here what to return...
        return full

    def get_queryset(self):
        return Litref.objects.exclude(full="").order_by('full').distinct()


class LibraryWidget(ModelSelect2MultipleWidget):
    model = Library
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        qs = Library.objects.all().order_by('name').distinct()
        return qs


class LibraryOneWidget(ModelSelect2Widget):
    model = Library
    search_fields = [ 'name__icontains' ]
    dependent_fields = {} # EG: {'lcity': 'lcity', 'lcountry': 'lcountry'}

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        return Library.objects.all().order_by('name').distinct()

    def filter_queryset(self, term, queryset = None, **dependent_fields):
        response = super(LibraryOneWidget, self).filter_queryset(term, queryset, **dependent_fields)
        return response


class LitrefManWidget(ModelSelect2MultipleWidget):
    model = LitrefMan
    search_fields = [ 'reference__full__icontains' ]

    def label_from_instance(self, obj):
        # The label only gives the SHORT version!!
        return obj.get_short()

    def get_queryset(self):
        return LitrefMan.objects.all().order_by('reference__full', 'pages').distinct()


class LitrefColWidget(ModelSelect2MultipleWidget):
    model = LitrefCol
    search_fields = [ 'reference__full__icontains' ]

    def label_from_instance(self, obj):
        # The label only gives the SHORT version!!
        return obj.get_short()

    def get_queryset(self):
        return LitrefCol.objects.all().order_by('reference__full', 'pages').distinct()


class LocationWidget(ModelSelect2MultipleWidget):
    model = Location
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        sLabel = "{} ({})".format(obj.name, obj.loctype)
        # sLabel = obj.name
        return sLabel


class LocationOneWidget(ModelSelect2Widget):
    model = Location
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        sLabel = "{} ({})".format(obj.name, obj.loctype)
        # sLabel = obj.name
        return sLabel

    def get_queryset(self):
        return Location.objects.all().order_by('name').distinct()


class LocTypeWidget(ModelSelect2MultipleWidget):
    model = LocationType
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        sLabel = "{} ({})".format(obj.name, obj.level)
        return sLabel

    def get_queryset(self):
        return LocationType.objects.all().order_by('level').distinct()


class LoctypeOneWidget(ModelSelect2Widget):
    model = LocationType
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        sLabel = "{} ({})".format(obj.name, obj.level)
        return sLabel

    def get_queryset(self):
        return LocationType.objects.all().order_by('level').distinct()


class ManuidWidget(ModelSelect2MultipleWidget):
    model = Manuscript
    search_fields = [ 'idno__icontains']

    def label_from_instance(self, obj):
        return obj.idno

    def get_queryset(self):
        return Manuscript.objects.exclude(mtype='tem').order_by('idno').distinct()


class ManuidOneWidget(ModelSelect2Widget):
    model = Manuscript
    search_fields = [ 'idno__icontains']

    def label_from_instance(self, obj):
        return obj.idno

    def get_queryset(self):
        qs = self.queryset
        if qs == None:
            qs = Manuscript.objects.filter(mtype='man').order_by('idno').distinct()
        return qs


class ManuReconWidget(ModelSelect2Widget):
    model = Manuscript
    search_fields = [ 'idno__icontains']

    def label_from_instance(self, obj):
        return obj.idno

    def get_queryset(self):
        qs = self.queryset
        if qs == None:
            qs = Manuscript.objects.filter(mtype='rec').order_by('idno').distinct()
        return qs


class ManuscriptExtWidget(ModelSelect2MultipleWidget):
    model = ManuscriptExt
    search_fields = [ 'url__icontains' ]
    addonly = False

    def label_from_instance(self, obj):
        return obj.url

    def get_queryset(self):
        if self.addonly:
            qs = ManuscriptExt.objects.none()
        else:
            qs = ManuscriptExt.objects.all().order_by('url').distinct()
        return qs        


class OriginOneWidget(ModelSelect2Widget):
    model = Origin
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        # sLabel = "{} ({})".format(obj.name, obj.loctype)
        sLoc = "" if obj.location == None else " ({})".format(obj.location.get_loc_name())
        sLabel = "{}{}".format(obj.name, sLoc)
        return sLabel

    def get_queryset(self):
        return Origin.objects.all().order_by('name').distinct()


class OriginCodWidget(ModelSelect2MultipleWidget):
    model = OriginCodico
    search_fields = [ 'origin__name__icontains', 'origin__location__name__icontains' ]
    addonly = False
    codico = None

    def label_from_instance(self, obj):
        oErr = ErrHandle()
        sLabel = ""
        try:
            ori = obj.origin
            if ori.name == "":
                if ori.location == None:
                    sLabel = "(undetermined)"
                else:
                    sLabel = ori.location.name
            else:
                if ori.location == None:
                    sLabel = ori.name
                else:
                    sLabel = "{}: {}".format(ori.name, ori.location.name)
            sNote = obj.note
            if sNote != None and sNote != "":
                sLabel = "{} ({}...)".format(sLabel, sNote[:30])
        except:
            msg = oErr.get_error_message()
            oErr.DoError("OriginCodWidget/label_from_instance")
        return sLabel

    def get_queryset(self):
        qs = OriginCodico.objects.none()
        oErr = ErrHandle()
        try:
            if self.addonly:
                if self.codico == None:
                    qs = OriginCodico.objects.none()
                else:
                    qs = self.codico.codico_origins.all().order_by('origin__name', 'origin__location__name')
            else:
                qs = OriginCodico.objects.all().order_by('origin__name', 'origin__location__name') # .distinct()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("OriginCodWidget/get_queryset")
        return qs        


class ProjectWidget(ModelSelect2MultipleWidget):
    model = Project
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        if self.queryset == None:
            qs = Project.objects.all().order_by('name').distinct()
        else:
            qs = self.queryset
        return qs


class ProjectOneWidget(ModelSelect2Widget):
    model = Project
    search_fields = [ 'name__icontains' ]

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        qs = Project.objects.all().order_by('name').distinct()
        return qs

    
class ProfileWidget(ModelSelect2MultipleWidget):
    model = Profile
    search_fields = [ 'user__username__icontains' ]

    def label_from_instance(self, obj):
        return obj.user.username

    def get_queryset(self):
        return Profile.objects.all().order_by('user__username').distinct()


class ProfileOneWidget(ModelSelect2Widget):
    model = Profile
    search_fields = [ 'user__username__icontains' ]

    def label_from_instance(self, obj):
        return obj.user.username

    def get_queryset(self):
        return Profile.objects.all().order_by('user__username').distinct()


class ProvenanceOneWidget(ModelSelect2Widget):
    model = Provenance
    search_fields = [ 'name__icontains', 'location__name__icontains' ]

    def label_from_instance(self, obj):
        sLabel = ""
        if obj.name == "":
            if obj.location == None:
                sLabel = "(undetermined)"
            else:
                sLabel = obj.location.name
        else:
            if obj.location == None:
                sLabel = obj.name
            else:
                sLabel = "{}: {}".format(obj.name, obj.location.name)
        return sLabel

    def get_queryset(self):
        qs = Provenance.objects.all().order_by('name', 'location__name').distinct()
        return qs        


class ProvenanceWidget(ModelSelect2MultipleWidget):
    model = Provenance
    search_fields = [ 'name__icontains' ]
    addonly = False
    manu = None

    def label_from_instance(self, obj):
        return obj.name

    def get_queryset(self):
        if self.addonly:
            if self.manu == None:
                qs = Provenance.objects.none()
            else:
                # qs = self.manu.provenances.all()
                qs = self.manu.manuprovenances.all().order_by('name')
        else:
            qs = Provenance.objects.all().order_by('name').distinct()
        return qs        


class ProvenanceManWidget(ModelSelect2MultipleWidget):
    model = ProvenanceMan
    search_fields = [ 'provenance__name__icontains', 'provenance__location__name__icontains' ]
    addonly = False
    manu = None

    def label_from_instance(self, obj):
        oErr = ErrHandle()
        sLabel = ""
        try:
            prov = obj.provenance
            if prov.name == "":
                if prov.location == None:
                    sLabel = "(undetermined)"
                else:
                    sLabel = prov.location.name
            else:
                if prov.location == None:
                    sLabel = prov.name
                else:
                    sLabel = "{}: {}".format(prov.name, prov.location.name)
            sNote = obj.note
            if sNote != None and sNote != "":
                sLabel = "{} ({}...)".format(sLabel, sNote[:30])
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ProvenanceManWidget/label_from_instance")
        return sLabel

    def get_queryset(self):
        qs = ProvenanceMan.objects.none()
        oErr = ErrHandle()
        try:
            if self.addonly:
                if self.manu == None:
                    qs = ProvenanceMan.objects.none()
                else:
                    # qs = self.manu.provenances.all()
                    qs = self.manu.manuscripts_provenances.all().order_by('provenance__name', 'provenance__location__name')
            else:
                qs = ProvenanceMan.objects.all().order_by('provenance__name', 'provenance__location__name') # .distinct()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ProvenanceManWidget/get_queryset")
        return qs        


class ProvenanceCodWidget(ModelSelect2MultipleWidget):
    model = ProvenanceCod
    search_fields = [ 'provenance__name__icontains', 'provenance__location__name__icontains' ]
    addonly = False
    codico = None

    def label_from_instance(self, obj):
        oErr = ErrHandle()
        sLabel = ""
        try:
            prov = obj.provenance
            if prov.name == "":
                if prov.location == None:
                    sLabel = "(undetermined)"
                else:
                    sLabel = prov.location.name
            else:
                if prov.location == None:
                    sLabel = prov.name
                else:
                    sLabel = "{}: {}".format(prov.name, prov.location.name)
            sNote = obj.note
            if sNote != None and sNote != "":
                sLabel = "{} ({}...)".format(sLabel, sNote[:30])
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ProvenanceCodWidget/label_from_instance")
        return sLabel

    def get_queryset(self):
        qs = ProvenanceCod.objects.none()
        oErr = ErrHandle()
        try:
            if self.addonly:
                if self.codico == None:
                    qs = ProvenanceCod.objects.none()
                else:
                    qs = self.codico.codico_provenances.all().order_by('provenance__name', 'provenance__location__name')
            else:
                qs = ProvenanceCod.objects.all().order_by('provenance__name', 'provenance__location__name') # .distinct()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ProvenanceCodWidget/get_queryset")
        return qs        


class CanwitSuperWidget(ModelSelect2MultipleWidget):
    model = CanwitAustat
    add_only = False
    search_fields = ['sermon__siglist__icontains',      'sermon__author__name__icontains', 
                     'austat__author__name__icontains', 'austat__code__icontains',
                     'austat__srchftext__icontains',  'austat__srchftrans__icontains' ]

    def label_from_instance(self, obj):
        # Determine the full text
        full = obj.get_label(do_incexpl=False)
        # Determine here what to return...
        return full

    def get_queryset(self):
        if self.add_only:
            qs = CanwitAustat.objects.none()
        else:
            qs = CanwitAustat.unique_list()
        return qs


class CanwitSuperAddOnlyWidget(CanwitSuperWidget):
    add_only = True


class ManualSignatureWidget(ModelSelect2MultipleWidget):
    # NOTE: experimental
    model = CanwitSignature
    search_fields = [ 'code__icontains' ]

    def label_from_instance(self, obj):
        return obj.code

    def get_queryset(self):
        return CanwitSignature.objects.all().order_by('code').distinct()


class ManutypeWidget(ModelSelect2Widget):
    model = FieldChoice
    search_fields = [ 'english_name__icontains']

    def label_from_instance(self, obj):
        return obj.english_name

    def get_queryset(self):
        return FieldChoice.objects.filter(field=MANUSCRIPT_TYPE).exclude(abbr='tem').order_by("english_name")


class StypeWidget(ModelSelect2MultipleWidget):
    model = FieldChoice
    search_fields = [ 'english_name__icontains']

    def label_from_instance(self, obj):
        return obj.english_name

    def get_queryset(self):
        return FieldChoice.objects.filter(field=STATUS_TYPE).order_by("english_name")


class SuperDistWidget(ModelSelect2Widget):
    model = AustatDist
    sermon = None
    search_fields = ['austat__code__icontains', 'austat__id__icontains', 'austat__author__name__icontains', 
                     'austat__srchftext__icontains', 'austat__srchftrans__icontains'
                     ]

    def label_from_instance(self, obj):
        sLabel = obj.austat.get_label(do_incexpl = True)
        return sLabel

    def get_queryset(self):
        qs = None
        if self.sermon == None:
            qs = AustatDist.objects.filter(austat__moved__isnull=True).order_by(
                'distance', 'austat__code', 'austat__author__name', 'id').distinct()
        else:
            # Check and possibly re-calculate the set of SSG candidates
            self.sermon.do_distance()
            if self.sermon.canwitsuperdist.count() == 0:
                qs = AustatDist.objects.filter(austat__moved__isnull=True).order_by(
                    'distance', 'austat__code', 'austat__author__name', 'id').distinct()
            else:
                # Get the ordered set of SSG candidates
                qs = self.sermon.canwitsuperdist.all().order_by(
                    'distance', 'austat__code', 'austat__author__name')
        return qs


class SuperOneWidget(ModelSelect2Widget):
    model = Austat
    search_fields = ['code__icontains', 'id__icontains', 'author__name__icontains', 
                     'srchftext__icontains', 'srchftrans__icontains']

    def label_from_instance(self, obj):
        sLabel = obj.get_label(do_incexpl = True)
        return sLabel

    def get_queryset(self):
        return Austat.objects.filter(moved__isnull=True, atype = 'acc').order_by('code', 'id').distinct()

    def filter_queryset(self, term, queryset = None, **dependent_fields):
        qs = super(SuperOneWidget, self).filter_queryset(term, queryset, **dependent_fields)
        # Adapt
        condition = Q(code__icontains=term) | Q(author__name__icontains=term) | \
                    Q(srchftext__icontains=term) | Q(srchftrans__icontains=term) 
        qs = qs.annotate(
            full_string_order=Case(
                When(condition, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
        )
        # Return result
        return qs.order_by("-full_string_order", "code", "id")


class TemplateOneWidget(ModelSelect2Widget):
    model = Template
    search_fields = [ 'name__icontains']

    def label_from_instance(self, obj):
        sLabel = "{} ({})".format(obj.name, obj.profile.user.username)
        return sLabel

    def get_queryset(self):
        #username = self.attrs.pop('username', '')
        #team_group = self.attrs.pop('team_group', '')
        return Template.objects.all().order_by('name').distinct()


class UserWidget(ModelSelect2MultipleWidget):
    model = User
    search_fields = [ 'username__icontains' ]

    def label_from_instance(self, obj):
        return obj.username

    def get_queryset(self):
        return User.objects.all().order_by('username').distinct()







# ================= FORMS =======================================

class lilaModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.username = kwargs.pop('username', "")
        self.team_group = kwargs.pop('team_group', "")
        self.userplus = kwargs.pop('userplus', "")
        # Start by executing the standard handling
        super(lilaModelForm, self).__init__(*args, **kwargs)


class BootstrapAuthenticationForm(AuthenticationForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(max_length=254,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'User name'}))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder':'Password'}))


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )


class SearchSermonForm(forms.Form):
    """Note: only for SEARCHING"""

    author = forms.CharField(label=_("Author"), required=False)
    incipit = forms.CharField(label=_("Incipit"), required=False)
    explicit = forms.CharField(label=_("Explicit"), required=False)
    title = forms.CharField(label=_("Title"), required=False)
    feast = forms.CharField(label=_("Feast"), required=False)
    keyword = forms.CharField(label=_("Keyword"), required=False)


class ManuReconForm(forms.Form):
    """Search through reconstructed manuscripts"""

    rmanu = ModelChoiceField(queryset=None, required=False,
            widget=ManuReconWidget(attrs={'data-placeholder': 'Select a reconstructed manuscript...', 'style': 'width: 100%;'}))
    rcodico = ModelChoiceField(queryset=None, required=False,
            widget=CodicoOneWidget(attrs={'data-placeholder': 'Select a codicological unit...', 'style': 'width: 100%;'}))

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuReconForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            self.fields['rmanu'].queryset = Manuscript.objects.filter(mtype='rec')
            self.fields['rcodico'].queryset = Codico.objects.filter(manuscript__mtype='man').order_by(
                'manuscript__idno', 'order').distinct()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("manureconform")


class SearchManuscriptForm(forms.Form):
    """Note: only for SEARCHING"""

    country = forms.CharField(label=_("Country"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching countries input-sm', 'placeholder': 'Country...', 'style': 'width: 100%;'}))
    city = forms.CharField(label=_("City"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching cities input-sm', 'placeholder': 'City...',  'style': 'width: 100%;'}))
    library = forms.CharField(label=_("Library"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Name of library...',  'style': 'width: 100%;'}))
    name = forms.CharField(label=_("Title"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'input-sm searching', 'placeholder': 'Name or title...',  'style': 'width: 100%;'}))
    idno = forms.CharField(label=_("Idno"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching manuidnos input-sm', 'placeholder': 'Shelfmark...',  'style': 'width: 100%;'}))
    typeaheads = ["countries", "cities", "libraries", "signatures", "manuidnos"]


class SearchManuForm(lilaModelForm):
    """Manuscript search form"""

    manuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                            widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))
    cmpmanuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                            widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))

    stypelist   = ModelMultipleChoiceField(queryset=None, required=False, 
                            widget=StypeWidget(attrs={'data-placeholder': 'Select multiple status types...', 'style': 'width: 100%;'}))

    country     = forms.CharField(required=False)
    country_ta  = forms.CharField(label=_("Country"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching countries input-sm', 'placeholder': 'Country...', 'style': 'width: 100%;'}))
    city        = forms.CharField(required=False)
    city_ta     = forms.CharField(label=_("City"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching cities input-sm', 'placeholder': 'City...',  'style': 'width: 100%;'}))
    libname_ta  = forms.CharField(label=_("Library"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Name of library...',  'style': 'width: 100%;'}))
    origin_ta   = forms.CharField(label=_("Origin"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching origins input-sm', 'placeholder': 'Origin (location)...',  'style': 'width: 100%;'}))
    prov        = forms.CharField(required=False)
    prov_ta     = forms.CharField(label=_("Provenance"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Provenance (location)...',  'style': 'width: 100%;'}))
    date_from   = forms.IntegerField(label=_("Date start"), required = False,
                                     widget=forms.TextInput(attrs={'placeholder': 'Starting from...',  'style': 'width: 30%;', 'class': 'searching'}))
    date_until  = forms.IntegerField(label=_("Date until"), required = False,
                                     widget=forms.TextInput(attrs={'placeholder': 'Until (including)...',  'style': 'width: 30%;', 'class': 'searching'}))
    signature   = forms.CharField(label=_("Signature"), required=False,
                            widget=forms.TextInput(attrs={'class': 'typeahead searching signatures input-sm', 
                                                          'placeholder': 'Signatures (Gryson, Clavis) using wildcards...', 'style': 'width: 100%;'}))
    signaturea  = forms.CharField(label=_("Signature"), required=False,
                            widget=forms.TextInput(attrs={'class': 'typeahead searching signatures input-sm', 
                                                          'placeholder': 'Signatures (Gryson, Clavis) using wildcards...', 'style': 'width: 100%;'}))
    signatureid = forms.CharField(label=_("Signature ID"), required=False)
    signatureaid = forms.CharField(label=_("Signature ID"), required=False)
    keyword = forms.CharField(label=_("Keyword"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching keywords input-sm', 'placeholder': 'Keyword(s)...', 'style': 'width: 100%;'}))
    kwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    projlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    srclist     = ModelMultipleChoiceField(queryset=None, required=False)
    manutype    = forms.ModelChoiceField(queryset=None, required=False, 
                widget=ManutypeWidget(attrs={'data-placeholder': 'Select a manuscript type...', 'style': 'width: 30%;', 'class': 'searching'}))
    bibrefbk    = forms.ModelChoiceField(queryset=None, required=False, 
                widget=BookWidget(attrs={'data-placeholder': 'Select a book...', 'style': 'width: 30%;', 'class': 'searching'}))
    bibrefchvs  = forms.CharField(label=_("Bible reference"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 30%;', 'placeholder': 'Use Chapter or Chapter:verse'}))
    lilalist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=AustatMultiWidget(attrs={'data-placeholder': 'Select multiple lila codes...', 'style': 'width: 100%;', 
                                                       'class': 'searching'}))
    lilacode  = forms.CharField(label=_("lila code"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 'placeholder': 'lila code. Use wildcards, e.g: *002.*, *003'}))
    collist_hist =  ModelMultipleChoiceField(queryset=None, required=False)
    collist_m =  ModelMultipleChoiceField(queryset=None, required=False)
    collist_s =  ModelMultipleChoiceField(queryset=None, required=False)
    collist_ssg =  ModelMultipleChoiceField(queryset=None, required=False)
    collection_m = forms.CharField(label=_("Collection m"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collection_s = forms.CharField(label=_("Collection s"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collection_ssg = forms.CharField(label=_("Collection ssg"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collone     = ModelChoiceField(queryset=None, required=False) #, 
    overlap    = forms.IntegerField(label=_("percentage overlap"), required=False, 
                widget=RangeSlider(attrs={'style': 'width: 30%;', 'class': 'searching', 'min': '0', 'max': '100', 'step': '1'}))
    typeaheads = ["countries", "cities", "libraries", "origins", "locations", "signatures", "keywords", "collections", 
                  "manuidnos"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Manuscript
        fields = ['name', 'library', 'idno', 'url', 'stype'] 
        widgets={'library':     forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'name':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'idno':        forms.TextInput(attrs={'class': 'typeahead searching manuidnos input-sm', 'placeholder': 'Shelfmarks using wildcards...',  'style': 'width: 100%;'}),
                 'url':         forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'stype':       forms.Select(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(SearchManuForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            # NONE of the fields are required in the SEARCH form!
            self.fields['stype'].required = False
            self.fields['name'].required = False

            self.fields['manuidlist'].queryset = Manuscript.objects.exclude(mtype='tem').order_by('idno')
            self.fields['cmpmanuidlist'].queryset = Manuscript.objects.exclude(mtype='tem').order_by('idno')
            self.fields['kwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            self.fields['projlist'].queryset = Project.objects.all().order_by('name')
            self.fields['srclist'].queryset = SourceInfo.objects.all()
            self.fields['stypelist'].queryset = FieldChoice.objects.filter(field=STATUS_TYPE).order_by("english_name")
            self.fields['lilalist'].queryset = Austat.objects.filter(code__isnull=False, moved__isnull=True, atype='acc').order_by('code')
            self.fields['bibrefbk'].queryset = Book.objects.all().order_by('idno')
            self.fields['manutype'].queryset = FieldChoice.objects.filter(field=MANUSCRIPT_TYPE).exclude(abbr='tem').order_by("english_name")

            # Set the widgets correctly
            self.fields['collist_hist'].widget = CollectionAustatWidget( attrs={'username': username, 'team_group': team_group, 'settype': 'hc',
                        'data-placeholder': 'Select multiple manuscript collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_m'].widget = CollectionManuWidget( attrs={'username': username, 'team_group': team_group, 'settype': 'pd',
                        'data-placeholder': 'Select multiple manuscript collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_s'].widget = CollectionCanwitWidget( attrs={'username': username, 'team_group': team_group,'settype': 'pd',
                        'data-placeholder': 'Select multiple manuscript collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_ssg'].widget = CollectionAustatWidget( attrs={'username': username, 'team_group': team_group,'settype': 'pd',
                        'data-placeholder': 'Select multiple manuscript collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collone'].widget = CollOneManuWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select a dataset...', 'style': 'width: 100%;', 'class': 'searching'})

            # Note: the collection filters must use the SCOPE of the collection
            self.fields['collist_hist'].queryset = Collection.get_scoped_queryset('austat', username, team_group, settype="hc")
            self.fields['collist_m'].queryset = Collection.get_scoped_queryset('manu', username, team_group)
            self.fields['collist_s'].queryset = Collection.get_scoped_queryset('sermo', username, team_group)
            self.fields['collist_ssg'].queryset = Collection.get_scoped_queryset('austat', username, team_group)

            # The CollOne information is needed for the basket (add basket to collection)
            prefix = "manu"
            # self.fields['collone'].queryset = Collection.objects.filter(type=prefix).order_by('name')
            self.fields['collone'].queryset = Collection.get_scoped_queryset(prefix, username, team_group)

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                # If there is an instance, then check if a library is specified
                library = instance.library
                if library != None:
                    # In this case: get the city and the country
                    city = library.get_city_name()
                    country = library.get_country_name()
                    if (country == None or country == "") and city != None and city != "":
                        # We have a city, but the country is not specified...
                        lstQ = []
                        lstQ.append(Q(loctype__name="country"))
                        lstQ.append(Q(relations_location=library.lcity))
                        obj = Location.objects.filter(*lstQ).first()
                        if obj != None:
                            country = obj.name
                    # Put them in the fields
                    self.fields['city_ta'].initial = city
                    self.fields['country_ta'].initial = country
                    # Also: make sure we put the library NAME in the initial
                    self.fields['libname_ta'].initial = library.name

                ## Look after origin
                #origin = instance.origin
                #self.fields['origname_ta'].initial = "" if origin == None else origin.name
        except:
            msg = oErr.get_error_message()
            oErr.DoError("SearchManuForm-init")
        return None


class ColwitForm(lilaModelForm):

    collone = ModelChoiceField(queryset=None, required=False)
    
    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Colwit
        fields = ['codhead', 'collection', 'descr', 'notes']
        widgets={'descr':       forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 'notes':       forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 # 'collection':  CollOneHistWidget(attrs={'data-placeholder': 'Select a collection...', 'style': 'width: 100%;', 'class': 'searching'}),
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ColwitForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)

            # Some fields are not required
            self.fields['codhead'].required = False
            self.fields['collection'].required = False
            self.fields['descr'].required = False
            self.fields['notes'].required = False
            self.fields['collone'].required = False

            self.fields['collone'].widget = CollOneHistWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select a collection...', 'style': 'width: 100%;', 'class': 'searching'})

            prefix = "austat"
            qs = Collection.get_scoped_queryset(prefix, username, team_group, settype="hc")
            self.fields['collone'].queryset = qs

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']

                # If there is an instance, then check the author specification
                # sAuthor = "" if not instance.author else instance.author.name
                if not instance.collection is None:
                    self.fields['collone'].initial = instance.collection.id
                    self.fields['collone'].widget.initial = instance.collection.id

            iStop = 1
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ColwitForm-init")
        return None


class CanwitForm(lilaModelForm):
    # Helper fields for Canwit fields
    stypelist   = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=StypeWidget(attrs={'data-placeholder': 'Select multiple status types...', 'style': 'width: 100%;'}))
    authorname  = forms.CharField(label=_("Author"), required=False, 
                    widget=forms.TextInput(attrs={'class': 'typeahead searching authors input-sm', 'placeholder': 'Authors using wildcards...', 'style': 'width: 100%;'}))
    authorlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=AuthorWidget(attrs={'data-placeholder': 'Select multiple authors...', 'style': 'width: 100%;', 'class': 'searching'}))
    authortype  = forms.ChoiceField(label=_("Author type"), required=False, 
                widget=forms.Select(attrs={'class': 'input-sm', 'placeholder': 'Type of Author...',  'style': 'width: 100%;', 'tdstyle': 'width: 150px;'}))
    manuidno    = forms.CharField(label=_("Manuscript"), required=False,
                    widget=forms.TextInput(attrs={'class': 'typeahead searching manuidnos input-sm', 'placeholder': 'Shelfmarks using wildcards...', 'style': 'width: 100%;'}))
    manuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))
    manutype    = forms.ModelChoiceField(queryset=None, required=False, 
                widget=ManutypeWidget(attrs={'data-placeholder': 'Select a manuscript type...', 'style': 'width: 30%;', 'class': 'searching'}))
    manu = forms.ModelChoiceField(queryset=None, required=False,
                widget=ManuidOneWidget(attrs={'data-placeholder': 'Select a manuscript...', 'style': 'width: 30%;', 'class': 'searching'}))
    signature   = forms.CharField(label=_("Signature"), required=False,
                    widget=forms.TextInput(attrs={'class': 'typeahead searching srmsignatures input-sm', 'placeholder': 'Signatures (Gryson, Clavis) using wildcards...', 'style': 'width: 100%;'}))
    signature_a = forms.CharField(label=_("Signature"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching signatures input-sm', 'placeholder': 'Signature/code (Gryson, Clavis)...', 'style': 'width: 100%;'}))
    signatureid = forms.CharField(label=_("Signature ID"), required=False)
    siglist_m = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=ManualSignatureWidget(attrs={'data-placeholder': 'Select multiple signatures (Gryson, Clavis)...', 'style': 'width: 100%;', 'class': 'searching'}))
    keyword = forms.CharField(label=_("Keyword"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching keywords input-sm', 'placeholder': 'Keyword(s)...', 'style': 'width: 100%;'}))
    kwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    ukwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple user-keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    projlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    feastlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=FeastWidget(attrs={'data-placeholder': 'Select multiple feasts...', 'style': 'width: 100%;', 'class': 'searching'}))
    superlist = ModelMultipleChoiceField(queryset=None, required=False,
                widget=CanwitSuperAddOnlyWidget(attrs={'data-placeholder': 'Add links with the green "+" sign...', 
                                                  'placeholder': 'Linked Fons materialis...', 'style': 'width: 100%;', 'class': 'searching'}))
    formalislist = ModelMultipleChoiceField(queryset=None, required=False,
                widget=CanwitSuperAddOnlyWidget(attrs={'data-placeholder': 'Add links with the green "+" sign...', 
                                                  'placeholder': 'Linked Fons formalis...', 'style': 'width: 100%;', 'class': 'searching'}))
    lilalist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=AustatMultiWidget(attrs={'data-placeholder': 'Select multiple lila codes...', 'style': 'width: 100%;', 
                                                       'class': 'searching'}))
    #lilacode  = forms.CharField(label=_("lila code"), required=False, 
    #            widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 'placeholder': 'lila code. Use wildcards, e.g: *002.*, *003'}))
    bibreflist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=BibrefAddonlyWidget(attrs={'data-placeholder': 'Use the "+" sign to add references...', 'style': 'width: 100%;', 'class': 'searching'}))
    bibrefbk    = forms.ModelChoiceField(queryset=None, required=False, 
                widget=BookWidget(attrs={'data-placeholder': 'Select a book...', 'style': 'width: 30%;', 'class': 'searching'}))
    bibrefchvs  = forms.CharField(label=_("Bible reference"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 30%;', 'placeholder': 'Use Chapter or Chapter:verse'}))
    sermonlist = forms.CharField(label=_("List of sermon IDs"), required=False)

    # Free text searching
    free_term  = forms.CharField(label=_("Term to look for"), required=False, 
                widget=forms.Textarea(attrs={'rows': 1, 'style': 'height: 40px; width: 30%;', 
                                             'class': 'searching', 'placeholder': 'Term to look for (use * or #)'}))
                #widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 30%;', 'placeholder': 'Term to look for (use * or #)'}))
    free_include = forms.ModelMultipleChoiceField(queryset=None, required=False, 
                widget=FreeWidget(attrs={'data-placeholder': 'May occur in any of...', 'style': 'width: 35%;', 'class': 'searching'}))
    free_exclude = forms.ModelMultipleChoiceField(queryset=None, required=False, 
                widget=FreeWidget(attrs={'data-placeholder': 'Must NOT occur in...', 'style': 'width: 30%;', 'class': 'searching'}))

    # Specifically for searching...
    srch_title = forms.CharField(required=False, 
                widget=forms.TextInput(attrs={'class': 'searching', 'placeholder': 'Title (use wildcards)...', 'style': 'width: 100%;'}))
    srch_sectiontitle = forms.CharField(required=False, 
                widget=forms.TextInput(attrs={'class': 'searching', 'placeholder': 'Section title (use wildcards)...', 'style': 'width: 100%;'}))

    collist_m =  ModelMultipleChoiceField(queryset=None, required=False)
    collist_s =  ModelMultipleChoiceField(queryset=None, required=False)
    collist_ssg =  ModelMultipleChoiceField(queryset=None, required=False)
    collist_hist =  ModelMultipleChoiceField(queryset=None, required=False)
    collection_m = forms.CharField(label=_("Collection m"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collection_s = forms.CharField(label=_("Collection s"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collection_ssg = forms.CharField(label=_("Collection ssg"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collone     = ModelChoiceField(queryset=None, required=False) #, 
                # widget=CollOneSermoWidget(attrs={'data-placeholder': 'Select one collection...', 'style': 'width: 100%;', 'class': 'searching'}))
   
    # Fields for searching sermons through their containing manuscripts
    country     = forms.CharField(required=False)
    country_ta  = forms.CharField(label=_("Country"), required=False, 
                    widget=forms.TextInput(attrs={'class': 'typeahead searching countries input-sm', 'placeholder': 'Country...', 'style': 'width: 100%;'}))
    city        = forms.CharField(required=False)
    city_ta     = forms.CharField(label=_("City"), required=False, 
                    widget=forms.TextInput(attrs={'class': 'typeahead searching cities input-sm', 'placeholder': 'City...',  'style': 'width: 100%;'}))
    library     = forms.CharField(required=False)
    libname_ta  = forms.CharField(label=_("Library"), required=False, 
                    widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Name of library...',  'style': 'width: 100%;'}))
    origin      = forms.CharField(required=False)
    origin_ta   = forms.CharField(label=_("Origin"), required=False, 
                    widget=forms.TextInput(attrs={'class': 'typeahead searching origins input-sm', 'placeholder': 'Origin (location)...',  'style': 'width: 100%;'}))
    autype      = forms.ChoiceField(label=_("Author certainty type"), required=False,
                     widget=forms.Select(attrs={'class': 'input-sm', 'placeholder': 'Author certainty level...',  'style': 'width: 100%;'}))
    prov        = forms.CharField(required=False)
    prov_ta     = forms.CharField(label=_("Provenance"), required=False, 
                    widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Provenance (location)...',  'style': 'width: 100%;'}))
    date_from   = forms.IntegerField(label=_("Date start"), required = False,
                    widget=forms.TextInput(attrs={'placeholder': 'Starting from...',  'style': 'width: 30%;', 'class': 'searching'}))
    date_until  = forms.IntegerField(label=_("Date until"), required = False,
                    widget=forms.TextInput(attrs={'placeholder': 'Until (including)...',  'style': 'width: 30%;', 'class': 'searching'}))
    typeaheads = ["authors", "manuidnos", "signatures", "keywords", "countries", "cities", "libraries", "origins", 
                  "locations", "cwftexts", "cwftrans"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Canwit
        fields = ['title', 'subtitle', 'author', 'locus', 'ftext', 'ftrans', 'quote', 'mtype', 'lilacode', 'caput',
                 'feast', 'bibnotes', 'additional', 'note', 'stype', 'sectiontitle', 'postscriptum']
        widgets={'title':       forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 'sectiontitle': forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'subtitle':    forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'author':      AuthorOneWidget(attrs={'data-placeholder': 'Select one author...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'locus':       forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'lilacode':    forms.TextInput(attrs={'placeholder': 'The number/code of this particular Canonical Witness...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'caput':       forms.TextInput(attrs={'placeholder': 'Enter the Caput / Capita as a decimal number...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'bibnotes':    forms.TextInput(attrs={'placeholder': 'Bibliography notes...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'feast':       FeastOneWidget(attrs={'data-placeholder': 'Select one feast...', 'style': 'width: 100%;', 'class': 'searching'}),

                 'ftext':       forms.TextInput(attrs={'class': 'typeahead searching cwftexts input-sm', 'placeholder': 'Full text...', 'style': 'width: 100%;'}),
                 'ftrans':      forms.TextInput(attrs={'class': 'typeahead searching cwftrans input-sm', 'placeholder': 'Translation...', 'style': 'width: 100%;'}),
                 'stype':       forms.Select(attrs={'style': 'width: 100%;'}),

                 # larger areas
                 'postscriptum': forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 'quote':       forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 'additional':  forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 'note':        forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CanwitForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)

            # Some fields are not required
            self.fields['autype'].required = False
            init_choices(self, 'autype', CERTAINTY_TYPE, bUseAbbr=True)
            self.fields['manu'].required = False
            self.fields['stype'].required = False
            self.fields['mtype'].required = False
            self.fields['authortype'].required = False
            
            # NEW 493
            #self.fields['atype'].required = False

            # Choice field initialization
            self.fields['authortype'].choices = AUTHOR_TYPE

            self.fields['manu'].queryset = Manuscript.objects.all().order_by('idno')
            self.fields['stypelist'].queryset = FieldChoice.objects.filter(field=STATUS_TYPE).order_by("english_name")
            self.fields['manuidlist'].queryset = Manuscript.objects.filter(mtype='man').order_by('idno')
            self.fields['authorlist'].queryset = Author.objects.all().order_by('name')
            self.fields['feastlist'].queryset = Feast.objects.all().order_by('name')
            self.fields['projlist'].queryset = profile.projects.all().order_by('name').distinct()
            self.fields['projlist'].widget.queryset = self.fields['projlist'].queryset
            self.fields['kwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            self.fields['ukwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            if user_is_in_team(username, team_group):
                self.fields['kwlist'].widget.is_team = True
                self.fields['ukwlist'].widget.is_team = True
            else:
                self.fields['kwlist'].widget.is_team = False
                self.fields['ukwlist'].widget.is_team = False

            # Note: what we show the user is the set of GOLD-signatures
            self.fields['siglist_m'].queryset = CanwitSignature.objects.all().order_by('code')

            # The available Sermondescr-Equal list
            self.fields['superlist'].queryset = CanwitAustat.objects.none()
            self.fields['formalislist'].queryset = CanwitAustat.objects.none()
            self.fields['lilalist'].queryset = Austat.objects.filter(code__isnull=False, moved__isnull=True, atype='acc').order_by('code')
            self.fields['bibrefbk'].queryset = Book.objects.all().order_by('idno')

            self.fields['manutype'].queryset = FieldChoice.objects.filter(field=MANUSCRIPT_TYPE).exclude(abbr='tem').order_by("english_name")

            self.fields['free_include'].queryset = Free.objects.filter(main="Canwit").order_by('name')
            self.fields['free_exclude'].queryset = Free.objects.filter(main="Canwit").order_by('name')
            self.fields['free_include'].widget.main = "Canwit"
            self.fields['free_exclude'].widget.main = "Canwit"

            # Some lists need to be initialized to NONE:
            self.fields['bibreflist'].queryset = Daterange.objects.none()

            self.fields['bibreflist'].widget.addonly = True

            # Set the widgets correctly
            self.fields['collist_m'].widget = CollectionManuWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select multiple manuscript collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_s'].widget = CollectionCanwitWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select multiple sermon manifestation collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_ssg'].widget = CollectionAustatWidget( attrs={'username': username, 'team_group': team_group, 'settype': 'pd',
                        'data-placeholder': 'Select multiple Authoritative statement collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_hist'].widget = CollectionAustatWidget( attrs={'username': username, 'team_group': team_group, 'settype': 'hc',
                        'data-placeholder': 'Select multiple historical collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collone'].widget = CollOneSermoWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select a dataset...', 'style': 'width: 100%;', 'class': 'searching'})

            # Note: the collection filters must use the SCOPE of the collection
            self.fields['collist_m'].queryset = Collection.get_scoped_queryset('manu', username, team_group)
            self.fields['collist_s'].queryset = Collection.get_scoped_queryset('sermo', username, team_group)
            self.fields['collist_ssg'].queryset = Collection.get_scoped_queryset('austat', username, team_group, settype='pd') 
            self.fields['collist_hist'].queryset = Collection.get_scoped_queryset('austat', username, team_group, settype='hc')

            # The CollOne information is needed for the basket (add basket to collection)
            prefix = "sermo"
            # self.fields['collone'].queryset = Collection.objects.filter(type=prefix).order_by('name')
            self.fields['collone'].queryset = Collection.get_scoped_queryset(prefix, username, team_group)

            # For searching/listing
            self.fields['mtype'].initial = "man"

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                # If there is an instance, then check the author specification
                sAuthor = "" if not instance.author else instance.author.name

                if instance.get_manuscript():
                    self.fields['manu'].queryset = Manuscript.objects.filter(id=instance.get_manuscript().id)

                self.fields['authorname'].initial = sAuthor
                self.fields['authorname'].required = False
                # Set initial values for lists, where appropriate. NOTE: need to have the initial ID values
                self.fields['kwlist'].initial = [x.pk for x in instance.keywords.all().order_by('name')]
                self.fields['ukwlist'].initial = [x.keyword.pk for x in instance.canwit_userkeywords.filter(profile=profile).order_by('keyword__name')]
                self.fields['projlist'].initial = [x.pk for x in instance.projects.all().order_by('name')] 

                # Determine the initial collections
                self.fields['collist_m'].initial = [x.pk for x in instance.collections.filter(type='manu').order_by('name')]
                self.fields['collist_s'].initial = [x.pk for x in instance.collections.filter(type='sermo').order_by('name')]
                self.fields['collist_ssg'].initial = [x.pk for x in instance.collections.filter(type='austat').order_by('name')]

                # Note: what we *show* are the signatures that have actually been copied -- the SERMON signatures
                # self.fields['siglist'].initial = [x.pk for x in instance.signatures.all().order_by('-editype', 'code')]
                self.fields['siglist_m'].initial = [x.pk for x in instance.canwitsignatures.all().order_by('-editype', 'code')]

                # Note: this is the list of links between Canwit-Austat: fons materialis
                self.fields['superlist'].initial = [x.pk for x in instance.canwit_austat.filter(fonstype='mat').order_by('linktype', 'canwit__author__name', 'canwit__siglist')]
                # Make sure the initial superlist captures exactly what we have
                self.fields['superlist'].queryset = CanwitAustat.objects.filter(Q(id__in = self.fields['superlist'].initial))

                # Note: this is the list of links between Canwit-Austat: fons formalis
                self.fields['formalislist'].initial = [x.pk for x in instance.canwit_austat.filter(fonstype='for').order_by('linktype', 'canwit__author__name', 'canwit__siglist')]
                # Make sure the initial formalislist captures exactly what we have
                self.fields['formalislist'].queryset = CanwitAustat.objects.filter(Q(id__in = self.fields['formalislist'].initial))

                self.fields['bibreflist'].initial = [x.pk for x in instance.canwitbibranges.all()]
                self.fields['bibreflist'].queryset = BibRange.objects.filter(id__in=self.fields['bibreflist'].initial)

                self.fields['autype'].initial = instance.autype

                iStop = 1
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CanwitForm-init")
        return None


class CodheadForm(lilaModelForm):
    # Helper fields for Codhead fields
    manuidno    = forms.CharField(label=_("Manuscript"), required=False,
                    widget=forms.TextInput(attrs={'class': 'typeahead searching manuidnos input-sm', 'placeholder': 'Shelfmarks using wildcards...', 'style': 'width: 100%;'}))
    manuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))
    manu = forms.ModelChoiceField(queryset=None, required=False,
                widget=ManuidOneWidget(attrs={'data-placeholder': 'Select a manuscript...', 'style': 'width: 30%;', 'class': 'searching'}))

    # Specifically for searching...
    srch_title = forms.CharField(required=False, 
                widget=forms.TextInput(attrs={'class': 'searching', 'placeholder': 'Title (use wildcards)...', 'style': 'width: 100%;'}))

    typeaheads = ["manuidnos"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Codhead
        fields = ['title', 'locus']
        widgets={'title':       forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 'locus':       forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CodheadForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)

            # Some fields are not required
            self.fields['manu'].required = False
            
            self.fields['manu'].queryset = Manuscript.objects.all().order_by('idno')
            self.fields['manuidlist'].queryset = Manuscript.objects.filter(mtype='man').order_by('idno')

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']

                if instance.get_manuscript():
                    self.fields['manu'].queryset = Manuscript.objects.filter(id=instance.get_manuscript().id)

                iStop = 1
        except:
            msg = oErr.get_error_message()
            oErr.DoError("CodheadForm-init")
        return None


class ColForm(forms.Form):
    """Allow selection of just one collection"""

    collection = ModelChoiceField(queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        self.username = kwargs.pop('username', "")
        self.team_group = kwargs.pop('team_group', "")
        self.userplus = kwargs.pop('userplus', "")
        # Start by executing the standard handling
        super(ColForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)

            self.fields['collection'].widget = CollOneHistWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select a collection...', 'style': 'width: 100%;', 'class': 'searching'})
            prefix = "austat"
            self.fields['collection'].queryset = Collection.get_scoped_queryset(prefix, username, team_group, settype="hc")
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ColForm-init")
        return None


class GenreForm(forms.ModelForm):
    """Genre editing and searching"""

    genre_ta = forms.CharField(label=_("Genre"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching genres input-sm', 'placeholder': 'Genre(s)...', 'style': 'width: 100%;'}))
    genrelist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=GenreWidget(attrs={'data-placeholder': 'Select multiple genres...', 'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = ["genres"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Genre
        fields = ['name', 'description']
        widgets={'name':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'description': forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'Comments on this genre...'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(GenreForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['name'].required = False
            self.fields['description'].required = False

            self.fields['genrelist'].queryset = Genre.objects.all().order_by('name')

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
        except:
            msg = oErr.get_error_message()
            oErr.DoError("GenreForm/init")


class AuworkForm(forms.ModelForm):
    """Auwork editing and searching"""

    work_ta = forms.CharField(label=_("Work"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching works input-sm', 'placeholder': 'Work(s)...', 'style': 'width: 100%;'}))
    worklist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuworkWidget(attrs={'data-placeholder': 'Select multiple works...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Auwork
        fields = ['key', 'work', 'full']
        widgets={'key':     forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'work':    forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'Work...'}),
                 'full':    forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'Full description...'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(AuworkForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['key'].required = False
            self.fields['work'].required = False
            self.fields['full'].required = False

            self.fields['worklist'].queryset = Auwork.objects.all().order_by('key')

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
        except:
            msg = oErr.get_error_message()
            oErr.DoError("AuworkForm/init")


class KeywordForm(forms.ModelForm):
    """Keyword list"""

    keyword_ta = forms.CharField(label=_("Keyword"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching keywords input-sm', 'placeholder': 'Keyword(s)...', 'style': 'width: 100%;'}))
    kwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = ["keywords"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Keyword
        fields = ['name', 'visibility', 'description']
        widgets={'name':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'visibility':  forms.Select(attrs={'class': 'input-sm', 'placeholder': 'Visibility type...',  'style': 'width: 100%;'}),
                 'description': forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'Comments on this keyword...'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(KeywordForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        self.fields['visibility'].required = False
        self.fields['description'].required = False
        self.fields['kwlist'].queryset = Keyword.objects.all().order_by('name')
        # Initialize choices for linktype
        init_choices(self, 'vistype', VISIBILITY_TYPE, bUseAbbr=True, use_helptext=False)
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            self.fields['visibility'].initial = instance.visibility


class UserKeywordForm(forms.ModelForm):
    """User Keyword list"""

    profilelist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProfileWidget(attrs={'data-placeholder': 'Select multiple users...', 'style': 'width: 100%;', 'class': 'searching'}))
    kwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = UserKeyword
        fields = ['keyword', 'profile', 'type']
        widgets={'keyword': KeywordOneWidget(attrs={'data-placeholder': 'Select one keyword...', 'style': 'width: 100%;'}),
                 'profile': ProfileOneWidget(attrs={'data-placeholder': 'Select one user profile...', 'style': 'width: 100%;'}),
                 'type':    forms.Select(attrs={'class': 'input-sm', 'placeholder': 'Item type...',  'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(UserKeywordForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['keyword'].required = False
        self.fields['profile'].required = False
        self.fields['type'].required = False

        self.fields['kwlist'].queryset = Keyword.objects.all().order_by('name')
        self.fields['profilelist'].queryset = Profile.objects.all().order_by('user__username')
        # Initialize choices for the type
        init_choices(self, 'type', COLLECTION_TYPE, bUseAbbr=True, use_helptext=False)
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            self.fields['keyword'].initial = instance.keyword
            self.fields['profile'].initial = instance.profile
            self.fields['type'].initial = instance.type


class ProvenanceForm(forms.ModelForm):
    """Provenance list"""

    manuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))
    location_ta = forms.CharField(label=_("Location"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Location...',  'style': 'width: 100%;'}))
    locationlist = ModelMultipleChoiceField(queryset=None, required=False,
                widget=LocationWidget(attrs={'data-placeholder': 'Location...', 'style': 'width: 100%;'}))
    typeaheads = ["locations"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Provenance
        fields = ['name', 'location']   # , 'note'
        widgets={'name':    forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching', 'placeholder': 'Name for this provenance'}),
                 'location': LocationOneWidget(attrs={'data-placeholder': 'Select one location...', 'style': 'width: 100%;'}),
                 #'note':    forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                 #                                     'class': 'searching', 'placeholder': 'Notes on this provenance...'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ProvenanceForm, self).__init__(*args, **kwargs)

        # Some fields are not required
        self.fields['name'].required = False
        self.fields['location'].required = False
        # self.fields['note'].required = False
        self.fields['location'].required = False
        self.fields['location_ta'].required = False
        self.fields['locationlist'].queryset = Location.objects.all().order_by('loctype__level', 'name')
        self.fields['manuidlist'].queryset = Manuscript.objects.filter(mtype='man').order_by('idno')

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            

class ProvenanceCodForm(forms.ModelForm):
    """ProvenanceCod item"""

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = ProvenanceCod
        fields = ['note']
        widgets={'note':    forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                            'class': 'searching', 'placeholder': 'Notes on this provenance...'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ProvenanceCodForm, self).__init__(*args, **kwargs)

        # Some fields are not required
        self.fields['note'].required = False

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            

class ProvenanceManForm(forms.ModelForm):
    """ProvenanceMan item"""

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = ProvenanceMan
        fields = ['note']
        widgets={'note':    forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'Notes on this provenance...'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ProvenanceManForm, self).__init__(*args, **kwargs)

        # Some fields are not required
        self.fields['note'].required = False

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            

class ProfileForm(forms.ModelForm):
    """Profile list and details"""

    projlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    deflist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Profile
        fields = ['user', 'ptype', 'affiliation']
        widgets={'user':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}),
                 'ptype':       forms.Select(attrs={'class': 'input-sm', 'placeholder': 'User profile status...',  'style': 'width: 100%;'}),
                 'affiliation': forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                                                      'class': 'searching', 'placeholder': 'List all affiliation details...'}),
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ProfileForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['user'].required = False
            self.fields['ptype'].required = False
            self.fields['affiliation'].required = False

            # Initialize a queryset for projlist and deflist
            self.fields['projlist'].queryset = Project.objects.all().order_by('name')
            self.fields['deflist'].queryset = Project.objects.all().order_by('name')

            # Initialize choices for linktype
            init_choices(self, 'ptype', PROFILE_TYPE, bUseAbbr=True, use_helptext=False)
            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                self.fields['ptype'].initial = instance.ptype
                self.fields['user'].initial = instance.user
                self.fields['user'].queryset = User.objects.filter(id=instance.user.id)

                self.fields['deflist'].queryset = instance.projects.all().order_by('name')
                self.fields['deflist'].widget.queryset = self.fields['deflist'].queryset

                self.fields['projlist'].initial = [x.pk for x in instance.projects.all().order_by('name')]
                # self.fields['deflist'].initial = [x.pk for x in instance.projects.filter(status="incl").order_by('name')]
                self.fields['deflist'].initial = [x.project.pk for x in instance.project_editor.filter(status="incl").order_by('project__name')]
        except:
            msg = oErr.get_error_message()
            oErr.DoError("ProfileForm-init")
        # We are okay
        return None

    def clean_user(self):
        data = self.cleaned_data.get("user")
        if data == None:
            data = self.fields['user'].initial
        return data
    

class ProjectForm(forms.ModelForm):
    """Project list"""

    project_ta = forms.CharField(label=_("Project"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching projects input-sm', 'placeholder': 'Project(s)...', 'style': 'width: 100%;'}))
    projlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = ["projects"]
    
    # Typeahead werkt niet
    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Project
        fields = ['name']
        widgets={'name':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ProjectForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        #self.fields['prjlist'].queryset = Project.objects.all().order_by('name') 
        self.fields['projlist'].queryset = Project.objects.all().order_by('name').distinct() 
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']    
    

class CollectionForm(lilaModelForm):
    """Collection list"""

    collection_ta = forms.CharField(label=_("Collection"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=CollectionWidget(attrs={'data-placeholder': 'Select multiple collections...', 'style': 'width: 100%;', 'class': 'searching'}))
    collist_m =  ModelMultipleChoiceField(queryset=None, required=False)
    collist_s =  ModelMultipleChoiceField(queryset=None, required=False, 
                widget=CollectionCanwitWidget(attrs={'data-placeholder': 'Select multiple sermon collections...', 'style': 'width: 100%;', 'class': 'searching'}))
    collist_ssg =  ModelMultipleChoiceField(queryset=None, required=False, 
                widget=CollectionAustatWidget(attrs={'data-placeholder': 'Select multiple super sg collections...', 'style': 'width: 100%;', 'class': 'searching'}))
    collone     = ModelChoiceField(queryset=None, required=False)   #, 
    ownlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProfileWidget(attrs={'data-placeholder': 'Select multiple profiles...', 'style': 'width: 100%;', 'class': 'searching'}))
    litlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=LitrefColWidget(attrs={'data-placeholder': 'Select multiple literature references...', 'style': 'width: 100%;', 'class': 'searching'}))
    projlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    # Author for collection
    newauthor = ModelChoiceField(queryset=None, required=False,
                widget=AuthorOneWidget(attrs={'data-placeholder': 'Select one author...', 'style': 'width: 100%;', 'class': 'searching'}))
    # SSG-specific
    ssgstypelist   = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=StypeWidget(attrs={'data-placeholder': 'Select multiple status types...', 'style': 'width: 100%;'}))
    ssgauthorname = forms.CharField(label=_("Author"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching authors input-sm', 'placeholder': 'Author...', 'style': 'width: 100%;'}))
    ssgauthorlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuthorWidget(attrs={'data-placeholder': 'Select multiple authors...', 'style': 'width: 100%;', 'class': 'searching'}))
    ssgcode     = forms.CharField(label=_("lila code"), required=False,
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 
                                    'placeholder': 'lila code. Use wildcards, e.g: *002.*, *003'}))
    ssglilalist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=AustatMultiWidget(attrs={'data-placeholder': 'Select multiple lila codes...', 'style': 'width: 100%;', 
                                                       'class': 'searching'}))
    ssgkwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    ssgnumber   = forms.CharField(label=_("Author Number"), required=False,
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 'data-placeholder': 'Author number'}))
    ssgincipit  = forms.CharField(label=_("Incipit"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching asftexts input-sm', 'placeholder': 'Incipit...', 'style': 'width: 100%;'}))
    ssgexplicit = forms.CharField(label=_("Explicit"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching asftrans input-sm', 'placeholder': 'Explicit...', 'style': 'width: 100%;'}))
    ssgstype    = forms.ChoiceField(label=_("Stype"), required=False, widget=forms.Select(attrs={'style': 'width: 100%;'}))
    
    
    # SERMON-specific
    sermoincipit  = forms.CharField(label=_("Incipit"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching asftexts input-sm', 'placeholder': 'Incipit...', 'style': 'width: 100%;'}))
    sermoexplicit = forms.CharField(label=_("Explicit"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching asftrans input-sm', 'placeholder': 'Explicit...', 'style': 'width: 100%;'}))
    sermotitle  = forms.CharField(label=_("Title"), required=False,
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 'placeholder': 'Title'}))
    sermofeast  = forms.CharField(label=_("Feast"), required=False,
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 'placeholder': 'Feast'}))
    bibrefbk    = forms.ModelChoiceField(queryset=None, required=False, 
                widget=BookWidget(attrs={'data-placeholder': 'Select a book...', 'style': 'width: 30%;', 'class': 'searching'}))
    bibrefchvs  = forms.CharField(label=_("Bible reference"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 30%;', 'placeholder': 'Use Chapter or Chapter:verse'}))
    sermonote  = forms.CharField(label=_("Note"), required=False,
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 'placeholder': 'Note'}))
    sermoauthorname = forms.CharField(label=_("Author"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching authors input-sm', 'placeholder': 'Author...', 'style': 'width: 100%;'}))

    sermokwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    sermostypelist   = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=StypeWidget(attrs={'data-placeholder': 'Select multiple status types...', 'style': 'width: 100%;'}))
    sermoauthorlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuthorWidget(attrs={'data-placeholder': 'Select multiple authors...', 'style': 'width: 100%;', 'class': 'searching'}))
    # MANUSCRIPT-specific
    manuidno    = forms.CharField(label=_("Manuscript"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching manuidnos input-sm', 'placeholder': 'Shelfmarks using wildcards...', 'style': 'width: 100%;'}))
    libname_ta  = forms.CharField(label=_("Library"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Name of library...',  'style': 'width: 100%;'}))
    prov_ta     = forms.CharField(label=_("Provenance"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Provenance (location)...',  'style': 'width: 100%;'}))
    origin_ta   = forms.CharField(label=_("Origin"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching origins input-sm', 'placeholder': 'Origin (location)...',  'style': 'width: 100%;'}))
    date_from   = forms.IntegerField(label=_("Date start"), required = False,
                widget=forms.TextInput(attrs={'placeholder': 'Starting from...',  'style': 'width: 30%;', 'class': 'searching'}))
    date_until  = forms.IntegerField(label=_("Date until"), required = False,
                widget=forms.TextInput(attrs={'placeholder': 'Until (including)...',  'style': 'width: 30%;', 'class': 'searching'}))
    manuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))
    manukwlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    manustypelist   = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=StypeWidget(attrs={'data-placeholder': 'Select multiple status types...', 'style': 'width: 100%;'}))

    typeaheads = ["collections", "authors", "signatures", "asftexts", "asftrans",
                  "countries", "cities", "libraries", "origins", "manuidnos"]


    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Collection
        fields = ['name', 'owner', 'descrip', 'readonly', 'url', 'lilacode', 'origin', 'date', 'type', 'scope', 'settype']
        widgets={'name':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'}), 
                 'owner':       forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'descrip':     forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 'class': 'searching'}),
                 'readonly':    forms.CheckboxInput(),
                 'url':         forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'lilacode':    forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'date':        forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'origin':      forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'scope':       forms.Select(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CollectionForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)

            # Get the prefix
            prefix = "any" if 'prefix' not in kwargs else kwargs['prefix']
            # Some fields are not required
            self.fields['name'].required = False
            self.fields['owner'].required = False
            self.fields['descrip'].required = False
            self.fields['readonly'].required = False
            self.fields['type'].required = False
            self.fields['settype'].required = False
            self.fields['scope'].required = False
            self.fields['url'].required = False
            self.fields['collone'].required = False

            self.fields['bibrefbk'].queryset = Book.objects.all().order_by('idno')

            # Set the widgets correctly
            self.fields['collist_m'].widget = CollectionManuWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select multiple manuscript collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_s'].widget = CollectionCanwitWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select multiple manuscript collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_ssg'].widget = CollectionAustatWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select multiple manuscript collections...', 'style': 'width: 100%;', 'class': 'searching'})

            # Author
            self.fields['newauthor'].queryset = Author.objects.all().order_by('name')

            # Project:
            # self.fields['projlist'].queryset = Project.objects.all().order_by('name').distinct()
            if profile is None:
                self.fields['projlist'].queryset = Project.objects.all().order_by('name').distinct()
            else:
                self.fields['projlist'].queryset = profile.projects.all().order_by('name').distinct()
            self.fields['projlist'].widget.queryset = self.fields['projlist'].queryset

            # SSG section
            self.fields['ssgstypelist'].queryset = FieldChoice.objects.filter(field=STATUS_TYPE).order_by("english_name")
            self.fields['ssgauthorlist'].queryset = Author.objects.all().order_by('name') 
            self.fields['ssglilalist'].queryset = Austat.objects.filter(code__isnull=False, moved__isnull=True, atype='acc').order_by('code') 
            self.fields['ssgkwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)

            # S section
            self.fields['sermokwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            self.fields['sermostypelist'].queryset = FieldChoice.objects.filter(field=STATUS_TYPE).order_by("english_name")
            self.fields['sermoauthorlist'].queryset = Author.objects.all().order_by('name')

            # M section
            self.fields['manuidlist'].queryset = Manuscript.objects.filter(mtype='man').order_by('idno')
            self.fields['manukwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            self.fields['manustypelist'].queryset = FieldChoice.objects.filter(field=STATUS_TYPE).order_by("english_name")

            if prefix == "priv" or prefix == "publ":
                self.fields['collist'].widget = CollectionWidget( attrs={'username': username, 'team_group': team_group, 'settype': "pd", "scope": prefix,
                            'data-placeholder': 'Select multiple datasets...', 'style': 'width: 100%;', 'class': 'searching'})
            elif prefix == "hist":
                self.fields['collist'].widget = CollectionWidget( attrs={'username': username, 'team_group': team_group,'settype': "hc",
                            'data-placeholder': 'Select multiple historical collections...', 'style': 'width: 100%;', 'class': 'searching'})
            else:
                self.fields['collist'].widget = CollectionWidget( attrs={'username': username, 'team_group': team_group,
                            'data-placeholder': 'Select multiple collections...', 'style': 'width: 100%;', 'class': 'searching'})

            self.fields['litlist'].queryset = LitrefCol.objects.all().order_by('reference__full', 'pages').distinct()

            if prefix == "any":
                all_collections = Collection.objects.all().order_by('name')
                self.fields['collist'].queryset = all_collections
                self.fields['collone'].queryset = all_collections

            elif prefix == "hist":
                # Historical collections
                type = "austat"
                settype = "hc"
                self.fields['collist'].queryset = Collection.objects.filter(type=type, settype=settype).order_by('name')
                self.fields['collone'].queryset = Collection.objects.filter(type=type, settype=settype).order_by('name')
                # Set the initial type
                self.fields['type'].initial = type
                self.initial['type'] = type
                # Obligatory values for the querysets of m/s/sg/ssg
                self.fields['collist_m'].queryset = Collection.objects.none()
                self.fields['collist_s'].queryset = Collection.objects.none()
                self.fields['collist_ssg'].queryset = Collection.objects.none()
            else:
                type = prefix.split("-")[0]
                # self.fields['collist'].queryset = Collection.objects.filter(type=type).order_by('name')
                self.fields['collist'].queryset = Collection.get_scoped_queryset('', username, team_group)
                self.fields['collone'].queryset = Collection.objects.filter(type=type).order_by('name')

                # Note: the collection filters must use the SCOPE of the collection
                self.fields['collist_m'].queryset = Collection.get_scoped_queryset('manu', username, team_group)
                self.fields['collist_s'].queryset = Collection.get_scoped_queryset('sermo', username, team_group)
                self.fields['collist_ssg'].queryset = Collection.get_scoped_queryset('austat', username, team_group)
            

                # Set the initial type - provided it fits
                if self.initial.get("type", "") == "":
                    self.fields['type'].initial = type
                    self.initial['type'] = type
                else:
                    # Make sure to retain its value
                    self.fields['type'].initial = self.initial.get("type", "")

            self.fields['ownlist'].queryset = Profile.objects.all()
            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                self.fields['litlist'].initial = [x.pk for x in instance.collection_litrefcols.all().order_by('reference__full', 'pages')]
                self.fields['projlist'].initial = [x.pk for x in instance.projects.all().order_by('name')] # zie verderop

                # If there is an instance, then check the author specification
                if not instance.author is None:
                    self.fields['newauthor'].initial = instance.author.id
                    self.fields['newauthor'].widget.initial = instance.author.id


        except:
            msg = oErr.get_error_message()
            oErr.DoError("CollectionForm/Init")

        return None


class CanwitSignatureForm(forms.ModelForm):
    """The link between Canwit and manually identified Signature"""
    newgr  = forms.CharField(label=_("Signature"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Gryson code...',  'style': 'width: 100%;'}))
    newcl  = forms.CharField(label=_("Signature"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': '...or Clavis code...',  'style': 'width: 100%;'}))
    newot  = forms.CharField(label=_("Signature"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': '...or Other code...',  'style': 'width: 100%;'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = CanwitSignature
        fields = ['canwit', 'code', 'editype']
        widgets={'editype':     forms.Select(attrs={'style': 'width: 100%;'}),
                 'code':        forms.TextInput(attrs={'class': 'typeahead searching signaturetype input-sm', 
                                                       'placeholder': 'Signature...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CanwitSignatureForm, self).__init__(*args, **kwargs)
        # Initialize choices for editype
        init_choices(self, 'editype', EDI_TYPE, bUseAbbr=True)
        # Set some parameters to optional for best processing
        self.fields['code'].required = False
        self.fields['editype'].required = False


    def clean(self):
        # Run any super class cleaning
        cleaned_data = super(CanwitSignatureForm, self).clean()
        sermon = cleaned_data.get("sermon")
        editype = cleaned_data.get("editype")
        code = cleaned_data.get("code")

        # Check if this is a new one
        if editype == "":
            newgr = cleaned_data.get("newgr")
            if newgr != "":
                code = newgr
                editype = "gr"
            else:
                newcl = cleaned_data.get("newcl")
                if newcl != "":
                    code = newcl
                    editype = "cl"
                else:
                    newot = cleaned_data.get("newot")
                    if newot != "":
                        code = newot
                        editype = "ot"
        # Do we actually have something?

        # Check if any of [name] or [newkw] already exists
        if code == "" or editype == "":
            # No keyword chosen
            raise forms.ValidationError(
                    "No signature specified to attach to this Sermon manifestation"
                )
        else:
            # Check if [code|editype] already exists
            signature = CanwitSignature.objects.filter(sermon=sermon, code=code, editype=editype).first()
            if signature:
                # This combination already exists
                raise forms.ValidationError(
                        "This signature already exists for this Sermon manifestation"
                    )


class CanwitSuperForm(forms.ModelForm):
    newlinktype = forms.ChoiceField(label=_("Linktype"), required=False, # help_text="editable", 
               widget=forms.Select(attrs={'class': 'input-sm', 'placeholder': 'Type of link...',  'style': 'width: 100%;', 'tdstyle': 'width: 100px;'}))
    # For the method "nodistance"
    newsuper    = forms.CharField(label=_("Canon witness"), required=False, help_text="editable", 
                widget=SuperOneWidget(attrs={'data-placeholder': 'Select links...', 
                                                  'placeholder': 'Select an Authoritative statement...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = CanwitAustat
        fields = ['canwit', 'linktype', 'austat' ]
        widgets={'linktype':    forms.Select(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Determine the method
        method = "nodistance"   # Alternative: "superdist"

        if method == "superdist":
            # First get out the canwit_id
            canwit_id = kwargs.pop('canwit_id', None)
        # Start by executing the standard handling
        super(CanwitSuperForm, self).__init__(*args, **kwargs)

        # Initialize choices for linktype
        init_choices(self, 'linktype', LINK_TYPE, bUseAbbr=True)
        init_choices(self, 'newlinktype', LINK_TYPE, bUseAbbr=True, use_helptext=False)

        # Set the keyword to optional for best processing
        self.fields['newlinktype'].required = False
        self.fields['austat'].required = False
        self.fields['linktype'].required = False
        self.fields['newlinktype'].initial = "uns"

        if method == "superdist":
            self.fields['newsuperdist'].required = False
            # NEW: Taking the canwit as starting point and ordering them according to distance
            canwit = Canwit.objects.filter(id=canwit_id).first()
            if canwit != None:
                qs = canwit.canwitsuperdist.all().order_by('distance', 'austat__code', 'austat__author__name')
                self.fields['newsuperdist'].widget.canwit = canwit
            else:
                self.fields['newsuperdist'].queryset =  AustatDist.objects.filter(austat__moved__isnull=True).order_by('distance', 'austat__code', 'austat__author__name', 'id').distinct()
        else:
            self.fields['newsuper'].required = False
            # Initialize queryset
            self.fields['newsuper'].queryset = Austat.objects.filter(moved__isnull=True, atype='acc').order_by('code', 'author__name', 'id')


        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            if instance != None:
                #  NOTE: the following has no effect because we use bound fields
                #       self.fields['linktype'].initial = instance.linktype
                #       self.fields['dst'].initial = instance.dst

                if method == "superdist":
                    if instance.austat_id != None:
                        self.fields['newsuperdist'].queryset = self.fields['newsuperdist'].queryset.exclude(austat__id=instance.austat.id).order_by(
                            'distance', 'austat__code', 'austat__author__name', 'id')
                    else:
                        self.fields['newsuperdist'].queryset = self.fields['newsuperdist'].queryset.order_by('distance', 'austat__code', 'austat__author__name', 'id')
                else:
                    # Make sure we exclude the instance from the queryset
                    self.fields['newsuper'].queryset = self.fields['newsuper'].queryset.exclude(id=instance.id).order_by('code', 'author__name', 'id')

        return None


class CanwitKeywordForm(forms.ModelForm):
    newkw  = forms.CharField(label=_("Keyword (new)"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Keyword...',  'style': 'width: 100%;'}))
    name = forms.CharField(label=_("Keyword"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching keywords input-sm', 'placeholder': 'Keyword...',  'style': 'width: 100%;'}))
    typeaheads = ["keywords"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = CanwitKeyword
        fields = ['canwit', 'keyword']

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CanwitKeywordForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['newkw'].required = False
        self.fields['keyword'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.keyword != None:
                kw = instance.keyword.name
                self.fields['name'].initial = kw


class AustatForm(lilaModelForm):
    stypelist   = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=StypeWidget(attrs={'data-placeholder': 'Select multiple status types...', 'style': 'width: 100%;'}))
    authorname = forms.CharField(label=_("Author"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching authors input-sm', 'placeholder': 'Author...', 'style': 'width: 100%;'}))
    authorlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuthorWidget(attrs={'data-placeholder': 'Select multiple authors...', 'style': 'width: 100%;', 'class': 'searching'}))
    newauthor = ModelChoiceField(queryset=None, required=False,
                widget=AuthorOneWidget(attrs={'data-placeholder': 'Select one author...', 'style': 'width: 100%;', 'class': 'searching'}))
    newftext = forms.CharField(label=_("Incipit"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching asftexts input-sm', 'placeholder': 'Full text...', 'style': 'width: 100%;'}))
    newftrans = forms.CharField(label=_("Explicit"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching asftexts input-sm', 'placeholder': 'Translation...', 'style': 'width: 100%;'}))
    signature = forms.CharField(label=_("Signature"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching signatures input-sm', 'placeholder': 'Signature/code (Gryson, Clavis)...', 'style': 'width: 100%;'}))
    signatureid = forms.CharField(label=_("Signature ID"), required=False)
    lilalist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=AustatMultiWidget(attrs={'data-placeholder': 'Select multiple Lilac codes...', 'style': 'width: 100%;', 
                                                       'class': 'searching'}))
    keycodelist  = ModelMultipleChoiceField(queryset=None, required=False, 
                    widget=KeycodeMultiWidget(attrs={'data-placeholder': 'Select multiple Key codes...', 'style': 'width: 100%;', 
                                                       'class': 'searching'}))
    worklist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuworkWidget(attrs={'data-placeholder': 'Select multiple works...', 'style': 'width: 100%;', 'class': 'searching'}))
    genrelist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=GenreWidget(attrs={'data-placeholder': 'Select multiple genres...', 'style': 'width: 100%;', 'class': 'searching'}))
    kwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    projlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    addprojlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    delprojlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    ukwlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple user-keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    scount      = forms.IntegerField(min_value=-1, required=False,
                widget=forms.NumberInput(attrs={'class': 'searching', 'style': 'width: 20%;', 'data-placeholder': 'Sermon set size'}))
    ssgcount    = forms.IntegerField(min_value=-1, required=False,
                widget=forms.NumberInput(attrs={'class': 'searching', 'style': 'width: 20%;', 'data-placeholder': 'Relation set size'}))
    soperator   = forms.ChoiceField(required=False, choices=SCOUNT_OPERATOR,widget=forms.Select())
    ssgoperator   = forms.ChoiceField(required=False, choices=SCOUNT_OPERATOR,widget=forms.Select())

    collist_m   = ModelMultipleChoiceField(queryset=None, required=False)
    collist_s   = ModelMultipleChoiceField(queryset=None, required=False)
    collist_ssg = ModelMultipleChoiceField(queryset=None, required=False)
    collist_hist = ModelMultipleChoiceField(queryset=None, required=False)
    superlist    = ModelMultipleChoiceField(queryset=None, required=False)
    collection_m = forms.CharField(label=_("Collection m"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collection_s = forms.CharField(label=_("Collection s"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collection_ssg = forms.CharField(label=_("Collection ssg"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collone     = ModelChoiceField(queryset=None, required=False) #, 
                # widget=CollOneSuperWidget(attrs={'data-placeholder': 'Select one collection...', 'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = ["authors", "asftexts", "asftrans", "signatures"]   # Add [signatures] because of select_gold
    initial_fields = ['author', 'ftext', 'ftrans']

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Austat
        fields = ['author', 'ftext', 'ftrans', 'code', 'keycode', 'auwork', 'number', 'stype', 'date']
        widgets={'code':      forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 
                                                       'placeholder': 'Lilac code. Use wildcards, e.g: *002.*, *003'}),
                 'keycode':   forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 
                                                       'placeholder': 'key code. Use wildcards, e.g: *men*, *aug*'}),
                 'auwork':    AuworkOneWidget(attrs={'class': 'searching', 'style': 'width: 100%;', 'data-placeholder': 'Work'}),
                 'date':      forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 'data-placeholder': 'Date...'}),
                 'number':    forms.TextInput(attrs={'class': 'searching', 'style': 'width: 100%;', 'data-placeholder': 'Author number'}),
                 'ftext':     forms.TextInput(attrs={'class': 'typeahead searching asftexts input-sm', 'placeholder': 'Full text...', 'style': 'width: 100%;'}),
                 'ftrans':    forms.TextInput(attrs={'class': 'typeahead searching asftrans input-sm', 'placeholder': 'Translation...', 'style': 'width: 100%;'}),
                 'stype':     forms.Select(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(AustatForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)
            # Some fields are not required
            self.fields['authorname'].required = False
            self.fields['stype'].required = False
            self.fields['soperator'].initial = 2
            self.fields['ssgoperator'].initial = 2
            self.fields['scount'].initial = -1
            self.fields['ssgcount'].initial = -1

            # Initialize querysets
            self.fields['stypelist'].queryset = FieldChoice.objects.filter(field=STATUS_TYPE).order_by("english_name")
            self.fields['authorlist'].queryset = Author.objects.all().order_by('name')
            self.fields['newauthor'].queryset = Author.objects.all().order_by('name')
            self.fields['superlist'].queryset = AustatLink.objects.none()
            self.fields['lilalist'].queryset = Austat.objects.filter(code__isnull=False, moved__isnull=True).order_by('code')
            self.fields['keycodelist'].queryset = Austat.objects.filter(keycode__isnull=False, moved__isnull=True).order_by('code')
            self.fields['worklist'].queryset = Auwork.objects.all().order_by('key')
            self.fields['genrelist'].queryset = Genre.objects.all().order_by('name')
            self.fields['kwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            self.fields['ukwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            # self.fields['superlist'].queryset = Austat.objects.all().order_by('code', 'author__name', 'number')

            self.fields['projlist'].queryset = profile.projects.all().order_by('name').distinct()
            self.fields['projlist'].widget.queryset = self.fields['projlist'].queryset

            current_proj_ids = [x.id for x in self.fields['projlist'].queryset]
            self.fields['addprojlist'].queryset = Project.objects.exclude(id__in=current_proj_ids).order_by('name').distinct()
            self.fields['addprojlist'].widget.queryset = self.fields['addprojlist'].queryset
            self.fields['delprojlist'].queryset = Project.objects.filter(id__in=current_proj_ids).order_by('name').distinct()
            self.fields['delprojlist'].widget.queryset = self.fields['delprojlist'].queryset

            # Set the widgets correctly
            self.fields['collist_m'].widget = CollectionManuWidget( attrs={'username': username, 'team_group': team_group, 'data-allow-clear': 'false',
                        'data-placeholder': 'Select multiple manuscript datasets...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_s'].widget = CollectionCanwitWidget( attrs={'username': username, 'team_group': team_group, 'data-allow-clear': 'false',
                        'data-placeholder': 'Select multiple Canon witness datasets...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_ssg'].widget = CollectionAustatWidget( attrs={'username': username, 'team_group': team_group, 'data-allow-clear': 'false',
                        'data-placeholder': 'Select multiple Authoritative Statement datasets...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collist_hist'].widget = CollectionAustatWidget( attrs={'username': username, 'team_group': team_group, 'data-allow-clear': 'false',
                        'settype': 'hc', 'data-debug': 'true', 'data-ajax--cache': "false",
                        'data-placeholder': 'Select multiple historical collections...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['collone'].widget = CollOneSuperWidget( attrs={'username': username, 'team_group': team_group,
                        'data-placeholder': 'Select a dataset...', 'style': 'width: 100%;', 'class': 'searching'})
            self.fields['superlist'].widget = AustatLinkAddOnlyWidget(attrs={
                        'data-placeholder': 'Use the + sign to add links...', 'data-allow-clear': 'false', 'style': 'width: 100%;', 'class': 'searching'})

            if user_is_in_team(username, team_group):
                self.fields['kwlist'].widget.is_team = True
                self.fields['ukwlist'].widget.is_team = True
            else:
                self.fields['kwlist'].widget.is_team = False
                self.fields['ukwlist'].widget.is_team = False

            # Note: the collection filters must use the SCOPE of the collection
            self.fields['collist_m'].queryset = Collection.get_scoped_queryset('manu', username, team_group)
            self.fields['collist_s'].queryset = Collection.get_scoped_queryset('sermo', username, team_group)
            self.fields['collist_ssg'].queryset = Collection.get_scoped_queryset('austat', username, team_group)
            self.fields['collist_hist'].queryset = Collection.get_scoped_queryset('austat', username, team_group, settype="hc")
            self.fields['superlist'].queryset = AustatLink.objects.none()

            # The CollOne information is needed for the basket (add basket to collection)
            prefix = "austat"
            # self.fields['collone'].queryset = Collection.objects.filter(type=prefix).order_by('name')
            self.fields['collone'].queryset = Collection.get_scoped_queryset(prefix, username, team_group)
        
           # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                # If there is an instance, then check the author specification
                if instance.author is None:
                    self.fields['authorname'].initial = ""
                else:
                    self.fields['authorname'].initial = instance.author.name
                    self.fields['newauthor'].initial = instance.author.id
                    self.fields['newauthor'].widget.initial = instance.author.id
                self.fields['newftext'].initial = instance.ftext
                self.fields['newftrans'].initial = instance.ftrans
                self.fields['collist_ssg'].initial = [x.pk for x in instance.collections.filter(settype="pd").order_by('name')]
                self.fields['collist_hist'].initial = [x.pk for x in instance.collections.filter(settype="hc").order_by('name')]
                self.fields['superlist'].initial = [x.pk for x in instance.austat_src.all().order_by('dst__code', 'dst__author__name', 'dst__number')]
                self.fields['superlist'].queryset = AustatLink.objects.filter(id__in=self.fields['superlist'].initial)
                self.fields['genrelist'].initial = [x.pk for x in instance.genres.all().order_by('name')]
                self.fields['kwlist'].initial = [x.pk for x in instance.keywords.all().order_by('name')]
                self.fields['ukwlist'].initial = [x.keyword.pk for x in instance.austat_userkeywords.filter(profile=profile).order_by('keyword__name')]
                self.fields['projlist'].initial = [x.pk for x in instance.projects.all().order_by('name')] #
                if not instance.auwork is None:
                    self.fields['worklist'].initial = [x.pk for x in Auwork.objects.filter(id=instance.auwork.id).order_by('key')]

                qs = instance.austat_dst.all()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("AustatForm-init")
        # We are okay
        return None

    def clean(self):        # -> Dict[str, Any]:
        oErr = ErrHandle()
        response = None
        try:
            response = super(AustatForm, self).clean()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("AustatForm-clean")
        return response


class AustatLinkForm(forms.ModelForm):
    newlinktype = forms.ChoiceField(label=_("Linktype"), required=False, help_text="editable", 
                widget=forms.Select(attrs={'class': 'input-sm', 'placeholder': 'Type of link...',  'style': 'width: 100%;', 'tdstyle': 'width: 150px;'}))
    newspectype = forms.ChoiceField(label=_("Spectype"), required=False, help_text="editable", 
                widget=forms.Select(attrs={'class': 'input-sm', 'placeholder': 'Type of specification...',  'style': 'width: 100%;', 'tdstyle': 'width: 130px;',
                    'title': 'Direction specification (optional)'}))
    newsuper = ModelChoiceField(queryset=None, required=False, help_text="editable",
                widget=AustatWidget(attrs={'data-placeholder': 'Select one Authoritative statement...', 'style': 'width: 100%;', 'class': 'searching select2-ssg'}))
    newalt = forms.CharField(label=_("Alternatives"), required=False, help_text="editable", 
                widget=CheckboxString(attrs={'class': 'input-sm', 'placeholder': 'Alternatives...',  'style': 'width: 100%;', 
                    'title': 'one of several alternatives: check this box when there are several options for a source (of a part of a text), but it is not clear which of these is the direct source'}))
    note = forms.CharField(label=_("Notes"), required=False, help_text="editable", 
                widget=forms.Textarea(attrs={'class': 'input-sm', 'placeholder': 'Notes...',  'style': 'height: 40px; width: 100%;', 
                    'tdstyle': 'width: 300px;', 'rows': 1, 
                    'title': 'everything that is not already specified in the link type itself, but that you do want to include'}))
    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = AustatLink
        fields = ['src', 'linktype', 'dst' ]
        widgets={'linktype':    forms.Select(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        oErr = ErrHandle()
        try:
            # Read the austat_id
            austat_id = kwargs.pop("austat_id", "")
            # Start by executing the standard handling
            super(AustatLinkForm, self).__init__(*args, **kwargs)
            # Initialize choices for linktype
            init_choices(self, 'linktype', LINK_TYPE, bUseAbbr=True, exclude=['eqs'])
            init_choices(self, 'newlinktype', LINK_TYPE, bUseAbbr=True, exclude=['eqs'], use_helptext=False)
            init_choices(self, 'newspectype', SPEC_TYPE, bUseAbbr=True, maybe_empty=True, use_helptext=False)
            init_choices(self, 'alternatives', YESNO_TYPE, bUseAbbr=True,maybe_empty=True, use_helptext=False)
            # Make sure to set required and optional fields
            self.fields['linktype'].required = False
            self.fields['newlinktype'].required = False
            self.fields['newspectype'].required = False
            self.fields['newalt'].required = False
            self.fields['note'].required = False
            self.fields['dst'].required = False
            self.fields['newsuper'].required = False

            # For searching/listing
            self.fields['newlinktype'].initial = "prt"

            if austat_id != None and austat_id != "":
                self.fields['newsuper'].queryset = Austat.objects.filter(moved__isnull=True).exclude(id=austat_id).order_by('code')
                # Adapt the widget QS
                self.fields['newsuper'].widget.exclude = austat_id
            else:
                self.fields['newsuper'].queryset = Austat.objects.filter(moved__isnull=True).order_by('code')
            # self.fields['target_list'].queryset = Austat.objects.none()
            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                if instance != None:
                    #  NOTE: the following has no effect because we use bound fields
                    #       self.fields['linktype'].initial = instance.linktype
                    #       self.fields['dst'].initial = instance.dst

                    self.fields['newsuper'].queryset = Austat.objects.filter(moved__isnull=True).exclude(id=instance.id).order_by('code')
        except:
            msg = oErr.get_error_message()
            oErr.DoError("AustatLinkForm")

        # REturn nothing
        return None

    def clean(self):
        # Run any super class cleaning
        cleaned_data = super(AustatLinkForm, self).clean()

        # Get the source
        src = cleaned_data.get("src")
        if src != None:
            # Any new destination is added in target_list
            dst = cleaned_data.get("newsuper")
            if dst != None:
                # WE have a DST, now check how many links there are with this one
                existing = src.relations.filter(id=dst.id)
                if existing.count() > 0:
                    # This combination already exists
                    raise forms.ValidationError(
                            "This Authoritative statement is already linked"
                        )
        # Make sure to return the correct cleaned data again
        return cleaned_data


class SuperSermonGoldCollectionForm(forms.ModelForm):
    name   = forms.CharField(label=_("Collection"), required=False, help_text="", 
               widget=forms.TextInput(attrs={'class': 'searching input-sm', 'placeholder': 'Collection...',  'style': 'width: 100%;'}))
    newcol = forms.CharField(label=_("Collection (new)"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Collection...',  'style': 'width: 100%;'}))
    #typeaheads = ["keywords"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = CollectionAustat
        fields = ['austat', 'collection']

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(SuperSermonGoldCollectionForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['newcol'].required = False
        self.fields['collection'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.collection != None:
                col = instance.collection.name
                self.fields['name'].initial = col


class ManuscriptCollectionForm(forms.ModelForm):
    name   = forms.CharField(label=_("Collection"), required=False, help_text="", 
               widget=forms.TextInput(attrs={'class': 'searching input-sm', 'placeholder': 'Collection...',  'style': 'width: 100%;'}))
    newcol = forms.CharField(label=_("Collection (new)"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Collection...',  'style': 'width: 100%;'}))
    #typeaheads = ["keywords"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = CollectionMan
        fields = ['manuscript', 'collection']

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuscriptCollectionForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['newcol'].required = False
        self.fields['collection'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.collection != None:
                col = instance.collection.name
                self.fields['name'].initial = col


class CanwitCollectionForm(forms.ModelForm):
    name = forms.CharField(label=_("Collection"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching collections input-sm', 'placeholder': 'Collection...',  'style': 'width: 100%;'}))
    newcol = forms.CharField(label=_("Collection (new)"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Collection...',  'style': 'width: 100%;'}))
    # typeaheads = ["collections"]
    
    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = CollectionCanwit
        fields = ['canwit', 'collection']

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CanwitCollectionForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['newcol'].required = False 
        self.fields['collection'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.collection != None:
                col = instance.collection.name
                self.fields['name'].initial = col

                
class ManuscriptProvForm(forms.ModelForm):
    prov_new = forms.ModelChoiceField(queryset=None, required=False, help_text="editable",
                widget = ProvenanceOneWidget(attrs={'data-placeholder': 'Select a provenance...', 'style': 'width: 100%;', 'class': 'searching'}))
    #name = forms.CharField(label=_("Name"), required=False, help_text="editable",
    #                       widget=forms.TextInput(attrs={'placeholder': 'Name...',  'style': 'width: 100%;'}))
    note = forms.CharField(label=_("Note"), required=False, help_text="editable",
                           widget = forms.Textarea(attrs={'placeholder': 'Note (optional)...',  'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}))
    #location = forms.ModelChoiceField(queryset=None, required=False, help_text="editable",
    #                       widget = LocationOneWidget(attrs={'data-placeholder': 'Select a location...', 'style': 'width: 100%;', 'class': 'searching'}))
    #location_ta = forms.CharField(label=_("Location"), required=False, 
    #                       widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Location...',  'style': 'width: 100%;'}))
    typeaheads = ["locations"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = ProvenanceMan
        fields = ['provenance', 'manuscript']
        widgets={'provenance':     ProvenanceOneWidget(attrs={'data-placeholder': 'Select a provenance...', 'style': 'width: 100%;', 'class': 'searching'}),
 
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuscriptProvForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        #self.fields['name'].required = False
        self.fields['note'].required = False
        self.fields['provenance'].required = False
        #self.fields['location'].required = False
        #self.fields['location_ta'].required = False
        #self.fields['location'].queryset = Location.objects.all().order_by('name')
        self.fields['prov_new'].queryset = Provenance.objects.all().order_by('name', 'location__name')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.provenance != None:
                self.fields['name'].initial = instance.provenance.name
                self.fields['note'].initial = instance.provenance.note
                if instance.provenance.location != None:
                    self.fields['location_ta'].initial = instance.provenance.location.get_loc_name()
                    # self.fields['location_ta'].initial = instance.provenance.location.name
                    # Make sure the location is set to the correct number
                    self.fields['location'].initial = instance.provenance.location.id


class CodicoProvForm(forms.ModelForm):
    prov_new = forms.ModelChoiceField(queryset=None, required=False, help_text="editable",
                widget = ProvenanceOneWidget(attrs={'data-placeholder': 'Select a provenance...', 'style': 'width: 100%;', 'class': 'searching'}))
    note = forms.CharField(label=_("Note"), required=False, help_text="editable",
                widget = forms.Textarea(attrs={'placeholder': 'Note (optional)...',  'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}))
    typeaheads = ["locations"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = ProvenanceCod
        fields = ['provenance', 'codico']
        widgets={'provenance':  ProvenanceOneWidget(attrs={'data-placeholder': 'Select a provenance...', 'style': 'width: 100%;', 'class': 'searching'}),
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CodicoProvForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['note'].required = False
        self.fields['provenance'].required = False
        self.fields['prov_new'].queryset = Provenance.objects.all().order_by('name', 'location__name')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.provenance != None:
                self.fields['name'].initial = instance.provenance.name
                self.fields['note'].initial = instance.provenance.note
                if instance.provenance.location != None:
                    self.fields['location_ta'].initial = instance.provenance.location.get_loc_name()
                    # Make sure the location is set to the correct number
                    self.fields['location'].initial = instance.provenance.location.id


class CodicoOriginForm(forms.ModelForm):
    origin_new = forms.ModelChoiceField(queryset=None, required=False, help_text="editable",
                widget = OriginOneWidget(attrs={'data-placeholder': 'Select a origin...', 'style': 'width: 100%;', 'class': 'searching'}))
    note = forms.CharField(label=_("Note"), required=False, help_text="editable",
                widget = forms.Textarea(attrs={'placeholder': 'Note (optional)...',  'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}))
    typeaheads = ["locations"]
    warning = "One codicological unit may only contain one Origin"

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = OriginCodico
        fields = ['origin', 'codico']
        widgets={'origin':  OriginOneWidget(attrs={'data-placeholder': 'Select a origin...', 'style': 'width: 100%;', 'class': 'searching'}),
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CodicoOriginForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['note'].required = False
        self.fields['origin'].required = False
        self.fields['origin_new'].queryset = Origin.objects.all().order_by('name', 'location__name')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.origin != None:
                self.fields['name'].initial = instance.origin.name
                self.fields['note'].initial = instance.origin.note
                if instance.origin.location != None:
                    self.fields['location_ta'].initial = instance.origin.location.get_loc_name()
                    # Make sure the location is set to the correct number
                    self.fields['location'].initial = instance.origin.location.id


class CollectionLitrefForm(forms.ModelForm):
    oneref = forms.ModelChoiceField(queryset=None, required=False, help_text="editable", 
               widget=LitrefWidget(attrs={'data-placeholder': 'Select one reference...', 'style': 'width: 100%;', 'class': 'searching'}))
    newpages  = forms.CharField(label=_("Page range"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Page range...',  'style': 'width: 100%;'}))
    # ORIGINAL:
    litref = forms.CharField(required=False)
    litref_ta = forms.CharField(label=_("Reference"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching litrefs input-sm', 'placeholder': 'Reference...',  'style': 'width: 100%;'}))
    typeaheads = ["litrefs"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = LitrefCol
        fields = ['reference', 'collection', 'pages']
        widgets={'pages':     forms.TextInput(attrs={'placeholder': 'Page range...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CollectionLitrefForm, self).__init__(*args, **kwargs)
        self.fields['reference'].required = False
        self.fields['litref'].required = False
        self.fields['litref_ta'].required = False
        # EK: Added for Sermon Gold new approach 
        self.fields['newpages'].required = False
        self.fields['oneref'].required = False
        self.fields['oneref'].queryset = Litref.objects.exclude(full="").order_by('full')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial reference should be added
            if instance.reference != None:
                self.fields['litref_ta'].initial = instance.reference.get_full()

    def clean(self):
        cleaned_data = super(CollectionLitrefForm, self).clean()
        litref = cleaned_data.get("litref")
        oneref = cleaned_data.get("oneref")
        reference = cleaned_data.get("reference")
        if reference == None and (litref == None or litref == "") and (oneref == None or oneref == ""):
            raise forms.ValidationError("Cannot find the reference. Make sure to select it. If it is not available, add it in Zotero and import it in lila")


class ManuscriptLitrefForm(forms.ModelForm):
    # EK: Added for Sermon Gold new approach 
    oneref = forms.ModelChoiceField(queryset=None, required=False, help_text="editable", 
               widget=LitrefWidget(attrs={'data-placeholder': 'Select one reference...', 'style': 'width: 100%;', 'class': 'searching'}))
    newpages  = forms.CharField(label=_("Page range"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Page range...',  'style': 'width: 100%;'}))
    # ORIGINAL:
    litref = forms.CharField(required=False)
    litref_ta = forms.CharField(label=_("Reference"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching litrefs input-sm', 'placeholder': 'Reference...',  'style': 'width: 100%;'}))
    typeaheads = ["litrefs"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = LitrefMan
        fields = ['reference', 'manuscript', 'pages']
        widgets={'pages':     forms.TextInput(attrs={'placeholder': 'Page range...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuscriptLitrefForm, self).__init__(*args, **kwargs)
        self.fields['reference'].required = False
        self.fields['litref'].required = False
        self.fields['litref_ta'].required = False
        # EK: Added for Sermon Gold new approach 
        self.fields['newpages'].required = False
        self.fields['oneref'].required = False
        self.fields['oneref'].queryset = Litref.objects.exclude(full="").order_by('full')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial reference should be added
            if instance.reference != None:
                self.fields['litref_ta'].initial = instance.reference.get_full()

    def clean(self):
        cleaned_data = super(ManuscriptLitrefForm, self).clean()
        litref = cleaned_data.get("litref")
        oneref = cleaned_data.get("oneref")
        reference = cleaned_data.get("reference")
        if reference == None and (litref == None or litref == "") and (oneref == None or oneref == ""):
            #litref_ta = cleaned_data.get("litref_ta")
            #obj = Litref.objects.filter(full=litref_ta).first()
            #if obj == None:
            raise forms.ValidationError("Cannot find the reference. Make sure to select it. If it is not available, add it in Zotero and import it in lila")


class ManuscriptExtForm(forms.ModelForm):
    newurl = forms.CharField(label=_("URL (new)"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'URL...',  'style': 'width: 100%;'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = ManuscriptExt
        fields = ['url']
        widgets={'url':     forms.TextInput(attrs={'placeholder': 'External link (URL)...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuscriptExtForm, self).__init__(*args, **kwargs)

        self.fields['url'].required = False
        self.fields['newurl'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class ManuscriptKeywordForm(forms.ModelForm):
    name = forms.CharField(label=_("Keyword"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching keywords input-sm', 'placeholder': 'Keyword...',  'style': 'width: 100%;'}))
    newkw = forms.CharField(label=_("Keyword (new)"), required=False, help_text="editable", 
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Keyword...',  'style': 'width: 100%;'}))
    typeaheads = ["keywords"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = ManuscriptKeyword
        fields = ['manuscript', 'keyword']

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuscriptKeywordForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['keyword'].required = False
        self.fields['name'].required = False
        self.fields['newkw'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.keyword != None:
                kw = instance.keyword.name
                self.fields['name'].initial = kw


class ManuscriptProjectForm(forms.ModelForm):
    """ManuscriptProjForm zoals Keywords / Prov?"""

    # kan nog niet toevoegen, mag sowieso niet, moet via Tools etc.
    proj_new = forms.ModelChoiceField(queryset=None, required=False, help_text="editable",
                widget = ProjectOneWidget(attrs={'data-placeholder': 'Select a project...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = ManuscriptProject
        fields = ['manuscript', 'project']
        widgets={'project':     ProjectOneWidget(attrs={'data-placeholder': 'Select a project...', 'style': 'width: 100%;', 'class': 'searching'}),
 
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuscriptProjectForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['project'].required = False
        self.fields['proj_new'].queryset = Project.objects.all().order_by('name')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.projects != None:
                self.fields['name'].initial = instance.project.name


class OriginForm(forms.ModelForm):
    location_ta = forms.CharField(label=_("Location"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Location...',  'style': 'width: 100%;'}))
    locationlist = ModelMultipleChoiceField(queryset=None, required=False,
                            widget=LocationWidget(attrs={'data-placeholder': 'Location...', 'style': 'width: 100%;'}))
    typeaheads = ["locations"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Origin
        fields = ['name', 'location', 'note']
        widgets={'name':     forms.TextInput(attrs={'placeholder': 'Name...', 'style': 'width: 100%;'}),
                 'location': LocationOneWidget(attrs={'data-placeholder': 'Select one location...', 'style': 'width: 100%;'}),
                 'note':     forms.Textarea(attrs={'rows': 1, 'cols': 40, 'placeholder': 'Note on this origin...', 'style': 'height: 40px; width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(OriginForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['name'].required = False
        self.fields['note'].required = False
        self.fields['location'].required = False
        self.fields['location_ta'].required = False
        self.fields['locationlist'].queryset = Location.objects.all().order_by('loctype__level', 'name')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance != None:
                self.fields['name'].initial = instance.name
                self.fields['note'].initial = instance.note
                if instance.location != None:
                    self.fields['location_ta'].initial = instance.location.get_loc_name()


class OriginCodForm(forms.ModelForm):
    """OriginCodico item"""

    warning = "One codicological unit may only contain one Origin"

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = OriginCodico
        fields = ['note']
        widgets={'note':    forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;', 
                            'class': 'searching', 'placeholder': 'Notes on this origin...'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(OriginCodForm, self).__init__(*args, **kwargs)

        # Some fields are not required
        self.fields['note'].required = False

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class LibrarySearchForm(forms.ModelForm):
    country = forms.CharField(label=_("Country"), required=False, 
                 widget=forms.TextInput(attrs={'class': 'typeahead searching countries input-sm', 'placeholder': 'Country...', 'style': 'width: 100%;'}))
    city = forms.CharField(label=_("City"), required=False, 
                 widget=forms.TextInput(attrs={'class': 'typeahead searching cities input-sm', 'placeholder': 'City...',  'style': 'width: 100%;'}))
    name = forms.CharField(label=_("Library"), required=False, 
                 widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Name of library...',  'style': 'width: 100%;'}))
    countrylist = ModelMultipleChoiceField(queryset=None, required=False,
                 widget=CountryWidget(attrs={'data-placeholder': 'Select countries...', 'style': 'width: 100%;'}))
    citylist = ModelMultipleChoiceField(queryset=None, required=False,
                 widget=CityWidget(attrs={'data-placeholder': 'Select cities...', 'style': 'width: 100%;'}))
    librarylist = ModelMultipleChoiceField(queryset=None, required=False,
                 widget=LibraryWidget(attrs={'data-placeholder': 'Select libraries...', 'style': 'width: 100%;'}))
    library_ta = forms.CharField(label=_("Libraru"), required=False, 
                 widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Library...',  'style': 'width: 100%;'}))
    typeaheads = ["countries", "cities", "libraries"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Library
        fields = ['lcity', 'lcountry']

    def __init__(self, *args, **kwargs):
        oErr = ErrHandle()
        try:
            # Start by executing the standard handling
            super(LibrarySearchForm, self).__init__(*args, **kwargs)
            # Set the keyword to optional for best processing
            self.fields['lcity'].required = False
            self.fields['lcountry'].required = False

            # Need to initialize the lists
            self.fields['countrylist'].queryset = Location.objects.all()
            self.fields['citylist'].queryset = Location.objects.all()
            self.fields['librarylist'].queryset = Library.objects.all()
        except:
            msg = oErr.get_error_message()
            oErr.DoError("LibrarySearchForm")
        return None


class LibraryForm(forms.ModelForm):
    #location = forms.ModelChoiceField(queryset=None, required=False, help_text="editable",
    #                       widget = LocationOneWidget(attrs={'data-placeholder': 'Select a location...', 'style': 'width: 100%;', 'class': 'searching'}))
    location_ta = forms.CharField(label=_("Location"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Location...',  'style': 'width: 100%;'}))
    typeaheads = ["locations"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Library
        fields = ['name', 'libtype', 'idLibrEtab', 'location', 'lcity', 'lcountry']
        widgets={'name':     forms.TextInput(attrs={'placeholder': 'Name...', 'style': 'width: 100%;'}),
                 'location': LocationOneWidget(attrs={'data-placeholder': 'Select a location...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'lcity':    forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'lcountry': forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'libtype':  forms.Select(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(LibraryForm, self).__init__(*args, **kwargs)
        # Set the keyword to optional for best processing
        self.fields['name'].required = False
        self.fields['libtype'].required = False
        self.fields['idLibrEtab'].required = False
        self.fields['location'].required = False
        self.fields['location_ta'].required = False
        self.fields['location'].queryset = Location.objects.all().order_by('name')
        self.fields['lcity'].required = False
        self.fields['lcountry'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance != None:
                self.fields['name'].initial = instance.name
                self.fields['libtype'].initial = instance.libtype
                self.fields['lcity'].initial = instance.lcity
                self.fields['lcountry'].initial = instance.lcountry
                if instance.location != None:
                    self.fields['location_ta'].initial = instance.location.get_loc_name()


class CodicoForm(lilaModelForm):
    stypelist   = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=StypeWidget(attrs={'data-placeholder': 'Select multiple status types...', 'style': 'width: 100%;'}))
    name_ta   = forms.CharField(label=_("Title"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching codicos input-sm', 'placeholder': 'Title...',  'style': 'width: 100%;'}))
    origin_ta   = forms.CharField(label=_("Origin"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching  input-sm', 'placeholder': 'Origin (location)...',  'style': 'width: 100%;'}))
    origone     = ModelChoiceField(queryset=None, required=False,
                widget=OriginOneWidget(attrs={'data-placeholder': 'Select an origin...', 'style': 'width: 100%;', 'class': 'searching'}))
    manuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))
    manuidno   = forms.CharField(label=_("Manuscript"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching input-sm', 'placeholder': 'Manuscript...',  'style': 'width: 100%;'}))
    prov_ta     = forms.CharField(label=_("Provenance"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Provenance (location)...',  'style': 'width: 100%;'}))
    date_from   = forms.IntegerField(label=_("Date start"), required = False,
                widget=forms.TextInput(attrs={'placeholder': 'Starting from...',  'style': 'width: 30%;', 'class': 'searching'}))
    date_until  = forms.IntegerField(label=_("Date until"), required = False,
                widget=forms.TextInput(attrs={'placeholder': 'Until (including)...',  'style': 'width: 30%;', 'class': 'searching'}))
    kwlist      = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    cprovlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProvenanceCodWidget(attrs={'data-placeholder': 'Select provenance-note combinations...', 'style': 'width: 100%;', 'class': 'searching'}))
    corilist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=OriginCodWidget(attrs={'data-placeholder': 'Select origin-note combinations...', 'style': 'width: 100%;', 'class': 'searching'}))
    datelist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=DaterangeWidget(attrs={'data-placeholder': 'Use the "+" sign to add dates...', 'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = ["origins"]
    action_log = ['name', 'origin', 'support', 'extent', 'format', 'stype', 'kwlist', 'cprovlist', 'corilist', 'datelist']
    exclude = ['origin_ta']

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Codico
        fields = ['name', 'notes', 'support', 'extent', 'format', 'stype', 'manuscript']
        widgets={'name':        forms.TextInput(attrs={'data-placeholder': 'Provide the name...', 'style': 'width: 100%;'}),
                 'format':      forms.TextInput(attrs={'data-placeholder': 'Provide the size...', 'style': 'width: 100%;'}),
                 'extent':      forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}),
                 'support':     forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}),
                 'notes':       forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}),
                 'stype':       forms.Select(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CodicoForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)
            # Some fields are not required
            self.fields['stype'].required = False
            self.fields['name'].required = False
            self.fields['manuscript'].required = False

            self.fields['manuidlist'].queryset = Manuscript.objects.filter(mtype='man').order_by('idno')
            self.fields['kwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            # self.fields['prjlist'].queryset = Project.objects.all().order_by('name')
            self.fields['stypelist'].queryset = FieldChoice.objects.filter(field=STATUS_TYPE).order_by("english_name")

            if user_is_in_team(username, team_group):
                self.fields['kwlist'].widget.is_team = True
            else:
                self.fields['kwlist'].widget.is_team = False

            self.fields['origone'].queryset = Origin.objects.all().order_by('name')

            # Some lists need to be initialized to NONE:
            self.fields['cprovlist'].queryset = ProvenanceCod.objects.none()
            self.fields['corilist'].queryset = OriginCodico.objects.none()
            self.fields['datelist'].queryset = Daterange.objects.none()

            self.fields['cprovlist'].widget.addonly = True
            self.fields['corilist'].widget.addonly = True
            self.fields['datelist'].widget.addonly = True
        
            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']

                # Look after origin
                origin = instance.origins.first()

                self.fields['origin_ta'].initial = "" if origin == None else origin.name
                self.fields['origone'].initial = None if origin == None else origin.id
                self.fields['kwlist'].initial = [x.pk for x in instance.keywords.all().order_by('name')]

                self.fields['cprovlist'].initial = [x.pk for x in instance.codico_provenances.all()]
                self.fields['corilist'].initial = [x.pk for x in instance.codico_origins.all()]
                self.fields['datelist'].initial = [x.pk for x in instance.codico_dateranges.all()]

                # The manuscriptext and the provenance should *just* contain what they have (no extension here)
                self.fields['cprovlist'].queryset = ProvenanceCod.objects.filter(id__in=self.fields['cprovlist'].initial)
                self.fields['corilist'].queryset = OriginCodico.objects.filter(id__in=self.fields['corilist'].initial)
                self.fields['datelist'].queryset = Daterange.objects.filter(id__in=self.fields['datelist'].initial)

                self.fields['cprovlist'].widget.codico = instance
                self.fields['corilist'].widget.codico = instance
                self.fields['datelist'].widget.codico = instance

        except:
            msg = oErr.get_error_message()
            oErr.DoError("CodicoForm")
        return None


class ManuscriptForm(lilaModelForm):
    country_ta  = forms.CharField(label=_("Country"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching countries input-sm', 'placeholder': 'Country...', 'style': 'width: 100%;'}))
    city_ta     = forms.CharField(label=_("City"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching cities input-sm', 'placeholder': 'City...',  'style': 'width: 100%;'}))
    libname_ta  = forms.CharField(label=_("Library"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Name of library...',  'style': 'width: 100%;'}))
    origname_ta = forms.CharField(label=_("Origin"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching origins input-sm', 'placeholder': 'Origin...',  'style': 'width: 100%;'}))
    origone     = ModelChoiceField(queryset=None, required=False,
                widget=OriginOneWidget(attrs={'data-placeholder': 'Select an origin...', 'style': 'width: 100%;', 'class': 'searching'}))
    collection  = forms.CharField(label=_("Collection"), required=False,
                widget=forms.TextInput(attrs={'class': 'searching input-sm', 'placeholder': 'Collection(s)...', 'style': 'width: 100%;'}))
    collist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=CollectionManuWidget(attrs={'data-placeholder': 'Select multiple collections...', 'style': 'width: 100%;', 'class': 'searching'}))
    kwlist      = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    projlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProjectWidget(attrs={'data-placeholder': 'Select multiple projects...', 'style': 'width: 100%;', 'class': 'searching'}))
    ukwlist      = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=KeywordWidget(attrs={'data-placeholder': 'Select multiple user-keywords...', 'style': 'width: 100%;', 'class': 'searching'}))
    litlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=LitrefManWidget(attrs={'data-placeholder': 'Select multiple literature references...', 'style': 'width: 100%;', 'class': 'searching'}))
    #provlist    = ModelMultipleChoiceField(queryset=None, required=False, 
    #            widget=ProvenanceWidget(attrs={'data-placeholder': 'Select multiple provenances...', 'style': 'width: 100%;', 'class': 'searching'}))
    mprovlist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProvenanceManWidget(attrs={'data-placeholder': 'Select provenance-note combinations...', 'style': 'width: 100%;', 'class': 'searching'}))
    extlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ManuscriptExtWidget(attrs={'data-placeholder': 'Select multiple external links...', 'style': 'width: 100%;', 'class': 'searching'}))
    datelist    = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=DaterangeWidget(attrs={'data-placeholder': 'Use the "+" sign to add dates...', 'style': 'width: 100%;', 'class': 'searching'}))
    headlist    = ModelChoiceField(queryset=None, required=False,
                widget=CodheadOneWidget(attrs={'data-placeholder': 'Optional: select a section in which to put the canon witnesses...', 
                                               'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = ["countries", "cities", "libraries", "origins", "manuidnos"]
    action_log = ['name', 'library', 'lcity', 'lcountry', 'idno', 
                  'origin', 'url', 'support', 'extent', 'format', 'stype', 'project',
                  'ukwlist', 'kwlist', 'litlist', 'collist', 'mprovlist', 'extlist', 'datelist', 'projlist'] 
    exclude = ['country_ta', 'city_ta', 'libname_ta', 'origname_ta']

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Manuscript
        fields = ['name', 'library', 'lcity', 'lcountry', 'idno', 'lilacode', 'notes', # 'yearstart', 'yearfinish', 'project' 
                  'origins', 'dates', 'script', 'size',
                  'origin', 'url', 'support', 'extent', 'format', 'stype']
        widgets={'library':     LibraryOneWidget(attrs={'data-placeholder': 'Select a library...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'lcity':       CityMonasteryOneWidget(attrs={'data-placeholder': 'Select a city, village or abbey...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'lcountry':    CountryOneWidget(attrs={'data-placeholder': 'Select a country...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'name':        forms.TextInput(attrs={'style': 'width: 100%;'}),
                 #'yearstart':   forms.TextInput(attrs={'style': 'width: 40%;'}),
                 #'yearfinish':  forms.TextInput(attrs={'style': 'width: 40%;'}),
                 'idno':        forms.TextInput(attrs={'class': 'typeahead searching manuidnos input-sm', 'placeholder': 'Identifier...',  'style': 'width: 100%;'}),
                 'origin':      OriginOneWidget(attrs={'data-placeholder': 'Select an origin...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'url':         forms.TextInput(attrs={'data-placeholder': 'Provide a URL...', 'style': 'width: 100%;'}),
                 'format':      forms.TextInput(attrs={'data-placeholder': 'Provide a format...', 'style': 'width: 100%;'}),
                 'lilacode':    forms.TextInput(attrs={'data-placeholder': 'Provide the (short) LiLaC code for the manuscript only...', 'style': 'width: 100%;'}),
                 'origins':     forms.TextInput(attrs={'data-placeholder': 'Provide the origins (string)...', 'style': 'width: 100%;'}),
                 'dates':       forms.TextInput(attrs={'data-placeholder': 'Provide the date(s)...', 'style': 'width: 100%;'}),
                 'script':      forms.TextInput(attrs={'data-placeholder': 'Provide the script...', 'style': 'width: 100%;'}),
                 'size':        forms.TextInput(attrs={'data-placeholder': 'Provide the size...', 'style': 'width: 100%;'}),
                 'extent':      forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}),
                 # 'literature':  forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}),
                 'support':     forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}),
                 'notes':       forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}),
                 'stype':       forms.Select(attrs={'style': 'width: 100%;'}),
                 # 'project':     ProjectOneWidget(attrs={'data-placeholder': 'Select one project...', 'style': 'width: 100%;', 'class': 'searching'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ManuscriptForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)
            # Some fields are not required
            self.fields['stype'].required = False
            #self.fields['yearstart'].required = False
            #self.fields['yearfinish'].required = False
            self.fields['name'].required = False
            self.fields['lcity'].required = False
            self.fields['lcountry'].required = False
            self.fields['litlist'].queryset = LitrefMan.objects.all().order_by('reference__full', 'pages').distinct()
            self.fields['kwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            self.fields['ukwlist'].queryset = Keyword.get_scoped_queryset(username, team_group)
            # self.fields['projlist'].queryset = Project.objects.all().order_by('name').distinct()
            self.fields['projlist'].queryset = profile.projects.all().order_by('name').distinct()
            self.fields['projlist'].widget.queryset = self.fields['projlist'].queryset

            # Set the dependent fields for [lcity]
            if self.prefix != "":
                self.fields['lcity'].widget.dependent_fields = {
                    '{}-lcountry'.format(self.prefix): 'lcountry'}
                self.fields['library'].widget.dependent_fields = {
                    '{}-lcountry'.format(self.prefix): 'lcountry',
                    '{}-lcity'.format(self.prefix): 'lcity'}

            if user_is_in_team(username, team_group):
                self.fields['kwlist'].widget.is_team = True
                self.fields['ukwlist'].widget.is_team = True
            else:
                self.fields['kwlist'].widget.is_team = False
                self.fields['ukwlist'].widget.is_team = False

            # Note: the collection filters must use the SCOPE of the collection
            self.fields['collist'].queryset = Collection.get_scoped_queryset('manu', username, team_group)

            self.fields['origone'].queryset = Origin.objects.all().order_by('name')

            self.fields['headlist'].queryset = Codhead.objects.all().order_by('locus')

            # Some lists need to be initialized to NONE:
            #self.fields['provlist'].queryset = Provenance.objects.none()
            self.fields['mprovlist'].queryset = ProvenanceMan.objects.none()
            self.fields['extlist'].queryset = ManuscriptExt.objects.none()
            self.fields['datelist'].queryset = Daterange.objects.none()

           # self.fields['provlist'].widget.addonly = True
            self.fields['mprovlist'].widget.addonly = True
            self.fields['extlist'].widget.addonly = True
            self.fields['datelist'].widget.addonly = True
        
            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                # If there is an instance, then check if a library is specified
                library = instance.library
                if library != None:
                    # In this case: get the city and the country
                    city = library.get_city_name()
                    country = library.get_country_name()
                    if (country == None or country == "") and city != None and city != "":
                        # We have a city, but the country is not specified...
                        lstQ = []
                        lstQ.append(Q(loctype__name="country"))
                        lstQ.append(Q(relations_location=library.lcity))
                        obj = Location.objects.filter(*lstQ).first()
                        if obj != None:
                            country = obj.name
                    # Put them in the fields
                    self.fields['city_ta'].initial = city
                    self.fields['country_ta'].initial = country
                    # Also: make sure we put the library NAME in the initial
                    self.fields['libname_ta'].initial = library.name

                    # New method
                    # self.fields['library'].initial = 
                # Look after origin
                origin = instance.origin
                self.fields['origname_ta'].initial = "" if origin == None else origin.name
                self.fields['origone'].initial = None if origin == None else origin.id
                self.fields['collist'].initial = [x.pk for x in instance.collections.all().order_by('name')]
                self.fields['litlist'].initial = [x.pk for x in instance.manuscript_litrefs.all().order_by('reference__full', 'pages')]
                self.fields['kwlist'].initial = [x.pk for x in instance.keywords.all().order_by('name')]
                self.fields['projlist'].initial = [x.pk for x in instance.projects.all().order_by('name')] 
                self.fields['ukwlist'].initial = [x.keyword.pk for x in instance.manu_userkeywords.filter(profile=profile).order_by('keyword__name')]

                self.fields['mprovlist'].initial = [x.pk for x in instance.manuscripts_provenances.all()]
                self.fields['extlist'].initial = [x.pk for x in instance.manuscriptexternals.all()]
                self.fields['datelist'].initial = [x.pk for x in Daterange.objects.filter(codico__manuscript=instance)]
                #self.fields['headlist'].initial = [x.pk for x in Codhead.objects.filter(msitem__codico__manuscript=instance)]
                qs_headlist = [x.pk for x in Codhead.objects.filter(msitem__codico__manuscript=instance)]

                # The manuscriptext and the provenance should *just* contain what they have (no extension here)
                self.fields['mprovlist'].queryset = ProvenanceMan.objects.filter(id__in=self.fields['mprovlist'].initial)
                self.fields['extlist'].queryset = ManuscriptExt.objects.filter(id__in=self.fields['extlist'].initial)
                self.fields['datelist'].queryset = Daterange.objects.filter(id__in=self.fields['datelist'].initial)
                self.fields['headlist'].queryset = Codhead.objects.filter(id__in=qs_headlist).order_by('locus')

                self.fields['mprovlist'].widget.manu = instance

        except:
            msg = oErr.get_error_message()
            oErr.DoError("manuscriptForm")
        return None


class TemplateImportForm(forms.Form):
    """Allow choosing a template to copy sermons into an existing manuscript"""

    manu_id  = forms.CharField(required=False,
               widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Manuscript id...',  'style': 'width: 100%;'}))
    template = ModelChoiceField(queryset=None, required=False, 
               widget=TemplateOneWidget(attrs={'data-placeholder': 'Select a template...', 'style': 'width: 100%;', 'class': 'searching'}))

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(TemplateImportForm, self).__init__(*args, **kwargs)
        # Set the list of templates
        self.fields['template'].queryset = Template.objects.all().order_by('name', 'profile__user__username').distinct()


class TemplateForm(lilaModelForm):
    profileid = forms.CharField(required=False)

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Template
        fields = ['name', 'description']
        widgets={'name':        forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'description': forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'}),
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(TemplateForm, self).__init__(*args, **kwargs)
        oErr = ErrHandle()
        try:
            username = self.username
            team_group = self.team_group
            profile = Profile.get_user_profile(username)
            # Make sure the profile is set correctly
            self.fields['profileid'].initial = profile.id

            # Some fields are not required
            self.fields['name'].required = False
            self.fields['description'].required = False

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                # Adapt the profile if this is needed
                self.fields['profileid'].initial = instance.profile.id
        except:
            msg = oErr.get_error_message()
            oErr.DoError("TemplateForm")
        return None


class LocationForm(forms.ModelForm):
    loctypechooser = ModelMultipleChoiceField(queryset=None, required=False,
                 widget=LocTypeWidget(attrs={'data-placeholder': 'Location type...', 'style': 'width: 100%;'}))
    location_ta = forms.CharField(label=_("Location"), required=False, 
                 widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Location...',  
                                               'style': 'width: 100%;'}))
    locchooser = ModelMultipleChoiceField(queryset=None, required=False,
                 widget=LocationWidget(attrs={'data-placeholder': 'Location...', 'style': 'width: 100%;'}))
    locationlist = ModelMultipleChoiceField(queryset=None, required=False,
                 widget=LocationWidget(attrs={'data-placeholder': 'Select containing locations...', 'style': 'width: 100%;'}))
    typeaheads = ["locations"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Location
        fields = ['name', 'loctype']
        widgets={'name':        forms.TextInput(attrs={'style': 'width: 100%;'}),
                 #'loctype':     forms.Select(attrs={'style': 'width: 100%;'})
                 'loctype':     LoctypeOneWidget(attrs={'data-placeholder': 'Select one type...', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(LocationForm, self).__init__(*args, **kwargs)
        # No fields are required for best processing
        self.fields['name'].required = False
        self.fields['loctype'].required = False
        self.fields['loctypechooser'].required = False
        self.fields['name'].required = False
        self.fields['location_ta'].required = False
        self.fields['locchooser'].required = False
        qs = Location.objects.all().order_by('loctype__level', 'name')
        self.fields['locationlist'].queryset = qs
        self.fields['locchooser'].queryset = qs
        self.fields['loctypechooser'].queryset = LocationType.objects.all().order_by('level')
        # Get the instance
        if 'instance' in kwargs:
            # Set the items that *may* be shown
            instance = kwargs['instance']
            qs = Location.objects.exclude(id=instance.id).order_by('loctype__level', 'name')
            self.fields['locationlist'].queryset = qs
            self.fields['locationlist'].widget.queryset = qs
            self.fields['locchooser'].queryset = qs
            self.fields['locchooser'].widget.queryset = qs

            # Set the list of initial items
            my_list = [x.id for x in instance.hierarchy(False)]
            self.initial['locationlist'] = my_list
        else:
            self.fields['locationlist'].queryset = Location.objects.all().order_by('loctype__level', 'name')


class LocationRelForm(forms.ModelForm):
    partof_ta = forms.CharField(label=_("Part of"), required=False, 
                           widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Part of...',  'style': 'width: 100%;'}))
    partof = forms.CharField(required=False)
    typeaheads = ["locations"]

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = LocationRelation
        fields = ['container', 'contained']

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(LocationRelForm, self).__init__(*args, **kwargs)

        # Set other parameters
        self.fields['partof_ta'].required = False
        self.fields['partof'].required = False
        self.fields['container'].required = False
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']
            # Check if the initial name should be added
            if instance.container != None:
                self.fields['partof_ta'].initial = instance.container.get_loc_name()


class DaterangeForm(forms.ModelForm):
    newstart    = forms.CharField(required=False, help_text='editable', 
                widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Start...',  'style': 'width: 100%;'}))
    newfinish   = forms.CharField(required=False, help_text='editable', 
                widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Finish (optional)...',  'style': 'width: 100%;'}))
    oneref      = forms.ModelChoiceField(queryset=None, required=False, help_text="editable", 
                widget=LitrefWidget(attrs={'data-placeholder': 'Select one reference...', 'style': 'width: 100%;', 'class': 'searching'}))
    newpages    = forms.CharField(label=_("Page range"), required=False, help_text="editable", 
                widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Page range...',  'style': 'width: 100%;'}))
    action_log = ['yearstart', 'yearfinish', 'pages', 'reference']
    exclude = []    # ['newstart', 'newfinish', 'oneref', 'newpages']

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Daterange
        fields = ['yearstart', 'yearfinish', 'reference', 'pages']
        widgets={'reference':   forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'pages':       forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'yearstart':   forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'yearfinish':  forms.TextInput(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(DaterangeForm, self).__init__(*args, **kwargs)

        # Set other parameters
        self.fields['yearstart'].required = False
        self.fields['yearfinish'].required = False
        self.fields['reference'].required = False
        self.fields['pages'].required = False
        self.fields['newpages'].required = False
        self.fields['oneref'].required = False
        self.fields['oneref'].queryset = Litref.objects.exclude(full="").order_by('full')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class FeastForm(forms.ModelForm):
    # =========== MANUSCRIPT-specific ===========================
    manuidno    = forms.CharField(label=_("Manuscript"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching manuidnos input-sm', 'placeholder': 'Shelfmarks using wildcards...', 'style': 'width: 100%;'}))
    libname_ta  = forms.CharField(label=_("Library"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Name of library...',  'style': 'width: 100%;'}))
    prov_ta     = forms.CharField(label=_("Provenance"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Provenance (location)...',  'style': 'width: 100%;'}))
    origin_ta   = forms.CharField(label=_("Origin"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching origins input-sm', 'placeholder': 'Origin (location)...',  'style': 'width: 100%;'}))
    date_from   = forms.IntegerField(label=_("Date start"), required = False,
                widget=forms.TextInput(attrs={'placeholder': 'Starting from...',  'style': 'width: 30%;', 'class': 'searching'}))
    date_until  = forms.IntegerField(label=_("Date until"), required = False,
                widget=forms.TextInput(attrs={'placeholder': 'Until (including)...',  'style': 'width: 30%;', 'class': 'searching'}))
    manuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))
    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Feast
        fields = ['name', 'latname', 'feastdate']
        widgets={'name':        forms.TextInput(attrs={'placeholder': 'English name...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'latname':     forms.TextInput(attrs={'placeholder': 'Latin name...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'feastdate':   forms.TextInput(attrs={'placeholder': 'Date of the feast...', 'style': 'width: 100%;', 'class': 'searching'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(FeastForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Set other parameters
            self.fields['name'].required = False
            
            # M section
            self.fields['manuidlist'].queryset = Manuscript.objects.filter(mtype='man').order_by('idno')

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                if instance != None:
                    pass
                    ## Make sure the initials are taken over into new-elements
                    #self.fields['newintro'].initial = instance.intro
                    #self.fields['onebook'].initial = [ instance.book.id ]
                    #self.fields['newchvs'].initial = instance.chvslist
                    #self.fields['newadded'].initial = instance.added
        except:
            msg = oErr.get_error_message()
            oErr.DoError("BibRangeForm")

        # Return the response
        return None


class BibRangeForm(forms.ModelForm):
    newintro    = forms.CharField(required=False, help_text='editable', 
                widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Intro...',  'style': 'width: 100%;'}))
    onebook    = forms.ModelChoiceField(queryset=None, required=False, help_text="editable", 
                widget=BookWidget(attrs={'data-placeholder': 'Select a book...', 'style': 'width: 100%;', 'class': 'searching'}))
    newchvs    = forms.CharField(required=False, help_text='editable', 
                widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Chapter-verse list...',  'style': 'width: 100%;'}))
    newadded    = forms.CharField(required=False, help_text='editable', 
                widget=forms.TextInput(attrs={'class': 'input-sm', 'placeholder': 'Note...',  'style': 'width: 100%;'}))

    # =========== SEarching for bible references ===============
    bibrefbk    = forms.ModelChoiceField(queryset=None, required=False, 
                widget=BookWidget(attrs={'data-placeholder': 'Select a book...', 'style': 'width: 30%;', 'class': 'searching'}))
    bibrefchvs  = forms.CharField(label=_("Bible reference"), required=False, 
                widget=forms.TextInput(attrs={'class': 'searching', 'style': 'width: 30%;', 'placeholder': 'Use Chapter or Chapter:verse'}))

    # =========== MANUSCRIPT-specific ===========================
    manuidno    = forms.CharField(label=_("Manuscript"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching manuidnos input-sm', 'placeholder': 'Shelfmarks using wildcards...', 'style': 'width: 100%;'}))
    libname_ta  = forms.CharField(label=_("Library"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching libraries input-sm', 'placeholder': 'Name of library...',  'style': 'width: 100%;'}))
    prov_ta     = forms.CharField(label=_("Provenance"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching locations input-sm', 'placeholder': 'Provenance (location)...',  'style': 'width: 100%;'}))
    origin_ta   = forms.CharField(label=_("Origin"), required=False, 
                widget=forms.TextInput(attrs={'class': 'typeahead searching origins input-sm', 'placeholder': 'Origin (location)...',  'style': 'width: 100%;'}))
    date_from   = forms.IntegerField(label=_("Date start"), required = False,
                widget=forms.TextInput(attrs={'placeholder': 'Starting from...',  'style': 'width: 30%;', 'class': 'searching'}))
    date_until  = forms.IntegerField(label=_("Date until"), required = False,
                widget=forms.TextInput(attrs={'placeholder': 'Until (including)...',  'style': 'width: 30%;', 'class': 'searching'}))
    manuidlist  = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ManuidWidget(attrs={'data-placeholder': 'Select multiple manuscript identifiers...', 'style': 'width: 100%;'}))

    action_log = ['book', 'chvslist', 'intro', 'added']

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = BibRange
        fields = ['book', 'chvslist', 'intro', 'added']
        widgets={'book':        BookWidget(attrs={'data-placeholder': 'Select a book...', 'style': 'width: 100%;', 'class': 'searching'}),
                 'chvslist':    forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'intro':       forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'added':       forms.TextInput(attrs={'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(BibRangeForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Set other parameters
            self.fields['book'].required = False
            self.fields['chvslist'].required = False
            self.fields['intro'].required = False
            self.fields['added'].required = False
            self.fields['newintro'].required = False
            self.fields['onebook'].required = False
            self.fields['newchvs'].required = False
            self.fields['newadded'].required = False
            self.fields['onebook'].queryset = Book.objects.all().order_by('idno')
            self.fields['bibrefbk'].queryset = Book.objects.all().order_by('idno')
            
            # M section
            self.fields['manuidlist'].queryset = Manuscript.objects.filter(mtype='man').order_by('idno')

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                if instance != None:
                    # Make sure the initials are taken over into new-elements
                    self.fields['newintro'].initial = instance.intro
                    self.fields['onebook'].initial = [ instance.book.id ]
                    self.fields['newchvs'].initial = instance.chvslist
                    self.fields['newadded'].initial = instance.added
        except:
            msg = oErr.get_error_message()
            oErr.DoError("BibRangeForm")

        # Return the response
        return None
    

class SearchCollectionForm(forms.Form):
    country = forms.CharField(label=_("Country"), required=False)
    city = forms.CharField(label=_("City"), required=False)
    library = forms.CharField(label=_("Library"), required=False)
    signature = forms.CharField(label=_("Signature code"), required=False)


class ReportEditForm(forms.ModelForm):
    userlist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=UserWidget(attrs={'data-placeholder': 'Select multiple users...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        model = Report
        fields = ['user', 'created', 'reptype', 'contents']
        widgets={'user':         forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'created':      forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'reptype':      forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'contents':     forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(ReportEditForm, self).__init__(*args, **kwargs)

        # Some fields are not required
        self.fields['created'].required = False
        self.fields['user'].required = False
        self.fields['reptype'].required = False
        self.fields['contents'].required = False
        
        # Set queryset(s) - for listview
        self.fields['userlist'].queryset = User.objects.all().order_by('username')
        

class SourceEditForm(forms.ModelForm):
    profile_ta = forms.CharField(label=_("Collector"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching users input-sm', 'placeholder': 'Collector(s)...', 'style': 'width: 100%;'}))
    profilelist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProfileWidget(attrs={'data-placeholder': 'Select collector(s)...', 'style': 'width: 100%;', 'class': 'searching'}))
    manulist = ModelChoiceField(queryset=None, required=False,
                 widget=ManuidOneWidget(attrs={'data-placeholder': 'Select corresponding manuscript...', 'style': 'width: 100%;'}))

    class Meta:
        model = SourceInfo
        fields = ['profile', 'code', 'url']
        widgets={'url':         forms.TextInput(attrs={'style': 'width: 100%;'}),
                 'code':        forms.Textarea(attrs={'rows': 1, 'cols': 40, 'style': 'height: 40px; width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(SourceEditForm, self).__init__(*args, **kwargs)

        oErr = ErrHandle()
        try:
            # Some fields are not required
            self.fields['url'].required = False
            self.fields['code'].required = False
            self.fields['profile_ta'].required = False
            # Set the initial value for the profile
            self.fields['profile'].required = False
        
            # Set queryset(s) - for listview
            self.fields['profilelist'].queryset = Profile.objects.all().order_by('user')
            # Set queryset(s) - for details view
            self.fields['manulist'].queryset = Manuscript.objects.none()

            # Get the instance
            if 'instance' in kwargs:
                instance = kwargs['instance']
                # Adapt the profile if this is needed
                self.fields['profile'].initial = instance.profile.id
                # Give a choice of manuscripts that are not linked to a SOURCE yet
                qs = Manuscript.objects.filter(mtype='man', source__isnull=True).order_by('idno')
                self.fields['manulist'].queryset = qs
                self.fields['manulist'].widget.queryset = qs
        except:
            msg = oErr.get_error_message()
            oErr.DoError("SourceEditForm")
        return None


class AuthorEditForm(forms.ModelForm):

    class Meta:
        model = Author
        fields = ['name', 'abbr']
        widgets={'name':    forms.TextInput(attrs={'placeholder': 'Name of this author', 'style': 'width: 100%;'}),
                 'abbr':    forms.TextInput(attrs={'placeholder': 'Abbreviation as e.g. used in Gryson', 'style': 'width: 100%;'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(AuthorEditForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False
        self.fields['abbr'].required = False


class AuthorSearchForm(forms.ModelForm):
    author_ta = forms.CharField(label=_("Author"), required=False,
                widget=forms.TextInput(attrs={'class': 'typeahead searching authors input-sm', 'placeholder': 'Author namee(s)...', 'style': 'width: 100%;'}))
    authlist     = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=AuthorWidget(attrs={'data-placeholder': 'Select multiple authors...', 'style': 'width: 100%;', 'class': 'searching'}))
    typeaheads = ["authors"]


    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Author
        fields = ('name',)
        widgets={'name':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(AuthorSearchForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['name'].required = False

        self.fields['authlist'].queryset = Author.objects.all().order_by('name')
        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class CommentForm(forms.ModelForm):
    """A form to upload a user-comment"""

    # otype = forms.CharField(label=_("Object type"), required=False)
    objid = forms.CharField(label=_("Object id"), required=False)
    profilelist = ModelMultipleChoiceField(queryset=None, required=False, 
                widget=ProfileWidget(attrs={'data-placeholder': 'Select multiple users...', 'style': 'width: 100%;', 'class': 'searching'}))

    class Meta:
        ATTRS_FOR_FORMS = {'class': 'form-control'};

        model = Comment
        fields = ['content', 'profile', 'otype']
        widgets={'content':        forms.TextInput(attrs={'style': 'width: 100%;', 'class': 'searching'})
                 }

    def __init__(self, *args, **kwargs):
        # Start by executing the standard handling
        super(CommentForm, self).__init__(*args, **kwargs)
        # Some fields are not required
        self.fields['profile'].required = False
        self.fields['content'].required = False
        self.fields['otype'].required = False
        self.fields['objid'].required = False
        self.fields['profilelist'].required = False

        # Initialize querysets
        self.fields['profilelist'].queryset = Profile.objects.all().order_by('user__username')

        # Get the instance
        if 'instance' in kwargs:
            instance = kwargs['instance']


class UploadFileForm(forms.Form):
    """This is for uploading just one file"""

    file_source = forms.FileField(label="Specify which file should be loaded")


class UploadFilesForm(forms.Form):
    """This is for uploading multiple files"""

    files_field = forms.FileField(label="Specify which file(s) should be loaded",
                                  widget=forms.ClearableFileInput(attrs={'multiple': True}))


class SearchUrlForm(forms.Form):
    """Specify an URL"""

    search_url = forms.URLField(label="Give the URL",
                                widget=forms.URLInput(attrs={'placeholder': 'Enter the search URL...', 'style': 'width: 100%;'}))
