from django.urls import path
from .views import web as views

app_name = 'billing'

urlpatterns = [
    path('invoices/', views.invoice_list, name='invoices'),
    path('invoices/create-from-visit/', views.invoice_create_from_visit, name='invoice_from_visit'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_pk>/pay/', views.payment_create, name='payment_create'),
    path('payments/', views.payment_list, name='payments'),
    path('charges/', views.charge_list, name='charges'),
    path('charges/new/', views.charge_create, name='charge_create'),
    path('charges/<int:pk>/edit/', views.charge_edit, name='charge_edit'),
    path('my-bills/', views.my_bills, name='my_bills'),
]
