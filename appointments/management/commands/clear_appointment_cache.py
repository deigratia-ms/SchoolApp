from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Clear appointment-related cache entries'

    def handle(self, *args, **options):
        """
        Clear all appointment-related cache entries.
        This should be run when appointment settings are changed.
        """
        cache_keys = [
            'appointment_settings',
            'appointment_system_active',
        ]
        
        # Clear specific cache keys
        for key in cache_keys:
            cache.delete(key)
            
        # Clear user-specific caches (this is a pattern, actual keys will vary)
        # In production, you might want to use cache.clear() or implement
        # a more sophisticated cache invalidation strategy
        
        self.stdout.write(
            self.style.SUCCESS('Successfully cleared appointment cache entries')
        )
        
        self.stdout.write(
            self.style.WARNING(
                'Note: User-specific caches (notifications, preferences) will expire naturally'
            )
        )
