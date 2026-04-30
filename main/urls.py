from django.urls import path
from .views import login_view, logout_view, dashboard_view, register_view, artist_list_view, artist_manage_view

urlpatterns = [
    path('', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('artists/', artist_list_view, name='artist_list'),
    path('artists/manage/', artist_manage_view, name='artist_manage'),
]