from django.core.management.base import BaseCommand
from django.utils import timezone
from communications.models import Event
from website.models import Event as WebsiteEvent
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Syncs all events marked for website display to the website'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting event sync...'))
        
        # Get all management events marked for website display
        events = Event.objects.filter(show_on_website=True)
        self.stdout.write(f'Found {events.count()} events marked for website display')
        
        synced_count = 0
        error_count = 0
        
        for event in events:
            try:
                # Check if there's already a website event linked to this management event
                website_event = WebsiteEvent.objects.filter(management_event=event).first()
                
                # If no existing website event, create a new one
                if not website_event:
                    website_event = WebsiteEvent()
                    website_event.management_event = event
                    self.stdout.write(f'Creating new website event for "{event.title}"')
                else:
                    self.stdout.write(f'Updating existing website event for "{event.title}"')
                
                # Update website event fields from management event
                website_event.title = event.title
                website_event.description = event.description or ""
                
                # Convert start_date and start_time to a datetime for the website event
                if event.all_day:
                    # For all-day events, use midnight as the time
                    date_str = event.start_date.strftime('%Y-%m-%d')
                    website_event.date = timezone.datetime.strptime(date_str, '%Y-%m-%d')
                else:
                    # For timed events, combine date and time
                    if event.start_time:
                        date_str = event.start_date.strftime('%Y-%m-%d')
                        time_str = event.start_time.strftime('%H:%M:%S')
                        datetime_str = f"{date_str} {time_str}"
                        website_event.date = timezone.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        # Fallback if no start_time is provided
                        date_str = event.start_date.strftime('%Y-%m-%d')
                        website_event.date = timezone.datetime.strptime(date_str, '%Y-%m-%d')
                
                # Set location
                website_event.location = event.location or "School Campus"
                
                # Copy attachment as image if available
                if event.attachment:
                    try:
                        # Always update the image when there's an attachment
                        website_event.image = event.attachment
                        self.stdout.write(f'Set image for website event from attachment: {event.attachment}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error copying attachment as image: {str(e)}'))
                
                # Set registration info if it's a virtual event
                if event.is_virtual:
                    website_event.registration_required = True
                    website_event.registration_link = event.virtual_link or ""
                
                # Save the website event
                website_event.save()
                synced_count += 1
                self.stdout.write(self.style.SUCCESS(f'Successfully synced event "{event.title}"'))
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'Error syncing event "{event.title}": {str(e)}'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'Event sync complete. Synced: {synced_count}, Errors: {error_count}'))
