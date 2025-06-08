"""
Management command to set up production environment.
This command handles all the necessary setup tasks for production deployment.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connection
import os


class Command(BaseCommand):
    help = 'Set up production environment with all necessary configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-cache',
            action='store_true',
            help='Skip cache table creation'
        )
        parser.add_argument(
            '--skip-static',
            action='store_true',
            help='Skip static files collection'
        )
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Skip database migrations'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Setting up production environment...')
        )

        success_count = 0
        total_steps = 6

        # 1. Run migrations
        if not options['skip_migrations']:
            self.stdout.write('1/6 Running database migrations...')
            try:
                call_command('migrate', verbosity=1)
                self.stdout.write(
                    self.style.SUCCESS('✓ Database migrations completed')
                )
                success_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Migration failed: {e}')
                )
        else:
            self.stdout.write('1/6 Skipping database migrations...')
            success_count += 1

        # 2. Create cache table
        if not options['skip_cache']:
            self.stdout.write('2/6 Creating cache table...')
            try:
                call_command('createcachetable', verbosity=0)
                self.stdout.write(
                    self.style.SUCCESS('✓ Cache table created/verified')
                )
                success_count += 1
            except Exception as e:
                # Cache table might already exist, which is fine
                if 'already exists' in str(e).lower() or 'relation' in str(e).lower():
                    self.stdout.write(
                        self.style.SUCCESS('✓ Cache table already exists')
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Cache table creation: {e}')
                    )
        else:
            self.stdout.write('2/6 Skipping cache table creation...')
            success_count += 1

        # 3. Collect static files
        if not options['skip_static']:
            self.stdout.write('3/6 Collecting static files...')
            try:
                call_command('collectstatic', '--noinput', verbosity=1)
                self.stdout.write(
                    self.style.SUCCESS('✓ Static files collected')
                )
                success_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Static files collection failed: {e}')
                )
        else:
            self.stdout.write('3/6 Skipping static files collection...')
            success_count += 1

        # 4. Create logs directory
        self.stdout.write('4/6 Setting up logging directory...')
        logs_dir = settings.BASE_DIR / 'logs'
        try:
            os.makedirs(logs_dir, exist_ok=True)
            self.stdout.write(
                self.style.SUCCESS('✓ Logs directory created')
            )
            success_count += 1
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Logs directory creation failed: {e}')
            )

        # 5. Verify database connection
        self.stdout.write('5/6 Verifying database connection...')
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result:
                    self.stdout.write(
                        self.style.SUCCESS('✓ Database connection verified')
                    )
                    success_count += 1
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Database connection failed: {e}')
            )

        # 6. Check critical settings
        self.stdout.write('6/6 Checking production settings...')
        settings_ok = self.check_production_settings()
        if settings_ok:
            success_count += 1

        # Summary
        self.stdout.write(f'\n📊 Setup Summary: {success_count}/{total_steps} steps completed')

        if success_count == total_steps:
            self.stdout.write(
                self.style.SUCCESS('🎉 Production setup completed successfully!')
            )
        elif success_count >= total_steps - 1:
            self.stdout.write(
                self.style.WARNING('⚠️  Production setup mostly completed with minor issues')
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ Production setup completed with errors - please review')
            )

        self.stdout.write('\n📋 Next steps:')
        self.stdout.write('1. Create a superuser: python manage.py createsuperuser')
        self.stdout.write('2. Verify all environment variables are set correctly')
        self.stdout.write('3. Test the application thoroughly')
        self.stdout.write('4. Check application health: curl https://your-app.fly.dev/health/')

    def check_production_settings(self):
        """Check critical production settings"""
        issues = []
        warnings = []

        # Check DEBUG setting
        if settings.DEBUG:
            issues.append('DEBUG is True - should be False in production')

        # Check SECRET_KEY
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 50:
            issues.append('SECRET_KEY is too short or missing')
        elif settings.SECRET_KEY == 'django-insecure-integration-key-replace-in-production':
            issues.append('SECRET_KEY is using default value - change it!')

        # Check ALLOWED_HOSTS
        if '*' in settings.ALLOWED_HOSTS:
            warnings.append('ALLOWED_HOSTS contains wildcard (*) - consider restricting for security')

        # Check database configuration
        if 'sqlite' in settings.DATABASES['default']['ENGINE']:
            warnings.append('Using SQLite in production - consider PostgreSQL for better performance')

        # Check if cache table exists (only if using database cache)
        if hasattr(settings, 'CACHES') and settings.CACHES.get('default', {}).get('BACKEND') == 'django.core.cache.backends.db.DatabaseCache':
            try:
                from django.core.cache import cache
                cache.get('test_key')  # This will fail if cache table doesn't exist
            except Exception:
                warnings.append('Database cache configured but cache table may not exist')

        # Display results
        if issues:
            self.stdout.write(
                self.style.ERROR('❌ Critical Production Issues:')
            )
            for issue in issues:
                self.stdout.write(f'  • {issue}')

        if warnings:
            self.stdout.write(
                self.style.WARNING('⚠️  Production Warnings:')
            )
            for warning in warnings:
                self.stdout.write(f'  • {warning}')

        if not issues and not warnings:
            self.stdout.write(
                self.style.SUCCESS('✓ Production settings look good')
            )

        return len(issues) == 0  # Return True if no critical issues
