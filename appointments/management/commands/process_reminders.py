from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment, AppointmentSettings
from appointments.notifications import send_appointment_reminder
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process appointment reminders'

    def handle(self, *args, **options):
        settings = AppointmentSettings.objects.first()
        if not settings:
            self.stdout.write(self.style.WARNING('No appointment settings found'))
            return
        
        if not settings.system_active:
            self.stdout.write(self.style.WARNING('Appointment system is not active'))
            return
        
        today = timezone.now().date()
        
        # Process 1-day reminders
        one_day_reminder_date = today + timedelta(days=1)
        one_day_appointments = Appointment.objects.filter(
            time_slot__date=one_day_reminder_date,
            status='confirmed',
            reminder_1day_sent=False
        )
        
        self.stdout.write(f'Processing {one_day_appointments.count()} 1-day reminders')
        
        for appointment in one_day_appointments:
            try:
                send_appointment_reminder(appointment)
                appointment.reminder_1day_sent = True
                appointment.save(update_fields=['reminder_1day_sent'])
                self.stdout.write(self.style.SUCCESS(f'Sent 1-day reminder for appointment {appointment.id}'))
            except Exception as e:
                logger.error(f'Failed to send 1-day reminder for appointment {appointment.id}: {e}')
        
        # Process 3-day reminders
        three_day_reminder_date = today + timedelta(days=3)
        three_day_appointments = Appointment.objects.filter(
            time_slot__date=three_day_reminder_date,
            status='confirmed',
            reminder_3days_sent=False
        )
        
        self.stdout.write(f'Processing {three_day_appointments.count()} 3-day reminders')
        
        for appointment in three_day_appointments:
            try:
                send_appointment_reminder(appointment)
                appointment.reminder_3days_sent = True
                appointment.save(update_fields=['reminder_3days_sent'])
                self.stdout.write(self.style.SUCCESS(f'Sent 3-day reminder for appointment {appointment.id}'))
            except Exception as e:
                logger.error(f'Failed to send 3-day reminder for appointment {appointment.id}: {e}')
        
        # Process custom day reminders based on settings
        if settings.reminder_days > 0 and settings.reminder_days not in [1, 3]:
            custom_reminder_date = today + timedelta(days=settings.reminder_days)
            custom_appointments = Appointment.objects.filter(
                time_slot__date=custom_reminder_date,
                status='confirmed',
                reminder_sent=False
            )
            
            self.stdout.write(f'Processing {custom_appointments.count()} {settings.reminder_days}-day reminders')
            
            for appointment in custom_appointments:
                try:
                    send_appointment_reminder(appointment)
                    appointment.reminder_sent = True
                    appointment.save(update_fields=['reminder_sent'])
                    self.stdout.write(self.style.SUCCESS(f'Sent {settings.reminder_days}-day reminder for appointment {appointment.id}'))
                except Exception as e:
                    logger.error(f'Failed to send {settings.reminder_days}-day reminder for appointment {appointment.id}: {e}')
        
        self.stdout.write(self.style.SUCCESS('Finished processing appointment reminders'))
