from django.urls import path
from .views import (
    PlanListView,
    PlanCreateView,
    PlanUpdateView,
    PlanDeleteView,
    DownloadQRCodePDFView,
)

app_name = 'plan'

urlpatterns = [
    path('plans/', PlanListView.as_view(), name='plan_management'),
    path('plans/create/', PlanCreateView.as_view(), name='create_plan'),
    path('plans/update/<int:pk>/', PlanUpdateView.as_view(), name='update_plan'),
    path('plans/delete/<int:pk>/', PlanDeleteView.as_view(), name='delete_plan'),
    path('customer/<int:customer_id>/download_qr/', DownloadQRCodePDFView.as_view(), name='download_qr_pdf'),
]
