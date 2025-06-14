#!/usr/bin/env python
"""
Script to test image URLs and verify they're accessible
"""

import os
import sys
from pathlib import Path
import django
import requests

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

django.setup()

from django.conf import settings
from website.models import PageContent, HeroSlide, SiteSettings
from users.models import SchoolSettings

def test_image_url(url, description=""):
    """Test if an image URL is accessible"""
    try:
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            return True, f"✅ {description}: {url}"
        else:
            return False, f"❌ {description}: {url} (Status: {response.status_code})"
    except Exception as e:
        return False, f"❌ {description}: {url} (Error: {str(e)})"

def test_all_images():
    """Test all images in the system"""
    print("🔄 Testing all image URLs...")
    print("=" * 70)
    
    results = []
    
    # Test HeroSlide images
    print("\n📸 HERO SLIDES:")
    for slide in HeroSlide.objects.all():
        if slide.image:
            if settings.DEBUG:
                # In development, construct local URL
                url = f"http://127.0.0.1:8000{settings.MEDIA_URL}{slide.image}"
            else:
                # In production, use Cloudinary URL
                url = f"https://res.cloudinary.com/{settings.CLOUDINARY_STORAGE['CLOUD_NAME']}/{slide.image}"
            
            success, message = test_image_url(url, f"Hero Slide: {slide.title}")
            results.append((success, message))
            print(message)
    
    # Test PageContent images
    print("\n📄 PAGE CONTENT IMAGES:")
    for content in PageContent.objects.filter(image__isnull=False):
        if content.image:
            if settings.DEBUG:
                url = f"http://127.0.0.1:8000{settings.MEDIA_URL}{content.image}"
            else:
                url = f"https://res.cloudinary.com/{settings.CLOUDINARY_STORAGE['CLOUD_NAME']}/{content.image}"
            
            success, message = test_image_url(url, f"{content.page}/{content.section}")
            results.append((success, message))
            print(message)
    
    # Test SiteSettings images
    print("\n🏫 SITE SETTINGS:")
    try:
        site_settings = SiteSettings.objects.first()
        if site_settings:
            for field_name in ['school_logo', 'footer_logo', 'favicon']:
                field_value = getattr(site_settings, field_name, None)
                if field_value:
                    if settings.DEBUG:
                        url = f"http://127.0.0.1:8000{settings.MEDIA_URL}{field_value}"
                    else:
                        url = f"https://res.cloudinary.com/{settings.CLOUDINARY_STORAGE['CLOUD_NAME']}/{field_value}"
                    
                    success, message = test_image_url(url, f"Site {field_name}")
                    results.append((success, message))
                    print(message)
    except Exception as e:
        print(f"❌ Error testing SiteSettings: {e}")
    
    # Test SchoolSettings logo
    print("\n🎓 SCHOOL SETTINGS:")
    try:
        school_settings = SchoolSettings.objects.first()
        if school_settings and school_settings.logo:
            if settings.DEBUG:
                url = f"http://127.0.0.1:8000{settings.MEDIA_URL}{school_settings.logo}"
            else:
                url = f"https://res.cloudinary.com/{settings.CLOUDINARY_STORAGE['CLOUD_NAME']}/{school_settings.logo}"
            
            success, message = test_image_url(url, "School Logo")
            results.append((success, message))
            print(message)
    except Exception as e:
        print(f"❌ Error testing SchoolSettings: {e}")
    
    # Summary
    successful = sum(1 for success, _ in results if success)
    total = len(results)
    failed = total - successful
    
    print(f"\n📊 SUMMARY:")
    print(f"✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {failed}/{total}")
    
    if failed > 0:
        print(f"\n🔧 RECOMMENDATIONS:")
        print(f"1. Check if your development server is running (python manage.py runserver)")
        print(f"2. Verify Cloudinary configuration in production")
        print(f"3. Re-upload missing images to Cloudinary")
    
    return successful, failed

if __name__ == "__main__":
    print("🚀 Image URL Testing Script")
    print("=" * 70)
    print(f"Environment: {'Development' if settings.DEBUG else 'Production'}")
    print(f"Media URL: {settings.MEDIA_URL}")
    if hasattr(settings, 'CLOUDINARY_STORAGE'):
        print(f"Cloudinary Cloud: {settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', 'Not configured')}")
    
    successful, failed = test_all_images()
    
    if failed == 0:
        print(f"\n🎉 All images are accessible!")
    else:
        print(f"\n⚠️  {failed} images need attention")
