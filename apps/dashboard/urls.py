from django.urls import path
from .views import (
    AdminLoginView
)

app_name = 'dashboard'

urlpatterns = [
    path('login/', AdminLoginView.as_view(), name='admin_login'),
]
