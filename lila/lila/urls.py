"""
Definition of urls for lila.
"""

from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import include, url # , handler404, handler400, handler403, handler500
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseNotFound
from django.urls import path
import django.contrib.auth.views
import django

import lila.seeker.forms
import lila.seeker.views
import lila.seeker.views_main
import lila.seeker.views_api
import lila.seeker.views_ta
import lila.reader.views
from lila import views
from lila.seeker.views import *
from lila.seeker.views_main import *
from lila.seeker.views_ta import *
from lila.seeker.views_api import *
from lila.seeker.visualizations import *
from lila.reader.views import *
from lila.reader.excel import ManuscriptUploadExcel, ManuscriptUploadJson, ManuscriptUploadGalway, ManuscriptUploadCanwits

# Import from lila as a whole
from lila.settings import APP_PREFIX

# Other Django stuff
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import RedirectView

admin.autodiscover()


# Set admin stie information
admin.site.site_header = "Patristic Sermons in the Middle Ages"
admin.site.site_title = "lila Admin"

pfx = APP_PREFIX
use_testapp = False

# ================ Custom error handling when debugging =============
def custom_page_not_found(request):
    return lila.seeker.views.view_404(request)

urlpatterns = [
    # ============ STANDARD VIEWS =====================
    url(r'^$', lila.seeker.views.home, name='home'),
    path("404/", custom_page_not_found),
    url(r'^favicon\.ico$',RedirectView.as_view(url='/static/seeker/content/favicon.ico')),
    url(r'^contact$', lila.seeker.views.contact, name='contact'),
    url(r'^about', lila.seeker.views.about, name='about'),
    url(r'^short', lila.seeker.views.about, name='short'),
    url(r'^guide', lila.seeker.views.guide, name='guide'),
    url(r'^mylila', lila.seeker.views.mylila, name='mylila'),
    url(r'^technical', lila.seeker.views.technical, name='technical'),
    url(r'^bibliography', lila.seeker.views.bibliography, name='bibliography'),
    url(r'^nlogin', lila.seeker.views.nlogin, name='nlogin'),

    # =============== VIEWS_MAIN ==========================

    url(r'^manuscript/list', ManuscriptListView.as_view(), name='manuscript_list'),
    url(r'^manuscript/details(?:/(?P<pk>\d+))?/$', ManuscriptDetails.as_view(), name='manuscript_details'),
    url(r'^manuscript/edit(?:/(?P<pk>\d+))?/$', ManuscriptEdit.as_view(), name='manuscript_edit'),
    url(r'^manuscript/hierarchy(?:/(?P<pk>\d+))?/$', ManuscriptHierarchy.as_view(), name='manuscript_hierarchy'),
    url(r'^manuscript/download(?:/(?P<pk>\d+))?/$', ManuscriptDownload.as_view(), name='manuscript_download'),
    url(r'^manuscript/import/canwits(?:/(?P<pk>\d+))?/$', ManuscriptUploadCanwits.as_view(), name='manuscript_upload_canwits'),
    url(r'^manuscript/import/excel/$', ManuscriptUploadExcel.as_view(), name='manuscript_upload_excel'),
    url(r'^manuscript/import/json/$', ManuscriptUploadJson.as_view(), name='manuscript_upload_json'),
    url(r'^manuscript/import/galway/$', ManuscriptUploadGalway.as_view(), name='manuscript_upload_galway'),
    url(r'^manuscript/codico/$', ManuscriptCodico.as_view(), name='manuscript_codico'),

    url(r'^codico/list', CodicoListView.as_view(), name='codico_list'),
    url(r'^codico/details(?:/(?P<pk>\d+))?/$', CodicoDetails.as_view(), name='codico_details'),
    url(r'^codico/edit(?:/(?P<pk>\d+))?/$', CodicoEdit.as_view(), name='codico_edit'),

    url(r'^codhead/details(?:/(?P<pk>\d+))?/$', CodheadDetails.as_view(), name='codhead_details'),
    url(r'^codhead/edit(?:/(?P<pk>\d+))?/$', CodheadEdit.as_view(), name='codhead_edit'),
    url(r'^codhead/list', CodheadListView.as_view(), name='codhead_list'),
    
    url(r'^canwit/details(?:/(?P<pk>\d+))?/$', CanwitDetails.as_view(), name='canwit_details'),
    url(r'^canwit/edit(?:/(?P<pk>\d+))?/$', CanwitEdit.as_view(), name='canwit_edit'),
    url(r'^canwit/list', CanwitListView.as_view(), name='canwit_list'),
    
    url(r'^colwit/details(?:/(?P<pk>\d+))?/$', ColwitDetails.as_view(), name='colwit_details'),
    url(r'^colwit/edit(?:/(?P<pk>\d+))?/$', ColwitEdit.as_view(), name='colwit_edit'),
    url(r'^colwit/list', ColwitListView.as_view(), name='colwit_list'),
    
    url(r'^austat/list', AustatListView.as_view(), name='austat_list'),
    url(r'^austat/details(?:/(?P<pk>\d+))?/$', AustatDetails.as_view(), name='austat_details'),
    url(r'^austat/edit(?:/(?P<pk>\d+))?/$', AustatEdit.as_view(), name='austat_edit'),
    url(r'^austat/pca(?:/(?P<pk>\d+))?/$', AustatPca.as_view(), name='austat_pca'),
    url(r'^austat/graph(?:/(?P<pk>\d+))?/$', AustatGraph.as_view(), name='austat_graph'),
    url(r'^austat/trans(?:/(?P<pk>\d+))?/$', AustatTrans.as_view(), name='austat_trans'),
    url(r'^austat/overlap(?:/(?P<pk>\d+))?/$', AustatOverlap.as_view(), name='austat_overlap'),

    url(r'^austat/scount/histo/download', AustatScountDownload.as_view(), name='austat_scount_download'),
    url(r'^austat/graph/download(?:/(?P<pk>\d+))?/$', AustatGraphDownload.as_view(), name='austat_graph_download'),
    url(r'^austat/trans/download(?:/(?P<pk>\d+))?/$', AustatTransDownload.as_view(), name='austat_trans_download'),
    url(r'^austat/overlap/download(?:/(?P<pk>\d+))?/$', AustatOverlapDownload.as_view(), name='austat_overlap_download'),

    url(r'^dataset/private/list', CollectionListView.as_view(prefix="priv"), name='collpriv_list'),
    url(r'^dataset/public/list', CollectionListView.as_view(prefix="publ"), name='collpubl_list'),
    url(r'^collection/hist/list', CollectionListView.as_view(prefix="hist"), name='collhist_list'),
    url(r'^collection/any/list', CollectionListView.as_view(prefix="any"), name='collany_list'),
    url(r'^collection/austat/list', CollectionListView.as_view(prefix="austat"), name='collaustat_list'),

    url(r'^dataset/private/details(?:/(?P<pk>\d+))?/$', CollPrivDetails.as_view(), name='collpriv_details'),
    url(r'^dataset/public/details(?:/(?P<pk>\d+))?/$', CollPublDetails.as_view(), name='collpubl_details'),
    url(r'^collection/hist/details(?:/(?P<pk>\d+))?/$', CollHistDetails.as_view(), name='collhist_details'),
    url(r'^collection/any/details(?:/(?P<pk>\d+))?/$', CollAnyDetails.as_view(), name='collany_details'),
    url(r'^collection/austat/details(?:/(?P<pk>\d+))?/$', CollSuperDetails.as_view(), name='collsuper_details'),

    url(r'^dataset/private/edit(?:/(?P<pk>\d+))?/$', CollPrivEdit.as_view(), name='collpriv_edit'),
    url(r'^dataset/public/edit(?:/(?P<pk>\d+))?/$', CollPublEdit.as_view(), name='collpubl_edit'),
    url(r'^collection/hist/edit(?:/(?P<pk>\d+))?/$', CollHistEdit.as_view(), name='collhist_edit'),
    url(r'^collection/any/edit(?:/(?P<pk>\d+))?/$', CollAnyEdit.as_view(), name='collany_edit'),
    url(r'^collection/austat/edit(?:/(?P<pk>\d+))?/$', CollSuperEdit.as_view(), name='collsuper_edit'),
    
    url(r'^dataset/elevate(?:/(?P<pk>\d+))?/$', CollHistElevate.as_view(), name='collhist_elevate'),
    url(r'^collection/hist/manuscript(?:/(?P<pk>\d+))?/$', CollHistManu.as_view(), name='collhist_manu'),
    url(r'^collection/hist/template(?:/(?P<pk>\d+))?/$', CollHistTemp.as_view(), name='collhist_temp'),
    url(r'^collection/hist/compare(?:/(?P<pk>\d+))?/$', CollHistCompare.as_view(), name='collhist_compare'),
    
    url(r'^basket/canwit/update', BasketUpdate.as_view(), name='basket_update'),
    url(r'^basket/canwit/show', BasketView.as_view(), name='basket_show'),

    url(r'^basket/manu/update', BasketUpdateManu.as_view(), name='basket_update_manu'),
    url(r'^basket/manu/show', BasketViewManu.as_view(), name='basket_show_manu'),

    url(r'^basket/austat/update', BasketUpdateSuper.as_view(), name='basket_update_austat'),
    url(r'^basket/austat/show', BasketViewSuper.as_view(), name='basket_show_austat'),
    
    # ============================== VIEWS ============================================
    
    url(r'^libraries/download', LibraryListDownload.as_view(), name='library_results'),
    url(r'^authors/download', AuthorListDownload.as_view(), name='author_results'),

    url(r'^location/list', LocationListView.as_view(), name='location_list'),
    url(r'^location/details(?:/(?P<pk>\d+))?/$', LocationDetails.as_view(), name='location_details'),
    url(r'^location/edit(?:/(?P<pk>\d+))?/$', LocationEdit.as_view(), name='location_edit'),

    url(r'^origin/list', OriginListView.as_view(), name='origin_list'),
    url(r'^origin/details(?:/(?P<pk>\d+))?/$', OriginDetails.as_view(), name='origin_details'),
    url(r'^origin/edit(?:/(?P<pk>\d+))?/$', OriginEdit.as_view(), name='origin_edit'),
    url(r'^origincod/details(?:/(?P<pk>\d+))?/$', OriginCodDetails.as_view(), name='origincod_details'),
    url(r'^origincod/edit(?:/(?P<pk>\d+))?/$', OriginCodEdit.as_view(), name='origincod_edit'),

    url(r'^library/list', LibraryListView.as_view(), name='library_list'),
    url(r'^library/details(?:/(?P<pk>\d+))?/$', LibraryDetails.as_view(), name='library_details'),
    url(r'^library/edit(?:/(?P<pk>\d+))?/$', LibraryEdit.as_view(), name='library_edit'),

    url(r'^author/list', AuthorListView.as_view(), name='author_list'),
    url(r'^author/details(?:/(?P<pk>\d+))?/$', AuthorDetails.as_view(), name='author_details'),
    url(r'^author/edit(?:/(?P<pk>\d+))?/$', AuthorEdit.as_view(), name='author_edit'),

    url(r'^report/list', ReportListView.as_view(), name='report_list'),
    url(r'^report/details(?:/(?P<pk>\d+))?/$', ReportDetails.as_view(), name='report_details'),
    url(r'^report/edit(?:/(?P<pk>\d+))?/$', ReportEdit.as_view(), name='report_edit'),
    url(r'^report/download(?:/(?P<pk>\d+))?/$', ReportDownload.as_view(), name='report_results'),

    url(r'^literature/list', LitRefListView.as_view(), name='literature_list'),

    url(r'^keyword/list', KeywordListView.as_view(), name='keyword_list'),
    url(r'^keyword/details(?:/(?P<pk>\d+))?/$', KeywordDetails.as_view(), name='keyword_details'),
    url(r'^keyword/edit(?:/(?P<pk>\d+))?/$', KeywordEdit.as_view(), name='keyword_edit'),

    url(r'^genre/list', GenreListView.as_view(), name='genre_list'),
    url(r'^genre/details(?:/(?P<pk>\d+))?/$', GenreDetails.as_view(), name='genre_details'),
    url(r'^genre/edit(?:/(?P<pk>\d+))?/$', GenreEdit.as_view(), name='genre_edit'),

    url(r'^auwork/list', AuworkListView.as_view(), name='auwork_list'),
    url(r'^auwork/details(?:/(?P<pk>\d+))?/$', AuworkDetails.as_view(), name='auwork_details'),
    url(r'^auwork/edit(?:/(?P<pk>\d+))?/$', AuworkEdit.as_view(), name='auwork_edit'),

    url(r'^userkeyword/list', UserKeywordListView.as_view(), name='userkeyword_list'),
    url(r'^userkeyword/details(?:/(?P<pk>\d+))?/$', UserKeywordDetails.as_view(), name='userkeyword_details'),
    url(r'^userkeyword/edit(?:/(?P<pk>\d+))?/$', UserKeywordEdit.as_view(), name='userkeyword_edit'),

    url(r'^provenance/list', ProvenanceListView.as_view(), name='provenance_list'),
    url(r'^provenance/details(?:/(?P<pk>\d+))?/$', ProvenanceDetails.as_view(), name='provenance_details'),
    url(r'^provenance/edit(?:/(?P<pk>\d+))?/$', ProvenanceEdit.as_view(), name='provenance_edit'),
    url(r'^provman/details(?:/(?P<pk>\d+))?/$', ProvenanceManDetails.as_view(), name='provenanceman_details'),
    url(r'^provman/edit(?:/(?P<pk>\d+))?/$', ProvenanceManEdit.as_view(), name='provenanceman_edit'),
    url(r'^provcod/details(?:/(?P<pk>\d+))?/$', ProvenanceCodDetails.as_view(), name='provenancecod_details'),
    url(r'^provcod/edit(?:/(?P<pk>\d+))?/$', ProvenanceCodEdit.as_view(), name='provenancecod_edit'),

    url(r'^comment/list', CommentListView.as_view(), name='comment_list'),
    url(r'^comment/details(?:/(?P<pk>\d+))?/$', CommentDetails.as_view(), name='comment_details'),
    url(r'^comment/edit(?:/(?P<pk>\d+))?/$', CommentEdit.as_view(), name='comment_edit'),
    url(r'^comment/send/$', CommentSend.as_view(), name='comment_send'),

    url(r'^bibrange/list', BibRangeListView.as_view(), name='bibrange_list'),
    url(r'^bibrange/details(?:/(?P<pk>\d+))?/$', BibRangeDetails.as_view(), name='bibrange_details'),
    url(r'^bibrange/edit(?:/(?P<pk>\d+))?/$', BibRangeEdit.as_view(), name='bibrange_edit'),

    url(r'^feast/list', FeastListView.as_view(), name='feast_list'),
    url(r'^feast/details(?:/(?P<pk>\d+))?/$', FeastDetails.as_view(), name='feast_details'),
    url(r'^feast/edit(?:/(?P<pk>\d+))?/$', FeastEdit.as_view(), name='feast_edit'),

    url(r'^profile/list', ProfileListView.as_view(), name='profile_list'),
    url(r'^profile/details(?:/(?P<pk>\d+))?/$', ProfileDetails.as_view(), name='profile_details'),
    url(r'^profile/edit(?:/(?P<pk>\d+))?/$', ProfileEdit.as_view(), name='profile_edit'),
    url(r'^default/details(?:/(?P<pk>\d+))?/$', DefaultDetails.as_view(), name='default_details'), 
    url(r'^default/edit(?:/(?P<pk>\d+))?/$', DefaultEdit.as_view(), name='default_edit'), 

    url(r'^project/list', ProjectListView.as_view(), name='project_list'), 
    url(r'^project/details(?:/(?P<pk>\d+))?/$', ProjectDetails.as_view(), name='project_details'), 
    url(r'^project/edit(?:/(?P<pk>\d+))?/$', ProjectEdit.as_view(), name='project_edit'), 

    url(r'^source/list', SourceListView.as_view(), name='source_list'),
    url(r'^source/details(?:/(?P<pk>\d+))?/$', SourceDetails.as_view(), name='source_details'),
    url(r'^source/edit(?:/(?P<pk>\d+))?/$', SourceEdit.as_view(), name='source_edit'),

    url(r'^template/list', TemplateListView.as_view(), name='template_list'),
    url(r'^template/details(?:/(?P<pk>\d+))?/$', TemplateDetails.as_view(), name='template_details'),
    url(r'^template/edit(?:/(?P<pk>\d+))?/$', TemplateEdit.as_view(), name='template_edit'),
    url(r'^template/apply(?:/(?P<pk>\d+))?/$', TemplateApply.as_view(), name='template_apply'),
    url(r'^template/import/$', TemplateImport.as_view(), name='template_import'),

    # ============ TYPEAHEAD VIEWS ============================================

    url(r'^api/countries/$', lila.seeker.views_ta.get_countries, name='api_countries'),
    url(r'^api/cities/$', lila.seeker.views_ta.get_cities, name='api_cities'),
    url(r'^api/libraries/$', lila.seeker.views_ta.get_libraries, name='api_libraries'),
    url(r'^api/origins/$', lila.seeker.views_ta.get_origins, name='api_origins'),
    url(r'^api/locations/$', lila.seeker.views_ta.get_locations, name='api_locations'),
    url(r'^api/litrefs/$', lila.seeker.views_ta.get_litrefs, name='api_litrefs'),
    url(r'^api/litref/$', lila.seeker.views_ta.get_litref, name='api_litref'),
    url(r'^api/aslink/$', lila.seeker.views_ta.get_aslink, name='api_aslink'),
    url(r'^api/as2as/$', lila.seeker.views_ta.get_as2as, name='api_as2as'),
    url(r'^api/as/$', lila.seeker.views_ta.get_as, name='api_as'),
    url(r'^api/asdist/$', lila.seeker.views_ta.get_asdist, name='api_asdist'),
    url(r'^api/sermosig/$', lila.seeker.views_ta.get_sermosig, name='api_sermosig'),
    url(r'^api/authors/list/$', lila.seeker.views_ta.get_authors, name='api_authors'),
    url(r'^api/cwftexts/$', lila.seeker.views_ta.get_cwftexts, name='api_cwtexts'),
    url(r'^api/cwftrans/$', lila.seeker.views_ta.get_cwftrans, name='api_cwftrans'),
    url(r'^api/asftexts/$', lila.seeker.views_ta.get_asftexts, name='api_asftexts'),
    url(r'^api/asftrans/$', lila.seeker.views_ta.get_asftrans, name='api_asftrans'),
    url(r'^api/srmsignatures/$', lila.seeker.views_ta.get_srmsignatures, name='api_srmsignatures'),
    url(r'^api/keywords/$', lila.seeker.views_ta.get_keywords, name='api_keywords'),
    url(r'^api/collections/$', lila.seeker.views_ta.get_collections, name='api_collections'),
    url(r'^api/manuidnos/$', lila.seeker.views_ta.get_manuidnos, name='api_manuidnos'),

    # ============ OTHER API AND SYNC VIEWS ============================================

    url(r'^api/import/authors/$', lila.seeker.views_api.import_authors, name='import_authors'),

    url(r'^api/import/pdf_lit/$', lila.seeker.views_api.do_create_pdf_lit, name='create_pdf_lit'), 
    url(r'^api/import/pdf_edi/$', lila.seeker.views_api.do_create_pdf_edi, name='create_pdf_edi'), 
    url(r'^api/import/pdf_manu/$', lila.seeker.views_api.do_create_pdf_manu, name='create_pdf_manu'),

    url(r'^sync/lila/$', lila.seeker.views_api.sync_lila, name='sync_lila'),
    url(r'^sync/start/$', lila.seeker.views_api.sync_start, name='sync_start'),
    url(r'^sync/progress/$', lila.seeker.views_api.sync_progress, name='sync_progress'),
    url(r'^sync/zotero/$', lila.seeker.views_api.redo_zotero, name='sync_zotero'),
     
    # ================ Any READER APP URLs should come here =======================================


    # =============================================================================================

    # For working with ModelWidgets from the select2 package https://django-select2.readthedocs.io
    url(r'^select2/', include('django_select2.urls')),

    url(r'^definitions$', RedirectView.as_view(url='/'+pfx+'admin/'), name='definitions'),
    url(r'^signup/$', lila.seeker.views.signup, name='signup'),

    url(r'^login/user/(?P<user_id>\w[\w\d_]+)$', lila.seeker.views.login_as_user, name='login_as'),

    url(r'^login/$', LoginView.as_view
        (
            template_name= 'login.html',
            authentication_form= lila.seeker.forms.BootstrapAuthenticationForm,
            extra_context= {'title': 'Log in','year': datetime.now().year,}
        ),
        name='login'),
    url(r'^logout$',  LogoutView.as_view(next_page=reverse_lazy('home')), name='logout'),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', admin.site.urls, name='admin_base'),
]

