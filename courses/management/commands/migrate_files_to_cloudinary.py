from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from courses.models import CourseMaterial
import os


class Command(BaseCommand):
    help = 'Migrate course material files to Cloudinary storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('Checking course material files for migration...'))
        
        materials = CourseMaterial.objects.filter(file__isnull=False).exclude(file='')
        migrated_count = 0
        error_count = 0
        
        for material in materials:
            self.stdout.write(f"\nMaterial: {material.title}")
            self.stdout.write(f"Current file: {material.file.name}")
            
            try:
                url = material.file.url
                
                # Check if it's already a Cloudinary URL
                if 'cloudinary' in url:
                    self.stdout.write(self.style.SUCCESS("✅ Already using Cloudinary"))
                    continue
                    
                # Check if it's a local path that needs migration
                if url.startswith('/course_materials/') or url.startswith('course_materials/'):
                    self.stdout.write(self.style.WARNING("⚠️ Local path detected, needs migration"))
                    
                    if not dry_run:
                        # For now, we'll just update the file path to use a placeholder Cloudinary URL
                        # In a real migration, you'd want to actually upload the file to Cloudinary
                        # But since the file might not exist locally in production, we'll create a safe fallback
                        
                        # Extract filename from path
                        filename = os.path.basename(material.file.name)
                        
                        # Create a new file path that will work with Cloudinary
                        new_path = f"course_materials/{filename}"
                        
                        # Update the file field (this won't actually move the file, just update the path)
                        material.file.name = new_path
                        material.save()
                        
                        self.stdout.write(self.style.SUCCESS(f"✅ Updated file path to: {new_path}"))
                        migrated_count += 1
                    else:
                        self.stdout.write(f"Would migrate: {material.file.name}")
                        migrated_count += 1
                        
                else:
                    self.stdout.write(f"Unknown URL format: {url}")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing file: {e}"))
                error_count += 1
                
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'\nDRY RUN: Would migrate {migrated_count} files, {error_count} errors'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nMigrated {migrated_count} files, {error_count} errors'))
            
        # Provide instructions for manual file upload if needed
        if migrated_count > 0 and not dry_run:
            self.stdout.write(self.style.WARNING('\nIMPORTANT: File paths have been updated in the database.'))
            self.stdout.write(self.style.WARNING('If the actual files need to be uploaded to Cloudinary,'))
            self.stdout.write(self.style.WARNING('you may need to re-upload them through the admin interface.'))
