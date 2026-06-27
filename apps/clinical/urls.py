from django.urls import path
from .views import web as views

app_name = 'clinical'

urlpatterns = [
    path('visits/', views.visit_list, name='visits'),
    path('visits/new/', views.visit_create, name='visit_create'),
    path('visits/<int:pk>/', views.visit_detail, name='visit_detail'),
    path('visits/<int:pk>/complete/', views.visit_complete, name='visit_complete'),
    path('wards/', views.ward_list, name='wards'),
    path('vitals/', views.vitals_chart, name='vitals'),
]
