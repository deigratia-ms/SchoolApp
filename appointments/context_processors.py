import logging
from django.core.cache import cache
from .models import AppointmentSettings

logger = logging.getLogger(__name__)

def appointment_settings(request):
    """
    Context processor to provide appointment settings to all templates.
    Uses caching to improve performance.
    """
    try:
        # Try to get from cache first
        settings = cache.get('appointment_settings')
        if settings is None:
            settings = AppointmentSettings.objects.first()
            if settings:
                # Cache for 5 minutes
                cache.set('appointment_settings', settings, 300)

        return {'appointment_settings': settings}
    except Exception as e:
        logger.error(f"Error fetching appointment settings: {str(e)}")
        return {
            'appointment_settings': None
        }
