from .models import SiteSettings

def site_settings(request):
    """Add site settings to template context."""
    settings = SiteSettings.objects.first()
    return {'site_settings': settings}