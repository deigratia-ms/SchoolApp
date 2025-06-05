from django.core.management.base import BaseCommand
from appointments.models import AppointmentSettings
from django.conf import settings

class Command(BaseCommand):
    help = 'Create default appointment settings if none exist'

    def handle(self, *args, **options):
        if not AppointmentSettings.objects.exists():
            self.stdout.write('Creating default appointment settings...')
            
            # Get school name from settings if available
            school_name = getattr(settings, 'DEFAULT_SCHOOL_NAME', 'School Appointment System')
            
            # Create default settings
            AppointmentSettings.objects.create(
                school_name=school_name,
                appointment_duration=30,
                day_start_time='09:00',
                day_end_time='15:00',
                excluded_hours=[],
                days_to_generate=14,
                excluded_days=[5, 6],  # Saturday and Sunday
                auto_confirm_appointments=False,
                default_appointment_purpose="Termly One-on-One Appointment",
                reminder_days=1,
                system_active=True
            )
            
            self.stdout.write(self.style.SUCCESS('Default appointment settings created successfully!'))
        else:
            self.stdout.write('Appointment settings already exist. No action taken.')
