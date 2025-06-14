#!/usr/bin/env python
"""
Script to fix Cloudinary URLs in the database
This will update the database records to use the correct Cloudinary URLs
"""

import os
import sys
from pathlib import Path
import django

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

# Set production environment
os.environ['DEBUG'] = 'False'
os.environ['ENVIRONMENT'] = 'production'

django.setup()

from django.conf import settings
from users.models import SchoolSettings, HeroSlide, Gallery, Staff, Event, Announcement, AcademicProgram, PageContent
from users.models import

def fix_site_settings():
    """Fix SchoolSettings image URLs"""
    print("🔄 Fixing SchoolSettings image URLs...")
    
    try:
        site_settings = SchoolSettings.objects.first()
        if site_settings:
            # Update school logo
            if site_settings.logo:
                # Use the uploaded logo from Cloudinary
                site_settings.logo = 'media/site/dgm_logo.png'
                print(f"✅ Updated SchoolSettings school_logo")
            
            site_settings.save()
            print(f"✅ SchoolSettings updated successfully")
            return True
    except Exception as e:
        print(f"❌ Error updating SchoolSettings: {e}")
        return False

def fix_school_settings():
    """Fix SchoolSettings logo URL"""
    print("🔄 Fixing SchoolSettings logo URL...")
    
    try:
        from users.models import SchoolSettings

        school_settings = SchoolSettings.objects.first()
        if school_settings:
            # Update logo
            if school_settings.logo:
                # Use the uploaded logo from Cloudinary
                school_settings.logo = 'media/school_logo/dgm_logo.png'
                print(f"✅ Updated SchoolSettings logo")
            
            school_settings.save()
            print(f"✅ SchoolSettings updated successfully")
            return True
    except Exception as e:
        print(f"❌ Error updating SchoolSettings: {e}")
        return False

def fix_hero_slides():
    """Fix HeroSlide image URLs"""
    print("🔄 Fixing HeroSlide image URLs...")
    
    updated_count = 0
    try:
        hero_slides = HeroSlide.objects.all()
        for slide in hero_slides:
            if slide.image:
                # Map to the uploaded images
                if 'about_montessori' in str(slide.image):
                    slide.image = 'media/hero_slides/about_montessori.jpg'
                    updated_count += 1
                elif 'gettyimages' in str(slide.image):
                    slide.image = 'media/hero_slides/gettyimages-1421987003-612x612.jpg'
                    updated_count += 1
                elif 'montessori-meta-study' in str(slide.image):
                    slide.image = 'media/hero_slides/montessori-meta-study.webp'
                    updated_count += 1
                
                slide.save()
        
        print(f"✅ Updated {updated_count} HeroSlide images")
        return True
    except Exception as e:
        print(f"❌ Error updating HeroSlides: {e}")
        return False

def test_cloudinary_urls():
    """Test if Cloudinary URLs are working"""
    print("🔄 Testing Cloudinary URLs...")
    
    test_urls = [
        'https://res.cloudinary.com/ds5udo8jc/image/upload/v1749684011/media/site/dgm_logo.png',
        'https://res.cloudinary.com/ds5udo8jc/image/upload/v1749684006/media/school_logo/dgm_logo.png',
        'https://res.cloudinary.com/ds5udo8jc/image/upload/v1749683993/media/hero_slides/about_montessori.jpg',
    ]
    
    try:
        import requests
        for url in test_urls:
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {url} - OK")
            else:
                print(f"❌ {url} - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing URLs: {e}")

def create_or_update_site_settings():
    """Create or update site settings with proper Cloudinary URLs"""
    print("🔄 Creating/updating site settings...")
    
    try:
        site_settings, created = SchoolSettings.objects.get_or_create(
            defaults={
                'contact_email': 'info@deigratiamontessori.edu.gh',
                'contact_phone': '+233 123 456 789',
                'address': 'Accra, Ghana',
                'about_text': 'Deigratia Montessori School is committed to providing quality education through the Montessori method.',
                'mission_statement': 'To nurture and develop each child\'s potential through innovative Montessori education.',
                'school_logo': 'media/site/dgm_logo.png',
            }
        )
        
        # Update the logo if it's not set correctly
        if not site_settings.logo or 'cloudinary' not in str(site_settings.logo):
            site_settings.logo = 'media/site/dgm_logo.png'
            site_settings.save()
        
        if created:
            print("✅ Created new SchoolSettings")
        else:
            print("✅ Updated existing SchoolSettings")
            
        return True
    except Exception as e:
        print(f"❌ Error creating/updating SchoolSettings: {e}")
        return False

def create_or_update_school_settings():
    """Create or update school settings with proper Cloudinary URLs"""
    print("🔄 Creating/updating school settings...")
    
    try:
        school_settings, created = SchoolSettings.objects.get_or_create(
            defaults={
                'school_name': 'Deigratia Montessori School',
                'logo': 'media/school_logo/dgm_logo.png',
                'address': 'Accra, Ghana',
                'phone': '+233 123 456 789',
                'email': 'info@deigratiamontessori.edu.gh',
            }
        )
        
        # Update the logo if it's not set correctly
        if not school_settings.logo or 'cloudinary' not in str(school_settings.logo):
            school_settings.logo = 'media/school_logo/dgm_logo.png'
            school_settings.save()
        
        if created:
            print("✅ Created new SchoolSettings")
        else:
            print("✅ Updated existing SchoolSettings")
            
        return True
    except Exception as e:
        print(f"❌ Error creating/updating SchoolSettings: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Cloudinary URL Fix Script")
    print("=" * 50)
    
    # Test Cloudinary URLs first
    test_cloudinary_urls()
    
    print("\n" + "=" * 50)
    
    # Fix/create settings
    site_success = create_or_update_site_settings()
    school_success = create_or_update_school_settings()
    
    # Fix hero slides
    hero_success = fix_hero_slides()
    
    print(f"\n🎉 Summary:")
    print(f"✅ SchoolSettings: {'Success' if site_success else 'Failed'}")
    print(f"✅ SchoolSettings: {'Success' if school_success else 'Failed'}")
    print(f"✅ HeroSlides: {'Success' if hero_success else 'Failed'}")
    
    if site_success and school_success:
        print(f"\n📝 Next steps:")
        print(f"1. Your images should now be loading from Cloudinary")
        print(f"2. Check your website: https://deigratia-school.fly.dev")
        print(f"3. Check the admin panel for the logo")
        print(f"4. If images still don't load, check the browser console for errors")
    else:
        print(f"\n⚠️ Some updates failed. Check the errors above.")
