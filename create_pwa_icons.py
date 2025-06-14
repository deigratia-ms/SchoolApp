#!/usr/bin/env python
"""
Script to create PWA icons from the school logo
"""

import os
import sys
from pathlib import Path
import django
import requests
from PIL import Image
import io

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

django.setup()

def create_pwa_icons():
    """Create PWA icons from school logo"""
    print("🔄 Creating PWA icons from school logo...")
    print("=" * 50)
    
    # School logo URL in Cloudinary
    logo_url = "https://res.cloudinary.com/ds5udo8jc/image/upload/v1749684011/media/site/dgm_logo.png"
    
    # Icon sizes needed
    icon_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Create images directory if it doesn't exist
    images_dir = BASE_DIR / 'static' / 'website' / 'images'
    images_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download the logo
        print(f"📥 Downloading logo from: {logo_url}")
        response = requests.get(logo_url)
        response.raise_for_status()
        
        # Open the image
        logo_image = Image.open(io.BytesIO(response.content))
        
        # Convert to RGBA if not already
        if logo_image.mode != 'RGBA':
            logo_image = logo_image.convert('RGBA')
        
        print(f"✅ Logo downloaded successfully: {logo_image.size}")
        
        # Create icons for each size
        for size in icon_sizes:
            try:
                # Create a square canvas with white background
                canvas = Image.new('RGBA', (size, size), (255, 255, 255, 255))
                
                # Resize logo to fit with some padding
                padding = size // 8  # 12.5% padding
                logo_size = size - (2 * padding)
                
                # Resize logo maintaining aspect ratio
                logo_resized = logo_image.copy()
                logo_resized.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
                
                # Center the logo on the canvas
                logo_x = (size - logo_resized.width) // 2
                logo_y = (size - logo_resized.height) // 2
                
                # Paste logo onto canvas
                canvas.paste(logo_resized, (logo_x, logo_y), logo_resized)
                
                # Save the icon
                icon_path = images_dir / f'icon-{size}x{size}.png'
                canvas.save(icon_path, 'PNG', optimize=True)
                
                print(f"✅ Created icon: {icon_path.name} ({size}x{size})")
                
            except Exception as e:
                print(f"❌ Failed to create {size}x{size} icon: {e}")
        
        print(f"\n🎉 PWA icons created successfully!")
        print(f"📁 Icons saved to: {images_dir}")
        
        # List created files
        print(f"\n📋 Created files:")
        for icon_file in sorted(images_dir.glob('icon-*.png')):
            file_size = icon_file.stat().st_size / 1024  # KB
            print(f"  {icon_file.name} ({file_size:.1f} KB)")
            
    except Exception as e:
        print(f"❌ Failed to create PWA icons: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Create PWA Icons Script")
    print("=" * 50)
    
    try:
        success = create_pwa_icons()
        
        if success:
            print(f"\n📝 Next steps:")
            print(f"1. Deploy to production: fly deploy")
            print(f"2. The PWA icons should now load correctly")
            print(f"3. Test your website's PWA functionality")
        else:
            print(f"\n❌ Icon creation failed")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)
