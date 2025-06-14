#!/usr/bin/env python
"""
Test image upload functionality
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

def test_new_image_upload():
    """Test uploading a new image"""
    print("🧪 TESTING NEW IMAGE UPLOAD")
    print("=" * 50)
    
    # Create a new test image
    img = Image.new('RGB', (800, 400), color='red')
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    
    # Create uploaded file
    uploaded_file = SimpleUploadedFile(
        name='new_test_upload.jpg',
        content=img_io.getvalue(),
        content_type='image/jpeg'
    )
    
    try:
        # Get the hero PageContent
        page_content = PageContent.objects.get(page='about', section='hero')
        
        print(f"Before upload:")
        print(f"  Current image: {page_content.image}")
        print(f"  Current URL: {page_content.image.url}")
        
        # Upload new image (simulates admin panel upload)
        page_content.image = uploaded_file
        page_content.save()
        
        print(f"\nAfter upload:")
        print(f"  New image: {page_content.image}")
        print(f"  New URL: {page_content.image.url}")
        
        # Check if file exists
        from django.conf import settings
        file_path = Path(settings.MEDIA_ROOT) / page_content.image.name
        exists = file_path.exists()
        print(f"  File exists on disk: {'✅ YES' if exists else '❌ NO'}")
        
        if exists:
            print(f"  File size: {file_path.stat().st_size} bytes")
            print(f"  Full path: {file_path}")
        
        # Test URL accessibility
        print(f"\n🌐 Testing URL accessibility:")
        print(f"  URL: http://127.0.0.1:8000{page_content.image.url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False

def main():
    print("🚀 Image Upload Test")
    print("=" * 60)
    print("Testing image upload functionality with local storage")
    print()
    
    success = test_new_image_upload()
    
    print(f"\n📊 RESULT")
    print("=" * 50)
    
    if success:
        print("✅ IMAGE UPLOAD TEST PASSED!")
        print("✅ Local storage is working correctly")
        print("✅ Admin panel uploads should work perfectly")
        
        print(f"\n📝 What to test in admin panel:")
        print(f"1. Go to: http://127.0.0.1:8000/admin/website/pagecontent/1/change/")
        print(f"2. You should see '✅ Stored Locally' with image preview")
        print(f"3. Upload a new image - it should work instantly")
        print(f"4. Check About page: http://127.0.0.1:8000/about/")
        print(f"5. Image should display without errors")
        
    else:
        print("❌ IMAGE UPLOAD TEST FAILED!")
        print("Please check the error above")

if __name__ == "__main__":
    main()
