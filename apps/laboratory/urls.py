from django.urls import path
from .views import web as views

app_name = 'laboratory'

urlpatterns = [
    path('requests/', views.request_list, name='requests'),
    path('results/', views.result_list, name='results'),
]
