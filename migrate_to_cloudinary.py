#!/usr/bin/env python
"""
Migrate existing local media files to Cloudinary and update database records
"""

import os
import sys
from pathlib import Path
import django

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

# Force production environment to use Cloudinary
os.environ['DEBUG'] = 'False'
os.environ['ENVIRONMENT'] = 'production'

django.setup()

from django.conf import settings
from website.models import PageContent, SiteSettings, HeroSlide
from users.models import SchoolSettings
import cloudinary
import cloudinary.uploader

def upload_local_file_to_cloudinary(local_path):
    """Upload a local file to Cloudinary and return the public_id"""
    try:
        # Get the full path
        full_path = Path(settings.MEDIA_ROOT) / local_path
        
        if not full_path.exists():
            print(f"  ❌ File not found: {full_path}")
            return None
        
        # Extract directory and filename for public_id
        # e.g., "hero_slides/test_hero.jpg" -> public_id: "hero_slides/test_hero"
        public_id = str(local_path).replace('\\', '/').rsplit('.', 1)[0]
        
        print(f"  📤 Uploading {local_path} to Cloudinary...")
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            str(full_path),
            public_id=public_id,
            overwrite=True,
            resource_type='image'
        )
        
        print(f"  ✅ Uploaded successfully: {result['secure_url']}")
        return public_id
        
    except Exception as e:
        print(f"  ❌ Upload failed for {local_path}: {e}")
        return None

def migrate_page_content():
    """Migrate PageContent images"""
    print("📋 MIGRATING PAGE CONTENT IMAGES")
    print("=" * 50)
    
    page_contents = PageContent.objects.filter(image__isnull=False).exclude(image='')
    
    for content in page_contents:
        print(f"\n🔍 Processing: {content.page}/{content.section}")
        print(f"  Current image: {content.image}")
        
        # Check if it's already a Cloudinary URL
        if 'cloudinary.com' in str(content.image.url):
            print(f"  ✅ Already using Cloudinary")
            continue
        
        # Upload to Cloudinary
        public_id = upload_local_file_to_cloudinary(content.image.name)
        
        if public_id:
            # Update the database record
            content.image = public_id
            content.save()
            print(f"  ✅ Database updated with Cloudinary URL")
        else:
            print(f"  ❌ Failed to migrate this image")

def migrate_site_settings():
    """Migrate SiteSettings images"""
    print(f"\n🏫 MIGRATING SITE SETTINGS IMAGES")
    print("=" * 50)
    
    try:
        site_settings = SiteSettings.objects.first()
        if not site_settings:
            print("  ⚠️ No SiteSettings found")
            return
        
        # Migrate school logo
        if site_settings.school_logo:
            print(f"\n🔍 Processing school logo: {site_settings.school_logo}")
            
            if 'cloudinary.com' not in str(site_settings.school_logo.url):
                public_id = upload_local_file_to_cloudinary(site_settings.school_logo.name)
                if public_id:
                    site_settings.school_logo = public_id
                    print(f"  ✅ School logo migrated")
            else:
                print(f"  ✅ School logo already using Cloudinary")
        
        # Migrate footer logo
        if site_settings.footer_logo:
            print(f"\n🔍 Processing footer logo: {site_settings.footer_logo}")
            
            if 'cloudinary.com' not in str(site_settings.footer_logo.url):
                public_id = upload_local_file_to_cloudinary(site_settings.footer_logo.name)
                if public_id:
                    site_settings.footer_logo = public_id
                    print(f"  ✅ Footer logo migrated")
            else:
                print(f"  ✅ Footer logo already using Cloudinary")
        
        # Migrate favicon
        if site_settings.favicon:
            print(f"\n🔍 Processing favicon: {site_settings.favicon}")
            
            if 'cloudinary.com' not in str(site_settings.favicon.url):
                public_id = upload_local_file_to_cloudinary(site_settings.favicon.name)
                if public_id:
                    site_settings.favicon = public_id
                    print(f"  ✅ Favicon migrated")
            else:
                print(f"  ✅ Favicon already using Cloudinary")
        
        # Save all changes
        site_settings.save()
        print(f"  ✅ SiteSettings saved")
        
    except Exception as e:
        print(f"  ❌ Error migrating SiteSettings: {e}")

def migrate_hero_slides():
    """Migrate HeroSlide images"""
    print(f"\n🎭 MIGRATING HERO SLIDES")
    print("=" * 50)
    
    hero_slides = HeroSlide.objects.filter(image__isnull=False).exclude(image='')
    
    for slide in hero_slides:
        print(f"\n🔍 Processing hero slide: {slide.title}")
        print(f"  Current image: {slide.image}")
        
        # Check if it's already a Cloudinary URL
        if 'cloudinary.com' in str(slide.image.url):
            print(f"  ✅ Already using Cloudinary")
            continue
        
        # Upload to Cloudinary
        public_id = upload_local_file_to_cloudinary(slide.image.name)
        
        if public_id:
            # Update the database record
            slide.image = public_id
            slide.save()
            print(f"  ✅ Database updated with Cloudinary URL")
        else:
            print(f"  ❌ Failed to migrate this image")

def test_cloudinary_connection():
    """Test Cloudinary connection"""
    print("🔧 TESTING CLOUDINARY CONNECTION")
    print("=" * 50)
    
    try:
        # Test connection
        result = cloudinary.api.ping()
        print(f"✅ Cloudinary connection successful!")
        print(f"📊 Status: {result.get('status', 'unknown')}")
        
        # Show configuration
        print(f"\n📋 Configuration:")
        print(f"  Cloud name: {settings.CLOUDINARY_STORAGE['CLOUD_NAME']}")
        print(f"  API key: {settings.CLOUDINARY_STORAGE['API_KEY']}")
        print(f"  Storage configured: {getattr(settings, 'CLOUDINARY_CONFIGURED', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cloudinary connection failed: {e}")
        return False

def main():
    print("🚀 Cloudinary Migration Script")
    print("=" * 60)
    print("This script will migrate local media files to Cloudinary")
    print()
    
    # Test connection first
    if not test_cloudinary_connection():
        print("❌ Cannot proceed without Cloudinary connection")
        return
    
    print()
    
    # Migrate different types of content
    migrate_page_content()
    migrate_site_settings()
    migrate_hero_slides()
    
    print(f"\n🎉 MIGRATION COMPLETE!")
    print("=" * 50)
    print("✅ All local images have been migrated to Cloudinary")
    print("✅ Database records updated with Cloudinary URLs")
    print("✅ Your website should now display images correctly")
    
    print(f"\n📝 Next steps:")
    print("1. Deploy the updated code: fly deploy")
    print("2. Check your website: https://deigratiams.edu.gh/")
    print("3. Test admin panel uploads")
    print("4. Verify all images load correctly")

if __name__ == "__main__":
    main()
