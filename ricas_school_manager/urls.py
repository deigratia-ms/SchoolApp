"""
URL Configuration for the integrated Ricas School Manager
This file combines URL patterns from both the DGMS website and SMS system.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect


def health_check(request):
    """Health check endpoint for deployment monitoring"""
    return JsonResponse({'status': 'healthy', 'service': 'school-management-system'})

def simple_sitemap(request):
    """Simple sitemap.xml view"""
    sitemap_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <!-- Main Pages -->
  <url>
    <loc>https://deigratiams.edu.gh/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/about/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/academics/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/admissions/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/contact/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/events/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/news/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/gallery/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/staff/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/careers/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/virtual-tour/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/calendar/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/faqs/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/privacy-policy/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.3</priority>
  </url>
  <url>
    <loc>https://deigratiams.edu.gh/terms-of-service/</loc>
    <lastmod>2025-01-27</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.3</priority>
  </url>
</urlset>'''
    return HttpResponse(sitemap_content, content_type='application/xml')

def robots_txt(request):
    """Simple robots.txt view"""
    robots_content = '''User-agent: *
Allow: /

# Disallow admin and private areas
Disallow: /admin/
Disallow: /dashboard/
Disallow: /users/
Disallow: /courses/
Disallow: /assignments/
Disallow: /attendance/
Disallow: /communications/
Disallow: /fees/
Disallow: /payroll/
Disallow: /appointments/
Disallow: /my-admin/

# Disallow API endpoints
Disallow: /api/

# Allow important pages
Allow: /
Allow: /about/
Allow: /academics/
Allow: /admissions/
Allow: /contact/
Allow: /events/
Allow: /news/
Allow: /gallery/
Allow: /staff/
Allow: /careers/
Allow: /virtual-tour/
Allow: /calendar/
Allow: /privacy-policy/
Allow: /terms-of-service/
Allow: /faqs/

# Sitemap location
Sitemap: https://deigratiams.edu.gh/sitemap.xml

# Crawl-delay for respectful crawling
Crawl-delay: 1'''
    return HttpResponse(robots_content, content_type='text/plain')

def my_admin_redirect(request):
    """Redirect /my-admin to /my-admin/ to handle missing trailing slash"""
    return redirect('/my-admin/')

urlpatterns = [
    # Health check endpoint
    path('health/', health_check, name='health_check'),

    # SEO URLs
    path('sitemap.xml', simple_sitemap, name='sitemap'),
    path('robots.txt', robots_txt, name='robots'),

    # Django Admin
    path('admin/', admin.site.urls),

    # Handle /my-admin without trailing slash (redirect to /my-admin/)
    path('my-admin', my_admin_redirect, name='my_admin_redirect'),

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

# Serve media and static files only in development (Cloudinary handles production media files)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
