from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

# Import models with error handling
try:
    from .models import Announcement, Event, Gallery, Staff
except ImportError:
    Announcement = Event = Gallery = Staff = None

try:
    from .models_career import JobPosition
except ImportError:
    JobPosition = None


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            'website:home',
            'website:about', 
            'website:academics',
            'website:admissions',
            'website:contact',
            'website:events',
            'website:news',
            'website:gallery',
            'website:staff-list',
            'website:careers',
            'website:virtual-tour',
            'website:school-calendar',
            'website:privacy-policy',
            'website:terms-of-service',
            'website:faqs',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        # Higher priority for important pages
        high_priority_pages = ['website:home', 'website:about', 'website:admissions']
        if item in high_priority_pages:
            return 1.0
        return 0.8

    def changefreq(self, item):
        # More frequent updates for dynamic content pages
        frequent_pages = ['website:home', 'website:events', 'website:news']
        if item in frequent_pages:
            return 'daily'
        return 'weekly'


class AnnouncementSitemap(Sitemap):
    """Sitemap for news/announcements"""
    changefreq = 'weekly'
    priority = 0.7
    protocol = 'https'

    def items(self):
        if Announcement is None:
            return []
        return Announcement.objects.all().order_by('-date_posted')

    def lastmod(self, obj):
        return obj.date_posted

    def location(self, obj):
        return reverse('website:announcement-detail', kwargs={'slug': obj.slug})


class EventSitemap(Sitemap):
    """Sitemap for events"""
    changefreq = 'weekly'
    priority = 0.7
    protocol = 'https'

    def items(self):
        if Event is None:
            return []
        return Event.objects.filter(date__gte=timezone.now()).order_by('date')

    def lastmod(self, obj):
        return obj.date

    def location(self, obj):
        return reverse('website:event-detail', kwargs={'pk': obj.pk})


class GallerySitemap(Sitemap):
    """Sitemap for gallery items"""
    changefreq = 'monthly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        if Gallery is None:
            return []
        return Gallery.objects.all().order_by('-date_added')

    def lastmod(self, obj):
        return obj.date_added

    def location(self, obj):
        return reverse('website:gallery-detail', kwargs={'pk': obj.pk})


class StaffSitemap(Sitemap):
    """Sitemap for staff profiles"""
    changefreq = 'monthly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        if Staff is None:
            return []
        return Staff.objects.all().order_by('name')

    def location(self, obj):
        return reverse('website:staff-detail', kwargs={'pk': obj.pk})


class JobSitemap(Sitemap):
    """Sitemap for job postings"""
    changefreq = 'weekly'
    priority = 0.6
    protocol = 'https'

    def items(self):
        if JobPosition is None:
            return []
        return JobPosition.objects.filter(
            is_active=True,
            application_deadline__gte=timezone.now().date()
        ).order_by('-date_posted')

    def lastmod(self, obj):
        return obj.date_posted

    def location(self, obj):
        # Note: You'll need to create a job detail view if you want individual job pages
        return reverse('website:careers')  # For now, link to careers page


# Dictionary of all sitemaps
sitemaps = {
    'static': StaticViewSitemap,
    'announcements': AnnouncementSitemap,
    'events': EventSitemap,
    'gallery': GallerySitemap,
    'staff': StaffSitemap,
    'jobs': JobSitemap,
}
