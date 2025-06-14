"""
Cache utilities for website app to improve performance.
"""
from django.core.cache import cache


def clear_settings_cache():
    """Clear all settings-related cache entries."""
    cache.delete('unified_site_settings')


def clear_user_cache(user_id):
    """Clear all cache entries for a specific user."""
    cache_keys = [
        f'notifications_context_{user_id}',
        f'sidebar_context_{user_id}',
        f'user_preferences_{user_id}',
    ]
    cache.delete_many(cache_keys)


def clear_all_user_caches():
    """Clear all user-related cache entries (use sparingly)."""
    # This is a more aggressive approach - use only when necessary
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    for user in User.objects.values_list('id', flat=True):
        clear_user_cache(user)


def warm_cache():
    """Pre-warm frequently accessed cache entries."""
    # This can be called during deployment or maintenance
    from .models import SiteSettings
    from users.models import SchoolSettings

    # Pre-load settings
    site_settings = SiteSettings.objects.first()
    school_settings = SchoolSettings.objects.first()
    
    if site_settings or school_settings:
        # This will populate the cache
        from .context_processors import site_settings as get_site_settings
        from django.test import RequestFactory
        
        request = RequestFactory().get('/')
        get_site_settings(request)
