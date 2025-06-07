from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models_career import JobApplication
from .models import SiteSettings
from users.models import SchoolSettings
from .cache_utils import clear_settings_cache

@receiver(post_save, sender=JobApplication)
def send_application_confirmation(sender, instance, created, **kwargs):
    """Send confirmation email when a new job application is created"""
    if created:
        instance.send_confirmation_email()


@receiver(post_save, sender=SiteSettings)
@receiver(post_delete, sender=SiteSettings)
@receiver(post_save, sender=SchoolSettings)
@receiver(post_delete, sender=SchoolSettings)
def clear_settings_cache_on_change(sender, **kwargs):
    """Clear settings cache when SiteSettings or SchoolSettings are modified"""
    clear_settings_cache()
