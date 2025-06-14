#!/usr/bin/env python
"""
Test upload functionality in production environment
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

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from website.models import PageContent

def test_production_upload():
    """Test upload in production environment"""
    print("🚀 PRODUCTION UPLOAD TEST")
    print("=" * 60)
    
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'Not set')}")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DEFAULT_FILE_STORAGE: {getattr(settings, 'DEFAULT_FILE_STORAGE', 'Not set')}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    print(f"Storage class: {default_storage.__class__.__name__}")
    print(f"Storage module: {default_storage.__class__.__module__}")
    
    # Check if it's Cloudinary
    is_cloudinary = 'cloudinary' in default_storage.__class__.__module__.lower()
    print(f"Is Cloudinary storage: {'✅ YES' if is_cloudinary else '❌ NO'}")
    
    if not is_cloudinary:
        print("❌ Production is not using Cloudinary storage!")
        return False
    
    try:
        # Create test image
        img = Image.new('RGB', (200, 200), color='purple')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # Create uploaded file
        uploaded_file = SimpleUploadedFile(
            name='production_test.jpg',
            content=img_io.getvalue(),
            content_type='image/jpeg'
        )
        
        # Test direct storage upload
        print(f"\n📤 Testing direct storage upload...")
        file_path = default_storage.save('test_production/direct_upload.jpg', uploaded_file)
        file_url = default_storage.url(file_path)
        
        print(f"✅ Direct upload successful:")
        print(f"  File path: {file_path}")
        print(f"  File URL: {file_url}")
        
        # Check if it's a Cloudinary URL
        is_cloudinary_url = 'cloudinary.com' in file_url
        print(f"  Is Cloudinary URL: {'✅ YES' if is_cloudinary_url else '❌ NO'}")
        
        # Test model upload
        print(f"\n📋 Testing model upload...")
        
        # Reset the uploaded file
        img_io.seek(0)
        uploaded_file2 = SimpleUploadedFile(
            name='production_model_test.jpg',
            content=img_io.getvalue(),
            content_type='image/jpeg'
        )
        
        # Create or update PageContent
        page_content, created = PageContent.objects.get_or_create(
            page='production',
            section='test',
            defaults={
                'title': 'Production Test',
                'content': 'Testing production upload'
            }
        )
        
        page_content.image = uploaded_file2
        page_content.save()
        
        print(f"✅ Model upload successful:")
        print(f"  Image field: {page_content.image}")
        print(f"  Image URL: {page_content.image.url}")
        
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
        print(f"❌ Upload test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_production_upload()
    
    print(f"\n📊 RESULT")
    print("=" * 60)
    
    if success:
        print("🎉 PRODUCTION UPLOAD TEST PASSED!")
        print("✅ Cloudinary storage is working correctly")
        print("✅ New uploads will go to Cloudinary")
        print("✅ Images are accessible via Cloudinary URLs")
    else:
        print("❌ PRODUCTION UPLOAD TEST FAILED!")
        print("🔧 Check the issues above")
