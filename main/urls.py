from django.urls import path

from django.views.generic import RedirectView
from .views import login_view, logout_view, dashboard_view, register_view, artist_list_view, artist_manage_view, list_venue, list_event, seats_view, ticket_category_manage_view, ticket_view, venue_manage_view

urlpatterns = [
    path('', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('artists/', artist_list_view, name='artist_list'),
    path('artists/manage/', artist_manage_view, name='artist_manage'),
    path('ticket-category/', ticket_category_manage_view, name='ticket_category_manage'),
    path('venues/', list_venue, name='list_venue'),
    path('venues/manage/', venue_manage_view, name='venue_manage'),
    path('events/', list_event, name='list_event'),
    path('tickets/', ticket_view, name='tickets'),
    path('tickets/my/', ticket_view, name='my_tickets'),
    path('seats/', seats_view, name='seats'),
    path('seats/manage/', seats_view, name='seats_manage'),
    path('orders-promo/my/', RedirectView.as_view(pattern_name='order_promo:order_list', permanent=False)),
    path('promotions/', RedirectView.as_view(pattern_name='order_promo:promotion_list', permanent=False)),
    path('assets/tickets/', RedirectView.as_view(pattern_name='tickets', permanent=False)),
    path('assets/orders/', RedirectView.as_view(pattern_name='order_promo:order_list', permanent=False)),
    path('profile/', dashboard_view, name='profile'),

]
