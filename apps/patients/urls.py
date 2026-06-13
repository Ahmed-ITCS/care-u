from django.urls import path
from .views import web as views

app_name = 'patients'

urlpatterns = [
    path('', views.patient_list, name='list'),
    path('register/', views.patient_register, name='register'),
    path('portal/', views.patient_portal, name='portal'),
    path('<int:pk>/', views.patient_detail, name='detail'),
    path('<int:pk>/edit/', views.patient_edit, name='edit'),
]
