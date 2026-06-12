from django.urls import path
from apps.tenants.views import public as views

app_name = 'tenants'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.hospital_register, name='register'),
    path('register/success/<slug:subdomain>/', views.register_success, name='register_success'),
    path('login/', views.unified_login, name='login'),
    path('logout/', views.public_logout, name='logout'),
    path('pricing/', views.pricing, name='pricing'),
    path('suspended/', views.suspended, name='suspended'),
]
