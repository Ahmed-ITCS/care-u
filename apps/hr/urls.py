from django.urls import path
from .views import web as views

app_name = 'hr'

urlpatterns = [
    path('attendance/', views.attendance_list, name='attendance'),
    path('attendance/new/', views.attendance_create, name='attendance_create'),
    path('attendance/<int:pk>/edit/', views.attendance_edit, name='attendance_edit'),
    path('leaves/', views.leave_list, name='leaves'),
    path('leaves/new/', views.leave_create, name='leave_create'),
    path('leaves/<int:pk>/approve/', views.leave_approve, name='leave_approve'),
    path('leaves/<int:pk>/reject/', views.leave_reject, name='leave_reject'),
    path('payroll/', views.payroll_list, name='payroll'),
    path('payroll/new/', views.payroll_create, name='payroll_create'),
    path('payroll/<int:pk>/', views.payroll_detail, name='payroll_detail'),
    path('payroll/<int:pk>/process/', views.payroll_process, name='payroll_process'),
]
