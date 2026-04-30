from django.urls import path
from . import views

app_name = 'order'

urlpatterns = [
    path('events/', views.list_event_view, name='event_list'),
    path('checkout/', views.create_order_view, name='checkout_order'),
    path('all/', views.list_order_view, name='order_list'),
    path('update/', views.update_order_view, name='order_update'),
    path('delete/', views.order_delete_view, name='order_delete'),
    path('promotion/', views.promotion_list_view, name='promotion_list'),
    path('promotion/dashboard/', views.promotion_dashboard_view, name='promotion_dashboard'),
]