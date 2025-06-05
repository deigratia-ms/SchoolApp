import os
import json
import shutil
import zipfile
import tempfile
import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Restore system from backup including database and media files'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_path',
            type=str,
            help='Path to backup file (.zip) or backup directory'
        )
        parser.add_argument(
            '--restore-media',
            action='store_true',
            default=True,
            help='Restore media files (default: True)'
        )
        parser.add_argument(
            '--flush-database',
            action='store_true',
            default=False,
            help='Flush existing database before restore (WARNING: This will delete all data)'
        )
        parser.add_argument(
            '--migrate-first',
            action='store_true',
            default=True,
            help='Run migrations before restoring data (default: True)'
        )

    def handle(self, *args, **options):
        backup_path = options['backup_path']
        
        if not os.path.exists(backup_path):
            self.stdout.write(
                self.style.ERROR(f'Backup path does not exist: {backup_path}')
            )
            return

        self.stdout.write(self.style.SUCCESS('Starting system restore...'))
        
        # Determine if backup is compressed or directory
        if backup_path.endswith('.zip'):
            self.restore_from_zip(backup_path, options)
        elif os.path.isdir(backup_path):
            self.restore_from_directory(backup_path, options)
        else:
            self.stdout.write(
                self.style.ERROR('Backup path must be a .zip file or directory')
            )

    def restore_from_zip(self, zip_path, options):
        """Restore from compressed backup"""
        self.stdout.write('Extracting backup archive...')
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Find the backup directory in temp
            backup_dirs = [d for d in os.listdir(temp_dir) 
                          if os.path.isdir(os.path.join(temp_dir, d))]
            
            if not backup_dirs:
                backup_dir = temp_dir
            else:
                backup_dir = os.path.join(temp_dir, backup_dirs[0])
            
            self.restore_from_directory(backup_dir, options)

    def restore_from_directory(self, backup_dir, options):
        """Restore from backup directory"""
        try:
            # Verify backup integrity
            self.verify_backup(backup_dir)
            
            # Show backup information
            self.show_backup_info(backup_dir)
            
            # Confirm restore
            if not self.confirm_restore():
                self.stdout.write(self.style.WARNING('Restore cancelled by user'))
                return
            
            # Flush database if requested
            if options['flush_database']:
                self.flush_database()
            
            # Run migrations if requested
            if options['migrate_first']:
                self.run_migrations()
            
            # Restore database
            self.restore_database(backup_dir)
            
            # Restore media files
            if options['restore_media']:
                self.restore_media_files(backup_dir)
            
            self.stdout.write(
                self.style.SUCCESS('System restore completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Restore failed: {str(e)}')
            )
            raise

    def verify_backup(self, backup_dir):
        """Verify backup integrity"""
        self.stdout.write('Verifying backup integrity...')
        
        required_files = ['system_info.json']
        required_dirs = ['database']
        
        for file in required_files:
            if not os.path.exists(os.path.join(backup_dir, file)):
                raise Exception(f'Required backup file missing: {file}')
        
        for dir in required_dirs:
            if not os.path.exists(os.path.join(backup_dir, dir)):
                raise Exception(f'Required backup directory missing: {dir}')
        
        # Check if database backup exists
        db_dir = os.path.join(backup_dir, 'database')
        if not os.path.exists(os.path.join(db_dir, 'full_database.json')):
            raise Exception('Database backup file missing: full_database.json')
        
        self.stdout.write(self.style.SUCCESS('Backup verification passed'))

    def show_backup_info(self, backup_dir):
        """Show backup information"""
        info_path = os.path.join(backup_dir, 'system_info.json')

        with open(info_path, 'r', encoding='utf-8') as f:
            system_info = json.load(f)
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('BACKUP INFORMATION')
        self.stdout.write('='*50)
        self.stdout.write(f"Backup Date: {system_info['backup_date']}")
        self.stdout.write(f"Django Version: {system_info['django_version']}")
        self.stdout.write(f"Database Engine: {system_info['database_engine']}")
        self.stdout.write(f"Number of Apps: {len(system_info['installed_apps'])}")
        
        # Check for media files
        media_dir = os.path.join(backup_dir, 'media')
        if os.path.exists(media_dir):
            media_size = self.get_directory_size(media_dir)
            self.stdout.write(f"Media Files: {media_size:.2f} MB")
        else:
            self.stdout.write("Media Files: None")
        
        self.stdout.write('='*50 + '\n')

    def confirm_restore(self):
        """Ask user to confirm restore operation"""
        self.stdout.write(
            self.style.WARNING(
                '\nWARNING: This will restore the backup and may overwrite existing data!'
            )
        )
        
        response = input('Do you want to continue? (yes/no): ').lower().strip()
        return response in ['yes', 'y']

    def flush_database(self):
        """Flush existing database"""
        self.stdout.write(
            self.style.WARNING('Flushing existing database...')
        )
        
        call_command('flush', '--noinput')
        self.stdout.write(self.style.SUCCESS('Database flushed'))

    def run_migrations(self):
        """Run database migrations"""
        self.stdout.write('Running database migrations...')
        
        call_command('migrate', '--noinput')
        self.stdout.write(self.style.SUCCESS('Migrations completed'))

    def restore_database(self, backup_dir):
        """Restore database from backup"""
        self.stdout.write('Restoring database...')
        
        db_file = os.path.join(backup_dir, 'database', 'full_database.json')
        
        try:
            call_command('loaddata', db_file)
            self.stdout.write(self.style.SUCCESS('Database restored successfully'))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Database restore failed: {str(e)}')
            )
            
            # Try restoring individual apps
            self.stdout.write('Attempting to restore individual apps...')
            db_dir = os.path.join(backup_dir, 'database')
            
            for file in os.listdir(db_dir):
                if file.endswith('.json') and file != 'full_database.json':
                    try:
                        app_file = os.path.join(db_dir, file)
                        call_command('loaddata', app_file)
                        self.stdout.write(f'Restored {file}')
                    except Exception as app_error:
                        self.stdout.write(
                            self.style.WARNING(f'Failed to restore {file}: {app_error}')
                        )

    def restore_media_files(self, backup_dir):
        """Restore media files"""
        self.stdout.write('Restoring media files...')
        
        media_backup = os.path.join(backup_dir, 'media')
        
        if not os.path.exists(media_backup):
            self.stdout.write(self.style.WARNING('No media files to restore'))
            return
        
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            self.stdout.write(
                self.style.WARNING('MEDIA_ROOT not configured, skipping media restore')
            )
            return
        
        # Backup existing media if it exists
        if os.path.exists(media_root):
            backup_existing = f"{media_root}_backup_{int(time.time())}"
            shutil.move(media_root, backup_existing)
            self.stdout.write(f'Existing media backed up to: {backup_existing}')
        
        # Copy media files
        shutil.copytree(media_backup, media_root)
        self.stdout.write(self.style.SUCCESS('Media files restored successfully'))

    def get_directory_size(self, directory):
        """Get directory size in MB"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # Convert to MB
