from django.urls import path
from .views import login_view, logout_view, dashboard_view, register_view

urlpatterns = [
    path('', login_view, name='login'),          # root → login
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
     path('register/', register_view, name='register'),
]