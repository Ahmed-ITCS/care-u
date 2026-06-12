from django.contrib import admin
from .models import Shift, StaffShiftAssignment, Attendance, LeaveRequest, PayrollRun, PayrollItem, DoctorCommission


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('staff', 'date', 'check_in', 'check_out', 'status')
    list_filter = ('status', 'date')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('staff', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'leave_type')


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'status', 'total_amount')


admin.site.register(Shift)
admin.site.register(StaffShiftAssignment)
admin.site.register(PayrollItem)
admin.site.register(DoctorCommission)
