from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appointments'
    verbose_name = 'Appointment Booking System'

    def ready(self):
        import appointments.signals

        # Start the scheduler only if not in migration mode
        from django.conf import settings
        import sys

        # Check if we're running migrations or other management commands
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv or 'collectstatic' in sys.argv:
            return

        # Don't start scheduler during Django startup - use management command instead
        # This prevents database queries during app initialization
        # To start scheduler, run: python manage.py start_appointment_scheduler
        pass
