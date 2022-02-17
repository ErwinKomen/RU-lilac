from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse

from lila.bible.models import *

# Register your models here.

class ChapterAdmin(admin.ModelAdmin):
    fields = ['book', 'number', 'vsnum']
    list_display = ['book', 'number', 'vsnum']


class ChapterInline(admin.TabularInline):
    model = Chapter
    fk_name = 'book'
    extra = 0


class BookAdmin(admin.ModelAdmin):
    list_display = ['name', 'latname', 'idno', 'abbr', 'latabbr', 'chnum']
    fields = ['name', 'latname', 'idno', 'abbr', 'latabbr', 'chnum']
    inlines = [ChapterInline]
    formfield_overrides = {
        models.TextField: {'widget': admin.widgets.AdminTextareaWidget(attrs={'rows': 1, 'class': 'mytextarea'})},
        }


# Main program models
admin.site.register(Chapter, ChapterAdmin)
admin.site.register(Book, BookAdmin)
