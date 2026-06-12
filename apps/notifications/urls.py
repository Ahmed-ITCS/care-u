from django.urls import path
from .views import web as views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
]
