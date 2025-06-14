#!/usr/bin/env python
"""
Script to diagnose Cloudinary configuration and test uploads
"""

import os
import sys
from pathlib import Path
import django

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

django.setup()

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import cloudinary.uploader

def diagnose_configuration():
    """Diagnose current Cloudinary configuration"""
    print("🔍 CLOUDINARY CONFIGURATION DIAGNOSIS")
    print("=" * 60)
    
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print(f"CLOUDINARY_CLOUD_NAME: {settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', 'Not set')}")
    print(f"CLOUDINARY_API_KEY: {settings.CLOUDINARY_STORAGE.get('API_KEY', 'Not set')}")
    print(f"CLOUDINARY_API_SECRET: {'***' if settings.CLOUDINARY_STORAGE.get('API_SECRET') else 'Not set'}")
    print(f"CLOUDINARY_CONFIGURED: {getattr(settings, 'CLOUDINARY_CONFIGURED', 'Not set')}")
    print(f"Default storage class: {default_storage.__class__.__name__}")
    
    # Check environment variables
    print(f"\n🌍 ENVIRONMENT VARIABLES:")
    env_vars = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET', 'DEBUG', 'ENVIRONMENT']
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        if 'SECRET' in var and value != 'Not set':
            value = '***'
        print(f"{var}: {value}")

def test_django_upload():
    """Test Django file upload using default storage"""
    print(f"\n🧪 TESTING DJANGO FILE UPLOAD")
    print("=" * 60)
    
    try:
        # Create a test file
        test_content = b"This is a test file for Cloudinary upload"
        test_file = ContentFile(test_content, name="test_django_upload.txt")
        
        # Save using Django's default storage
        saved_path = default_storage.save("test_uploads/test_django_upload.txt", test_file)
        saved_url = default_storage.url(saved_path)
        
        print(f"✅ Django upload successful:")
        print(f"   Saved path: {saved_path}")
        print(f"   Saved URL: {saved_url}")
        
        # Check if it's actually in Cloudinary
        if 'cloudinary.com' in saved_url:
            print(f"✅ File uploaded to Cloudinary!")
        else:
            print(f"❌ File uploaded to local storage, not Cloudinary!")
            
        return True
        
    except Exception as e:
        print(f"❌ Django upload failed: {e}")
        return False

def test_direct_cloudinary():
    """Test direct Cloudinary upload"""
    print(f"\n🧪 TESTING DIRECT CLOUDINARY UPLOAD")
    print("=" * 60)
    
    try:
        # Test direct Cloudinary upload
        result = cloudinary.uploader.upload(
            "data:text/plain;base64,VGhpcyBpcyBhIHRlc3QgZmlsZQ==",  # "This is a test file" in base64
            public_id="test_direct_upload",
            overwrite=True
        )
        
        print(f"✅ Direct Cloudinary upload successful:")
        print(f"   Public ID: {result['public_id']}")
        print(f"   URL: {result['secure_url']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct Cloudinary upload failed: {e}")
        return False

def check_existing_images():
    """Check what images currently exist in database vs Cloudinary"""
    print(f"\n📋 CHECKING EXISTING IMAGES")
    print("=" * 60)
    
    from website.models import PageContent, SiteSettings, HeroSlide
    
    # Check PageContent images
    print("PageContent images:")
    for content in PageContent.objects.filter(image__isnull=False):
        image_path = str(content.image)
        full_url = f"https://res.cloudinary.com/ds5udo8jc/{image_path}"
        print(f"  {content.page}/{content.section}: {image_path}")
        print(f"    Full URL: {full_url}")
    
    # Check SiteSettings
    site_settings = SiteSettings.objects.first()
    if site_settings:
        print(f"\nSiteSettings:")
        if site_settings.school_logo:
            print(f"  School logo: {site_settings.school_logo}")
        if site_settings.favicon:
            print(f"  Favicon: {site_settings.favicon}")
    
    # Check HeroSlides
    print(f"\nHeroSlides:")
    for slide in HeroSlide.objects.all():
        if slide.image:
            print(f"  Slide {slide.id}: {slide.image}")

def provide_solution():
    """Provide solution recommendations"""
    print(f"\n💡 SOLUTION RECOMMENDATIONS")
    print("=" * 60)
    
    if settings.DEBUG:
        print("❌ ISSUE: DEBUG=True means you're in development mode")
        print("   SOLUTION: Cloudinary is only used in production (DEBUG=False)")
        print("   ACTION: Set DEBUG=False in production environment")
    
    if getattr(settings, 'DEFAULT_FILE_STORAGE', '') != 'cloudinary_storage.storage.MediaCloudinaryStorage':
        print("❌ ISSUE: DEFAULT_FILE_STORAGE is not set to Cloudinary")
        print("   SOLUTION: Ensure Cloudinary storage is configured properly")
    
    print(f"\n📝 NEXT STEPS:")
    print(f"1. Fix Cloudinary configuration in settings.py")
    print(f"2. Clean up existing images and re-upload to Cloudinary")
    print(f"3. Test admin panel uploads")
    print(f"4. Deploy and verify production behavior")

if __name__ == "__main__":
    print("🚀 Cloudinary Diagnosis Script")
    print("=" * 60)
    
    try:
        diagnose_configuration()
        django_success = test_django_upload()
        cloudinary_success = test_direct_cloudinary()
        check_existing_images()
        provide_solution()
        
        print(f"\n📊 SUMMARY:")
        print(f"Django upload: {'✅ Working' if django_success else '❌ Failed'}")
        print(f"Cloudinary direct: {'✅ Working' if cloudinary_success else '❌ Failed'}")
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        sys.exit(1)
