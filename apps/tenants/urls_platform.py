from django.urls import path
from apps.tenants.views import platform as views

app_name = 'platform'

urlpatterns = [
    path('login/', views.platform_login, name='login'),
    path('logout/', views.platform_logout, name='logout'),
    path('dashboard/', views.platform_dashboard, name='dashboard'),
    path('plans/', views.plan_list, name='plans'),
    path('plans/create/', views.plan_create, name='plan_create'),
    path('plans/<int:pk>/edit/', views.plan_edit, name='plan_edit'),
    path('plans/<int:pk>/delete/', views.plan_delete, name='plan_delete'),
    path('hospitals/', views.hospital_list, name='hospitals'),
    path('hospitals/<int:pk>/', views.hospital_detail, name='hospital_detail'),
    path('hospitals/<int:pk>/action/', views.hospital_suspend, name='hospital_action'),
]
