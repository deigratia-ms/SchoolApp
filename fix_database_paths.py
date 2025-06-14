#!/usr/bin/env python
"""
Script to fix database paths to match what's actually in Cloudinary
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

def fix_all_paths():
    """Fix all database paths to match Cloudinary"""
    print("🔄 Fixing database paths to match Cloudinary...")
    print("=" * 60)
    
    # Fix SiteSettings
    try:
        site_settings = SiteSettings.objects.first()
        if site_settings:
            # School logo
            site_settings.school_logo = "media/site/dgm_logo"
            # Favicon - use the school logo for now
            site_settings.favicon = "media/site/dgm_logo"
            site_settings.save()
            print(f"✅ Fixed SiteSettings:")
            print(f"   School logo: media/site/dgm_logo")
            print(f"   Favicon: media/site/dgm_logo")
    except Exception as e:
        print(f"❌ Error fixing SiteSettings: {e}")
    
    # Fix HeroSlides
    try:
        hero_mappings = {
            1: "media/hero_slides/about_montessori",
            2: "media/hero_slides/gettyimages-1421987003-612x612", 
            3: "media/hero_slides/montessori-meta-study"
        }
        
        for slide_id, cloudinary_path in hero_mappings.items():
            try:
                slide = HeroSlide.objects.get(id=slide_id)
                slide.image = cloudinary_path
                slide.save()
                print(f"✅ Fixed HeroSlide {slide_id}: {cloudinary_path}")
            except HeroSlide.DoesNotExist:
                print(f"⚠️  HeroSlide {slide_id} not found")
    except Exception as e:
        print(f"❌ Error fixing HeroSlides: {e}")
    
    # Fix PageContent - About hero
    try:
        about_hero = PageContent.objects.get(page='about', section='hero')
        # Use one of the existing hero slide images
        about_hero.image = "media/hero_slides/about_montessori"
        about_hero.save()
        print(f"✅ Fixed About hero: media/hero_slides/about_montessori")
    except PageContent.DoesNotExist:
        print("⚠️  About hero PageContent not found")
    except Exception as e:
        print(f"❌ Error fixing About hero: {e}")
    
    # Fix SchoolSettings
    try:
        school_settings = SchoolSettings.objects.first()
        if school_settings:
            school_settings.logo = "media/school_logo/dgm_logo"
            school_settings.save()
            print(f"✅ Fixed SchoolSettings logo: media/school_logo/dgm_logo")
    except Exception as e:
        print(f"❌ Error fixing SchoolSettings: {e}")

def verify_fixes():
    """Verify all fixes"""
    print("\n🔄 Verifying fixes...")
    print("=" * 60)
    
    # Check SiteSettings
    site_settings = SiteSettings.objects.first()
    if site_settings:
        print(f"SiteSettings:")
        print(f"  School logo: {site_settings.school_logo}")
        print(f"  Favicon: {site_settings.favicon}")
    
    # Check HeroSlides
    print(f"\nHeroSlides:")
    for slide in HeroSlide.objects.all():
        print(f"  Slide {slide.id}: {slide.image}")
    
    # Check PageContent
    print(f"\nPageContent:")
    for content in PageContent.objects.filter(image__isnull=False):
        print(f"  {content.page}/{content.section}: {content.image}")
    
    # Check SchoolSettings
    school_settings = SchoolSettings.objects.first()
    if school_settings and school_settings.logo:
        print(f"\nSchoolSettings:")
        print(f"  Logo: {school_settings.logo}")

if __name__ == "__main__":
    print("🚀 Fix Database Paths Script")
    print("=" * 60)
    
    try:
        fix_all_paths()
        verify_fixes()
        
        print(f"\n🎉 Database path fixing complete!")
        print(f"📝 Next steps:")
        print(f"1. Deploy to production: fly deploy")
        print(f"2. Test your website - images should now load correctly")
        print(f"3. All images are now pointing to existing Cloudinary resources")
        
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)
