from django.contrib import admin
from .models import (
    TestCategory, TestCatalog, LabTestRequest, LabTestRequestItem,
    SampleCollection, TestResult, LabReport,
)


class LabTestRequestItemInline(admin.TabularInline):
    model = LabTestRequestItem
    extra = 1


@admin.register(LabTestRequest)
class LabTestRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'patient', 'status', 'created_at')
    list_filter = ('status',)
    inlines = [LabTestRequestItemInline]


@admin.register(TestCatalog)
class TestCatalogAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'price', 'is_active')
    search_fields = ('name', 'code')


admin.site.register(TestCategory)
admin.site.register(SampleCollection)
admin.site.register(TestResult)
admin.site.register(LabReport)
