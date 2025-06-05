from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment

@receiver(post_save, sender=Appointment)
def appointment_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for post-save on Appointment model
    """
    # We're not sending confirmation emails here anymore
    # The view handles sending the confirmation email
    pass
