from django.contrib import admin
from .models import AppointmentType, DoctorSchedule, Appointment, QueueEntry


@admin.register(AppointmentType)
class AppointmentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'duration_minutes', 'is_active')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'scheduled_date', 'scheduled_time', 'status', 'source')
    list_filter = ('status', 'source', 'scheduled_date')
    search_fields = ('patient__full_name', 'patient__mr_number')
    date_hierarchy = 'scheduled_date'


admin.site.register(DoctorSchedule)
admin.site.register(QueueEntry)
