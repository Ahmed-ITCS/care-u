from django.urls import path
from apps.tenants.views import platform as views

app_name = 'platform'

urlpatterns = [
    path('login/', views.platform_login, name='login'),
    path('logout/', views.platform_logout, name='logout'),
    path('dashboard/', views.platform_dashboard, name='dashboard'),
    path('hospitals/', views.hospital_list, name='hospitals'),
    path('hospitals/<int:pk>/', views.hospital_detail, name='hospital_detail'),
    path('hospitals/<int:pk>/action/', views.hospital_suspend, name='hospital_action'),
]
