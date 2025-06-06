import os
import json
import shutil
import zipfile
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.apps import apps
from django.db import connection
import tempfile


class Command(BaseCommand):
    help = 'Create a comprehensive backup of the entire system including database and media files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory to save backup files (default: backups)'
        )
        parser.add_argument(
            '--include-media',
            action='store_true',
            default=True,
            help='Include media files in backup (default: True)'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            default=True,
            help='Compress backup into zip file (default: True)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting comprehensive system backup...'))
        
        # Create backup directory
        backup_dir = options['output_dir']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'school_backup_{timestamp}'
        backup_path = os.path.join(backup_dir, backup_name)
        
        os.makedirs(backup_path, exist_ok=True)
        
        try:
            # 1. Backup database
            self.backup_database(backup_path)
            
            # 2. Backup media files
            if options['include_media']:
                self.backup_media_files(backup_path)
            
            # 3. Backup static files (if collected)
            self.backup_static_files(backup_path)
            
            # 4. Create system info file
            self.create_system_info(backup_path)
            
            # 5. Create restore script
            self.create_restore_script(backup_path)
            
            # 6. Compress if requested
            if options['compress']:
                zip_path = self.compress_backup(backup_dir, backup_name, backup_path)
                self.stdout.write(
                    self.style.SUCCESS(f'Backup completed successfully: {zip_path}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Backup completed successfully: {backup_path}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Backup failed: {str(e)}')
            )
            # Clean up partial backup
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            raise

    def backup_database(self, backup_path):
        """Backup database using Django's dumpdata command"""
        self.stdout.write('Backing up database...')

        db_backup_path = os.path.join(backup_path, 'database')
        os.makedirs(db_backup_path, exist_ok=True)

        # Full database dump with UTF-8 encoding
        full_dump_path = os.path.join(db_backup_path, 'full_database.json')
        try:
            with open(full_dump_path, 'w', encoding='utf-8') as f:
                call_command('dumpdata',
                            '--natural-foreign',
                            '--natural-primary',
                            '--indent', '2',
                            stdout=f)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Full database dump failed: {e}')
            )

        # Individual app dumps for easier restoration
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith('django.'):
                app_dump_path = os.path.join(db_backup_path, f'{app_config.name}.json')
                try:
                    with open(app_dump_path, 'w', encoding='utf-8') as f:
                        call_command('dumpdata',
                                    app_config.name,
                                    '--natural-foreign',
                                    '--natural-primary',
                                    '--indent', '2',
                                    stdout=f)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Could not backup app {app_config.name}: {e}')
                    )

        self.stdout.write(self.style.SUCCESS('Database backup completed'))

    def backup_media_files(self, backup_path):
        """Backup media files"""
        self.stdout.write('Backing up media files...')
        
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root and os.path.exists(media_root):
            media_backup_path = os.path.join(backup_path, 'media')
            shutil.copytree(media_root, media_backup_path)
            self.stdout.write(self.style.SUCCESS('Media files backup completed'))
        else:
            self.stdout.write(self.style.WARNING('No media files found to backup'))

    def backup_static_files(self, backup_path):
        """Backup collected static files if they exist"""
        self.stdout.write('Backing up static files...')
        
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if static_root and os.path.exists(static_root):
            static_backup_path = os.path.join(backup_path, 'static')
            shutil.copytree(static_root, static_backup_path)
            self.stdout.write(self.style.SUCCESS('Static files backup completed'))
        else:
            self.stdout.write(self.style.WARNING('No collected static files found to backup'))

    def create_system_info(self, backup_path):
        """Create system information file"""
        self.stdout.write('Creating system information file...')
        
        # Get database info
        db_config = settings.DATABASES['default']
        db_engine = db_config['ENGINE']
        
        # Get installed apps
        installed_apps = list(settings.INSTALLED_APPS)
        
        # Get Django version
        import django
        django_version = django.get_version()
        
        # Get Python version
        import sys
        python_version = sys.version
        
        system_info = {
            'backup_date': datetime.now().isoformat(),
            'django_version': django_version,
            'python_version': python_version,
            'database_engine': db_engine,
            'database_config': {
                'ENGINE': db_config['ENGINE'],
                'NAME': db_config.get('NAME', ''),
                'HOST': db_config.get('HOST', ''),
                'PORT': db_config.get('PORT', ''),
            },
            'installed_apps': installed_apps,
            'settings': {
                'DEBUG': getattr(settings, 'DEBUG', False),
                'TIME_ZONE': getattr(settings, 'TIME_ZONE', 'UTC'),
                'LANGUAGE_CODE': getattr(settings, 'LANGUAGE_CODE', 'en-us'),
                'USE_TZ': getattr(settings, 'USE_TZ', True),
            }
        }
        
        info_path = os.path.join(backup_path, 'system_info.json')
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(system_info, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(self.style.SUCCESS('System information file created'))

    def create_restore_script(self, backup_path):
        """Create restore script"""
        self.stdout.write('Creating restore script...')
        
        restore_script = '''#!/usr/bin/env python
"""
School Management System Backup Restore Script
Usage: python restore_backup.py [options]
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, 
                              capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr}")
        return None

def restore_database(backup_dir, django_project_dir):
    """Restore database from backup"""
    print("Restoring database...")
    
    # Load full database dump
    db_file = os.path.join(backup_dir, 'database', 'full_database.json')
    if os.path.exists(db_file):
        # First, migrate to create tables
        run_command('python manage.py migrate', cwd=django_project_dir)
        
        # Then load data
        run_command(f'python manage.py loaddata "{db_file}"', cwd=django_project_dir)
        print("Database restored successfully")
    else:
        print("Database backup file not found")

def restore_media_files(backup_dir, django_project_dir):
    """Restore media files"""
    print("Restoring media files...")
    
    media_backup = os.path.join(backup_dir, 'media')
    if os.path.exists(media_backup):
        # Read system info to get media root
        with open(os.path.join(backup_dir, 'system_info.json'), 'r') as f:
            system_info = json.load(f)
        
        # Default media directory
        media_dir = os.path.join(django_project_dir, 'media')
        
        # Remove existing media directory if it exists
        if os.path.exists(media_dir):
            shutil.rmtree(media_dir)
        
        # Copy media files
        shutil.copytree(media_backup, media_dir)
        print("Media files restored successfully")
    else:
        print("No media files to restore")

def main():
    print("School Management System Backup Restore")
    print("=" * 50)
    
    # Get current directory (should be backup directory)
    backup_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ask for Django project directory
    django_project_dir = input("Enter path to Django project directory: ").strip()
    if not django_project_dir:
        django_project_dir = input("Please enter a valid path: ").strip()
    
    if not os.path.exists(django_project_dir):
        print(f"Directory {django_project_dir} does not exist")
        return
    
    # Check if it's a Django project
    manage_py = os.path.join(django_project_dir, 'manage.py')
    if not os.path.exists(manage_py):
        print(f"manage.py not found in {django_project_dir}")
        return
    
    print(f"Restoring backup to: {django_project_dir}")
    
    # Restore database
    restore_database(backup_dir, django_project_dir)
    
    # Restore media files
    restore_media_files(backup_dir, django_project_dir)
    
    print("\\nRestore completed successfully!")
    print("Don't forget to:")
    print("1. Update your .env file with correct database settings")
    print("2. Run 'python manage.py collectstatic' if needed")
    print("3. Create a superuser if needed: 'python manage.py createsuperuser'")

if __name__ == '__main__':
    main()
'''
        
        script_path = os.path.join(backup_path, 'restore_backup.py')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(restore_script)
        
        # Make script executable on Unix systems
        try:
            os.chmod(script_path, 0o755)
        except:
            pass  # Windows doesn't support chmod
        
        self.stdout.write(self.style.SUCCESS('Restore script created'))

    def compress_backup(self, backup_dir, backup_name, backup_path):
        """Compress backup into zip file"""
        self.stdout.write('Compressing backup...')
        
        zip_path = os.path.join(backup_dir, f'{backup_name}.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_path)
                    zipf.write(file_path, arcname)
        
        # Remove uncompressed backup directory
        shutil.rmtree(backup_path)
        
        self.stdout.write(self.style.SUCCESS('Backup compressed successfully'))
        return zip_path
