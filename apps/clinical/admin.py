from django.contrib import admin
from .models import (
    Ward, Bed, Visit, OPDVisit, Admission, Discharge, Transfer,
    NursingNote, Prescription, PrescriptionItem, LabOrder, RadiologyOrder,
    Referral, ProcedureNote, Diagnosis,
)


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('visit', 'doctor', 'status', 'created_at')
    inlines = [PrescriptionItemInline]


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'visit_type', 'status', 'visit_date')
    list_filter = ('visit_type', 'status')


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('name', 'ward_type', 'floor', 'capacity', 'is_active')


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('ward', 'bed_number', 'status', 'daily_rate')
    list_filter = ('status', 'ward')


admin.site.register(OPDVisit)
admin.site.register(Admission)
admin.site.register(Discharge)
admin.site.register(Transfer)
admin.site.register(NursingNote)
admin.site.register(LabOrder)
admin.site.register(RadiologyOrder)
admin.site.register(Referral)
admin.site.register(ProcedureNote)
admin.site.register(Diagnosis)
