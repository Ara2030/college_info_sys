"""Корневые маршруты ИС колледжа."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('contingent.urls')),
    path('journal/', include('journal.urls')),
    path('attestation/', include('attestation.urls')),
    path('schedule/', include('schedule.urls')),
    path('hr/', include('hr.urls')),
    path('reporting/', include('reporting.urls')),
]
