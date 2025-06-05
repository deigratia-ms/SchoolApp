from django.core.management.base import BaseCommand
from django.utils import timezone
from appointments.models import TimeSlot
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up past time slots'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Get all past time slots
        past_slots = TimeSlot.objects.filter(date__lt=today)
        count = past_slots.count()
        
        if count > 0:
            # Mark all past slots as unavailable
            past_slots.update(is_available=False)
            self.stdout.write(self.style.SUCCESS(f'Marked {count} past time slots as unavailable'))
        else:
            self.stdout.write('No past time slots to clean up')
        
        # Auto-complete appointments for past slots
        from appointments.models import Appointment
        past_appointments = Appointment.objects.filter(
            time_slot__date__lt=today,
            status='confirmed'
        )
        
        if past_appointments.count() > 0:
            for appointment in past_appointments:
                appointment.status = 'completed'
                appointment.completed_at = timezone.now()
                appointment.save()
            
            self.stdout.write(self.style.SUCCESS(f'Auto-completed {past_appointments.count()} past appointments'))
        else:
            self.stdout.write('No past appointments to auto-complete')
