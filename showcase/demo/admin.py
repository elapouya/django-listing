#
# Created : 2018-03-06
#
# @author: Eric Lapouyade
#

from django.contrib import admin
from .models import *

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name',
                    'last_name',
                    'age',
                    'designation',
                    'salary',
                    'joined')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'address',
                    'city',
                    'country')


@admin.register(BooleanModel)
class BooleanModelAdmin(admin.ModelAdmin):
    pass


