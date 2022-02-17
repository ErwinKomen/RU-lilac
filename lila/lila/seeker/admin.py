from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse

from lila.seeker.models import *
from lila.seeker.forms import *
from lila.settings import ADMIN_SITE_URL

class LogEntryAdmin(admin.ModelAdmin):

    date_hierarchy = 'action_time'

    # readonly_fields = LogEntry._meta.get_all_field_names()
    readonly_fields = [f.name for f in LogEntry._meta.get_fields()]

    list_filter = ['user', 'content_type', 'action_flag' ]
    search_fields = [ 'object_repr', 'change_message' ]    
    list_display = ['action_time', 'user', 'content_type', 'object_link', 'action_flag_', 'change_message', ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and request.method != 'POST'

    def has_delete_permission(self, request, obj=None):
        return False

    def action_flag_(self, obj):
        flags = { 1: "Addition", 2: "Changed", 3: "Deleted", }
        return flags[obj.action_flag]

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            link = '<a href="{}">{}</a>'.format(
                reverse('admin:{}_{}_change'.format(ct.app_label, ct.model), args=[obj.object_id]),
                escape(obj.object_repr),
            )
        return link
    object_link.allow_tags = True
    object_link.admin_order_field = 'object_repr'
    object_link.short_description = u'object'


class FieldChoiceAdmin(admin.ModelAdmin):
    readonly_fields=['machine_value']
    list_display = ['english_name','dutch_name','abbr', 'machine_value','field']
    list_filter = ['field']

    def save_model(self, request, obj, form, change):

        if obj.machine_value == None:
            # Check out the query-set and make sure that it exists
            qs = FieldChoice.objects.filter(field=obj.field)
            if len(qs) == 0:
                # The field does not yet occur within FieldChoice
                # Future: ask user if that is what he wants (don't know how...)
                # For now: assume user wants to add a new field (e.g: wordClass)
                # NOTE: start with '0'
                obj.machine_value = 0
            else:
                # Calculate highest currently occurring value
                highest_machine_value = max([field_choice.machine_value for field_choice in qs])
                # The automatic machine value we calculate is 1 higher
                obj.machine_value= highest_machine_value+1

        obj.save()


class HelpChoiceAdmin(admin.ModelAdmin):
    list_display = ['field', 'display_name', 'help_url', 'help_html']
    list_filter = ['field']
    fields = ['field', 'display_name', 'searchable', 'help_url', 'help_html']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'nameFR', 'idPaysEtab']
    

class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'idVilleEtab', 'country']
    list_filter = ['country']


class LibraryAdmin(admin.ModelAdmin):
    list_display = ['name', 'idLibrEtab', 'libtype', 'country', 'city']
    list_filter = ['libtype', 'country']


class NewsItemAdmin(admin.ModelAdmin):
    """Display and edit of [NewsItem] definitions"""

    list_display = ['title', 'until', 'status', 'created', 'saved' ]
    search_fields = ['title', 'status']
    fields = ['title', 'created', 'until', 'status', 'msg']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class VisitAdmin(admin.ModelAdmin):
    """Display and edit Visit moments"""

    list_display = ['user', 'when', 'name', 'path']
    list_filter = ['user', 'name']
    search_fields = ['user']
    fields = ['user', 'when', 'name', 'path']


class ActionAdmin(admin.ModelAdmin):
    """Display and edit Action moments"""

    list_display = ['user', 'when', 'itemtype', 'actiontype', 'details']
    list_filter = ['user', 'itemtype', 'actiontype']
    search_fields = ['user']
    fields = ['user', 'when', 'itemtype', 'actiontype', 'details']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class FreeAdmin(admin.ModelAdmin):

    list_display = ['name', 'field', 'main']
    list_filter = ['main']
    search_fields = ['name', 'field']
    fields = ['name', 'field', 'main']


class ProfileAdmin(admin.ModelAdmin):
    """Display user profiles"""

    list_display = ['user', 'stack']
    fields = ['user', 'stack']


class SermonGoldKeywordAdmin(admin.ModelAdmin):
    """Display keywords"""

    list_display = ['name', 'created']
    fields = ['name', 'created']


class InformationAdmin(admin.ModelAdmin):
    """Information k/v pairs"""

    list_display = ['name', 'kvalue']
    fields = ['name', 'kvalue']


class ReportAdmin(admin.ModelAdmin):
    """Information k/v pairs"""

    list_display = ['user', 'created', 'reptype', 'contents']
    fields = ['user', 'created', 'reptype', 'contents']


class LocationTypeAdmin(admin.ModelAdmin):
    """Definition of each location type"""

    fields = ['name', 'level']
    list_display = ['name', 'level']


class LocationAdmin(admin.ModelAdmin):
    """Definition of each location"""

    fields = ['name', 'loctype']
    list_display = ['name', 'loctype']
    list_filter = ['loctype']


class SourceInfoAdmin(admin.ModelAdmin):
    """Sources from where information has been extracted"""
    fields = ['created', 'code', 'url', 'collector']
    list_display = ['created', 'code', 'url', 'collector']
    list_filter = ['collector']


class LitrefAdmin(admin.ModelAdmin):
    """Literature references"""
    fields = ['itemid', 'data', 'abbr', 'short', 'full']
    list_display = ['itemid', 'abbr', 'short']
    list_filter = ['itemid']


class CanwitAdmin(admin.ModelAdmin):
    """Canwit"""

    list_display = ['id', 'siglist', 'verses', 'title', 'author']
    search_fields = ['id', 'siglist']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class AustatAdmin(admin.ModelAdmin):
    """Austat = SSG"""

    list_display = ['id', 'code', 'number', 'author']
    search_fields = ['id', 'code']  
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


class ManuscriptAdmin(admin.ModelAdmin):
    """Manuscript"""
    list_display = ['id', 'name', 'idno', 'mtype']
    search_fields = ['name', 'idno']
    # WEG! list_filter = ['project'] 
    list_filter = ['mtype']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


# Models that serve others
admin.site.register(FieldChoice, FieldChoiceAdmin)
admin.site.register(HelpChoice, HelpChoiceAdmin)
admin.site.register(NewsItem, NewsItemAdmin)
admin.site.register(Information, InformationAdmin)

# Main program models
admin.site.register(Country, CountryAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(Library, LibraryAdmin)
admin.site.register(Keyword)
admin.site.register(Origin)
admin.site.register(Free, FreeAdmin)
admin.site.register(LocationType, LocationTypeAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(SourceInfo, SourceInfoAdmin)
admin.site.register(Litref, LitrefAdmin)
admin.site.register(LitrefMan)
admin.site.register(Comment)
admin.site.register(Canwit, CanwitAdmin)
admin.site.register(Manuscript, ManuscriptAdmin)
admin.site.register(Austat, AustatAdmin)

admin.site.register(Report, ReportAdmin)

# Logbook of activities
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(Visit, VisitAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Action, ActionAdmin)

# How to display user information
admin.site.unregister(User)
# What to display in a list
UserAdmin.list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'last_login']
# Turn it on again
admin.site.register(User, UserAdmin)

# Register link
admin.site.site_url = ADMIN_SITE_URL