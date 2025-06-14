#!/usr/bin/env python
"""
Debug the actual upload process to find why files aren't going to Cloudinary
"""

import os
import sys
from pathlib import Path
import django
from PIL import Image
from io import BytesIO

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

# Force production environment
os.environ['DEBUG'] = 'False'
os.environ['ENVIRONMENT'] = 'production'

django.setup()

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from website.models import PageContent
import cloudinary
import cloudinary.uploader

def test_django_configuration():
    """Test Django configuration"""
    print("🔧 DJANGO CONFIGURATION TEST")
    print("=" * 60)
    
    print(f"DEBUG: {settings.DEBUG}")
    print(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'Not set')}")
    print(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print(f"CLOUDINARY_CONFIGURED: {getattr(settings, 'CLOUDINARY_CONFIGURED', 'Not set')}")
    
    print(f"\nStorage Backend:")
    print(f"  Class: {default_storage.__class__.__name__}")
    print(f"  Module: {default_storage.__class__.__module__}")
    
    # Check if it's actually Cloudinary storage
    is_cloudinary = 'cloudinary' in default_storage.__class__.__module__.lower()
    print(f"  Is Cloudinary: {'✅ YES' if is_cloudinary else '❌ NO'}")
    
    return is_cloudinary

def test_cloudinary_direct():
    """Test direct Cloudinary upload"""
    print(f"\n☁️ DIRECT CLOUDINARY TEST")
    print("=" * 60)
    
    try:
        # Test connection
        result = cloudinary.api.ping()
        print(f"✅ Connection successful: {result.get('status', 'unknown')}")
        
        # Create test image
        img = Image.new('RGB', (100, 100), color='blue')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # Upload directly to Cloudinary
        upload_result = cloudinary.uploader.upload(
            img_io.getvalue(),
            public_id='debug_test/direct_upload',
            overwrite=True,
            resource_type='image'
        )
        
        print(f"✅ Direct upload successful:")
        print(f"  Public ID: {upload_result['public_id']}")
        print(f"  URL: {upload_result['secure_url']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct Cloudinary test failed: {e}")
        return False

def test_django_storage_upload():
    """Test Django storage upload"""
    print(f"\n📁 DJANGO STORAGE TEST")
    print("=" * 60)
    
    try:
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # Create uploaded file
        uploaded_file = SimpleUploadedFile(
            name='django_storage_test.jpg',
            content=img_io.getvalue(),
            content_type='image/jpeg'
        )
        
        # Save using Django storage
        file_path = default_storage.save('debug_test/django_storage_test.jpg', uploaded_file)
        file_url = default_storage.url(file_path)
        
        print(f"✅ Django storage upload successful:")
        print(f"  File path: {file_path}")
        print(f"  File URL: {file_url}")
        
        # Check if it's a Cloudinary URL
        is_cloudinary_url = 'cloudinary.com' in file_url
        print(f"  Is Cloudinary URL: {'✅ YES' if is_cloudinary_url else '❌ NO'}")
        
        return is_cloudinary_url
        
    except Exception as e:
        print(f"❌ Django storage test failed: {e}")
        return False

def test_model_upload():
    """Test model upload (simulates admin panel)"""
    print(f"\n📋 MODEL UPLOAD TEST")
    print("=" * 60)
    
    try:
        # Create test image
        img = Image.new('RGB', (100, 100), color='green')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # Create uploaded file
        uploaded_file = SimpleUploadedFile(
            name='model_upload_test.jpg',
            content=img_io.getvalue(),
            content_type='image/jpeg'
        )
        
        # Create or update PageContent
        page_content, created = PageContent.objects.get_or_create(
            page='debug',
            section='upload_test',
            defaults={
                'title': 'Debug Upload Test',
                'content': 'Testing model upload process'
            }
        )
        
        print(f"PageContent {'created' if created else 'found'}: {page_content}")
        
        # Assign the image (this simulates admin panel upload)
        page_content.image = uploaded_file
        page_content.save()
        
        print(f"✅ Model upload successful:")
        print(f"  Image field: {page_content.image}")
        print(f"  Image URL: {page_content.image.url}")
        print(f"  Image name: {page_content.image.name}")
        
        # Check if it's a Cloudinary URL
        is_cloudinary_url = 'cloudinary.com' in page_content.image.url
        print(f"  Is Cloudinary URL: {'✅ YES' if is_cloudinary_url else '❌ NO'}")
        
        # Test URL accessibility
        import requests
        try:
            response = requests.head(page_content.image.url, timeout=10)
            url_accessible = response.status_code == 200
            print(f"  URL accessible: {'✅ YES' if url_accessible else f'❌ NO ({response.status_code})'}")
        except Exception as e:
            print(f"  URL accessible: ❌ NO ({e})")
            url_accessible = False
        
        return is_cloudinary_url and url_accessible
        
    except Exception as e:
        print(f"❌ Model upload test failed: {e}")
        return False

def inspect_storage_backend():
    """Inspect the storage backend in detail"""
    print(f"\n🔍 STORAGE BACKEND INSPECTION")
    print("=" * 60)
    
    print(f"Storage object: {default_storage}")
    print(f"Storage class: {default_storage.__class__}")
    print(f"Storage module: {default_storage.__class__.__module__}")
    
    # Check storage attributes
    if hasattr(default_storage, 'cloud_name'):
        print(f"Cloud name: {default_storage.cloud_name}")
    if hasattr(default_storage, 'api_key'):
        print(f"API key: {default_storage.api_key}")
    if hasattr(default_storage, 'api_secret'):
        print(f"API secret: {'***' if default_storage.api_secret else 'Not set'}")
    
    # Check if storage has required methods
    required_methods = ['save', 'url', 'exists', 'delete']
    for method in required_methods:
        has_method = hasattr(default_storage, method)
        print(f"Has {method}(): {'✅ YES' if has_method else '❌ NO'}")

def main():
    print("🚀 Upload Process Debug")
    print("=" * 80)
    print("This script will debug why uploads aren't going to Cloudinary")
    print()
    
    # Test 1: Django configuration
    django_ok = test_django_configuration()
    
    # Test 2: Direct Cloudinary
    cloudinary_ok = test_cloudinary_direct()
    
    # Test 3: Django storage
    storage_ok = test_django_storage_upload()
    
    # Test 4: Model upload
    model_ok = test_model_upload()
    
    # Test 5: Storage inspection
    inspect_storage_backend()
    
    # Final diagnosis
    print(f"\n🏥 DIAGNOSIS")
    print("=" * 60)
    
    if not django_ok:
        print("❌ ISSUE: Django is not configured to use Cloudinary storage")
        print("   FIX: Check DEFAULT_FILE_STORAGE setting")
    elif not cloudinary_ok:
        print("❌ ISSUE: Cloudinary connection/credentials problem")
        print("   FIX: Check CLOUDINARY_* environment variables")
    elif not storage_ok:
        print("❌ ISSUE: Django storage backend not working with Cloudinary")
        print("   FIX: Check cloudinary_storage package installation")
    elif not model_ok:
        print("❌ ISSUE: Model uploads not working properly")
        print("   FIX: Check model field configuration")
    else:
        print("✅ Everything should be working!")
        print("   The issue might be elsewhere")
    
    print(f"\n📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Django configuration: {'✅' if django_ok else '❌'}")
    print(f"Direct Cloudinary: {'✅' if cloudinary_ok else '❌'}")
    print(f"Django storage: {'✅' if storage_ok else '❌'}")
    print(f"Model upload: {'✅' if model_ok else '❌'}")

if __name__ == "__main__":
    main()
