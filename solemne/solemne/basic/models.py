"""Models for the BASIC app.

"""
from django.db import models, transaction
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.db.models.functions import Lower
from django.db.models.query import QuerySet 
from django.utils import timezone

import json

# provide error handling
from .utils import ErrHandle

LONG_STRING=255
MAX_TEXT_LEN = 200

def get_current_datetime():
    """Get the current time"""
    return timezone.now()


# Create your models here.
class UserSearch(models.Model):
    """User's searches"""
    
    # [1] The listview where this search is being used
    view = models.CharField("Listview", max_length = LONG_STRING)
    # [1] The parameters used for this search
    params = models.TextField("Parameters", default="[]")    
    # [1] The number of times this search has been done
    count = models.IntegerField("Count", default=0)
    # [1] The usage history
    history = models.TextField("History", default="{}")    
    
    class Meta:
        verbose_name = "User search"
        verbose_name_plural = "User searches"

    def add_search(view, param_list, username):
        """Add or adapt search query based on the listview"""

        oErr = ErrHandle()
        obj = None
        try:
            # DOuble check
            if len(param_list) == 0:
                return obj

            params = json.dumps(sorted(param_list))
            if view[-1] == "/":
                view = view[:-1]
            history = {}
            obj = UserSearch.objects.filter(view=view, params=params).first()
            if obj == None:
                history['count'] = 1
                history['users'] = [dict(username=username, count=1)]
                obj = UserSearch.objects.create(view=view, params=params, history=json.dumps(history), count=1)
            else:
                # Get the current count
                count = obj.count
                # Adapt it
                count += 1
                obj.count = count
                # Get and adapt the history
                history = json.loads(obj.history)
                history['count'] = count
                # Make sure there are users
                if not 'users' in history:
                    history['users'] = []
                    oErr.Status("Usersearch/add_search: added 'users' to history: {}".format(json.dumps(history)))
                bFound = False
                for oUser in history['users']:
                    if oUser['username'] == username:
                        # This is the count for a particular user
                        oUser['count'] += 1
                        bFound = True
                        break
                if not bFound:
                    history['users'].append(dict(username=username, count=1))
                obj.history = json.dumps(history)
                obj.save()

        except:
            msg = oErr.get_error_message()
            oErr.DoError("UserSearch/add_search")
        # Return what we found
        return obj

    def load_parameters(search_id, qd):
        """Retrieve the parameters for the search with the indicated id"""

        oErr = ErrHandle()
        try:
            obj = UserSearch.objects.filter(id=search_id).first()
            if obj != None:
                param_list = json.loads(obj.params)
                for param_str in param_list:
                    arParam = param_str.split("=")
                    if len(arParam) == 2:
                        k = arParam[0]
                        v = arParam[1]
                        qd[k] = v
        except:
            msg = oErr.get_error_message()
            oErr.DoError("UserSearch/load_parameters")
        # Return what we found
        return qd


# =================== HELPER classes ==================================

class Custom():
    """Just adding some functions"""

    specification = []

    def custom_getkv(self, item, **kwargs):
        """Get key and value from the manuitem entry"""

        oErr = ErrHandle()
        key = ""
        value = ""
        try:
            keyfield = kwargs.get("keyfield", "name")
            if keyfield == "path" and item['type'] == "fk_id":
                key = "{}_id".format(key)
            key = item[keyfield]
            if self != None:
                if item['type'] == 'field':
                    value = getattr(self, item['path'])
                elif item['type'] == "fk":
                    fk_obj = getattr(self, item['path'])
                    if fk_obj != None:
                        value = getattr( fk_obj, item['fkfield'])
                elif item['type'] == "fk_id":
                    # On purpose: do not allow downloading the actual ID of a foreign ky - id's migh change
                    pass
                    #fk_obj = getattr(self, item['path'])
                    #if fk_obj != None:
                    #    value = getattr( fk_obj, "id")
                elif item['type'] == 'func':
                    value = self.custom_get(item['path'], kwargs=kwargs)
                    # return either as string or as object
                    if keyfield == "name":
                        # Adaptation for empty lists
                        if value == "[]": value = ""
                    else:
                        if value == "": 
                            value = None
                        elif value[0] == '[':
                            value = json.loads(value)
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Custom/custom_getkv")
        return key, value


class Address(models.Model):
    """IP addresses that have been blocked"""

    # [1] The IP address itself
    ip = models.CharField("IP address", max_length = MAX_TEXT_LEN)
    # [1] The reason for blocking
    reason = models.TextField("Reason")

    # [0-1] The date when blocked
    created = models.DateTimeField(default=get_current_datetime)

    # [0-1] The path that the user has used
    path = models.TextField("Path", null=True, blank=True)

    # [0-1] The whole body of the request
    body = models.TextField("Body", null=True, blank=True)

    def __str__(self):
        sBack = self.ip
        return sBack

    def add_address(ip, request, reason):
        """Add an IP to the blocked ones"""

        bResult = True
        oErr = ErrHandle()
        try:
            if ip != "127.0.0.1":
                # Check if it is on there already
                obj = Address.objects.filter(ip=ip).first()
                if obj is None:
                    # It is not on there, so continue
                    path = request.path
                    get = request.POST if request.POST else request.GET
                    body = json.dumps(get)
                    obj = Address.objects.create(ip=ip, path=path, body=body, reason=reason)

        except:
            msg = oErr.get_error_message()
            oErr.DoError("Address/add_address")
            bResult = False

        return bResult

    def is_blocked(ip, request):
        """Check if an IP address is blocked or not"""

        bResult = False
        oErr = ErrHandle()
        look_for = [
            ".php", "%3dphp", "win.ini", "/passwd", ".env", "config.ini", ".local", ".zip", "jasperserver"
            ]
        try:
            # Check if it is on there already
            obj = Address.objects.filter(ip=ip).first()
            if obj is None:
                # Double check
                path = request.path.lower()
                if path != "/":
                    # We need to look further
                    for item in look_for:
                        if item in path:
                            # Block it
                            Address.add_address(ip, request, item)
                            bResult = True
                            break
            else:
                # It is already blocked
                bResult = True
        except:
            msg = oErr.get_error_message()
            oErr.DoError("Address/is_blocked")

        return bResult
