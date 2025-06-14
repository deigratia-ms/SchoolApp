#!/usr/bin/env python
"""
Script to upload existing media files to Cloudinary
This will help migrate local media files to Cloudinary for production use
"""

import os
import sys
from pathlib import Path
import django

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

# Set production environment
os.environ['DEBUG'] = 'False'
os.environ['ENVIRONMENT'] = 'production'

django.setup()

from django.conf import settings
from users.models import SchoolSettings, HeroSlide, Gallery, Staff, Event, Announcement, AcademicProgram, PageContent
from users.models import
import cloudinary
import cloudinary.uploader

def upload_model_images():
    """Upload images from Django models to Cloudinary"""
    print("🔄 Uploading model images to Cloudinary...")
    print("=" * 50)
    
    uploaded_count = 0
    error_count = 0
    
    # Upload SchoolSettings images
    try:
        site_settings = SchoolSettings.objects.first()
        if site_settings:
            if site_settings.logo and hasattr(site_settings.logo, 'path'):
                try:
                    result = cloudinary.uploader.upload(
                        site_settings.logo.path,
                        public_id=f"site/school_logo",
                        overwrite=True
                    )
                    print(f"✅ Uploaded school logo: {result['secure_url']}")
                    uploaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to upload school logo: {e}")
                    error_count += 1
                    
            if site_settings.footer_logo and hasattr(site_settings.footer_logo, 'path'):
                try:
                    result = cloudinary.uploader.upload(
                        site_settings.footer_logo.path,
                        public_id=f"site/footer_logo",
                        overwrite=True
                    )
                    print(f"✅ Uploaded footer logo: {result['secure_url']}")
                    uploaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to upload footer logo: {e}")
                    error_count += 1
    except Exception as e:
        print(f"❌ Error processing SchoolSettings: {e}")
        error_count += 1
    
    # Upload SchoolSettings logo
    try:
        from users.models import SchoolSettings

        school_settings = SchoolSettings.objects.first()
        if school_settings and school_settings.logo and hasattr(school_settings.logo, 'path'):
            try:
                result = cloudinary.uploader.upload(
                    school_settings.logo.path,
                    public_id=f"school_logo/main_logo",
                    overwrite=True
                )
                print(f"✅ Uploaded school settings logo: {result['secure_url']}")
                uploaded_count += 1
            except Exception as e:
                print(f"❌ Failed to upload school settings logo: {e}")
                error_count += 1
    except Exception as e:
        print(f"❌ Error processing SchoolSettings: {e}")
        error_count += 1
    
    # Upload HeroSlide images
    try:
        hero_slides = HeroSlide.objects.all()
        for slide in hero_slides:
            if slide.image and hasattr(slide.image, 'path'):
                try:
                    result = cloudinary.uploader.upload(
                        slide.image.path,
                        public_id=f"hero_slides/{slide.id}_{slide.title[:20]}",
                        overwrite=True
                    )
                    print(f"✅ Uploaded hero slide: {slide.title} -> {result['secure_url']}")
                    uploaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to upload hero slide {slide.title}: {e}")
                    error_count += 1
    except Exception as e:
        print(f"❌ Error processing HeroSlides: {e}")
        error_count += 1
    
    # Upload Gallery images
    try:
        galleries = Gallery.objects.all()
        for gallery in galleries:
            if gallery.image and hasattr(gallery.image, 'path'):
                try:
                    result = cloudinary.uploader.upload(
                        gallery.image.path,
                        public_id=f"gallery/{gallery.id}_{gallery.title[:20]}",
                        overwrite=True
                    )
                    print(f"✅ Uploaded gallery image: {gallery.title} -> {result['secure_url']}")
                    uploaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to upload gallery image {gallery.title}: {e}")
                    error_count += 1
    except Exception as e:
        print(f"❌ Error processing Gallery: {e}")
        error_count += 1
    
    # Upload Staff images
    try:
        staff_members = Staff.objects.all()
        for staff in staff_members:
            if staff.image and hasattr(staff.image, 'path'):
                try:
                    result = cloudinary.uploader.upload(
                        staff.image.path,
                        public_id=f"staff/{staff.id}_{staff.name[:20]}",
                        overwrite=True
                    )
                    print(f"✅ Uploaded staff image: {staff.name} -> {result['secure_url']}")
                    uploaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to upload staff image {staff.name}: {e}")
                    error_count += 1
    except Exception as e:
        print(f"❌ Error processing Staff: {e}")
        error_count += 1
    
    print(f"\n📊 Upload Summary:")
    print(f"✅ Successfully uploaded: {uploaded_count} files")
    print(f"❌ Failed uploads: {error_count} files")
    
    return uploaded_count, error_count

def upload_media_directory():
    """Upload files from media directory to Cloudinary"""
    print("\n🔄 Uploading media directory files to Cloudinary...")
    print("=" * 50)
    
    media_root = Path(settings.MEDIA_ROOT)
    if not media_root.exists():
        print("❌ Media directory doesn't exist")
        return 0, 0
    
    uploaded_count = 0
    error_count = 0
    
    # Common image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    for file_path in media_root.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            try:
                # Create a public_id based on the relative path
                relative_path = file_path.relative_to(media_root)
                public_id = str(relative_path).replace('\\', '/').rsplit('.', 1)[0]
                
                result = cloudinary.uploader.upload(
                    str(file_path),
                    public_id=public_id,
                    overwrite=True
                )
                print(f"✅ Uploaded: {relative_path} -> {result['secure_url']}")
                uploaded_count += 1
            except Exception as e:
                print(f"❌ Failed to upload {relative_path}: {e}")
                error_count += 1
    
    print(f"\n📊 Media Directory Upload Summary:")
    print(f"✅ Successfully uploaded: {uploaded_count} files")
    print(f"❌ Failed uploads: {error_count} files")
    
    return uploaded_count, error_count

if __name__ == "__main__":
    print("🚀 Cloudinary Media Upload Script")
    print("=" * 50)
    
    try:
        # Test Cloudinary connection first
        result = cloudinary.api.ping()
        print(f"✅ Cloudinary connection successful: {result.get('status', 'unknown')}")
        
        # Upload model images
        model_uploaded, model_errors = upload_model_images()
        
        # Upload media directory files
        media_uploaded, media_errors = upload_media_directory()
        
        total_uploaded = model_uploaded + media_uploaded
        total_errors = model_errors + media_errors
        
        print(f"\n🎉 Final Summary:")
        print(f"✅ Total files uploaded: {total_uploaded}")
        print(f"❌ Total errors: {total_errors}")
        
        if total_uploaded > 0:
            print(f"\n📝 Next steps:")
            print(f"1. Check your Cloudinary dashboard at https://cloudinary.com/console")
            print(f"2. Your images should now be accessible via Cloudinary URLs")
            print(f"3. Test your website to see if images are loading")
        
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)
