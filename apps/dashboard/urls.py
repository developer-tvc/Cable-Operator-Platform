from django.urls import path
from .views import (
    AdminLoginView, AdminLogoutView, AdminDashboardView, CustomerListView, CreateCustomerView, UpdateCustomerView,
    DeleteCustomerView,PlanInfoView,CustomerDetailView,RazorpayPaymentView, RazorpayVerifyPaymentView,
    CheckCustomerDuplicatesView,PaymentReceiptView, PaymentReceiptPDFView
)
from django.views.generic import TemplateView
from . import views


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

    path('customer/check-duplicates/', CheckCustomerDuplicatesView.as_view(), name='check_customer_duplicates'),

    # Payment URLs
    path("pay/<str:customer_id>/", views.RazorpayPaymentView.as_view(), name="gpay_redirect"),
    path("payments/verify/", views.RazorpayVerifyPaymentView.as_view(), name="razorpay-verify"),

    # Success and Failure pages - Updated to use class-based views
    path("payments/success/", views.PaymentSuccessView.as_view(), name="payment_success_page"),
    path("payments/failed/", views.PaymentFailedView.as_view(), name="payment_failed_page"),

    # Alternative URLs if needed
    path("payments/no-dues/", TemplateView.as_view(template_name="payments/No-Dues.html"), name="no_dues_page"),

    path("receipt/<int:payment_id>/", PaymentReceiptView.as_view(), name="payment-receipt"),
    path("receipt/<int:payment_id>/download/", PaymentReceiptPDFView.as_view(), name="payment-receipt-download"),

]
