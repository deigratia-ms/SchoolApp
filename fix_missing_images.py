#!/usr/bin/env python
"""
Script to fix missing image references in the database
This will update database records to use existing images from Cloudinary
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

from website.models import PageContent, HeroSlide
import cloudinary
import cloudinary.api

def fix_missing_hero_images():
    """Fix missing hero images by using existing ones"""
    print("🔄 Fixing missing hero images...")
    print("=" * 50)
    
    # Get the problematic About page hero section
    try:
        about_hero = PageContent.objects.get(page='about', section='hero')
        print(f"Found About hero section with image: {about_hero.image}")
        
        # Check if the image exists in Cloudinary
        current_image = str(about_hero.image)
        if '1000_F_525789717_UVawu5xdqz2hxl14mwFrQV7RdwnXToxT.jpg' in current_image:
            print("❌ Found problematic image reference")
            
            # Use one of the existing hero slide images
            hero_slides = HeroSlide.objects.filter(is_active=True).first()
            if hero_slides:
                # Use the first hero slide image with correct path
                new_image_path = "media/hero_slides/about_montessori.jpg"
                about_hero.image = new_image_path
                about_hero.save()
                print(f"✅ Updated About hero image to: {new_image_path}")
            else:
                print("❌ No hero slides found to use as replacement")
        else:
            print("✅ About hero image looks fine")
            
    except PageContent.DoesNotExist:
        print("❌ About hero section not found")
    except Exception as e:
        print(f"❌ Error fixing About hero: {e}")

def check_all_page_content_images():
    """Check all PageContent images for missing files"""
    print("\n🔄 Checking all PageContent images...")
    print("=" * 50)
    
    problematic_images = []
    
    for content in PageContent.objects.all():
        if content.image:
            image_path = str(content.image)
            # Check for problematic patterns
            if ('1000_F_' in image_path or 
                'shutterstock' in image_path.lower() or 
                not any(ext in image_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif'])):
                problematic_images.append({
                    'id': content.id,
                    'page': content.page,
                    'section': content.section,
                    'image': image_path
                })
                print(f"❌ Problematic: {content.page}/{content.section} -> {image_path}")
    
    if problematic_images:
        print(f"\n📊 Found {len(problematic_images)} problematic images")
        
        # Fix them by using existing hero slide images
        replacement_images = [
            "hero_slides/about_montessori.jpg",
            "hero_slides/gettyimages-1421987003-612x612.jpg", 
            "hero_slides/montessori-meta-study.webp"
        ]
        
        for i, prob_img in enumerate(problematic_images):
            try:
                content = PageContent.objects.get(id=prob_img['id'])
                new_image = replacement_images[i % len(replacement_images)]
                content.image = new_image
                content.save()
                print(f"✅ Fixed {prob_img['page']}/{prob_img['section']} -> {new_image}")
            except Exception as e:
                print(f"❌ Failed to fix {prob_img['page']}/{prob_img['section']}: {e}")
    else:
        print("✅ No problematic images found")

def list_available_cloudinary_images():
    """List available images in Cloudinary"""
    print("\n🔄 Checking available Cloudinary images...")
    print("=" * 50)
    
    try:
        # List hero_slides folder
        result = cloudinary.api.resources(
            type="upload",
            prefix="hero_slides/",
            max_results=20
        )
        
        print("Available hero slide images in Cloudinary:")
        for resource in result.get('resources', []):
            print(f"  - {resource['public_id']}")
            
    except Exception as e:
        print(f"❌ Error listing Cloudinary images: {e}")

if __name__ == "__main__":
    print("🚀 Fix Missing Images Script")
    print("=" * 50)
    
    try:
        # List available images first
        list_available_cloudinary_images()
        
        # Fix the specific About hero issue
        fix_missing_hero_images()
        
        # Check and fix all other problematic images
        check_all_page_content_images()
        
        print(f"\n🎉 Image fixing complete!")
        print(f"📝 Next steps:")
        print(f"1. Test your website to see if images are now loading")
        print(f"2. Deploy to production to test Cloudinary integration")
        
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)
