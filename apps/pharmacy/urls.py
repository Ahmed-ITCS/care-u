from django.urls import path
from .views import web as views

app_name = 'pharmacy'

urlpatterns = [
    path('inventory/', views.inventory_list, name='inventory'),
    path('dispense/', views.dispense_list, name='dispense'),
    path('purchase-orders/', views.purchase_order_list, name='purchase_orders'),
]
