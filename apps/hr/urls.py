from django.urls import path
from .views import web as views

app_name = 'hr'

urlpatterns = [
    path('attendance/', views.attendance_list, name='attendance'),
    path('leaves/', views.leave_list, name='leaves'),
    path('payroll/', views.payroll_list, name='payroll'),
]
