from django.urls import path
from .views import web as views

app_name = 'appointments'

urlpatterns = [
    path('', views.appointment_list, name='list'),
    path('book/', views.appointment_create, name='create'),
    path('<int:pk>/edit/', views.appointment_edit, name='edit'),
    path('calendar/', views.doctor_calendar, name='doctor_calendar'),
    path('queue/', views.queue_board, name='queue'),
    path('my/', views.my_appointments, name='my_appointments'),
]
