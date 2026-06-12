from django.urls import path
from apps.tenants.views import onboarding as views

app_name = 'tenants'

urlpatterns = [
    path('', views.onboarding_wizard, name='onboarding'),
    path('settings/', views.hospital_settings, name='hospital_settings'),
]
