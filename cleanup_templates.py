import os
import shutil
from pathlib import Path

# Define paths
APP_TEMPLATES_DIR = Path('website/templates/website')
MAIN_TEMPLATES_DIR = Path('templates/website')

def backup_templates():
    """Create a backup of the app templates directory"""
    backup_dir = Path('website/templates_backup')
    if APP_TEMPLATES_DIR.exists():
        print(f"Creating backup of {APP_TEMPLATES_DIR} to {backup_dir}")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(APP_TEMPLATES_DIR, backup_dir)
        print("Backup created successfully")
    else:
        print(f"Directory {APP_TEMPLATES_DIR} does not exist, no backup needed")

def list_duplicate_templates():
    """List templates that exist in both directories"""
    if not APP_TEMPLATES_DIR.exists() or not MAIN_TEMPLATES_DIR.exists():
        print("One of the template directories does not exist")
        return []
    
    app_templates = set(os.listdir(APP_TEMPLATES_DIR))
    main_templates = set(os.listdir(MAIN_TEMPLATES_DIR))
    
    duplicates = app_templates.intersection(main_templates)
    print(f"Found {len(duplicates)} duplicate templates:")
    for template in sorted(duplicates):
        print(f"  - {template}")
    
    return duplicates

def remove_duplicate_templates():
    """Remove duplicate templates from the app templates directory"""
    duplicates = list_duplicate_templates()
    
    if not duplicates:
        print("No duplicate templates to remove")
        return
    
    print("\nRemoving duplicate templates from app templates directory...")
    for template in duplicates:
        template_path = APP_TEMPLATES_DIR / template
        if template_path.exists():
            os.remove(template_path)
            print(f"  - Removed {template}")
    
    print("Duplicate templates removed successfully")

if __name__ == "__main__":
    print("Template Cleanup Utility")
    print("=======================")
    
    # Create backup first
    backup_templates()
    
    # Remove duplicate templates
    remove_duplicate_templates()
    
    print("\nCleanup complete!")
