"""
Definition of urls for solemne.
"""

from datetime import datetime
import django
import django.contrib.auth.views
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import include # , url # , handler404, handler400, handler403, handler500
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseNotFound
from django.urls import path
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy, re_path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import RedirectView

# ================================ PROJECT SPECIFIC STUFF ==============================================

import solemne.seeker.forms
import solemne.seeker.views
import solemne.seeker.views_main
import solemne.seeker.views_api
import solemne.seeker.views_ta
import solemne.reader.views
import solemne.cms.views

from solemne.basic.models import Custom
from solemne import views
from solemne.seeker.views import *
from solemne.seeker.views_main import *
from solemne.seeker.views_ta import *
from solemne.seeker.views_api import *
from solemne.seeker.visualizations import *
from solemne.reader.views import *
from solemne.reader.excel import ManuscriptUploadExcel, ManuscriptUploadJson, ManuscriptUploadCanwits, \
    AustatUploadExcel, AuworkUploadExcel, ColwitUploadExcel
from solemne.cms.views import *

# Import from solemne as a whole
from solemne.settings import APP_PREFIX

# Other Django stuff
admin.autodiscover()


# Set admin stie information
admin.site.site_header = "The Social Life of Early Medieval Normative Texts"
admin.site.site_title = "solemne Admin"

pfx = APP_PREFIX
use_testapp = False

# ================ Custom error handling when debugging =============
def custom_page_not_found(request, exception=None):
    return solemne.seeker.views.view_404(request)

handler404 = custom_page_not_found

urlpatterns = [
    # ============ STANDARD VIEWS =====================
    re_path(r'^$', solemne.seeker.views.home, name='home'),
    path("404/", custom_page_not_found),
    re_path(r'^favicon\.ico$',RedirectView.as_view(url='/static/seeker/content/favicon.ico')),
    re_path(r'^contact$', solemne.seeker.views.contact, name='contact'),
    re_path(r'^about', solemne.seeker.views.about, name='about'),
    re_path(r'^short', solemne.seeker.views.about, name='short'),
    re_path(r'^guide', solemne.seeker.views.guide, name='guide'),
    re_path(r'^mysolemne', solemne.seeker.views.mysolemne, name='mysolemne'),
    re_path(r'^technical', solemne.seeker.views.technical, name='technical'),
    re_path(r'^bibliography', solemne.seeker.views.bibliography, name='bibliography'),
    re_path(r'^nlogin', solemne.seeker.views.nlogin, name='nlogin'),

    # =============== VIEWS_MAIN ==========================

    re_path(r'^manuscript/list', ManuscriptListView.as_view(), name='manuscript_list'),
    re_path(r'^manuscript/details(?:/(?P<pk>\d+))?/$', ManuscriptDetails.as_view(), name='manuscript_details'),
    re_path(r'^manuscript/edit(?:/(?P<pk>\d+))?/$', ManuscriptEdit.as_view(), name='manuscript_edit'),
    re_path(r'^manuscript/hierarchy(?:/(?P<pk>\d+))?/$', ManuscriptHierarchy.as_view(), name='manuscript_hierarchy'),
    re_path(r'^manuscript/download(?:/(?P<pk>\d+))?/$', ManuscriptDownload.as_view(), name='manuscript_download'),
    re_path(r'^manuscript/import/canwits(?:/(?P<pk>\d+))?/$', ManuscriptUploadCanwits.as_view(), name='manuscript_upload_canwits'),
    re_path(r'^manuscript/import/excel/$', ManuscriptUploadExcel.as_view(), name='manuscript_upload_excel'),
    re_path(r'^manuscript/import/json/$', ManuscriptUploadJson.as_view(), name='manuscript_upload_json'),
    re_path(r'^manuscript/codico/$', ManuscriptCodico.as_view(), name='manuscript_codico'),

    re_path(r'^codico/list', CodicoListView.as_view(), name='codico_list'),
    re_path(r'^codico/details(?:/(?P<pk>\d+))?/$', CodicoDetails.as_view(), name='codico_details'),
    re_path(r'^codico/edit(?:/(?P<pk>\d+))?/$', CodicoEdit.as_view(), name='codico_edit'),

    re_path(r'^codhead/details(?:/(?P<pk>\d+))?/$', CodheadDetails.as_view(), name='codhead_details'),
    re_path(r'^codhead/edit(?:/(?P<pk>\d+))?/$', CodheadEdit.as_view(), name='codhead_edit'),
    re_path(r'^codhead/list', CodheadListView.as_view(), name='codhead_list'),
    
    re_path(r'^canwit/details(?:/(?P<pk>\d+))?/$', CanwitDetails.as_view(), name='canwit_details'),
    re_path(r'^canwit/edit(?:/(?P<pk>\d+))?/$', CanwitEdit.as_view(), name='canwit_edit'),
    re_path(r'^canwit/list', CanwitListView.as_view(), name='canwit_list'),

    re_path(r'^canwitau/details(?:/(?P<pk>\d+))?/$', CanwitAustatDetails.as_view(), name='canwitaustat_details'),
    re_path(r'^canwitau/edit(?:/(?P<pk>\d+))?/$', CanwitAustatEdit.as_view(), name='canwitaustat_edit'),
    
    re_path(r'^caned/details(?:/(?P<pk>\d+))?/$', CanedDetails.as_view(), name='caned_details'),
    re_path(r'^caned/edit(?:/(?P<pk>\d+))?/$', CanedEdit.as_view(), name='caned_edit'),
    re_path(r'^caned/list', CanedListView.as_view(), name='caned_list'),
    
    re_path(r'^colwit/details(?:/(?P<pk>\d+))?/$', ColwitDetails.as_view(), name='colwit_details'),
    re_path(r'^colwit/edit(?:/(?P<pk>\d+))?/$', ColwitEdit.as_view(), name='colwit_edit'),
    re_path(r'^colwit/list', ColwitListView.as_view(), name='colwit_list'),
    re_path(r'^colwit/import/excel/$', ColwitUploadExcel.as_view(), name='colwit_upload_excel'),
    
    re_path(r'^austat/list', AustatListView.as_view(), name='austat_list'),
    re_path(r'^austat/details(?:/(?P<pk>\d+))?/$', AustatDetails.as_view(), name='austat_details'),
    re_path(r'^austat/edit(?:/(?P<pk>\d+))?/$', AustatEdit.as_view(), name='austat_edit'),
    re_path(r'^austat/import/excel/$', AustatUploadExcel.as_view(), name='austat_upload_excel'),
    re_path(r'^austat/pca(?:/(?P<pk>\d+))?/$', AustatPca.as_view(), name='austat_pca'),
    re_path(r'^austat/graph(?:/(?P<pk>\d+))?/$', AustatGraph.as_view(), name='austat_graph'),
    re_path(r'^austat/trans(?:/(?P<pk>\d+))?/$', AustatTrans.as_view(), name='austat_trans'),
    re_path(r'^austat/overlap(?:/(?P<pk>\d+))?/$', AustatOverlap.as_view(), name='austat_overlap'),
    re_path(r'^austat/drag/start(?:/(?P<pk>\d+))?/$', AustatDragStart.as_view(), name='austat_drag_start'),
    re_path(r'^austat/drag/end(?:/(?P<pk>\d+))?/$', AustatDragEnd.as_view(), name='austat_drag_end'),
    re_path(r'^austat/drag/drop(?:/(?P<pk>\d+))?/$', AustatDragDrop.as_view(), name='austat_drag_drop'),

    re_path(r'^austat/scount/histo/download', AustatScountDownload.as_view(), name='austat_scount_download'),
    re_path(r'^austat/graph/download(?:/(?P<pk>\d+))?/$', AustatGraphDownload.as_view(), name='austat_graph_download'),
    re_path(r'^austat/trans/download(?:/(?P<pk>\d+))?/$', AustatTransDownload.as_view(), name='austat_trans_download'),
    re_path(r'^austat/overlap/download(?:/(?P<pk>\d+))?/$', AustatOverlapDownload.as_view(), name='austat_overlap_download'),

    re_path(r'^dataset/private/list', CollectionListView.as_view(prefix="priv"), name='collpriv_list'),
    re_path(r'^dataset/public/list', CollectionListView.as_view(prefix="publ"), name='collpubl_list'),
    re_path(r'^collection/hist/list', CollectionListView.as_view(prefix="hist"), name='collhist_list'),
    re_path(r'^collection/any/list', CollectionListView.as_view(prefix="any"), name='collany_list'),
    re_path(r'^collection/austat/list', CollectionListView.as_view(prefix="austat"), name='collaustat_list'),

    re_path(r'^dataset/private/details(?:/(?P<pk>\d+))?/$', CollPrivDetails.as_view(), name='collpriv_details'),
    re_path(r'^dataset/public/details(?:/(?P<pk>\d+))?/$', CollPublDetails.as_view(), name='collpubl_details'),
    re_path(r'^collection/hist/details(?:/(?P<pk>\d+))?/$', CollHistDetails.as_view(), name='collhist_details'),
    re_path(r'^collection/any/details(?:/(?P<pk>\d+))?/$', CollAnyDetails.as_view(), name='collany_details'),
    re_path(r'^collection/austat/details(?:/(?P<pk>\d+))?/$', CollSuperDetails.as_view(), name='collsuper_details'),

    re_path(r'^dataset/private/edit(?:/(?P<pk>\d+))?/$', CollPrivEdit.as_view(), name='collpriv_edit'),
    re_path(r'^dataset/public/edit(?:/(?P<pk>\d+))?/$', CollPublEdit.as_view(), name='collpubl_edit'),
    re_path(r'^collection/hist/edit(?:/(?P<pk>\d+))?/$', CollHistEdit.as_view(), name='collhist_edit'),
    re_path(r'^collection/any/edit(?:/(?P<pk>\d+))?/$', CollAnyEdit.as_view(), name='collany_edit'),
    re_path(r'^collection/austat/edit(?:/(?P<pk>\d+))?/$', CollSuperEdit.as_view(), name='collsuper_edit'),
    
    re_path(r'^dataset/elevate(?:/(?P<pk>\d+))?/$', CollHistElevate.as_view(), name='collhist_elevate'),
    re_path(r'^collection/hist/manuscript(?:/(?P<pk>\d+))?/$', CollHistManu.as_view(), name='collhist_manu'),
    re_path(r'^collection/hist/template(?:/(?P<pk>\d+))?/$', CollHistTemp.as_view(), name='collhist_temp'),
    re_path(r'^collection/hist/compare(?:/(?P<pk>\d+))?/$', CollHistCompare.as_view(), name='collhist_compare'),
    
    re_path(r'^basket/canwit/update', BasketUpdate.as_view(), name='basket_update'),
    re_path(r'^basket/canwit/show', BasketView.as_view(), name='basket_show'),

    re_path(r'^basket/manu/update', BasketUpdateManu.as_view(), name='basket_update_manu'),
    re_path(r'^basket/manu/show', BasketViewManu.as_view(), name='basket_show_manu'),

    re_path(r'^basket/austat/update', BasketUpdateSuper.as_view(), name='basket_update_austat'),
    re_path(r'^basket/austat/show', BasketViewSuper.as_view(), name='basket_show_austat'),

    # ============================== CMS VIEWS ========================================

    re_path(r'^cpage/list', CpageListView.as_view(), name='cpage_list'),
    re_path(r'^cpage/details(?:/(?P<pk>\d+))?/$', CpageDetails.as_view(), name='cpage_details'),
    re_path(r'^cpage/edit(?:/(?P<pk>\d+))?/$', CpageEdit.as_view(), name='cpage_edit'),
    re_path(r'^cpage/clocation/add(?:/(?P<pk>\d+))?/$', CpageAdd.as_view(), name='cpage_add_loc'),

    re_path(r'^clocation/list', ClocationListView.as_view(), name='clocation_list'),
    re_path(r'^clocation/details(?:/(?P<pk>\d+))?/$', ClocationDetails.as_view(), name='clocation_details'),
    re_path(r'^clocation/edit(?:/(?P<pk>\d+))?/$', ClocationEdit.as_view(), name='clocation_edit'),
    re_path(r'^clocation/citem/add(?:/(?P<pk>\d+))?/$', ClocationAdd.as_view(), name='clocation_add_item'),

    re_path(r'^citem/list', CitemListView.as_view(), name='citem_list'),
    re_path(r'^citem/details(?:/(?P<pk>\d+))?/$', CitemDetails.as_view(), name='citem_details'),
    re_path(r'^citem/edit(?:/(?P<pk>\d+))?/$', CitemEdit.as_view(), name='citem_edit'),

    
    # ============================== VIEWS ============================================
    
    re_path(r'^libraries/download', LibraryListDownload.as_view(), name='library_results'),
    re_path(r'^authors/download', AuthorListDownload.as_view(), name='author_results'),

    re_path(r'^location/list', LocationListView.as_view(), name='location_list'),
    re_path(r'^location/details(?:/(?P<pk>\d+))?/$', LocationDetails.as_view(), name='location_details'),
    re_path(r'^location/edit(?:/(?P<pk>\d+))?/$', LocationEdit.as_view(), name='location_edit'),

    re_path(r'^origin/list', OriginListView.as_view(), name='origin_list'),
    re_path(r'^origin/details(?:/(?P<pk>\d+))?/$', OriginDetails.as_view(), name='origin_details'),
    re_path(r'^origin/edit(?:/(?P<pk>\d+))?/$', OriginEdit.as_view(), name='origin_edit'),
    re_path(r'^origincod/details(?:/(?P<pk>\d+))?/$', OriginCodDetails.as_view(), name='origincod_details'),
    re_path(r'^origincod/edit(?:/(?P<pk>\d+))?/$', OriginCodEdit.as_view(), name='origincod_edit'),

    re_path(r'^library/list', LibraryListView.as_view(), name='library_list'),
    re_path(r'^library/details(?:/(?P<pk>\d+))?/$', LibraryDetails.as_view(), name='library_details'),
    re_path(r'^library/edit(?:/(?P<pk>\d+))?/$', LibraryEdit.as_view(), name='library_edit'),

    re_path(r'^author/list', AuthorListView.as_view(), name='author_list'),
    re_path(r'^author/details(?:/(?P<pk>\d+))?/$', AuthorDetails.as_view(), name='author_details'),
    re_path(r'^author/edit(?:/(?P<pk>\d+))?/$', AuthorEdit.as_view(), name='author_edit'),

    re_path(r'^report/list', ReportListView.as_view(), name='report_list'),
    re_path(r'^report/details(?:/(?P<pk>\d+))?/$', ReportDetails.as_view(), name='report_details'),
    re_path(r'^report/edit(?:/(?P<pk>\d+))?/$', ReportEdit.as_view(), name='report_edit'),
    re_path(r'^report/download(?:/(?P<pk>\d+))?/$', ReportDownload.as_view(), name='report_results'),

    re_path(r'^literature/list', LitRefListView.as_view(), name='literature_list'),

    re_path(r'^keyword/list', KeywordListView.as_view(), name='keyword_list'),
    re_path(r'^keyword/details(?:/(?P<pk>\d+))?/$', KeywordDetails.as_view(), name='keyword_details'),
    re_path(r'^keyword/edit(?:/(?P<pk>\d+))?/$', KeywordEdit.as_view(), name='keyword_edit'),

    re_path(r'^genre/list', GenreListView.as_view(), name='genre_list'),
    re_path(r'^genre/details(?:/(?P<pk>\d+))?/$', GenreDetails.as_view(), name='genre_details'),
    re_path(r'^genre/edit(?:/(?P<pk>\d+))?/$', GenreEdit.as_view(), name='genre_edit'),

    re_path(r'^litref/list', LitrefListView.as_view(), name='litref_list'),
    re_path(r'^litref/details(?:/(?P<pk>\d+))?/$', LitrefDetails.as_view(), name='litref_details'),
    re_path(r'^litref/edit(?:/(?P<pk>\d+))?/$', LitrefEdit.as_view(), name='litref_edit'),

    re_path(r'^auwork/list', AuworkListView.as_view(), name='auwork_list'),
    re_path(r'^auwork/details(?:/(?P<pk>\d+))?/$', AuworkDetails.as_view(), name='auwork_details'),
    re_path(r'^auwork/edit(?:/(?P<pk>\d+))?/$', AuworkEdit.as_view(), name='auwork_edit'),
    re_path(r'^auwork/import/excel/$', AuworkUploadExcel.as_view(), name='auwork_upload_excel'),

    re_path(r'^userkeyword/list', UserKeywordListView.as_view(), name='userkeyword_list'),
    re_path(r'^userkeyword/details(?:/(?P<pk>\d+))?/$', UserKeywordDetails.as_view(), name='userkeyword_details'),
    re_path(r'^userkeyword/edit(?:/(?P<pk>\d+))?/$', UserKeywordEdit.as_view(), name='userkeyword_edit'),

    re_path(r'^provenance/list', ProvenanceListView.as_view(), name='provenance_list'),
    re_path(r'^provenance/details(?:/(?P<pk>\d+))?/$', ProvenanceDetails.as_view(), name='provenance_details'),
    re_path(r'^provenance/edit(?:/(?P<pk>\d+))?/$', ProvenanceEdit.as_view(), name='provenance_edit'),
    re_path(r'^provman/details(?:/(?P<pk>\d+))?/$', ProvenanceManDetails.as_view(), name='provenanceman_details'),
    re_path(r'^provman/edit(?:/(?P<pk>\d+))?/$', ProvenanceManEdit.as_view(), name='provenanceman_edit'),
    re_path(r'^provcod/details(?:/(?P<pk>\d+))?/$', ProvenanceCodDetails.as_view(), name='provenancecod_details'),
    re_path(r'^provcod/edit(?:/(?P<pk>\d+))?/$', ProvenanceCodEdit.as_view(), name='provenancecod_edit'),

    re_path(r'^comment/list', CommentListView.as_view(), name='comment_list'),
    re_path(r'^comment/details(?:/(?P<pk>\d+))?/$', CommentDetails.as_view(), name='comment_details'),
    re_path(r'^comment/edit(?:/(?P<pk>\d+))?/$', CommentEdit.as_view(), name='comment_edit'),
    re_path(r'^comment/send/$', CommentSend.as_view(), name='comment_send'),

    re_path(r'^bibrange/list', BibRangeListView.as_view(), name='bibrange_list'),
    re_path(r'^bibrange/details(?:/(?P<pk>\d+))?/$', BibRangeDetails.as_view(), name='bibrange_details'),
    re_path(r'^bibrange/edit(?:/(?P<pk>\d+))?/$', BibRangeEdit.as_view(), name='bibrange_edit'),

    re_path(r'^feast/list', FeastListView.as_view(), name='feast_list'),
    re_path(r'^feast/details(?:/(?P<pk>\d+))?/$', FeastDetails.as_view(), name='feast_details'),
    re_path(r'^feast/edit(?:/(?P<pk>\d+))?/$', FeastEdit.as_view(), name='feast_edit'),

    re_path(r'^profile/list', ProfileListView.as_view(), name='profile_list'),
    re_path(r'^profile/details(?:/(?P<pk>\d+))?/$', ProfileDetails.as_view(), name='profile_details'),
    re_path(r'^profile/edit(?:/(?P<pk>\d+))?/$', ProfileEdit.as_view(), name='profile_edit'),
    re_path(r'^default/details(?:/(?P<pk>\d+))?/$', DefaultDetails.as_view(), name='default_details'), 
    re_path(r'^default/edit(?:/(?P<pk>\d+))?/$', DefaultEdit.as_view(), name='default_edit'), 

    re_path(r'^project/list', ProjectListView.as_view(), name='project_list'), 
    re_path(r'^project/details(?:/(?P<pk>\d+))?/$', ProjectDetails.as_view(), name='project_details'), 
    re_path(r'^project/edit(?:/(?P<pk>\d+))?/$', ProjectEdit.as_view(), name='project_edit'), 

    re_path(r'^source/list', SourceListView.as_view(), name='source_list'),
    re_path(r'^source/details(?:/(?P<pk>\d+))?/$', SourceDetails.as_view(), name='source_details'),
    re_path(r'^source/edit(?:/(?P<pk>\d+))?/$', SourceEdit.as_view(), name='source_edit'),

    re_path(r'^template/list', TemplateListView.as_view(), name='template_list'),
    re_path(r'^template/details(?:/(?P<pk>\d+))?/$', TemplateDetails.as_view(), name='template_details'),
    re_path(r'^template/edit(?:/(?P<pk>\d+))?/$', TemplateEdit.as_view(), name='template_edit'),
    re_path(r'^template/apply(?:/(?P<pk>\d+))?/$', TemplateApply.as_view(), name='template_apply'),
    re_path(r'^template/import/$', TemplateImport.as_view(), name='template_import'),

    # ============ TYPEAHEAD VIEWS ============================================

    re_path(r'^api/countries/$', solemne.seeker.views_ta.get_countries, name='api_countries'),
    re_path(r'^api/cities/$', solemne.seeker.views_ta.get_cities, name='api_cities'),
    re_path(r'^api/libraries/$', solemne.seeker.views_ta.get_libraries, name='api_libraries'),
    re_path(r'^api/origins/$', solemne.seeker.views_ta.get_origins, name='api_origins'),
    re_path(r'^api/locations/$', solemne.seeker.views_ta.get_locations, name='api_locations'),
    re_path(r'^api/litrefs/$', solemne.seeker.views_ta.get_litrefs, name='api_litrefs'),
    re_path(r'^api/litref/$', solemne.seeker.views_ta.get_litref, name='api_litref'),
    re_path(r'^api/aslink/$', solemne.seeker.views_ta.get_aslink, name='api_aslink'),
    re_path(r'^api/as2as/$', solemne.seeker.views_ta.get_as2as, name='api_as2as'),
    re_path(r'^api/as/$', solemne.seeker.views_ta.get_as, name='api_as'),
    re_path(r'^api/asdist/$', solemne.seeker.views_ta.get_asdist, name='api_asdist'),
    re_path(r'^api/sermosig/$', solemne.seeker.views_ta.get_sermosig, name='api_sermosig'),
    re_path(r'^api/authors/list/$', solemne.seeker.views_ta.get_authors, name='api_authors'),
    re_path(r'^api/cwftexts/$', solemne.seeker.views_ta.get_cwftexts, name='api_cwtexts'),
    re_path(r'^api/cwftrans/$', solemne.seeker.views_ta.get_cwftrans, name='api_cwftrans'),
    re_path(r'^api/asftexts/$', solemne.seeker.views_ta.get_asftexts, name='api_asftexts'),
    re_path(r'^api/asftrans/$', solemne.seeker.views_ta.get_asftrans, name='api_asftrans'),
    re_path(r'^api/srmsignatures/$', solemne.seeker.views_ta.get_srmsignatures, name='api_srmsignatures'),
    re_path(r'^api/keywords/$', solemne.seeker.views_ta.get_keywords, name='api_keywords'),
    re_path(r'^api/collections/$', solemne.seeker.views_ta.get_collections, name='api_collections'),
    re_path(r'^api/manuidnos/$', solemne.seeker.views_ta.get_manuidnos, name='api_manuidnos'),

    # ============ OTHER API AND SYNC VIEWS ============================================

    re_path(r'^api/import/authors/$', solemne.seeker.views_api.import_authors, name='import_authors'),

    re_path(r'^api/import/pdf_lit/$', solemne.seeker.views_api.do_create_pdf_lit, name='create_pdf_lit'), 
    re_path(r'^api/import/pdf_edi/$', solemne.seeker.views_api.do_create_pdf_edi, name='create_pdf_edi'), 
    re_path(r'^api/import/pdf_manu/$', solemne.seeker.views_api.do_create_pdf_manu, name='create_pdf_manu'),

    re_path(r'^sync/solemne/$', solemne.seeker.views_api.sync_solemne, name='sync_solemne'),
    re_path(r'^sync/start/$', solemne.seeker.views_api.sync_start, name='sync_start'),
    re_path(r'^sync/progress/$', solemne.seeker.views_api.sync_progress, name='sync_progress'),
    re_path(r'^sync/zotero/$', solemne.seeker.views_api.redo_zotero, name='sync_zotero'),
     
    # ================ Any READER APP URLs should come here =======================================


    # =============================================================================================

    # For working with ModelWidgets from the select2 package https://django-select2.readthedocs.io
    re_path(r'^select2/', include('django_select2.urls')),

    re_path(r'^definitions$', RedirectView.as_view(url='/'+pfx+'admin/'), name='definitions'),
    re_path(r'^signup/$', solemne.seeker.views.signup, name='signup'),

    re_path(r'^login/user/(?P<user_id>\w[\w\d_]+)$', solemne.seeker.views.login_as_user, name='login_as'),

    re_path(r'^login/$', LoginView.as_view
        (
            template_name= 'login.html',
            authentication_form= solemne.seeker.forms.BootstrapAuthenticationForm,
            extra_context= {'title': 'Log in','year': datetime.now().year,}
        ),
        name='login'),
    re_path(r'^logout$',  LogoutView.as_view(next_page=reverse_lazy('home')), name='logout'),

    # Uncomment the next line to enable the admin:
    re_path(r'^admin/', admin.site.urls, name='admin_base'),
]

