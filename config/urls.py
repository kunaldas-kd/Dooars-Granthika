from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('authentication/', include('accounts.urls')),
    path("books/", include("books.urls")),
    path("members/", include("members.urls")),
    path("transactions/", include("transactions.urls")),
    path("reports/", include("reports.urls")),
    path("finance/", include("finance.urls")),
    path('dashboard/', include('dashboards.urls')),
    path('subscriptions/', include('subscriptions.urls')),
    path('superuser/', include('superuser.urls', namespace='superuser')),
]