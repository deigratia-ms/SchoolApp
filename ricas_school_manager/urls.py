"""
URL Configuration for the integrated Ricas School Manager
This file combines URL patterns from both the DGMS website and SMS system.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # DGMS Website URLs - mounted at the root for public access
    path('', include(('website.urls', 'website'), namespace='website')),

    # SMS System URLs
    path('users/', include('users.urls')),
    path('courses/', include('courses.urls')),
    path('assignments/', include('assignments.urls')),
    path('attendance/', include('attendance.urls')),
    path('communications/', include('communications.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('fees/', include(('fees.urls', 'fees'), namespace='fees')),
    path('payroll/', include(('payroll.urls', 'payroll'), namespace='payroll')),
    path('appointments/', include(('appointments.urls', 'appointments'), namespace='appointments')),

    # SMS custom admin route
    path('my-admin/', include(('users.urls', 'my_admin'), namespace='my_admin')),

    # TinyMCE
    path('tinymce/', include('tinymce.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
