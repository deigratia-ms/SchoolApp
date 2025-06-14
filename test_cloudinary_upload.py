#!/usr/bin/env python
"""
Test actual Cloudinary upload process
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

django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from website.models import PageContent
import cloudinary
import cloudinary.uploader

def test_direct_cloudinary_upload():
    """Test direct Cloudinary upload"""
    print("🔧 TESTING DIRECT CLOUDINARY UPLOAD")
    print("=" * 60)
    
    try:
        # Create test image
        img = Image.new('RGB', (100, 100), color='blue')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # Upload directly to Cloudinary
        result = cloudinary.uploader.upload(
            img_io.getvalue(),
            public_id='test_direct_upload',
            overwrite=True,
            resource_type='image'
        )
        
        print(f"✅ Direct upload successful:")
        print(f"  Public ID: {result['public_id']}")
        print(f"  URL: {result['secure_url']}")
        
        # Test URL accessibility
        import requests
        response = requests.head(result['secure_url'], timeout=10)
        accessible = response.status_code == 200
        print(f"  URL accessible: {'✅ YES' if accessible else f'❌ NO ({response.status_code})'}")
        
        return accessible
        
    except Exception as e:
        print(f"❌ Direct upload failed: {e}")
        return False

def test_django_model_upload():
    """Test Django model upload"""
    print(f"\n📋 TESTING DJANGO MODEL UPLOAD")
    print("=" * 60)
    
    try:
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # Create uploaded file
        uploaded_file = SimpleUploadedFile(
            name='test_model_upload.jpg',
            content=img_io.getvalue(),
            content_type='image/jpeg'
        )
        
        # Upload via Django model
        page_content, created = PageContent.objects.get_or_create(
            page='test',
            section='upload_test',
            defaults={
                'title': 'Upload Test',
                'content': 'Testing model upload'
            }
        )
        
        print(f"PageContent {'created' if created else 'found'}")
        
        # Assign image
        page_content.image = uploaded_file
        page_content.save()
        
        print(f"✅ Model upload completed:")
        print(f"  Image field: {page_content.image}")
        print(f"  Image URL: {page_content.image.url}")
        
        # Check if it's a Cloudinary URL
        is_cloudinary_url = 'cloudinary.com' in page_content.image.url
        print(f"  Is Cloudinary URL: {'✅ YES' if is_cloudinary_url else '❌ NO'}")
        
        if is_cloudinary_url:
            # Test URL accessibility
            import requests
            try:
                response = requests.head(page_content.image.url, timeout=10)
                accessible = response.status_code == 200
                print(f"  URL accessible: {'✅ YES' if accessible else f'❌ NO ({response.status_code})'}")
                return accessible
            except Exception as e:
                print(f"  URL test failed: {e}")
                return False
        else:
            return False
        
    except Exception as e:
        print(f"❌ Model upload failed: {e}")
        return False

def check_cloudinary_credentials():
    """Check Cloudinary credentials"""
    print(f"\n🔑 CHECKING CLOUDINARY CREDENTIALS")
    print("=" * 60)
    
    from django.conf import settings
    
    cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', '')
    api_key = getattr(settings, 'CLOUDINARY_API_KEY', '')
    api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', '')
    
    print(f"Cloud name: {cloud_name}")
    print(f"API key: {api_key}")
    print(f"API secret: {'***' if api_secret else 'NOT SET'}")
    
    # Test connection
    try:
        result = cloudinary.api.ping()
        print(f"✅ Connection successful: {result.get('status', 'unknown')}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def main():
    print("🚀 Cloudinary Upload Test")
    print("=" * 80)
    print("Testing why uploads aren't actually going to Cloudinary")
    print()
    
    # Test 1: Check credentials
    creds_ok = check_cloudinary_credentials()
    
    # Test 2: Direct Cloudinary upload
    direct_ok = test_direct_cloudinary_upload()
    
    # Test 3: Django model upload
    model_ok = test_django_model_upload()
    
    # Final diagnosis
    print(f"\n🏥 DIAGNOSIS")
    print("=" * 60)
    
    if not creds_ok:
        print("❌ ISSUE: Cloudinary credentials are invalid")
        print("   FIX: Check CLOUDINARY_* environment variables")
    elif not direct_ok:
        print("❌ ISSUE: Direct Cloudinary uploads are failing")
        print("   FIX: Check Cloudinary account status and API limits")
    elif not model_ok:
        print("❌ ISSUE: Django model uploads aren't reaching Cloudinary")
        print("   FIX: Check Django storage configuration")
    else:
        print("✅ Everything is working correctly!")
    
    print(f"\n📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Cloudinary credentials: {'✅' if creds_ok else '❌'}")
    print(f"Direct Cloudinary upload: {'✅' if direct_ok else '❌'}")
    print(f"Django model upload: {'✅' if model_ok else '❌'}")

if __name__ == "__main__":
    main()
