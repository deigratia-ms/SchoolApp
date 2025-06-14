#!/usr/bin/env python
"""
Script to fix Cloudinary image paths in the database
This will update database records to use correct Cloudinary paths
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

from website.models import PageContent, SiteSettings, HeroSlide
from users.models import SchoolSettings
import cloudinary.api

def fix_site_settings():
    """Fix SiteSettings image paths"""
    print("🔄 Fixing SiteSettings image paths...")
    print("=" * 50)
    
    try:
        site_settings = SiteSettings.objects.first()
        if site_settings:
            # Fix school logo path
            if site_settings.school_logo and 'media/' in str(site_settings.school_logo):
                old_path = str(site_settings.school_logo)
                # Remove 'media/' prefix for Cloudinary
                new_path = old_path.replace('media/', '')
                site_settings.school_logo = new_path
                site_settings.save()
                print(f"✅ Fixed school logo: {old_path} -> {new_path}")
            
            # Check favicon
            if site_settings.favicon:
                print(f"✅ Favicon path looks good: {site_settings.favicon}")
            else:
                print("ℹ️  No favicon set")
                
        else:
            print("❌ No SiteSettings found")
            
    except Exception as e:
        print(f"❌ Error fixing SiteSettings: {e}")

def fix_hero_slides():
    """Fix HeroSlide image paths"""
    print("\n🔄 Fixing HeroSlide image paths...")
    print("=" * 50)
    
    try:
        for slide in HeroSlide.objects.all():
            if slide.image and 'media/' in str(slide.image):
                old_path = str(slide.image)
                # Remove 'media/' prefix for Cloudinary
                new_path = old_path.replace('media/', '')
                slide.image = new_path
                slide.save()
                print(f"✅ Fixed hero slide {slide.id}: {old_path} -> {new_path}")
            else:
                print(f"✅ Hero slide {slide.id} path looks good: {slide.image}")
                
    except Exception as e:
        print(f"❌ Error fixing HeroSlides: {e}")

def fix_page_content():
    """Fix PageContent image paths"""
    print("\n🔄 Fixing PageContent image paths...")
    print("=" * 50)
    
    try:
        for content in PageContent.objects.filter(image__isnull=False):
            if content.image and 'media/' in str(content.image):
                old_path = str(content.image)
                # Remove 'media/' prefix for Cloudinary
                new_path = old_path.replace('media/', '')
                content.image = new_path
                content.save()
                print(f"✅ Fixed {content.page}/{content.section}: {old_path} -> {new_path}")
            else:
                print(f"✅ {content.page}/{content.section} path looks good: {content.image}")
                
    except Exception as e:
        print(f"❌ Error fixing PageContent: {e}")

def fix_school_settings():
    """Fix SchoolSettings image paths"""
    print("\n🔄 Fixing SchoolSettings image paths...")
    print("=" * 50)
    
    try:
        school_settings = SchoolSettings.objects.first()
        if school_settings and school_settings.logo:
            if 'media/' in str(school_settings.logo):
                old_path = str(school_settings.logo)
                # Remove 'media/' prefix for Cloudinary
                new_path = old_path.replace('media/', '')
                school_settings.logo = new_path
                school_settings.save()
                print(f"✅ Fixed school settings logo: {old_path} -> {new_path}")
            else:
                print(f"✅ School settings logo path looks good: {school_settings.logo}")
        else:
            print("ℹ️  No SchoolSettings logo found")
            
    except Exception as e:
        print(f"❌ Error fixing SchoolSettings: {e}")

def verify_cloudinary_images():
    """Verify that images exist in Cloudinary"""
    print("\n🔄 Verifying images exist in Cloudinary...")
    print("=" * 50)
    
    try:
        # Get all unique image paths from database
        image_paths = set()
        
        # From SiteSettings
        site_settings = SiteSettings.objects.first()
        if site_settings:
            if site_settings.school_logo:
                image_paths.add(str(site_settings.school_logo))
            if site_settings.favicon:
                image_paths.add(str(site_settings.favicon))
        
        # From PageContent
        for content in PageContent.objects.filter(image__isnull=False):
            image_paths.add(str(content.image))
        
        # From HeroSlides
        for slide in HeroSlide.objects.all():
            if slide.image:
                image_paths.add(str(slide.image))
        
        # From SchoolSettings
        school_settings = SchoolSettings.objects.first()
        if school_settings and school_settings.logo:
            image_paths.add(str(school_settings.logo))
        
        print(f"Found {len(image_paths)} unique image paths to verify:")
        
        for path in sorted(image_paths):
            # Remove file extension for public_id
            public_id = path.rsplit('.', 1)[0] if '.' in path else path
            try:
                result = cloudinary.api.resource(public_id)
                print(f"✅ {path} -> {result['secure_url']}")
            except Exception as e:
                print(f"❌ {path} -> Not found in Cloudinary: {e}")
                
    except Exception as e:
        print(f"❌ Error verifying Cloudinary images: {e}")

if __name__ == "__main__":
    print("🚀 Fix Cloudinary Paths Script")
    print("=" * 50)
    
    try:
        # Fix all image paths
        fix_site_settings()
        fix_hero_slides()
        fix_page_content()
        fix_school_settings()
        
        # Verify images exist in Cloudinary
        verify_cloudinary_images()
        
        print(f"\n🎉 Cloudinary path fixing complete!")
        print(f"📝 Next steps:")
        print(f"1. Deploy to production: fly deploy")
        print(f"2. Test your website to see if images are now loading")
        print(f"3. Upload any missing images through the admin panel")
        
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)
