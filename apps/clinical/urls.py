from django.urls import path
from .views import web as views

app_name = 'clinical'

urlpatterns = [
    path('visits/', views.visit_list, name='visits'),
    path('visits/<int:pk>/', views.visit_detail, name='visit_detail'),
    path('wards/', views.ward_list, name='wards'),
    path('vitals/', views.vitals_chart, name='vitals'),
]
