from django.urls import path
from .views import web as views
from .views import import_views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('health/', views.health_check, name='health'),
    path('import/', import_views.data_import, name='data_import'),
    path('import/sample/<str:import_type>/', import_views.data_import_sample, name='data_import_sample'),
    path('api/chart/revenue/', views.revenue_chart_api, name='revenue_chart'),
    path('api/chart/appointments/', views.appointment_chart_api, name='appointment_chart'),
    path('api/chart/demographics/', views.demographics_chart_api, name='demographics_chart'),
]
