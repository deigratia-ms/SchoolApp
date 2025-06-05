from django.db.models.signals import post_save
from django.dispatch import receiver

from .models_career import JobApplication

@receiver(post_save, sender=JobApplication)
def send_application_confirmation(sender, instance, created, **kwargs):
    """Send confirmation email when a new job application is created"""
    if created:
        instance.send_confirmation_email()
