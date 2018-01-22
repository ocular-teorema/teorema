from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

UserAdmin.list_display += ('is_organization_admin', 'organization')
UserAdmin.fieldsets += ((None,  {'fields': ('organization', 'is_organization_admin')}), )

admin.site.register(User, UserAdmin)

'''
from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import User

@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ('id', 'username', 'fio')
'''
