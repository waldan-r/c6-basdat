from django.urls import path
from . import views

app_name = 'order_promo'

urlpatterns = [
    path('events/', views.event_list, name='event_list'),
    path('checkout/', views.checkout, name='checkout_order'),
    path('all/', views.order_list, name='order_list'),
    path('update/', views.order_update, name='order_update'),
    path('delete/', views.order_delete, name='order_delete'),
    path('promotion/', views.promotion_list, name='promotion_list'),
    path('promotion/create/', views.promotion_create, name='promotion_create'),
    path('promotion/update/', views.promotion_update, name='promotion_update'),
    path('promotion/delete/', views.promotion_delete, name='promotion_delete'),
    path('promotion/dashboard/', views.promotion_dashboard, name='promotion_dashboard'),
]
