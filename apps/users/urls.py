from django.urls import path
from .views import web as views

app_name = 'users'

urlpatterns = [
    path('login/', views.GPHLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('otp/', views.otp_request_view, name='otp_request'),
    path('otp/verify/', views.otp_verify_view, name='otp_verify'),
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
]
