from django.urls import path
from .views import login_view, logout_view, dashboard_view, register_view, artist_list_view, artist_manage_view, seats_view, ticket_category_manage_view, ticket_view

urlpatterns = [
    path('', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('artists/', artist_list_view, name='artist_list'),
    path('artists/manage/', artist_manage_view, name='artist_manage'),
    path('ticket-category/', ticket_category_manage_view, name='ticket_category_manage'),
    path('tickets/my/', ticket_view, name='my_tickets'),
    path('tickets/manage/', ticket_view, name='ticket_manage'),
    path('seats/', seats_view, name='seats'),

]