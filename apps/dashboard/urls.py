from django.urls import path
from .views import (
    AdminLoginView, AdminLogoutView, AdminDashboardView, CreateCustomerView
)

app_name = 'dashboard'

urlpatterns = [
    path('login/', AdminLoginView.as_view(), name='admin_login'),
    path('logout/',AdminLogoutView.as_view(), name='logout'),
    path('admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('create-customer/', CreateCustomerView.as_view(), name='create_customer'),
]
