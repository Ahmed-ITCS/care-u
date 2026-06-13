from django.urls import path
from apps.tenants.views import billing as views

app_name = 'tenants'

urlpatterns = [
    path('', views.billing_paywall, name='billing'),
    path('checkout/', views.billing_checkout, name='billing_checkout'),
    path('jazzcash/', views.billing_jazzcash, name='billing_jazzcash'),
    path('easypaisa/', views.billing_easypaisa, name='billing_easypaisa'),
    path('portal/', views.billing_portal, name='billing_portal'),
    path('success/', views.billing_success, name='billing_success'),
    path('cancel/', views.billing_cancel, name='billing_cancel'),
    path('status/', views.billing_status_api, name='billing_status'),
]
