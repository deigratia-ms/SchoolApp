import os
import json
import zipfile
import tempfile
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Diagnose backup file structure and content'

    def add_arguments(self, parser):
        parser.add_argument('backup_path', type=str, help='Path to backup file or directory')

    def handle(self, *args, **options):
        backup_path = options['backup_path']
        
        if not os.path.exists(backup_path):
            self.stdout.write(self.style.ERROR(f'Backup path does not exist: {backup_path}'))
            return

        self.stdout.write(self.style.SUCCESS('🔍 BACKUP DIAGNOSTIC REPORT'))
        self.stdout.write('=' * 60)
        
        if backup_path.endswith('.zip'):
            self.diagnose_zip_backup(backup_path)
        elif os.path.isdir(backup_path):
            self.diagnose_directory_backup(backup_path)
        else:
            self.stdout.write(self.style.ERROR('Backup must be a .zip file or directory'))

    def diagnose_zip_backup(self, zip_path):
        """Diagnose ZIP backup file"""
        self.stdout.write(f'📁 ZIP File: {os.path.basename(zip_path)}')
        file_size = os.path.getsize(zip_path) / (1024 * 1024)
        self.stdout.write(f'📏 Size: {file_size:.2f} MB')
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                file_list = zipf.namelist()
                self.stdout.write(f'📄 Files in ZIP: {len(file_list)}')
                
                # Show structure
                self.stdout.write('\n📂 ZIP Structure:')
                for file in sorted(file_list)[:20]:  # Show first 20 files
                    size = zipf.getinfo(file).file_size
                    self.stdout.write(f'  {file} ({size} bytes)')
                
                if len(file_list) > 20:
                    self.stdout.write(f'  ... and {len(file_list) - 20} more files')
                
                # Extract and analyze
                with tempfile.TemporaryDirectory() as temp_dir:
                    zipf.extractall(temp_dir)
                    
                    # Find backup directory
                    backup_dirs = [d for d in os.listdir(temp_dir) 
                                  if os.path.isdir(os.path.join(temp_dir, d))]
                    
                    if backup_dirs:
                        backup_dir = os.path.join(temp_dir, backup_dirs[0])
                    else:
                        backup_dir = temp_dir
                    
                    self.diagnose_directory_backup(backup_dir)
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to read ZIP file: {e}'))

    def diagnose_directory_backup(self, backup_dir):
        """Diagnose directory backup"""
        self.stdout.write(f'\n📁 Backup Directory: {backup_dir}')
        
        # List all files
        all_files = []
        for root, dirs, files in os.walk(backup_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, backup_dir)
                file_size = os.path.getsize(file_path)
                all_files.append((rel_path, file_size))
        
        self.stdout.write(f'📄 Total Files: {len(all_files)}')
        
        # Categorize files
        json_files = [f for f in all_files if f[0].endswith('.json')]
        media_files = [f for f in all_files if 'media' in f[0]]
        other_files = [f for f in all_files if not f[0].endswith('.json') and 'media' not in f[0]]
        
        self.stdout.write(f'📊 JSON Files: {len(json_files)}')
        self.stdout.write(f'🖼️  Media Files: {len(media_files)}')
        self.stdout.write(f'📋 Other Files: {len(other_files)}')
        
        # Analyze JSON files
        if json_files:
            self.stdout.write('\n🔍 JSON File Analysis:')
            for json_file, size in sorted(json_files, key=lambda x: x[1], reverse=True):
                self.stdout.write(f'  📄 {json_file} ({size / 1024:.1f} KB)')
                
                # Try to read and analyze
                try:
                    file_path = os.path.join(backup_dir, json_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        self.stdout.write(f'    ✅ Valid JSON list with {len(data)} records')
                        
                        if len(data) > 0:
                            first_record = data[0]
                            if isinstance(first_record, dict):
                                if 'model' in first_record:
                                    self.stdout.write(f'    ✅ Django fixture format detected')
                                    self.stdout.write(f'    📋 First model: {first_record["model"]}')
                                    
                                    # Count models
                                    models = {}
                                    for record in data[:100]:  # Sample first 100
                                        if isinstance(record, dict) and 'model' in record:
                                            model = record['model']
                                            models[model] = models.get(model, 0) + 1
                                    
                                    self.stdout.write(f'    📊 Models found (sample):')
                                    for model, count in sorted(models.items()):
                                        self.stdout.write(f'      - {model}: {count}')
                                else:
                                    self.stdout.write(f'    ⚠️  Not Django fixture format (no "model" field)')
                            else:
                                self.stdout.write(f'    ⚠️  Records are not dictionaries')
                    else:
                        self.stdout.write(f'    ⚠️  Not a JSON list: {type(data)}')
                        
                except json.JSONDecodeError as e:
                    self.stdout.write(f'    ❌ Invalid JSON: {e}')
                except Exception as e:
                    self.stdout.write(f'    ❌ Error reading file: {e}')
        
        # Check for system info
        system_info_path = os.path.join(backup_dir, 'system_info.json')
        if os.path.exists(system_info_path):
            self.stdout.write('\n✅ System Info Found:')
            try:
                with open(system_info_path, 'r', encoding='utf-8') as f:
                    system_info = json.load(f)
                
                for key, value in system_info.items():
                    self.stdout.write(f'  {key}: {value}')
            except Exception as e:
                self.stdout.write(f'  ❌ Error reading system info: {e}')
        else:
            self.stdout.write('\n⚠️  No system_info.json found (legacy backup)')
        
        # Recommendations
        self.stdout.write('\n💡 RECOMMENDATIONS:')
        
        if not json_files:
            self.stdout.write('  ❌ No JSON database files found - this backup cannot be restored')
        elif len([f for f in json_files if f[1] > 1024]) == 0:  # No files > 1KB
            self.stdout.write('  ⚠️  All JSON files are very small - may be empty backup')
        else:
            largest_json = max(json_files, key=lambda x: x[1])
            self.stdout.write(f'  ✅ Try restoring with largest JSON file: {largest_json[0]}')
            
            # Test loaddata command
            self.stdout.write('\n🧪 Testing Django loaddata compatibility:')
            try:
                file_path = os.path.join(backup_dir, largest_json[0])
                # Try dry run
                call_command('loaddata', file_path, verbosity=0, dry_run=True)
                self.stdout.write('  ✅ File is compatible with Django loaddata')
            except Exception as e:
                self.stdout.write(f'  ❌ File incompatible with loaddata: {e}')
                self.stdout.write('  💡 Try manual data import or contact support')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('🏁 Diagnostic complete!')
