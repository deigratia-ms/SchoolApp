#!/usr/bin/env python
"""
Test script to verify admin panel uploads work with Cloudinary
"""

import os
import sys
from pathlib import Path
import django
from io import BytesIO
from PIL import Image

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

django.setup()

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from website.models import PageContent

def create_test_image():
    """Create a test image file"""
    # Create a simple test image
    img = Image.new('RGB', (800, 600), color='blue')
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    
    return SimpleUploadedFile(
        name='test_admin_upload.jpg',
        content=img_io.getvalue(),
        content_type='image/jpeg'
    )

def test_storage_configuration():
    """Test storage configuration"""
    print("🔧 TESTING STORAGE CONFIGURATION")
    print("=" * 50)
    
    print(f"DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print(f"CLOUDINARY_CONFIGURED: {getattr(settings, 'CLOUDINARY_CONFIGURED', 'Not set')}")
    print(f"Default storage class: {default_storage.__class__.__name__}")
    print(f"Storage module: {default_storage.__class__.__module__}")
    
    # Test if storage is actually Cloudinary
    is_cloudinary = 'cloudinary' in default_storage.__class__.__module__.lower()
    print(f"Is Cloudinary storage: {'✅ YES' if is_cloudinary else '❌ NO'}")
    
    return is_cloudinary

def test_direct_storage_upload():
    """Test direct storage upload"""
    print(f"\n📤 TESTING DIRECT STORAGE UPLOAD")
    print("=" * 50)
    
    try:
        # Create test image
        test_file = create_test_image()
        
        # Upload using default storage
        file_path = default_storage.save('test_uploads/direct_test.jpg', test_file)
        file_url = default_storage.url(file_path)
        
        print(f"✅ Direct upload successful:")
        print(f"   File path: {file_path}")
        print(f"   File URL: {file_url}")
        
        # Check if it's a Cloudinary URL
        is_cloudinary_url = 'cloudinary.com' in file_url
        print(f"   Is Cloudinary URL: {'✅ YES' if is_cloudinary_url else '❌ NO'}")
        
        return True, file_url
        
    except Exception as e:
        print(f"❌ Direct upload failed: {e}")
        return False, None

def test_model_upload():
    """Test upload through Django model"""
    print(f"\n📋 TESTING MODEL UPLOAD")
    print("=" * 50)
    
    try:
        # Create test image
        test_file = create_test_image()
        
        # Create or update PageContent with image
        page_content, created = PageContent.objects.get_or_create(
            page='about',
            section='test_upload',
            defaults={
                'title': 'Test Upload',
                'content': 'This is a test upload to verify Cloudinary integration.'
            }
        )
        
        # Assign the image
        page_content.image = test_file
        page_content.save()
        
        # Get the URL
        image_url = page_content.image.url
        
        print(f"✅ Model upload successful:")
        print(f"   Image field: {page_content.image}")
        print(f"   Image URL: {image_url}")
        
        # Check if it's a Cloudinary URL
        is_cloudinary_url = 'cloudinary.com' in image_url
        print(f"   Is Cloudinary URL: {'✅ YES' if is_cloudinary_url else '❌ NO'}")
        
        return True, image_url
        
    except Exception as e:
        print(f"❌ Model upload failed: {e}")
        return False, None

def test_existing_image():
    """Test existing problematic image"""
    print(f"\n🔍 TESTING EXISTING PROBLEMATIC IMAGE")
    print("=" * 50)
    
    try:
        # Get the problematic PageContent
        page_content = PageContent.objects.get(page='about', section='hero')
        
        print(f"Current image path: {page_content.image}")
        print(f"Current image URL: {page_content.image.url}")
        
        # Check if file exists in storage
        exists = default_storage.exists(page_content.image.name)
        print(f"File exists in storage: {'✅ YES' if exists else '❌ NO'}")
        
        # Try to access the URL
        import requests
        try:
            response = requests.head(page_content.image.url, timeout=10)
            print(f"URL accessible: {'✅ YES' if response.status_code == 200 else f'❌ NO ({response.status_code})'}")
        except Exception as e:
            print(f"URL accessible: ❌ NO ({e})")
            
        return exists
        
    except PageContent.DoesNotExist:
        print("❌ No about/hero PageContent found")
        return False
    except Exception as e:
        print(f"❌ Error checking existing image: {e}")
        return False

def main():
    print("🚀 Admin Panel Upload Test")
    print("=" * 60)
    print("This script tests if admin panel uploads work with Cloudinary")
    print()
    
    # Test 1: Storage configuration
    is_cloudinary_configured = test_storage_configuration()
    
    # Test 2: Direct storage upload
    direct_success, direct_url = test_direct_storage_upload()
    
    # Test 3: Model upload (simulates admin panel)
    model_success, model_url = test_model_upload()
    
    # Test 4: Check existing problematic image
    existing_works = test_existing_image()
    
    # Summary
    print(f"\n📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Storage configured for Cloudinary: {'✅' if is_cloudinary_configured else '❌'}")
    print(f"Direct storage upload works: {'✅' if direct_success else '❌'}")
    print(f"Model upload works: {'✅' if model_success else '❌'}")
    print(f"Existing image accessible: {'✅' if existing_works else '❌'}")
    
    if is_cloudinary_configured and direct_success and model_success:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ Admin panel uploads should now work with Cloudinary")
        print(f"✅ New uploads will be stored in Cloudinary")
        print(f"✅ Images will be served via Cloudinary CDN")
    else:
        print(f"\n⚠️ SOME TESTS FAILED")
        print(f"🔧 Admin panel uploads may not work correctly")
        
        if not is_cloudinary_configured:
            print(f"   - Fix: Check Cloudinary configuration in settings.py")
        if not direct_success:
            print(f"   - Fix: Check DEFAULT_FILE_STORAGE setting")
        if not model_success:
            print(f"   - Fix: Check model field configuration")

if __name__ == "__main__":
    main()
