from django.contrib import admin
from .models import Server

class ServerAdmin(admin.ModelAdmin):
    fields = ('name', 'address', 'organization')

admin.site.register(Server, ServerAdmin)
