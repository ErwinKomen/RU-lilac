"""
Definition of visualization views for the SEEKER app.
"""

from django.db import transaction
from django.db.models import Q, Prefetch, Count, F
from django.template.loader import render_to_string
import pandas as pd 
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import json
import copy
import itertools

# ======= imports from my own application ======
from lila.utils import ErrHandle
from lila.basic.views import BasicPart
from lila.seeker.models import get_crpp_date, get_current_datetime, process_lib_entries, adapt_search, get_searchable, get_now_time, \
    add_gold2equal, add_equal2equal, add_ssg_equal2equal, get_helptext, Information, Country, City, Author, Manuscript, \
    User, Group, Origin, Canwit, MsItem, Codhead, CanwitKeyword, CanwitAustat, NewsItem, \
    FieldChoice, SourceInfo, AustatKeyword, ManuscriptExt, \
    ManuscriptKeyword, Action, Austat, AustatLink, Location, LocationName, LocationIdentifier, LocationRelation, LocationType, \
    ProvenanceMan, Provenance, Daterange, CollOverlap, BibRange, Feast, Comment, AustatDist, \
    Project, Basket, BasketMan, BasketAustat, Litref, LitrefMan, LitrefCol, Report, \
    Visit, Profile, Keyword, CanwitSignature, Status, Library, Collection, CollectionSerm, \
    CollectionMan, CollectionSuper, UserKeyword, Template, ManuscriptCorpus, ManuscriptCorpusLock, \
    AustatCorpus, AustatCorpusItem, \
   LINK_EQUAL, LINK_PRT, LINK_BIDIR, LINK_PARTIAL, STYPE_IMPORTED, STYPE_EDITED, LINK_UNSPECIFIED
from lila.stylo.corpus import Corpus
from lila.stylo.analysis import bootstrapped_distance_matrices, hierarchical_clustering, distance_matrix

# ======= from RU-Basic ========================
from lila.basic.views import BasicList, BasicDetails, make_search_list, add_rel_item


COMMON_NAMES = ["Actibus", "Adiubante", "Africa", "Amen", "Andreas", "Apostolorum", "Apringio", "Augustinus", 
                "Austri", "Baptistae", "Beatum", "Christi", "Christo", "Christum", 
                "Christus", "Christus", "Chrsiti", "Cosmae", "Cui", "Dauid", "Dedicatur", "Dei", 
                "Deum", "Deus", "Dies", "Domenicae", "Domiani", "Domine", "Domini", "Dominico", "Domino", 
                "Dominum", "Dominus", "Ecce", "Ephesum", "Epiphaniae", "Eua", "Euangelista", 
                "Eusebii", "Eustochium", "Explicit", "Filio", "Fraternitatis", "Fulgentio", "Galilaea\u2026piscatores",
                "Herodes", "Iesse", "Iesu", "Iesu", "Iesum", "Iesus", "Ihesu", "In", "Ioannis", "Iohanne", 
                "Iohannem", "Iohannes", "Iohannis", "Ipse", "Ipsi", "Ipso", "Iudaea", "Iudaeis", "Lectis", 
                "Lucas", "Marcellino", "Maria", "Mariam", "Moysen", "Nam", "Naue", "Niniue", "Paschae", 
                "Patre", "Patrem", "Patre\u2026", "Patris", "Paula", "Pauli", "Paulino", 
                "Paulus", "Per", "Petri", "Petrus", "Possidius", "Praecursoris", "Praestante\u2026", "Primus", 
                "Qui", "Quid", "Quis", "Quod", "Remedia", "Rex", "Salomon", "Salomonem", "Saluator", 
                "Saluatoris", "Salvator", "Sancti", "Saulus", "Si", "Sicut", "Simon", "Sine", "Solomonis", 
                "Spiritu", "Spiritus", "Stephanus", "Testamenti", "Therasiae", "Thomam", "Thomas"]


def get_ssg_corpus(profile, instance):
    oErr = ErrHandle()
    lock_status = "new"
    ssg_corpus = None
    try:
        
        # Set the lock, or return if we are busy with this ssg_corpus
        ssg_corpus = AustatCorpus.objects.filter(profile=profile, ssg=instance).last()
        if ssg_corpus != None:
            lock_status = ssg_corpus.status
            # Check the status
            if lock_status == "busy":
                # Already busy
                return context
        else:
            # Need to create a lock
            ssg_corpus = AustatCorpus.objects.create(profile=profile, ssg=instance)
            lock_status = "busy"

        # Save the status
        ssg_corpus.status = lock_status
        ssg_corpus.save()

        if lock_status == "new":
            # Remove earlier corpora made by me based on this SSG
            AustatCorpus.objects.filter(profile=profile, ssg=instance).delete()

            # Create a new one
            ssg_corpus = AustatCorpus.objects.create(profile=profile, ssg=instance, status="busy")

    except:
        msg = oErr.get_error_message()
        oErr.DoError("get_ssg_corpus")       
    return ssg_corpus, lock_status

def get_ssg_lila(ssg_id, obj=None):
    oErr = ErrHandle()
    code = ""
    try:
        # Get the lila Code
        if obj == None:
            obj = Austat.objects.filter(id=ssg_id).first()
        if obj.code == None:
            code = "eqg_{}".format(obj.id)
        elif " " in obj.code:
            code = obj.code.split(" ")[1]
        else:
            code = obj.code
    except:
        msg = oErr.get_error_message()
        oErr.DoError("get_ssg_lila")
    return code

def get_watermark():
    """Create and return a watermark"""

    oErr = ErrHandle()
    watermark_template = "seeker/lila_watermark.html"
    watermark = ""
    try:
            # create a watermark with the right datestamp
            context_wm = dict(datestamp=get_crpp_date(get_current_datetime(), True))
            watermark = render_to_string(watermark_template, context_wm)
    except:
        msg = oErr.get_error_message()
        oErr.DoError("get_watermark")
    # Return the result
    return watermark



class DrawPieChart(BasicPart):
    """Fetch data for a particular type of pie-chart for the home page
    
    Current types: 'sermo', 'austat', 'manu'
    """

    pass


class AustatOverlap(BasicPart):
    """Network of textual overlap between SSGs"""

    MainModel = Austat

    def add_to_context(self, context):

        oErr = ErrHandle()
        spec_dict = {}
        link_dict = {}
        graph_template = 'seeker/super_graph_hist.html'

        try:
            # Define the linktype and spectype
            for obj in FieldChoice.objects.filter(field="seeker.spectype"):
                spec_dict[obj.abbr]= obj.english_name
            for obj in FieldChoice.objects.filter(field="seeker.linktype"):
                link_dict[obj.abbr]= obj.english_name

            # Need to figure out who I am
            profile = Profile.get_user_profile(self.request.user.username)
            instance = self.obj

            # The networkslider determines whether we are looking for 1st degree, 2nd degree or more
            networkslider = self.qd.get("network_overlap_slider", "1")            
            if isinstance(networkslider, str):
                networkslider = int(networkslider)

            # Initializations
            ssg_link = {}
            bUseDirectionality = True

            # Read the table with links from SSG to SSG
            eqg_link = AustatLink.objects.all().order_by('src', 'dst').values(
                'src', 'dst', 'spectype', 'linktype', 'alternatives', 'note')
            # Transform into a dictionary with src as key and list-of-dst as value
            for item in eqg_link:
                src = item['src']
                dst = item['dst']
                if bUseDirectionality:
                    spectype = item['spectype']
                    linktype = item['linktype']
                    note = item['note']
                    alternatives = item['alternatives']
                    if alternatives == None: alternatives = False
                    # Make room for the SRC if needed
                    if not src in ssg_link: ssg_link[src] = []
                    # Add this link to the list
                    oLink = {   'dst': dst, 
                                'note': note,
                                'spectype': "", 
                                'linktype': linktype,
                                'spec': "",
                                'link': link_dict[linktype],
                                'alternatives': alternatives}
                    if spectype != None:
                        oLink['spectype'] = spectype
                        oLink['spec'] = spec_dict[spectype]
                    ssg_link[src].append(oLink)
                else:
                    # Make room for the SRC if needed
                    if not src in ssg_link: ssg_link[src] = []
                    # Add this link to the list
                    ssg_link[src].append(dst)

            # Create the overlap network
            node_list, link_list, hist_set, max_value, max_group = self.do_overlap(ssg_link, networkslider)

            # Create the buttons for the historical collections
            hist_list=[{'id': k, 'name': v} for k,v in hist_set.items()]
            hist_list = sorted(hist_list, key=lambda x: x['name']);
            context = dict(hist_list = hist_list)
            hist_buttons = render_to_string(graph_template, context, self.request)

            # Add the information to the context in data
            context['data'] = dict(node_list=node_list, 
                                   link_list=link_list,
                                   watermark=get_watermark(),
                                   hist_set=hist_set,
                                   hist_buttons=hist_buttons,
                                   max_value=max_value,
                                   max_group=max_group,
                                   networkslider=networkslider,
                                   legend="SSG overlap network")
            
        except:
            msg = oErr.get_error_message()
            oErr.DoError("AustatOverlap/add_to_context")

        return context

    def do_overlap(self, ssg_link, degree):
        """Calculate the overlap network up until 'degree'"""

        def add_nodeset(ssg_id, group):
            node_key = ssg_id

            # ---------- DEBUG --------------
            if node_key == 4968:
                iStop = 1
            # -------------------------------

            # Possibly add the node to the set
            if not node_key in node_set:
                code_sig = get_ssg_sig(ssg_id)
                ssg = Austat.objects.filter(id=ssg_id).first()
                code_pas = get_ssg_lila(ssg_id, ssg)
                scount = ssg.scount

                # Get a list of the HCs that this SSG is part of
                hc_list = ssg.collections.filter(settype="hc").values("id", "name")
                hcs = []
                for oItem in hc_list:
                    id = oItem['id']
                    if not id in hist_set:
                        hist_set[id] = oItem['name']
                    hcs.append(id)

                node_value = dict(label=code_sig, id=ssg_id, group=group, 
                                  lila=code_pas, scount=scount, hcs=hcs)
                node_set[node_key] = node_value
                
        node_list = []
        link_list = []
        node_set = {}
        link_set = {}
        hist_set = {}
        max_value = 0
        max_group = 1
        oErr = ErrHandle()

        try:
            # Degree 0: direct contacts
            ssg_id = self.obj.id

            ssg_queue = [ ssg_id ]
            ssg_add = []
            group = 1
            degree -= 1
            while len(ssg_queue) > 0 and degree >= 0:
                # Get the next available node
                node_key = ssg_queue.pop()

                # Possibly add the node to the set
                add_nodeset(node_key, group)

                # Add links from this SSG to others
                if node_key in ssg_link:
                    dst_list = ssg_link[node_key]
                    for oDst in dst_list:
                        dst = oDst['dst']
                        # Add this one to the add list
                        ssg_add.append(dst)
                        link_key = "{}_{}".format(node_key, dst)
                        if not link_key in link_set:
                            oLink = dict(source=node_key,
                                         target=dst,
                                         spectype=oDst['spectype'],
                                         linktype=oDst['linktype'],
                                         spec=oDst['spec'],
                                         link=oDst['link'],
                                         alternatives = oDst['alternatives'],
                                         note=oDst['note'],
                                         value=0)
                            # Add the link to the set
                            link_set[link_key] = oLink
                            # Add the destination node to nodeset
                            add_nodeset(dst, group + 1)

                        # Increment the link value
                        link_set[link_key]['value'] += 1

                # Go to the next degree
                if len(ssg_queue) == 0 and degree >= 0:
                    # Decrement the degree
                    degree -= 1

                    group += 1
                    # Add the items from ssg_add into the queue
                    while len(ssg_add) > 0:
                        ssg_queue.append(ssg_add.pop())


            # Turn the sets into lists
            node_list = [v for k,v in node_set.items()]
            link_list = [v for k,v in link_set.items()]

            # Calculate max_value
            for oItem in link_list:
                value = oItem['value']
                if value > max_value: max_value = value
            for oItem in node_list:
                group = oItem['group']
                if group > max_group: max_group = group
            
        except:
            msg = oErr.get_error_message()
            oErr.DoError("AustatOverlap/do_overlap")

        return node_list, link_list, hist_set, max_value, max_group


class AustatTrans(BasicPart):
    """Prepare for a network graph"""


    MainModel = Austat

    def add_to_context(self, context):

        def add_to_dict(this_dict, item):
            if item != "":
                if not item in this_dict: 
                    this_dict[item] = 1
                else:
                    this_dict[item] += 1
                    
        oErr = ErrHandle()
        try:
            # Need to figure out who I am
            profile = Profile.get_user_profile(self.request.user.username)
            instance = self.obj

            networkslider = self.qd.get("network_trans_slider", "1")            
            if isinstance(networkslider, str):
                networkslider = int(networkslider)

            # Get the 'manuscript-corpus': all manuscripts in which a sermon is that belongs to the same SSG
            manu_list = CanwitAustat.objects.filter(super=instance).distinct().values("manu_id")
            manu_dict = {}
            for idx, manu in enumerate(manu_list):
                manu_dict[manu['manu_id']] = idx + 1

            ssg_corpus, lock_status = get_ssg_corpus(profile, instance)

            if lock_status != "ready":

                # Create an AustatCorpus based on the SSGs in these manuscripts
                ssg_list = CanwitAustat.objects.filter(manu__id__in=manu_list).order_by(
                    'austat_id').distinct().values('austat_id')
                ssg_list_id = [x['austat_id'] for x in ssg_list]
                with transaction.atomic():
                    for ssg in Austat.objects.filter(id__in=ssg_list_id):
                        # Get the name of the author
                        authorname = "empty" if ssg.author==None else ssg.author.name
                        # Get the scount
                        scount = ssg.scount
                        # Create new ssg_corpus item
                        obj = AustatCorpusItem.objects.create(
                            corpus=ssg_corpus, equal=ssg, 
                            authorname=authorname, scount=scount)

                # Add this list to the ssg_corpus
                ssg_corpus.status = "ready"
                ssg_corpus.save()

            node_list, link_list, author_list, max_value = self.do_manu_method(ssg_corpus, manu_list, networkslider)


            # Add the information to the context in data
            context['data'] = dict(node_list=node_list, 
                                   link_list=link_list,
                                   watermark=get_watermark(),
                                   author_list=author_list,
                                   max_value=max_value,
                                   networkslider=networkslider,
                                   legend="SSG network")
            
            # Can remove the lock
            ssg_corpus.status = "ready"
            ssg_corpus.save()


        except:
            msg = oErr.get_error_message()
            oErr.DoError("AustatTrans/add_to_context")

        return context

    def do_manu_method(self, ssg_corpus, manu_list, min_value):
        """Calculation like 'MedievalManuscriptTransmission' description
        
        The @min_value is the minimum link-value the user wants to see
        """

        oErr = ErrHandle()
        author_dict = {}
        node_list = []
        link_list = []
        max_value = 0       # Maximum number of manuscripts in which an SSG occurs
        max_scount = 1      # Maximum number of sermons associated with one SSG

        try:
            # Initializations
            ssg_dict = {}
            link_dict = {}
            scount_dict = {}
            node_listT = []
            link_listT = []
            node_set = {}       # Put the nodes in a set, with their SSG_ID as key
            title_set = {}      # Link from title to SSG_ID

            # Walk the ssg_corpus: each SSG is one 'text', having a title and a category (=author code)
            for idx, item in enumerate(AustatCorpusItem.objects.filter(corpus=ssg_corpus).values(
                'authorname', 'scount', 'equal__code', 'equal__id')):
                # Determine the name for this row
                category = item['authorname']
                ssg_id = item['equal__id']
                code = item['equal__code']
                if code == None or code == "" or not " " in code or not "." in code:
                    title = "eqg{}".format(ssg_id)
                else:
                    title = code.split(" ")[1]
                # Get the Signature that is most appropriate
                sig = get_ssg_sig(ssg_id)

                # Add author to dictionary
                if not category in author_dict: author_dict[category] = 0
                author_dict[category] += 1
               
                # the scount and store it in a dictionary
                scount = item['scount']
                scount_dict[ssg_id] = scount
                if scount > max_scount:
                    max_scount = scount

                node_key = ssg_id
                node_value = dict(label=title, category=category, scount=scount, sig=sig, rating=0)
                if node_key in node_set:
                    oErr.Status("AustatGraph/do_manu_method: attempt to add same title '{}' for {} and {}".format(
                        title, ssg_id, title_set[title]))
                else:
                    node_set[node_key] = node_value
                    title_set[title] = ssg_id

            # Create list of authors
            author_list = [dict(category=k, count=v) for k,v in author_dict.items()]
            author_list = sorted(author_list, key=lambda x: (-1 * x['count'], x['category'].lower()))

            # Create a dictionary of manuscripts, each having a list of SSG ids
            manu_set = {}
            for manu_item in manu_list:
                manu_id = manu_item["manu_id"]
                # Get a list of all SSGs in this manuscript
                ssg_list = CanwitAustat.objects.filter(manu__id=manu_id).order_by(
                    'austat_id').distinct()
                # Add the SSG id list to the manuset
                manu_set[manu_id] = [x.austat for x in ssg_list]

            # Create a list of edges based on the above
            link_dict = {}
            for manu_id, ssg_list in manu_set.items():
                # Only treat ssg_lists that are larger than 1
                if len(ssg_list) > 1:
                    # itertool.combinations creates all combinations of SSG to SSG in one manuscript
                    for subset in itertools.combinations(ssg_list, 2):
                        source = subset[0]
                        target = subset[1]
                        source_id = source.id
                        target_id = target.id
                        link_code = "{}_{}".format(source_id, target_id)
                        if link_code in link_dict:
                            oLink = link_dict[link_code]
                        else:
                            oLink = dict(source=source_id,
                                         target=target_id,
                                         value=0)
                            link_dict[link_code] = oLink
                        # Add 1
                        oLink['value'] += 1
                        if oLink['value'] > max_value:
                            max_value = oLink['value']
            # Turn the link_dict into a list
            # link_list = [v for k,v in link_dict.items()]
            
            # Only accept the links that have a value >= min_value
            node_dict = {}
            link_list = []
            for k, oItem in link_dict.items():
                if oItem['value'] >= min_value:
                    link_list.append(copy.copy(oItem))
                    # Take note of the nodes
                    src = oItem['source']
                    dst = oItem['target']
                    if not src in node_dict: node_dict[src] = node_set[src]
                    if not dst in node_dict: node_dict[dst] = node_set[dst]
            # Walk the nodes
            node_list = []
            for ssg_id, oItem in node_dict.items():
                oItem['id'] = ssg_id
                oItem['scount'] = 100 * scount_dict[oItem['id']] / max_scount
                node_list.append(copy.copy(oItem))

 
        except:
            msg = oErr.get_error_message()
            oErr.DoError("do_manu_method")

        return node_list, link_list,  author_list, max_value


class AustatGraph(BasicPart):
    """Prepare for a network graph"""

    MainModel = Austat

    def add_to_context(self, context):
        def get_author(code):
            """Get the author id from the lila code"""
            author = 10000
            if "lila" in code:
                author = int(code.replace("lila", "").strip().split(".")[0])
            return author

        def add_to_dict(this_dict, item):
            if item != "":
                if not item in this_dict: 
                    this_dict[item] = 1
                else:
                    this_dict[item] += 1
                    
        oErr = ErrHandle()
        try:
            # Need to figure out who I am
            profile = Profile.get_user_profile(self.request.user.username)
            instance = self.obj

            networkslider = self.qd.get("networkslider", "1")            
            if isinstance(networkslider, str):
                networkslider = int(networkslider)

            # Get the 'manuscript-corpus': the manuscripts in which the same kind of sermon like me is
            manu_list = CanwitAustat.objects.filter(super=instance).distinct().values("manu_id")
            manu_dict = {}
            for idx, manu in enumerate(manu_list):
                manu_dict[manu['manu_id']] = idx + 1
            author_dict = {}

            lock_status = "new"
            # Set the lock, or return if we are busy with this ssg_corpus
            ssg_corpus = AustatCorpus.objects.filter(profile=profile, ssg=instance).last()
            if ssg_corpus != None:
                lock_status = ssg_corpus.status
                # Check the status
                if lock_status == "busy":
                    # Already busy
                    return context
            else:
                # Need to create a lock
                ssg_corpus = AustatCorpus.objects.create(profile=profile, ssg=instance)
                lock_status = "busy"

            # Save the status
            ssg_corpus.status = lock_status
            ssg_corpus.save()

            if lock_status == "new":
                # Remove earlier corpora made by me based on this SSG
                AustatCorpus.objects.filter(profile=profile, ssg=instance).delete()

                # Create a new one
                ssg_corpus = AustatCorpus.objects.create(profile=profile, ssg=instance, status="busy")

            if lock_status != "ready":

                # Create an AustatCorpus based on the SSGs in these manuscripts
                ssg_list = CanwitAustat.objects.filter(manu__id__in=manu_list).order_by(
                    'austat_id').distinct().values('austat_id')
                ssg_list_id = [x['austat_id'] for x in ssg_list]
                all_words = {}
                with transaction.atomic():
                    for ssg in Austat.objects.filter(id__in=ssg_list_id):
                        # Add this item to the ssg_corpus
                        latin = {}
                        if ssg.incipit != None:
                            for item in ssg.srchftext.replace(",", "").replace("…", "").split(" "): 
                                add_to_dict(latin, item)
                                add_to_dict(all_words, item)
                        if ssg.explicit != None:
                            for item in ssg.srchftrans.replace(",", "").replace("…", "").split(" "): 
                                add_to_dict(latin, item)
                                add_to_dict(all_words, item)
                        # Get the name of the author
                        authorname = "empty" if ssg.author==None else ssg.author.name
                        # Get the scount
                        scount = ssg.scount
                        # Create new ssg_corpus item
                        obj = AustatCorpusItem.objects.create(
                            corpus=ssg_corpus, words=json.dumps(latin), equal=ssg, 
                            authorname=authorname, scount=scount)

                # What are the 100 MFWs in all_words?
                mfw = [dict(word=k, count=v) for k,v in all_words.items()]
                mfw_sorted = sorted(mfw, key = lambda x: -1 * x['count'])
                mfw_cento = mfw_sorted[:100]
                mfw = []
                for item in mfw_cento: mfw.append(item['word'])
                # Add this list to the ssg_corpus
                ssg_corpus.mfw = json.dumps(mfw)
                ssg_corpus.status = "ready"
                ssg_corpus.save()

            node_list, link_list, max_value = self.do_manu_method(ssg_corpus, manu_list, networkslider)


            # Add the information to the context in data
            context['data'] = dict(node_list=node_list, 
                                   link_list=link_list,
                                   watermark=get_watermark(),
                                   max_value=max_value,
                                   networkslider=networkslider,
                                   legend="SSG network")
            
            # Can remove the lock
            ssg_corpus.status = "ready"
            ssg_corpus.save()


        except:
            msg = oErr.get_error_message()
            oErr.DoError("AustatGraph/add_to_context")

        return context

    def do_manu_method(self, ssg_corpus, manu_list, min_value):
        """Calculation like Manuscript_Transmission_Of_se172
        
        The @min_value is the minimum link-value the user wants to see
        """
        oErr = ErrHandle()
        node_list = []
        link_list = []
        max_value = 0       # Maximum number of manuscripts in which an SSG occurs
        max_scount = 1      # Maximum number of sermons associated with one SSG
        manu_count = []

        def get_nodes(crp):
            nodes = []
            for idx, item in enumerate(crp.target_ints):
                oNode = dict(group=item, author=crp.target_idx[item], id=crp.titles[idx])
                nodes.append(oNode)
            return nodes

        try:
            # Create a pystyl-corpus object (see above)
            sty_corpus = Corpus(texts=[], titles=[], target_ints=[], target_idx=[])

            ssg_dict = {}
            link_dict = {}
            scount_dict = {}
            node_listT = []
            link_listT = []

            # Initialize manu_count: the number of SSG co-occurring in N manuscripts
            for item in manu_list:
                manu_count.append(0)

            # Walk the ssg_corpus: each SSG is one 'text', having a title and a category (=author code)
            for idx, item in enumerate(AustatCorpusItem.objects.filter(corpus=ssg_corpus).values(
                'words', 'authorname', 'scount', 'equal__code', 'equal__id')):
                # Determine the name for this row
                category = item['authorname']
                code = item['equal__code']
                if code == None or code == "" or not " " in code or not "." in code:
                    title = "eqg{}".format(item['equal__id'])
                else:
                    title = code.split(" ")[1]
                # The text = the words
                text = " ".join(json.loads(item['words']))
                
                # the scount and store it in a dictionary
                scount_dict[title] = item['scount']
                if item['scount'] > max_scount:
                    max_scount = item['scount']

                # Add the text to the corpus
                if title in sty_corpus.titles:
                    ssg_id = -1
                    bFound = False
                    for k,v in ssg_dict.items():
                        if v == title:
                            ssg_id = k
                            bFound = True
                            break
                    oErr.Status("AustatGraph/do_manu_method: attempt to add same title '{}' for {} and {}".format(
                        title, ssg_id, item['equal__id']))
                else:
                    # Also make sure to buidl an SSG-dictionary
                    ssg_dict[item['equal__id']] = title

                    sty_corpus.add_text(text, title, category)

            # Get a list of nodes
            node_listT = get_nodes(sty_corpus)

            # Walk the manuscripts
            for manu_item in manu_list:
                manu_id = manu_item["manu_id"]
                # Get a list of all SSGs in this manuscript
                ssg_list = CanwitAustat.objects.filter(manu__id=manu_id).order_by(
                    'austat_id').distinct().values('austat_id')
                ssg_list_id = [x['austat_id'] for x in ssg_list]
                # evaluate links between a source and target SSG
                for idx_s, source_id in enumerate(ssg_list_id):
                    # sanity check
                    if source_id in ssg_dict:
                        # Get the title of the source
                        source = ssg_dict[source_id]
                        for idx_t in range(idx_s+1, len(ssg_list_id)-1):
                            target_id = ssg_list_id[idx_t]
                            # Double check
                            if target_id in ssg_dict:
                                # Get the title of the target
                                target = ssg_dict[target_id]
                                # Retrieve or create a link from the link_listT
                                link_code = "{}_{}".format(source_id, target_id)
                                if link_code in link_dict:
                                    oLink = link_listT[link_dict[link_code]]
                                else:
                                    oLink = dict(source=source, source_id=source_id,
                                                 target=target, target_id=target_id,
                                                 value=0)
                                    link_listT.append(oLink)
                                    link_dict[link_code] = len(link_listT) - 1
                                # Now add to the value
                                oLink['value'] += 1
                                if oLink['value'] > max_value:
                                    max_value = oLink['value']
            
            # Only accept the links that have a value >= min_value
            node_dict = []
            for oItem in link_listT:
                if oItem['value'] >= min_value:
                    link_list.append(copy.copy(oItem))
                    # Take note of the nodes
                    src = oItem['source']
                    dst = oItem['target']
                    if not src in node_dict: node_dict.append(src)
                    if not dst in node_dict: node_dict.append(dst)
            # Walk the nodes
            for oItem in node_listT:
                if oItem['id'] in node_dict:
                    oItem['scount'] = 100 * scount_dict[oItem['id']] / max_scount
                    node_list.append(copy.copy(oItem))

 
        except:
            msg = oErr.get_error_message()
            oErr.DoError("do_hier_method1")

        return node_list, link_list, max_value
    

class AustatPca(BasicPart):
    """Principle component analysis of a set of SSGs"""

    MainModel = Austat

    def add_to_context(self, context):

        names_list = [x.lower() for x in COMMON_NAMES]

        def get_author(code):
            """Get the author id from the lila code"""
            author = 10000
            if "lila" in code:
                author = int(code.replace("lila", "").strip().split(".")[0])
            return author

        def add_to_dict(this_dict, item):
            if item != "":
                if not item in this_dict: 
                    this_dict[item] = 1
                else:
                    this_dict[item] += 1
                    
        oErr = ErrHandle()
        try:
            # Need to figure out who I am
            profile = Profile.get_user_profile(self.request.user.username)
            instance = self.obj

            # Get the 'manuscript-corpus': the manuscripts in which the same kind of sermon like me is
            manu_list = CanwitAustat.objects.filter(super=instance).distinct().values("manu_id")
            manu_dict = {}
            for idx, manu in enumerate(manu_list):
                manu_dict[manu['manu_id']] = idx + 1
            author_dict = {}

            lock_status = "new"
            # Set the lock, or return if we are busy with this ssg_corpus
            ssg_corpus = AustatCorpus.objects.filter(profile=profile, ssg=instance).last()
            if ssg_corpus != None:
                lock_status = ssg_corpus.status
                # Check the status
                if lock_status == "busy":
                    # Already busy
                    return context
            else:
                # Need to create a lock
                ssg_corpus = AustatCorpus.objects.create(profile=profile, ssg=instance)
                lock_status = "busy"

            # Save the status
            ssg_corpus.status = lock_status
            ssg_corpus.save()

            if lock_status == "new":
                # Remove earlier corpora made by me based on this SSG
                AustatCorpus.objects.filter(profile=profile, ssg=instance).delete()

                # Create a new one
                ssg_corpus = AustatCorpus.objects.create(profile=profile, ssg=instance, status="busy")

            if lock_status != "ready":

                # Create an AustatCorpus based on the SSGs in these manuscripts
                ssg_list = CanwitAustat.objects.filter(manu__id__in=manu_list).order_by(
                    'austat_id').distinct().values('austat_id')
                ssg_list_id = [x['austat_id'] for x in ssg_list]
                all_words = {}
                with transaction.atomic():
                    for ssg in Austat.objects.filter(id__in=ssg_list_id):
                        # Add this item to the ssg_corpus
                        latin = {}
                        if ssg.incipit != None:
                            for item in ssg.srchftext.replace(",", "").replace("…", "").split(" "): 
                                add_to_dict(latin, item)
                                add_to_dict(all_words, item)
                        if ssg.explicit != None:
                            for item in ssg.srchftrans.replace(",", "").replace("…", "").split(" "): 
                                add_to_dict(latin, item)
                                add_to_dict(all_words, item)
                        # Get the name of the author
                        authorname = "empty" if ssg.author==None else ssg.author.name
                        # Create new ssg_corpus item
                        obj = AustatCorpusItem.objects.create(
                            corpus=ssg_corpus, words=json.dumps(latin), equal=ssg, authorname=authorname)

                # What are the 100 MFWs in all_words?
                mfw = [dict(word=k, count=v) for k,v in all_words.items()]
                mfw_sorted = sorted(mfw, key = lambda x: -1 * x['count'])
                mfw_cento = mfw_sorted[:100]
                mfw = []
                for item in mfw_cento: mfw.append(item['word'])
                # Add this list to the ssg_corpus
                ssg_corpus.mfw = json.dumps(mfw)
                ssg_corpus.status = "ready"
                ssg_corpus.save()

            node_list, link_list, max_value = self.do_hier_method3(ssg_corpus, names_list)


            # Add the information to the context in data
            context['data'] = dict(node_list=node_list, 
                                   link_list=link_list,
                                   watermark=get_watermark(),
                                   max_value=max_value,
                                   legend="SSG network")
            
            # Can remove the lock
            ssg_corpus.status = "ready"
            ssg_corpus.save()

        except:
            msg = oErr.get_error_message()
            oErr.DoError("AustatPca/add_to_context")

        return context

    def do_hier_method3(self, ssg_corpus, names_list):
        """Calculate distance matrix with PYSTYL, do the rest myself"""
        oErr = ErrHandle()
        node_list = []
        link_list = []
        max_value = 0

        def dm_to_leo(matrix, crp):
            links = []
            i = 0
            maxv = 0
            for row_id, row in enumerate(matrix):
                # Calculate the link
                minimum = None
                min_id = -1
                for col_idx in range(row_id+1, len(row)-1):
                    value = row[col_idx]
                    if minimum == None:
                        if value > 0: minimum = value
                    elif value < minimum:
                        minimum = value
                        min_id = col_idx
                if minimum != None and min_id >=0:
                    # Create a link
                    oLink = dict(source_id=row_id, source = crp.titles[row_id],
                                 target_id=min_id, target = crp.titles[min_id],
                                 value=minimum)
                    links.append(oLink)
                    # Keep track of max_value
                    if minimum > maxv: 
                        maxv = minimum

            return links, maxv

        def get_nodes(crp):
            nodes = []
            for idx, item in enumerate(crp.target_ints):
                oNode = dict(group=item, author=crp.target_idx[item], id=crp.titles[idx], scount=5)
                nodes.append(oNode)
            return nodes

        do_example = False
        try:
            # Create a pystyl-corpus object (see above)
            sty_corpus = Corpus(texts=[], titles=[], target_ints=[], target_idx=[])

            ssg_dict = {}

            # Walk the ssg_corpus: each SSG is one 'text', having a title and a category (=author code)
            for idx, item in enumerate(AustatCorpusItem.objects.filter(corpus=ssg_corpus).values(
                'words', 'authorname', 'equal__code', 'equal__id')):
                # Determine the name for this row
                category = item['authorname']
                code = item['equal__code']
                if code == None or code == "" or not " " in code or not "." in code:
                    title = "eqg{}".format(item['equal__id'])
                else:
                    title = code.split(" ")[1]
                # The text = the words
                text = " ".join(json.loads(item['words']))

                # Add the text to the corpus
                if title in sty_corpus.titles:
                    ssg_id = -1
                    bFound = False
                    for k,v in ssg_dict.items():
                        if v == title:
                            ssg_id = k
                            bFound = True
                            break
                    oErr.Status("AustatGraph/do_manu_method: attempt to add same title '{}' for {} and {}".format(
                        title, ssg_id, item['equal__id']))
                else:
                    # Also make sure to buidl an SSG-dictionary
                    ssg_dict[item['equal__id']] = title

                    sty_corpus.add_text(text, title, category)

            # We now 'have' the corpus, so we can work with it...
            sty_corpus.preprocess(alpha_only=True, lowercase=True)
            sty_corpus.tokenize()
            
            # REmove the common names
            sty_corpus.remove_tokens(rm_tokens=names_list, rm_pronouns=False)

            # Vectorize the corpus
            sty_corpus.vectorize(mfi=200, ngram_type="word", ngram_size=1, vector_space="tf_std")

            # Get a list of nodes
            node_list = get_nodes(sty_corpus)

            # Create a distance matrix
            dm = distance_matrix(sty_corpus, "minmax")

            # Convert the distance matrix into a list of 'nearest links'
            link_list, max_value = dm_to_leo(dm, sty_corpus) 

            # Convert the cluster_tree into a node_list and a link_list (i.e. get the list of edges)
            iRead = 1

        except:
            msg = oErr.get_error_message()
            oErr.DoError("do_hier_method1")

        return node_list, link_list, max_value
