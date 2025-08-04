from django.urls import path
from .views import (
    AdminLoginView, AdminLogoutView, AdminDashboardView, CustomerListView, CreateCustomerView, UpdateCustomerView,
    DeleteCustomerView,PlanInfoView,GPayRedirectView,CustomerDetailView
)

app_name = 'dashboard'

urlpatterns = [
    path('login/', AdminLoginView.as_view(), name='admin_login'),
    path('logout/',AdminLogoutView.as_view(), name='logout'),
    path('admin/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', CreateCustomerView.as_view(), name='create_customer'),
    path('customer/edit/<int:pk>/', UpdateCustomerView.as_view(), name='edit_customer'),
    path('customers/<str:pk>/delete/', DeleteCustomerView.as_view(), name='delete_customer'),
    path('customer/detail/<int:pk>/', CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/plan-info/',  PlanInfoView.as_view(),   name='plan_info'),
    path('pay/<str:customer_id>/', GPayRedirectView.as_view(), name='gpay_redirect'),

]
