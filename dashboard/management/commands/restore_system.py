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
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Skip confirmation prompts (for automated restore)',
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

            # Find the backup directory in temp - improved logic for various structures
            backup_dir = None

            # Check if temp_dir itself contains backup files
            if self.has_backup_files(temp_dir):
                backup_dir = temp_dir
            else:
                # Look for subdirectories that contain backup files
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isdir(item_path) and self.has_backup_files(item_path):
                        backup_dir = item_path
                        break

                # If still not found, use the first directory or temp_dir
                if not backup_dir:
                    backup_dirs = [d for d in os.listdir(temp_dir)
                                  if os.path.isdir(os.path.join(temp_dir, d))]
                    if backup_dirs:
                        backup_dir = os.path.join(temp_dir, backup_dirs[0])
                    else:
                        backup_dir = temp_dir

            self.stdout.write(f'Using backup directory: {os.path.basename(backup_dir)}')
            self.restore_from_directory(backup_dir, options)

    def has_backup_files(self, directory):
        """Check if directory contains backup files"""
        # Check for JSON files in root
        for file in os.listdir(directory):
            if file.endswith('.json'):
                return True

        # Check for database subdirectory with JSON files
        db_dir = os.path.join(directory, 'database')
        if os.path.exists(db_dir):
            for file in os.listdir(db_dir):
                if file.endswith('.json'):
                    return True

        return False

    def restore_from_directory(self, backup_dir, options):
        """Restore from backup directory"""
        try:
            # Verify backup integrity
            self.verify_backup(backup_dir)
            
            # Show backup information
            self.show_backup_info(backup_dir)
            
            # Confirm restore (skip if no-input)
            if not options.get('no_input', False) and not self.confirm_restore():
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

        # Check for database backup files (more flexible)
        db_backup_found = False
        possible_db_files = [
            'full_database.json',
            'database.json',
            'backup.json',
            'data.json'
        ]

        # Check in root directory first
        for db_file in possible_db_files:
            if os.path.exists(os.path.join(backup_dir, db_file)):
                db_backup_found = True
                self.stdout.write(f'Found database backup: {db_file}')
                break

        # Check in database subdirectory
        if not db_backup_found:
            db_dir = os.path.join(backup_dir, 'database')
            if os.path.exists(db_dir):
                for db_file in possible_db_files:
                    if os.path.exists(os.path.join(db_dir, db_file)):
                        db_backup_found = True
                        self.stdout.write(f'Found database backup: database/{db_file}')
                        break

        # Check for any JSON files that might be database backups
        if not db_backup_found:
            json_files = []
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        # Only consider files larger than 10 bytes (not empty)
                        if os.path.getsize(file_path) > 10:
                            json_files.append(file_path)

            if json_files:
                # Use the largest JSON file as it's likely the database backup
                largest_json = max(json_files, key=os.path.getsize)
                db_backup_found = True
                self.stdout.write(f'Using largest JSON file as database backup: {os.path.relpath(largest_json, backup_dir)}')

                # Validate the JSON file
                try:
                    with open(largest_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        self.stdout.write(f'Validated JSON file with {len(data)} records')
                    else:
                        self.stdout.write('Warning: JSON file is not a list format')
                except Exception as e:
                    self.stdout.write(f'Warning: Could not validate JSON file: {e}')

        if not db_backup_found:
            # List all files for debugging
            self.stdout.write('Available files in backup:')
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, backup_dir)
                    file_size = os.path.getsize(file_path)
                    self.stdout.write(f'  - {rel_path} ({file_size} bytes)')

            raise Exception('No database backup file found. Expected JSON file with database data.')

        self.stdout.write(self.style.SUCCESS('Backup verification passed'))

    def show_backup_info(self, backup_dir):
        """Show backup information"""
        info_path = os.path.join(backup_dir, 'system_info.json')

        self.stdout.write('\n' + '='*50)
        self.stdout.write('BACKUP INFORMATION')
        self.stdout.write('='*50)

        if os.path.exists(info_path):
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    system_info = json.load(f)

                self.stdout.write(f"Backup Date: {system_info.get('backup_date', 'Unknown')}")
                self.stdout.write(f"Django Version: {system_info.get('django_version', 'Unknown')}")
                self.stdout.write(f"Database Engine: {system_info.get('database_engine', 'Unknown')}")

                installed_apps = system_info.get('installed_apps', [])
                if installed_apps:
                    self.stdout.write(f"Number of Apps: {len(installed_apps)}")
                else:
                    self.stdout.write("Number of Apps: Unknown")
            except Exception as e:
                self.stdout.write(f"Could not read system info: {e}")
                self.stdout.write("Backup Type: Legacy or External Backup")
        else:
            self.stdout.write("Backup Type: Legacy or External Backup")
            self.stdout.write("System Info: Not available")

        # Check for database files
        db_files = []
        for root, dirs, files in os.walk(backup_dir):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    db_files.append(f"{os.path.relpath(file_path, backup_dir)} ({file_size:.2f} MB)")

        if db_files:
            self.stdout.write("Database Files:")
            for db_file in db_files[:5]:  # Show first 5 files
                self.stdout.write(f"  - {db_file}")
            if len(db_files) > 5:
                self.stdout.write(f"  ... and {len(db_files) - 5} more files")

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

        # Find database backup file(s)
        db_files_to_try = []

        # Check for common database backup file names
        possible_db_files = [
            'full_database.json',
            'database.json',
            'backup.json',
            'data.json'
        ]

        # Check in root directory
        for db_file in possible_db_files:
            file_path = os.path.join(backup_dir, db_file)
            if os.path.exists(file_path):
                db_files_to_try.append(file_path)

        # Check in database subdirectory
        db_dir = os.path.join(backup_dir, 'database')
        if os.path.exists(db_dir):
            for db_file in possible_db_files:
                file_path = os.path.join(db_dir, db_file)
                if os.path.exists(file_path):
                    db_files_to_try.append(file_path)

        # If no standard files found, find all JSON files and try the largest one
        if not db_files_to_try:
            json_files = []
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    if file.endswith('.json'):
                        json_files.append(os.path.join(root, file))

            if json_files:
                # Sort by size (largest first) as main database backup is usually largest
                json_files.sort(key=os.path.getsize, reverse=True)
                db_files_to_try = json_files

        if not db_files_to_try:
            raise Exception('No database backup files found')

        # Try to restore database files
        restored = False
        for db_file in db_files_to_try:
            try:
                self.stdout.write(f'Trying to restore from: {os.path.relpath(db_file, backup_dir)}')

                # Check file content first
                file_size = os.path.getsize(db_file) / (1024 * 1024)  # MB
                self.stdout.write(f'File size: {file_size:.2f} MB')

                # Try to read and validate JSON
                try:
                    with open(db_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    if isinstance(data, list) and len(data) > 0:
                        self.stdout.write(f'Found {len(data)} records in JSON file')

                        # Check if it looks like Django fixture format
                        first_record = data[0]
                        if isinstance(first_record, dict) and 'model' in first_record:
                            self.stdout.write('File appears to be in Django fixture format')
                        else:
                            self.stdout.write('File does not appear to be in Django fixture format')
                            continue
                    else:
                        self.stdout.write('File is empty or not a list')
                        continue

                except json.JSONDecodeError as je:
                    self.stdout.write(f'Invalid JSON format: {je}')
                    continue
                except UnicodeDecodeError as ue:
                    self.stdout.write(f'Encoding error: {ue}')
                    continue

                # Try to load the data
                call_command('loaddata', db_file, verbosity=2)
                self.stdout.write(self.style.SUCCESS(f'Database restored successfully from {os.path.basename(db_file)}'))
                restored = True
                break

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Failed to restore from {os.path.basename(db_file)}: {str(e)}')
                )
                # Print more detailed error info
                import traceback
                self.stdout.write(f'Detailed error: {traceback.format_exc()}')
                continue

        if not restored:
            # Try restoring individual app files if they exist
            self.stdout.write('Attempting to restore individual app files...')
            db_dir = os.path.join(backup_dir, 'database')

            if os.path.exists(db_dir):
                app_files = [f for f in os.listdir(db_dir) if f.endswith('.json')]
                for file in app_files:
                    try:
                        app_file = os.path.join(db_dir, file)
                        self.stdout.write(f'Trying individual file: {file}')
                        call_command('loaddata', app_file, verbosity=2)
                        self.stdout.write(f'Restored {file}')
                        restored = True
                    except Exception as app_error:
                        self.stdout.write(
                            self.style.WARNING(f'Failed to restore {file}: {app_error}')
                        )

            # Try alternative restore methods
            if not restored:
                self.stdout.write('Trying alternative restore methods...')
                restored = self.try_alternative_restore(backup_dir, db_files_to_try)

            if not restored:
                raise Exception('Could not restore any database files. Please check the backup format and try manual restoration.')

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

    def try_alternative_restore(self, backup_dir, db_files):
        """Try alternative restore methods for problematic backups"""
        self.stdout.write('Attempting alternative restore approaches...')

        for db_file in db_files:
            try:
                # Method 1: Try with natural foreign keys
                self.stdout.write(f'Trying natural foreign keys for: {os.path.basename(db_file)}')
                call_command('loaddata', db_file, use_natural_foreign_keys=True, verbosity=2)
                self.stdout.write(self.style.SUCCESS('Restored using natural foreign keys'))
                return True
            except Exception as e:
                self.stdout.write(f'Natural foreign keys failed: {e}')

            try:
                # Method 2: Try ignoring conflicts
                self.stdout.write(f'Trying to ignore conflicts for: {os.path.basename(db_file)}')
                call_command('loaddata', db_file, ignore_conflicts=True, verbosity=2)
                self.stdout.write(self.style.SUCCESS('Restored ignoring conflicts'))
                return True
            except Exception as e:
                self.stdout.write(f'Ignore conflicts failed: {e}')

            try:
                # Method 3: Try loading specific models
                self.stdout.write(f'Analyzing file structure: {os.path.basename(db_file)}')
                with open(db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list) and len(data) > 0:
                    # Try loading just a few records first
                    sample_data = data[:10]  # First 10 records
                    temp_file = os.path.join(backup_dir, 'temp_sample.json')

                    with open(temp_file, 'w', encoding='utf-8') as tf:
                        json.dump(sample_data, tf, indent=2)

                    call_command('loaddata', temp_file, verbosity=1)
                    self.stdout.write('Sample data loaded successfully')
                    os.remove(temp_file)

                    # If sample works, try the full file
                    call_command('loaddata', db_file, ignore_conflicts=True, verbosity=1)
                    self.stdout.write(self.style.SUCCESS('Full data loaded successfully'))
                    return True

            except Exception as e:
                self.stdout.write(f'Sample loading failed: {e}')
                # Clean up temp file if it exists
                temp_file = os.path.join(backup_dir, 'temp_sample.json')
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        return False
