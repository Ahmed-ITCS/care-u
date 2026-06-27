from django.urls import path
from .views import web as views

app_name = 'laboratory'

urlpatterns = [
    path('requests/', views.request_list, name='requests'),
    path('requests/new/', views.request_create, name='request_create'),
    path('results/', views.result_list, name='results'),
    path('tests/', views.catalog_list, name='catalog'),
    path('tests/add/', views.test_create, name='test_create'),
    path('tests/<int:pk>/edit/', views.test_edit, name='test_edit'),
]
