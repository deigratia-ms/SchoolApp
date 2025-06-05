from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Event
from website.models import Event as WebsiteEvent
from website.models import EventCategory
import logging

# Get logger for better error tracking
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Event)
def sync_event_to_website(sender, instance, **kwargs):
    """
    When a management system event is saved with show_on_website=True,
    create or update a corresponding event on the website.
    """
    try:
        # Only proceed if the event should be shown on the website
        if instance.show_on_website:
            logger.info(f"Syncing event {instance.id} to website: {instance.title}")

            # Check if there's already a website event linked to this management event
            website_event = WebsiteEvent.objects.filter(management_event=instance).first()

            # If no existing website event, create a new one
            if not website_event:
                website_event = WebsiteEvent()
                website_event.management_event = instance
                logger.info(f"Creating new website event for {instance.title}")
            else:
                logger.info(f"Updating existing website event for {instance.title}")

            # Update website event fields from management event
            website_event.title = instance.title
            website_event.description = instance.description or ""

            # Convert start_date and start_time to a datetime for the website event
            if instance.all_day:
                # For all-day events, use midnight as the time
                date_str = instance.start_date.strftime('%Y-%m-%d')
                website_event.date = timezone.datetime.strptime(date_str, '%Y-%m-%d')
            else:
                # For timed events, combine date and time
                if instance.start_time:
                    date_str = instance.start_date.strftime('%Y-%m-%d')
                    time_str = instance.start_time.strftime('%H:%M:%S')
                    datetime_str = f"{date_str} {time_str}"
                    website_event.date = timezone.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                else:
                    # Fallback if no start_time is provided
                    date_str = instance.start_date.strftime('%Y-%m-%d')
                    website_event.date = timezone.datetime.strptime(date_str, '%Y-%m-%d')

            # Set location
            website_event.location = instance.location or "School Campus"

            # Copy attachment as image if available
            if instance.attachment:
                try:
                    # Always update the image when there's an attachment
                    website_event.image = instance.attachment
                    logger.info(f"Set image for website event from management event attachment: {instance.attachment}")
                except Exception as e:
                    logger.error(f"Error copying attachment as image: {str(e)}")

            # Set registration info if it's a virtual event
            if instance.is_virtual:
                website_event.registration_required = True
                website_event.registration_link = instance.virtual_link or ""

            # Save the website event
            website_event.save()
            logger.info(f"Successfully synced event {instance.id} to website event {website_event.id}")

        # If show_on_website is False but there's a linked website event, delete it
        elif not instance.show_on_website:
            website_event = WebsiteEvent.objects.filter(management_event=instance).first()
            if website_event:
                logger.info(f"Deleting website event {website_event.id} as management event {instance.id} is no longer marked for website display")
                website_event.delete()

    except Exception as e:
        logger.error(f"Error syncing event to website: {str(e)}", exc_info=True)
