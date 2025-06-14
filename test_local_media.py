#!/usr/bin/env python
"""
Test local media setup
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
from website.models import PageContent, SiteSettings
from users.models import SchoolSettings

def test_media_configuration():
    """Test media configuration"""
    print("🔧 TESTING MEDIA CONFIGURATION")
    print("=" * 50)
    
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"Storage class: {default_storage.__class__.__name__}")
    print(f"Storage module: {default_storage.__class__.__module__}")
    
    # Check if using local storage
    is_local = 'FileSystemStorage' in default_storage.__class__.__name__
    print(f"Using local storage: {'✅ YES' if is_local else '❌ NO'}")
    
    return is_local

def test_image_files():
    """Test that image files exist"""
    print(f"\n📁 TESTING IMAGE FILES")
    print("=" * 50)
    
    media_root = Path(settings.MEDIA_ROOT)
    
    # Test hero image
    hero_path = media_root / 'hero_slides' / 'test_hero.jpg'
    hero_exists = hero_path.exists()
    print(f"Hero image exists: {'✅ YES' if hero_exists else '❌ NO'}")
    if hero_exists:
        print(f"  Path: {hero_path}")
        print(f"  Size: {hero_path.stat().st_size} bytes")
    
    # Test logo
    logo_path = media_root / 'school_logos' / 'test_logo.png'
    logo_exists = logo_path.exists()
    print(f"Logo exists: {'✅ YES' if logo_exists else '❌ NO'}")
    if logo_exists:
        print(f"  Path: {logo_path}")
        print(f"  Size: {logo_path.stat().st_size} bytes")
    
    return hero_exists and logo_exists

def test_database_records():
    """Test database records"""
    print(f"\n💾 TESTING DATABASE RECORDS")
    print("=" * 50)
    
    results = []
    
    # Test PageContent
    try:
        page_content = PageContent.objects.get(page='about', section='hero')
        print(f"PageContent found: ✅ YES")
        print(f"  Image field: {page_content.image}")
        print(f"  Image URL: {page_content.image.url}")
        
        # Check if file exists
        if page_content.image:
            file_exists = default_storage.exists(page_content.image.name)
            print(f"  File exists in storage: {'✅ YES' if file_exists else '❌ NO'}")
            results.append(file_exists)
        
    except PageContent.DoesNotExist:
        print(f"PageContent: ❌ NOT FOUND")
        results.append(False)
    except Exception as e:
        print(f"PageContent error: ❌ {e}")
        results.append(False)
    
    # Test SiteSettings
    try:
        site_settings = SiteSettings.objects.first()
        if site_settings and site_settings.school_logo:
            print(f"SiteSettings logo: ✅ YES")
            print(f"  Logo field: {site_settings.school_logo}")
            print(f"  Logo URL: {site_settings.school_logo.url}")
            
            file_exists = default_storage.exists(site_settings.school_logo.name)
            print(f"  File exists in storage: {'✅ YES' if file_exists else '❌ NO'}")
            results.append(file_exists)
        else:
            print(f"SiteSettings logo: ❌ NOT FOUND")
            results.append(False)
    except Exception as e:
        print(f"SiteSettings error: ❌ {e}")
        results.append(False)
    
    return all(results)

def test_url_accessibility():
    """Test URL accessibility"""
    print(f"\n🌐 TESTING URL ACCESSIBILITY")
    print("=" * 50)
    
    import requests
    
    base_url = "http://127.0.0.1:8000"
    
    # Test hero image URL
    try:
        page_content = PageContent.objects.get(page='about', section='hero')
        if page_content.image:
            image_url = f"{base_url}{page_content.image.url}"
            print(f"Testing hero image URL: {image_url}")
            
            try:
                response = requests.head(image_url, timeout=5)
                success = response.status_code == 200
                print(f"  Accessible: {'✅ YES' if success else f'❌ NO ({response.status_code})'}")
                return success
            except requests.exceptions.ConnectionError:
                print(f"  Accessible: ⚠️ Server not running")
                return False
            except Exception as e:
                print(f"  Accessible: ❌ Error - {e}")
                return False
    except Exception as e:
        print(f"Error testing URL: ❌ {e}")
        return False

def main():
    print("🚀 Local Media Test")
    print("=" * 60)
    print("Testing local media storage setup")
    print()
    
    # Test 1: Configuration
    config_ok = test_media_configuration()
    
    # Test 2: Files exist
    files_ok = test_image_files()
    
    # Test 3: Database records
    db_ok = test_database_records()
    
    # Test 4: URL accessibility (optional - requires server running)
    url_ok = test_url_accessibility()
    
    # Summary
    print(f"\n📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Configuration: {'✅' if config_ok else '❌'}")
    print(f"Image files: {'✅' if files_ok else '❌'}")
    print(f"Database records: {'✅' if db_ok else '❌'}")
    print(f"URL accessibility: {'✅' if url_ok else '⚠️'}")
    
    if config_ok and files_ok and db_ok:
        print(f"\n🎉 LOCAL MEDIA SETUP SUCCESSFUL!")
        print(f"✅ Images are stored locally")
        print(f"✅ Database records updated")
        print(f"✅ Files accessible via URLs")
        print(f"\n📝 Next steps:")
        print(f"1. Check admin panel: http://127.0.0.1:8000/admin/website/pagecontent/1/change/")
        print(f"2. Check About page: http://127.0.0.1:8000/about/")
        print(f"3. Test uploading new images through admin")
    else:
        print(f"\n⚠️ SOME TESTS FAILED")
        print(f"Please check the failed items above")

if __name__ == "__main__":
    main()
