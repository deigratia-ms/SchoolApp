from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.db.utils import ProgrammingError


class Command(BaseCommand):
    help = 'Start the appointment scheduler'

    def handle(self, *args, **options):
        """
        Start the appointment scheduler.
        This command should be run after Django is fully initialized.
        """
        try:
            # Check if tables exist before starting scheduler
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM django_apscheduler_djangojob LIMIT 1")
                # If we get here, tables exist, so start scheduler
                from appointments.scheduler import start
                start()
                self.stdout.write(
                    self.style.SUCCESS('Successfully started appointment scheduler')
                )
            except ProgrammingError:
                # Tables don't exist yet, skip scheduler startup
                self.stdout.write(
                    self.style.WARNING('Skipping scheduler startup - database tables not ready')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error starting appointment scheduler: {e}')
            )
