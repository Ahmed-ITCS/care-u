from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_index, name='index'),
    path('daily-opd/', views.daily_opd_report, name='daily_opd'),
    path('revenue/', views.revenue_report, name='revenue'),
    path('stock/', views.stock_report, name='stock'),
]
