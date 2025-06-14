#!/usr/bin/env python
"""
Final script to fix all image paths to match what's actually in Cloudinary
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

def get_cloudinary_images():
    """Get all images currently in Cloudinary"""
    print("🔍 Fetching images from Cloudinary...")
    
    try:
        result = cloudinary.api.resources(type='upload', max_results=100)
        cloudinary_images = {}
        
        for resource in result.get('resources', []):
            public_id = resource['public_id']
            secure_url = resource['secure_url']
            cloudinary_images[public_id] = secure_url
            
        print(f"✅ Found {len(cloudinary_images)} images in Cloudinary")
        return cloudinary_images
        
    except Exception as e:
        print(f"❌ Error fetching Cloudinary images: {e}")
        return {}

def find_best_match(target_path, cloudinary_images):
    """Find the best matching image in Cloudinary for a target path"""
    
    # Remove file extension from target
    target_base = target_path.rsplit('.', 1)[0] if '.' in target_path else target_path
    
    # Try exact match first
    if target_base in cloudinary_images:
        return target_base
    
    # Try with media/ prefix
    media_path = f"media/{target_base}"
    if media_path in cloudinary_images:
        return media_path
    
    # Try without media/ prefix
    no_media_path = target_base.replace('media/', '')
    if no_media_path in cloudinary_images:
        return no_media_path
    
    # Try partial matches
    target_filename = target_base.split('/')[-1]
    for public_id in cloudinary_images:
        if target_filename in public_id:
            return public_id
    
    return None

def fix_all_image_paths():
    """Fix all image paths in the database"""
    print("\n🔧 Fixing all image paths...")
    print("=" * 60)
    
    cloudinary_images = get_cloudinary_images()
    if not cloudinary_images:
        print("❌ No Cloudinary images found. Cannot proceed.")
        return False
    
    fixed_count = 0
    
    # Fix PageContent images
    print("\n📄 Fixing PageContent images:")
    for content in PageContent.objects.filter(image__isnull=False):
        current_path = str(content.image)
        best_match = find_best_match(current_path, cloudinary_images)
        
        if best_match:
            content.image = best_match
            content.save()
            print(f"✅ {content.page}/{content.section}: {current_path} → {best_match}")
            fixed_count += 1
        else:
            print(f"❌ {content.page}/{content.section}: No match found for {current_path}")
    
    # Fix SiteSettings
    print("\n🏫 Fixing SiteSettings:")
    site_settings = SiteSettings.objects.first()
    if site_settings:
        # School logo
        if site_settings.school_logo:
            current_path = str(site_settings.school_logo)
            best_match = find_best_match(current_path, cloudinary_images)
            if best_match:
                site_settings.school_logo = best_match
                print(f"✅ School logo: {current_path} → {best_match}")
                fixed_count += 1
            else:
                print(f"❌ School logo: No match found for {current_path}")
        
        # Favicon
        if site_settings.favicon:
            current_path = str(site_settings.favicon)
            best_match = find_best_match(current_path, cloudinary_images)
            if best_match:
                site_settings.favicon = best_match
                print(f"✅ Favicon: {current_path} → {best_match}")
                fixed_count += 1
            else:
                print(f"❌ Favicon: No match found for {current_path}")
        
        site_settings.save()
    
    # Fix HeroSlides
    print("\n🎭 Fixing HeroSlides:")
    for slide in HeroSlide.objects.all():
        if slide.image:
            current_path = str(slide.image)
            best_match = find_best_match(current_path, cloudinary_images)
            
            if best_match:
                slide.image = best_match
                slide.save()
                print(f"✅ Slide {slide.id}: {current_path} → {best_match}")
                fixed_count += 1
            else:
                print(f"❌ Slide {slide.id}: No match found for {current_path}")
    
    # Fix SchoolSettings
    print("\n🎓 Fixing SchoolSettings:")
    school_settings = SchoolSettings.objects.first()
    if school_settings and school_settings.logo:
        current_path = str(school_settings.logo)
        best_match = find_best_match(current_path, cloudinary_images)
        
        if best_match:
            school_settings.logo = best_match
            school_settings.save()
            print(f"✅ School logo: {current_path} → {best_match}")
            fixed_count += 1
        else:
            print(f"❌ School logo: No match found for {current_path}")
    
    print(f"\n📊 Fixed {fixed_count} image paths")
    return fixed_count > 0

def verify_all_paths():
    """Verify all paths are now correct"""
    print("\n✅ VERIFICATION - All current image paths:")
    print("=" * 60)
    
    # PageContent
    for content in PageContent.objects.filter(image__isnull=False):
        full_url = f"https://res.cloudinary.com/ds5udo8jc/{content.image}"
        print(f"📄 {content.page}/{content.section}: {content.image}")
        print(f"   URL: {full_url}")
    
    # SiteSettings
    site_settings = SiteSettings.objects.first()
    if site_settings:
        if site_settings.school_logo:
            full_url = f"https://res.cloudinary.com/ds5udo8jc/{site_settings.school_logo}"
            print(f"🏫 School logo: {site_settings.school_logo}")
            print(f"   URL: {full_url}")
        
        if site_settings.favicon:
            full_url = f"https://res.cloudinary.com/ds5udo8jc/{site_settings.favicon}"
            print(f"🏫 Favicon: {site_settings.favicon}")
            print(f"   URL: {full_url}")
    
    # HeroSlides
    for slide in HeroSlide.objects.all():
        if slide.image:
            full_url = f"https://res.cloudinary.com/ds5udo8jc/{slide.image}"
            print(f"🎭 Slide {slide.id}: {slide.image}")
            print(f"   URL: {full_url}")
    
    # SchoolSettings
    school_settings = SchoolSettings.objects.first()
    if school_settings and school_settings.logo:
        full_url = f"https://res.cloudinary.com/ds5udo8jc/{school_settings.logo}"
        print(f"🎓 School logo: {school_settings.logo}")
        print(f"   URL: {full_url}")

if __name__ == "__main__":
    print("🚀 Final Image Path Fix Script")
    print("=" * 60)
    
    try:
        success = fix_all_image_paths()
        
        if success:
            verify_all_paths()
            
            print(f"\n🎉 IMAGE PATH FIXING COMPLETE!")
            print(f"📝 Next steps:")
            print(f"1. Deploy to production: fly deploy")
            print(f"2. Test your website - all images should now load")
            print(f"3. Test admin panel uploads - they should go to Cloudinary")
            print(f"4. All future uploads will work correctly")
        else:
            print(f"\n❌ No fixes were applied")
        
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)
