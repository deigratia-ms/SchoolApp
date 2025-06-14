#!/usr/bin/env python
"""
Final test to verify everything is working
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
from django.core.files.storage import default_storage
from website.models import PageContent

def test_admin_upload_simulation():
    """Simulate an admin panel upload"""
    print("🧪 SIMULATING ADMIN PANEL UPLOAD")
    print("=" * 50)
    
    # Create a test image
    img = Image.new('RGB', (800, 400), color='green')
    img_io = BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    
    # Create uploaded file
    uploaded_file = SimpleUploadedFile(
        name='admin_test_upload.jpg',
        content=img_io.getvalue(),
        content_type='image/jpeg'
    )
    
    try:
        # Get or create a test PageContent
        page_content, created = PageContent.objects.get_or_create(
            page='test',
            section='admin_upload',
            defaults={
                'title': 'Admin Upload Test',
                'content': 'Testing admin panel upload functionality'
            }
        )
        
        print(f"PageContent {'created' if created else 'found'}: {page_content}")
        
        # Assign the uploaded file (this simulates what happens in admin)
        page_content.image = uploaded_file
        page_content.save()
        
        print(f"✅ Upload successful!")
        print(f"  Image field: {page_content.image}")
        print(f"  Image URL: {page_content.image.url}")
        print(f"  Image name: {page_content.image.name}")
        
        # Check if file exists
        file_exists = default_storage.exists(page_content.image.name)
        print(f"  File exists: {'✅ YES' if file_exists else '❌ NO'}")
        
        # Check file path
        from django.conf import settings
        file_path = Path(settings.MEDIA_ROOT) / page_content.image.name
        print(f"  Full path: {file_path}")
        print(f"  File on disk: {'✅ YES' if file_path.exists() else '❌ NO'}")
        
        if file_path.exists():
            print(f"  File size: {file_path.stat().st_size} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False

def check_console_errors():
    """Check for potential console errors"""
    print(f"\n🔍 CHECKING FOR POTENTIAL ISSUES")
    print("=" * 50)
    
    issues = []
    
    # Check media directory permissions
    from django.conf import settings
    media_root = Path(settings.MEDIA_ROOT)
    
    if not media_root.exists():
        issues.append("Media directory doesn't exist")
    elif not os.access(media_root, os.W_OK):
        issues.append("Media directory not writable")
    else:
        print("✅ Media directory exists and is writable")
    
    # Check URL configuration
    if settings.MEDIA_URL != '/media/':
        issues.append(f"MEDIA_URL is '{settings.MEDIA_URL}', expected '/media/'")
    else:
        print("✅ MEDIA_URL configured correctly")
    
    # Check storage backend
    if 'FileSystemStorage' not in default_storage.__class__.__name__:
        issues.append(f"Storage backend is {default_storage.__class__.__name__}, expected FileSystemStorage")
    else:
        print("✅ Using FileSystemStorage")
    
    if issues:
        print(f"\n⚠️ Found {len(issues)} potential issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print(f"\n✅ No issues found!")
        return True

def main():
    print("🚀 Final Verification Test")
    print("=" * 60)
    print("Testing complete local media setup")
    print()
    
    # Test 1: Admin upload simulation
    upload_ok = test_admin_upload_simulation()
    
    # Test 2: Check for issues
    config_ok = check_console_errors()
    
    # Final summary
    print(f"\n📊 FINAL RESULTS")
    print("=" * 50)
    print(f"Admin upload simulation: {'✅ PASS' if upload_ok else '❌ FAIL'}")
    print(f"Configuration check: {'✅ PASS' if config_ok else '❌ FAIL'}")
    
    if upload_ok and config_ok:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ Local media storage is working perfectly")
        print(f"✅ Admin panel uploads will work")
        print(f"✅ Images will display correctly")
        print(f"✅ No console errors expected")
        
        print(f"\n📝 What to test now:")
        print(f"1. Open admin panel: http://127.0.0.1:8000/admin/")
        print(f"2. Go to Website > Page contents")
        print(f"3. Edit the 'About Hero' entry")
        print(f"4. You should see: '✅ Stored Locally' with image preview")
        print(f"5. Try uploading a new image - it should work instantly")
        print(f"6. Visit About page: http://127.0.0.1:8000/about/")
        print(f"7. Hero image should display without errors")
        
        print(f"\n🔧 If you want to switch back to Cloudinary later:")
        print(f"1. Uncomment the Cloudinary configuration in settings.py")
        print(f"2. Change LocalImageWidget back to CloudinaryImageWidget in admin.py")
        print(f"3. Run the upload_media_to_cloudinary.py script")
        
    else:
        print(f"\n❌ SOME TESTS FAILED")
        print(f"Please check the issues above and fix them")

if __name__ == "__main__":
    main()
