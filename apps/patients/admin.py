from django.contrib import admin
from .models import (
    Patient, InsuranceProvider, PatientInsurance, EmergencyContact,
    Allergy, ChronicCondition, MedicalHistory, FamilyHistory,
    VitalSign, PatientDocument,
)


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 1


class AllergyInline(admin.TabularInline):
    model = Allergy
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('mr_number', 'full_name', 'cnic', 'phone', 'gender', 'created_at')
    search_fields = ('mr_number', 'cnic', 'full_name', 'phone')
    list_filter = ('gender', 'city')
    inlines = [EmergencyContactInline, AllergyInline]
    readonly_fields = ('mr_number', 'full_name')


@admin.register(InsuranceProvider)
class InsuranceProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_phone', 'is_active')


admin.site.register(PatientInsurance)
admin.site.register(Allergy)
admin.site.register(ChronicCondition)
admin.site.register(MedicalHistory)
admin.site.register(FamilyHistory)
admin.site.register(VitalSign)
admin.site.register(PatientDocument)
