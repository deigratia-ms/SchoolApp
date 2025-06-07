#!/usr/bin/env python
"""
Migration Reset Script for PythonAnywhere Deployment Issues

This script helps reset migrations if you encounter issues on PythonAnywhere.
Use this ONLY if you get migration conflicts or database errors.

IMPORTANT: This will reset ALL migrations. Use with caution!
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.apps import apps

def reset_migrations():
    """Reset all migrations for the project"""
    
    print("🚨 MIGRATION RESET SCRIPT")
    print("=" * 50)
    print("This will:")
    print("1. Remove all migration files (except __init__.py)")
    print("2. Reset the django_migrations table")
    print("3. Create fresh initial migrations")
    print("4. Apply all migrations")
    print()
    
    # Get confirmation
    confirm = input("Are you sure you want to reset ALL migrations? (type 'yes' to continue): ")
    if confirm.lower() != 'yes':
        print("❌ Migration reset cancelled.")
        return
    
    # List of apps to reset
    apps_to_reset = [
        'website',
        'users', 
        'courses',
        'assignments',
        'attendance',
        'communications',
        'dashboard',
        'fees',
        'payroll',
        'appointments'
    ]
    
    print("\n🗑️  Step 1: Removing migration files...")
    for app_name in apps_to_reset:
        migrations_dir = Path(app_name) / 'migrations'
        if migrations_dir.exists():
            for migration_file in migrations_dir.glob('*.py'):
                if migration_file.name != '__init__.py':
                    print(f"   Removing {migration_file}")
                    migration_file.unlink()
    
    print("\n🗄️  Step 2: Clearing django_migrations table...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_migrations WHERE app IN %s", [tuple(apps_to_reset)])
        print("   ✅ Migration records cleared")
    except Exception as e:
        print(f"   ⚠️  Could not clear migration records: {e}")
    
    print("\n🆕 Step 3: Creating fresh migrations...")
    for app_name in apps_to_reset:
        try:
            execute_from_command_line(['manage.py', 'makemigrations', app_name])
            print(f"   ✅ Created migrations for {app_name}")
        except Exception as e:
            print(f"   ⚠️  Could not create migrations for {app_name}: {e}")
    
    print("\n🚀 Step 4: Applying all migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("   ✅ All migrations applied successfully")
    except Exception as e:
        print(f"   ❌ Error applying migrations: {e}")
        return
    
    print("\n✅ Migration reset completed successfully!")
    print("\nNext steps:")
    print("1. Run: python manage.py collectstatic --noinput")
    print("2. Test your application")
    print("3. If using appointment scheduler, run: python manage.py start_appointment_scheduler")

if __name__ == '__main__':
    reset_migrations()
