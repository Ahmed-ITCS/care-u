from django.urls import path
from .views import web as views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('health/', views.health_check, name='health'),
    path('api/chart/revenue/', views.revenue_chart_api, name='revenue_chart'),
    path('api/chart/appointments/', views.appointment_chart_api, name='appointment_chart'),
    path('api/chart/demographics/', views.demographics_chart_api, name='demographics_chart'),
]
