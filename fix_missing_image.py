#!/usr/bin/env python
"""
Fix the missing hero image by uploading a replacement and updating the database
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

from website.models import PageContent
import cloudinary
import cloudinary.uploader

def fix_missing_hero_image():
    """Fix the missing hero image"""
    print("🔧 FIXING MISSING HERO IMAGE")
    print("=" * 50)
    
    try:
        # Get the problematic PageContent
        page_content = PageContent.objects.get(page='about', section='hero')
        print(f"Found PageContent: {page_content.page}/{page_content.section}")
        print(f"Current image path: {page_content.image}")
        print(f"Current image URL: {page_content.image.url}")
        
        # List available images in Cloudinary hero_slides folder
        print(f"\n📋 Available images in Cloudinary hero_slides:")
        try:
            result = cloudinary.api.resources(
                type='upload',
                prefix='hero_slides/',
                max_results=20
            )
            
            available_images = []
            for resource in result.get('resources', []):
                public_id = resource['public_id']
                url = resource['secure_url']
                print(f"  - {public_id}")
                available_images.append(public_id)
                
            if available_images:
                # Use the first available hero slide image
                new_image_path = available_images[0]
                print(f"\n✅ Using available image: {new_image_path}")
                
                # Update the PageContent
                page_content.image = new_image_path
                page_content.save()
                
                print(f"✅ Updated PageContent image to: {page_content.image}")
                print(f"✅ New URL: {page_content.image.url}")
                
                # Test the new URL
                import requests
                try:
                    response = requests.head(page_content.image.url, timeout=10)
                    if response.status_code == 200:
                        print(f"✅ New URL is accessible!")
                    else:
                        print(f"❌ New URL returned status: {response.status_code}")
                except Exception as e:
                    print(f"❌ Error testing new URL: {e}")
                    
            else:
                print(f"❌ No hero slide images found in Cloudinary")
                
        except Exception as e:
            print(f"❌ Error listing Cloudinary images: {e}")
            
    except PageContent.DoesNotExist:
        print("❌ No about/hero PageContent found")
    except Exception as e:
        print(f"❌ Error: {e}")

def upload_default_hero_image():
    """Upload a default hero image if none exist"""
    print(f"\n📤 UPLOADING DEFAULT HERO IMAGE")
    print("=" * 50)
    
    try:
        # Create a simple hero image
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        
        # Create image
        img = Image.new('RGB', (1920, 600), color='#0a2351')  # School navy color
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            # Try to use a nice font
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
            
        text = "Welcome to Deigratia Montessori School"
        
        # Get text size and center it
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (1920 - text_width) // 2
        y = (600 - text_height) // 2
        
        draw.text((x, y), text, fill='white', font=font)
        
        # Save to BytesIO
        img_io = BytesIO()
        img.save(img_io, format='JPEG', quality=85)
        img_io.seek(0)
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            img_io.getvalue(),
            public_id='hero_slides/default_hero',
            overwrite=True,
            resource_type='image'
        )
        
        print(f"✅ Uploaded default hero image: {result['secure_url']}")
        
        # Update PageContent to use this image
        try:
            page_content = PageContent.objects.get(page='about', section='hero')
            page_content.image = 'hero_slides/default_hero'
            page_content.save()
            print(f"✅ Updated PageContent to use default hero image")
        except PageContent.DoesNotExist:
            print(f"❌ PageContent not found to update")
            
        return result['secure_url']
        
    except Exception as e:
        print(f"❌ Error uploading default hero image: {e}")
        return None

def main():
    print("🚀 Fix Missing Image Script")
    print("=" * 60)
    
    # First try to fix with existing images
    fix_missing_hero_image()
    
    # If no images available, upload a default one
    print(f"\n" + "=" * 60)
    upload_default_hero_image()
    
    print(f"\n🎉 Image fixing complete!")
    print(f"📝 Next steps:")
    print(f"1. Check your admin panel - the image should now display")
    print(f"2. Visit your About page to see the hero image")
    print(f"3. Upload a better hero image through the admin panel if needed")

if __name__ == "__main__":
    main()
