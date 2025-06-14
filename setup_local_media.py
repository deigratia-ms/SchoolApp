#!/usr/bin/env python
"""
Setup local media storage and create test images
"""

import os
import sys
from pathlib import Path
import django
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from website.models import PageContent, SiteSettings, HeroSlide
from users.models import SchoolSettings

def create_media_directories():
    """Create necessary media directories"""
    print("📁 Creating media directories...")
    
    media_root = Path('media')
    directories = [
        'hero_slides',
        'site_images',
        'school_logos',
        'page_images'
    ]
    
    for directory in directories:
        dir_path = media_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Created: {dir_path}")

def create_test_hero_image():
    """Create a test hero image"""
    print("🎨 Creating test hero image...")
    
    # Create image
    img = Image.new('RGB', (1920, 600), color='#0a2351')  # School navy color
    draw = ImageDraw.Draw(img)
    
    # Add gradient effect
    for y in range(600):
        alpha = int(255 * (1 - y / 600))
        color = (10, 35, 81, alpha)  # Navy with alpha
        draw.line([(0, y), (1920, y)], fill=(10 + y//10, 35 + y//20, 81 + y//15))
    
    # Add text
    try:
        font_large = ImageFont.truetype("arial.ttf", 80)
        font_small = ImageFont.truetype("arial.ttf", 40)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Main title
    title = "Welcome to Deigratia Montessori School"
    subtitle = "Excellence in Education • Oyibi, Greater Accra"
    
    # Calculate text positions
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (1920 - title_width) // 2
    title_y = 200
    
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=font_small)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (1920 - subtitle_width) // 2
    subtitle_y = 320
    
    # Draw text with shadow effect
    # Shadow
    draw.text((title_x + 3, title_y + 3), title, fill='black', font=font_large)
    draw.text((subtitle_x + 2, subtitle_y + 2), subtitle, fill='black', font=font_small)
    
    # Main text
    draw.text((title_x, title_y), title, fill='white', font=font_large)
    draw.text((subtitle_x, subtitle_y), subtitle, fill='#ffd700', font=font_small)  # Gold color
    
    # Save image
    img_path = Path('media/hero_slides/test_hero.jpg')
    img.save(img_path, 'JPEG', quality=85)
    print(f"  ✅ Created hero image: {img_path}")
    
    return 'hero_slides/test_hero.jpg'

def create_test_logo():
    """Create a test school logo"""
    print("🏫 Creating test school logo...")
    
    # Create circular logo
    img = Image.new('RGBA', (200, 200), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw circle background
    draw.ellipse([10, 10, 190, 190], fill='#0a2351', outline='#ffd700', width=5)
    
    # Add text
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # School initials
    text = "DMS"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    text_x = (200 - text_width) // 2
    text_y = (200 - text_height) // 2 - 10
    
    draw.text((text_x, text_y), text, fill='white', font=font)
    
    # Add small text
    try:
        small_font = ImageFont.truetype("arial.ttf", 12)
    except:
        small_font = ImageFont.load_default()
    
    small_text = "MONTESSORI"
    small_bbox = draw.textbbox((0, 0), small_text, font=small_font)
    small_width = small_bbox[2] - small_bbox[0]
    small_x = (200 - small_width) // 2
    small_y = text_y + 40
    
    draw.text((small_x, small_y), small_text, fill='#ffd700', font=small_font)
    
    # Save logo
    logo_path = Path('media/school_logos/test_logo.png')
    img.save(logo_path, 'PNG')
    print(f"  ✅ Created logo: {logo_path}")
    
    return 'school_logos/test_logo.png'

def update_database_records():
    """Update database records to use local media"""
    print("💾 Updating database records...")
    
    # Create test images
    hero_image_path = create_test_hero_image()
    logo_path = create_test_logo()
    
    # Update PageContent for about hero
    try:
        page_content = PageContent.objects.get(page='about', section='hero')
        page_content.image = hero_image_path
        page_content.save()
        print(f"  ✅ Updated PageContent hero image: {page_content.image}")
    except PageContent.DoesNotExist:
        print("  ⚠️ PageContent about/hero not found")
    
    # Update SiteSettings
    try:
        site_settings = SiteSettings.objects.first()
        if site_settings:
            site_settings.school_logo = logo_path
            site_settings.favicon = logo_path
            site_settings.save()
            print(f"  ✅ Updated SiteSettings logo: {site_settings.school_logo}")
    except Exception as e:
        print(f"  ⚠️ Error updating SiteSettings: {e}")
    
    # Update SchoolSettings
    try:
        school_settings = SchoolSettings.objects.first()
        if school_settings:
            school_settings.logo = logo_path
            school_settings.save()
            print(f"  ✅ Updated SchoolSettings logo: {school_settings.logo}")
    except Exception as e:
        print(f"  ⚠️ Error updating SchoolSettings: {e}")

def test_local_media():
    """Test that local media is working"""
    print("🧪 Testing local media setup...")
    
    from django.conf import settings
    
    print(f"  MEDIA_URL: {settings.MEDIA_URL}")
    print(f"  MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"  DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    print(f"  Storage class: {default_storage.__class__.__name__}")
    
    # Test PageContent
    try:
        page_content = PageContent.objects.get(page='about', section='hero')
        print(f"  Hero image path: {page_content.image}")
        print(f"  Hero image URL: {page_content.image.url}")
        
        # Check if file exists
        if page_content.image:
            file_path = Path(settings.MEDIA_ROOT) / page_content.image.name
            exists = file_path.exists()
            print(f"  File exists: {'✅ YES' if exists else '❌ NO'}")
            
            if exists:
                print(f"  File size: {file_path.stat().st_size} bytes")
        
    except PageContent.DoesNotExist:
        print("  ❌ PageContent not found")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def main():
    print("🚀 Setting up Local Media Storage")
    print("=" * 50)
    
    # Step 1: Create directories
    create_media_directories()
    
    print()
    
    # Step 2: Update database
    update_database_records()
    
    print()
    
    # Step 3: Test setup
    test_local_media()
    
    print()
    print("🎉 Local media setup complete!")
    print("📝 Next steps:")
    print("1. Run the development server: python manage.py runserver")
    print("2. Check admin panel - images should display correctly")
    print("3. Visit About page - hero image should load")
    print("4. Test uploading new images through admin")

if __name__ == "__main__":
    main()
