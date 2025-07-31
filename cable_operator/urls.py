from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import debug_toolbar
from django.shortcuts import redirect


urlpatterns = [
    path('', lambda request: redirect('dashboard:admin_login')),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('payments/', include('apps.payments.urls')),
    path('plans/', include('apps.plans.urls')),
    path('subscriptions/', include('apps.subscriptions.urls')),
    path('__debug__/', include(debug_toolbar.urls)),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
