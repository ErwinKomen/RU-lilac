from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.forms.widgets import *

from lila.basic.models import *


class UserSearchAdmin(admin.ModelAdmin):
    """User search queries"""

    list_display = ['view', 'count', 'params']
    fields = ['view', 'count', 'params', 'history']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class AddressAdmin(admin.ModelAdmin):
    """IP addresses"""

    list_display = ['ip', 'reason', 'created']
    fields = ['ip', 'reason', 'path', 'body']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }




# Register your models here.
admin.site.register(UserSearch, UserSearchAdmin)
admin.site.register(Address, AddressAdmin)
