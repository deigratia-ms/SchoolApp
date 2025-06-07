from django.core.cache import cache
from .models import SiteSettings
from users.models import SchoolSettings

def site_settings(request):
    """Add site settings to template context with caching for performance."""
    # Try to get from cache first
    cache_key = 'unified_site_settings'
    cached_settings = cache.get(cache_key)

    if cached_settings is not None:
        return cached_settings

    # If not in cache, fetch from database
    site_settings = SiteSettings.objects.first()
    school_settings = SchoolSettings.objects.first()

    # Create a unified settings object that prioritizes SchoolSettings logo
    # but falls back to SiteSettings if needed
    unified_settings = site_settings

    if unified_settings and school_settings:
        # If SchoolSettings has a logo, use it as the school_logo
        if school_settings.logo:
            unified_settings.school_logo = school_settings.logo
    elif school_settings:
        # If no SiteSettings but we have SchoolSettings, create a minimal object
        from types import SimpleNamespace
        unified_settings = SimpleNamespace()
        unified_settings.school_logo = school_settings.logo if school_settings.logo else None

    result = {
        'site_settings': unified_settings,
        'school_settings': school_settings
    }

    # Cache for 5 minutes
    cache.set(cache_key, result, 300)

    return result