#!/usr/bin/env python
"""
Simple test script to verify backup and restore functionality
"""
import os
import sys
import django
import tempfile
import zipfile
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_management.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User

def test_backup_restore():
    """Test backup and restore functionality"""
    print("🔄 Testing Backup and Restore Functionality")
    print("=" * 50)
    
    # Create a test backup
    print("1. Creating test backup...")
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Create backup
            call_command('backup_system', 
                        output_dir=temp_dir, 
                        compress=True,
                        verbosity=1)
            
            # Find the backup file
            backup_files = [f for f in os.listdir(temp_dir) if f.endswith('.zip')]
            if not backup_files:
                print("❌ No backup file created")
                return False
            
            backup_file = os.path.join(temp_dir, backup_files[0])
            print(f"✅ Backup created: {backup_files[0]}")
            
            # Test backup structure
            print("2. Testing backup structure...")
            with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Check for database files
                has_db = any(f.endswith('.json') for f in file_list)
                if has_db:
                    print("✅ Database backup found")
                else:
                    print("❌ No database backup found")
                    return False
                
                # Check for system info (optional)
                has_system_info = any('system_info.json' in f for f in file_list)
                if has_system_info:
                    print("✅ System info found")
                else:
                    print("⚠️  System info not found (this is OK for legacy backups)")
            
            # Test restore (dry run)
            print("3. Testing restore functionality...")
            try:
                # Extract to test restore
                extract_dir = os.path.join(temp_dir, 'test_restore')
                with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Find backup directory
                backup_dirs = [d for d in os.listdir(extract_dir) 
                              if os.path.isdir(os.path.join(extract_dir, d))]
                
                if backup_dirs:
                    test_backup_dir = os.path.join(extract_dir, backup_dirs[0])
                else:
                    test_backup_dir = extract_dir
                
                # Test the verification function
                from dashboard.management.commands.restore_system import Command
                restore_cmd = Command()
                
                # This should not raise an exception with our improved verification
                restore_cmd.verify_backup(test_backup_dir)
                print("✅ Backup verification passed")
                
                # Test backup info display
                restore_cmd.show_backup_info(test_backup_dir)
                print("✅ Backup info display works")
                
            except Exception as e:
                print(f"❌ Restore test failed: {e}")
                return False
            
            print("\n🎉 All backup/restore tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Backup creation failed: {e}")
            return False

def test_legacy_backup_format():
    """Test restore with legacy backup format (no system_info.json)"""
    print("\n🔄 Testing Legacy Backup Format Support")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock legacy backup structure
        legacy_backup_dir = os.path.join(temp_dir, 'legacy_backup')
        os.makedirs(legacy_backup_dir)
        
        # Create a mock database file
        db_file = os.path.join(legacy_backup_dir, 'database.json')
        with open(db_file, 'w') as f:
            json.dump([
                {
                    "model": "auth.user",
                    "pk": 1,
                    "fields": {
                        "username": "test_user",
                        "email": "test@example.com"
                    }
                }
            ], f)
        
        # Create media directory
        media_dir = os.path.join(legacy_backup_dir, 'media')
        os.makedirs(media_dir)
        
        try:
            # Test verification with legacy format
            from dashboard.management.commands.restore_system import Command
            restore_cmd = Command()
            
            restore_cmd.verify_backup(legacy_backup_dir)
            print("✅ Legacy backup verification passed")
            
            restore_cmd.show_backup_info(legacy_backup_dir)
            print("✅ Legacy backup info display works")
            
            print("🎉 Legacy backup format support works!")
            return True
            
        except Exception as e:
            print(f"❌ Legacy backup test failed: {e}")
            return False

if __name__ == '__main__':
    print("🧪 School Management System - Backup/Restore Test Suite")
    print("=" * 60)
    
    # Run tests
    test1_passed = test_backup_restore()
    test2_passed = test_legacy_backup_format()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"✅ Standard Backup/Restore: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"✅ Legacy Format Support: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! Backup system is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED! Please check the backup system.")
        sys.exit(1)
