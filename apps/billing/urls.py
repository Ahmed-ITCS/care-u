from django.urls import path
from .views import web as views

app_name = 'billing'

urlpatterns = [
    path('invoices/', views.invoice_list, name='invoices'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('payments/', views.payment_list, name='payments'),
    path('my-bills/', views.my_bills, name='my_bills'),
]
