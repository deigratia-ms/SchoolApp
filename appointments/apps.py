from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appointments'
    verbose_name = 'Appointment Booking System'

    def ready(self):
        import appointments.signals

        # Start the scheduler only if not in migration mode
        from django.conf import settings
        from django.core.management import get_commands
        import sys

        # Check if we're running migrations or other management commands
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return

        run_scheduler = getattr(settings, 'RUN_SCHEDULER_IN_DEBUG', False)
        if not settings.DEBUG or run_scheduler:
            try:
                # Check if tables exist before starting scheduler
                from django.db import connection
                from django.db.utils import ProgrammingError

                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM django_apscheduler_djangojob LIMIT 1")
                    # If we get here, tables exist, so start scheduler
                    from appointments.scheduler import start
                    start()
                except ProgrammingError:
                    # Tables don't exist yet, skip scheduler startup
                    print("Skipping scheduler startup - database tables not ready")
            except Exception as e:
                print(f"Error starting appointment scheduler: {e}")
