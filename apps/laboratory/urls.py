from django.urls import path
from .views import web as views

app_name = 'laboratory'

urlpatterns = [
    path('requests/', views.request_list, name='requests'),
    path('requests/new/', views.request_create, name='request_create'),
    path('results/', views.result_list, name='results'),
]
