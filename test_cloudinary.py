#!/usr/bin/env python
"""
Test script to verify Cloudinary configuration
Run this to check if Cloudinary is properly set up
"""

import os
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

def test_cloudinary_config():
    """Test Cloudinary configuration"""
    print("🔍 Testing Cloudinary Configuration...")
    print("=" * 50)
    
    try:
        from django.conf import settings
        import cloudinary
        
        # Check if Cloudinary is in INSTALLED_APPS
        if 'cloudinary' in settings.INSTALLED_APPS:
            print("✅ Cloudinary is in INSTALLED_APPS")
        else:
            print("❌ Cloudinary is NOT in INSTALLED_APPS")
            return False
            
        # Check if cloudinary_storage is in INSTALLED_APPS
        if 'cloudinary_storage' in settings.INSTALLED_APPS:
            print("✅ cloudinary_storage is in INSTALLED_APPS")
        else:
            print("❌ cloudinary_storage is NOT in INSTALLED_APPS")
            return False
        
        # Check Cloudinary configuration
        cloudinary_config = getattr(settings, 'CLOUDINARY_STORAGE', {})
        
        if cloudinary_config.get('CLOUD_NAME'):
            print(f"✅ Cloud Name: {cloudinary_config['CLOUD_NAME']}")
        else:
            print("❌ Cloud Name is missing")
            return False
            
        if cloudinary_config.get('API_KEY'):
            print(f"✅ API Key: {cloudinary_config['API_KEY'][:6]}...")
        else:
            print("❌ API Key is missing")
            return False
            
        if cloudinary_config.get('API_SECRET'):
            print(f"✅ API Secret: {cloudinary_config['API_SECRET'][:6]}...")
        else:
            print("❌ API Secret is missing")
            return False
        
        # Check DEBUG setting
        if settings.DEBUG:
            print("⚠️ DEBUG is True - using local storage")
            print(f"📁 MEDIA_URL: {settings.MEDIA_URL}")
            print(f"📁 MEDIA_ROOT: {settings.MEDIA_ROOT}")
        else:
            print("✅ DEBUG is False - should use Cloudinary")
            print(f"☁️ MEDIA_URL: {settings.MEDIA_URL}")
            
        # Check DEFAULT_FILE_STORAGE
        storage = getattr(settings, 'DEFAULT_FILE_STORAGE', 'default')
        print(f"💾 DEFAULT_FILE_STORAGE: {storage}")
        
        # Test Cloudinary connection
        try:
            result = cloudinary.api.ping()
            print("✅ Cloudinary connection successful!")
            print(f"📊 Status: {result.get('status', 'unknown')}")
            return True
        except Exception as e:
            print(f"❌ Cloudinary connection failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_media_upload():
    """Test media file upload to Cloudinary"""
    print("\n🔍 Testing Media Upload...")
    print("=" * 50)
    
    try:
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.files.storage import default_storage
        
        # Create a simple test file
        test_content = b"This is a test file for Cloudinary upload"
        test_file = SimpleUploadedFile("test.txt", test_content, content_type="text/plain")
        
        # Try to save the file
        file_name = default_storage.save("test_uploads/test.txt", test_file)
        print(f"✅ File uploaded successfully: {file_name}")
        
        # Get the URL
        file_url = default_storage.url(file_name)
        print(f"🔗 File URL: {file_url}")
        
        # Clean up - delete the test file
        if default_storage.exists(file_name):
            default_storage.delete(file_name)
            print("🗑️ Test file cleaned up")
            
        return True
        
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Cloudinary Configuration Test")
    print("=" * 50)
    
    config_ok = test_cloudinary_config()
    
    if config_ok:
        upload_ok = test_media_upload()
        
        if upload_ok:
            print("\n🎉 All tests passed! Cloudinary is working correctly.")
        else:
            print("\n⚠️ Configuration OK but upload failed. Check your credentials.")
    else:
        print("\n❌ Configuration failed. Please check your settings.")
        
    print("\n📝 Next steps:")
    print("1. If tests failed, check your .env file has correct Cloudinary credentials")
    print("2. Make sure DEBUG=False in production")
    print("3. Redeploy your app to Fly.io")
    print("4. Check that existing images are uploaded to Cloudinary")
