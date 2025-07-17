from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('payments/', include('apps.payments.urls')),
    path('plans/', include('apps.plans.urls')),
    path('subscriptions/', include('apps.subscriptions.urls')),
]
