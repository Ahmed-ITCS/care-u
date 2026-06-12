from django.contrib import admin
from .models import HospitalConfig, Department


@admin.register(HospitalConfig)
class HospitalConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'currency')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
