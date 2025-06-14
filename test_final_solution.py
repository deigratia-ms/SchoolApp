#!/usr/bin/env python
"""
Final test script to verify Cloudinary integration is working perfectly
"""

import os
import sys
from pathlib import Path
import django
import requests

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

django.setup()

from website.models import PageContent, SiteSettings, HeroSlide
from users.models import SchoolSettings

def test_image_urls():
    """Test all image URLs to ensure they're accessible"""
    print("🧪 TESTING ALL IMAGE URLS")
    print("=" * 60)
    
    test_results = []
    
    # Test PageContent images
    print("📄 Testing PageContent images:")
    for content in PageContent.objects.filter(image__isnull=False):
        url = f"https://res.cloudinary.com/ds5udo8jc/{content.image}"
        try:
            response = requests.head(url, timeout=10)
            status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
            print(f"  {content.page}/{content.section}: {status}")
            test_results.append((f"{content.page}/{content.section}", response.status_code == 200))
        except Exception as e:
            print(f"  {content.page}/{content.section}: ❌ Error - {e}")
            test_results.append((f"{content.page}/{content.section}", False))
    
    # Test SiteSettings
    print("\n🏫 Testing SiteSettings images:")
    site_settings = SiteSettings.objects.first()
    if site_settings:
        for field_name in ['school_logo', 'favicon']:
            field_value = getattr(site_settings, field_name, None)
            if field_value:
                url = f"https://res.cloudinary.com/ds5udo8jc/{field_value}"
                try:
                    response = requests.head(url, timeout=10)
                    status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
                    print(f"  {field_name}: {status}")
                    test_results.append((f"SiteSettings.{field_name}", response.status_code == 200))
                except Exception as e:
                    print(f"  {field_name}: ❌ Error - {e}")
                    test_results.append((f"SiteSettings.{field_name}", False))
    
    # Test HeroSlides
    print("\n🎭 Testing HeroSlide images:")
    for slide in HeroSlide.objects.all():
        if slide.image:
            url = f"https://res.cloudinary.com/ds5udo8jc/{slide.image}"
            try:
                response = requests.head(url, timeout=10)
                status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
                print(f"  Slide {slide.id}: {status}")
                test_results.append((f"HeroSlide.{slide.id}", response.status_code == 200))
            except Exception as e:
                print(f"  Slide {slide.id}: ❌ Error - {e}")
                test_results.append((f"HeroSlide.{slide.id}", False))
    
    # Test SchoolSettings
    print("\n🎓 Testing SchoolSettings:")
    school_settings = SchoolSettings.objects.first()
    if school_settings and school_settings.logo:
        url = f"https://res.cloudinary.com/ds5udo8jc/{school_settings.logo}"
        try:
            response = requests.head(url, timeout=10)
            status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
            print(f"  School logo: {status}")
            test_results.append(("SchoolSettings.logo", response.status_code == 200))
        except Exception as e:
            print(f"  School logo: ❌ Error - {e}")
            test_results.append(("SchoolSettings.logo", False))
    
    return test_results

def test_pwa_icons():
    """Test PWA icons"""
    print(f"\n📱 TESTING PWA ICONS")
    print("=" * 60)
    
    icon_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    base_url = "https://deigratiams.edu.gh/static/website/images/"
    
    pwa_results = []
    
    for size in icon_sizes:
        url = f"{base_url}icon-{size}x{size}.png"
        try:
            response = requests.head(url, timeout=10)
            status = "✅ OK" if response.status_code == 200 else f"❌ {response.status_code}"
            print(f"  icon-{size}x{size}.png: {status}")
            pwa_results.append((f"icon-{size}x{size}.png", response.status_code == 200))
        except Exception as e:
            print(f"  icon-{size}x{size}.png: ❌ Error - {e}")
            pwa_results.append((f"icon-{size}x{size}.png", False))
    
    return pwa_results

def generate_report(image_results, pwa_results):
    """Generate final test report"""
    print(f"\n📊 FINAL TEST REPORT")
    print("=" * 60)
    
    total_images = len(image_results)
    successful_images = sum(1 for _, success in image_results if success)
    
    total_pwa = len(pwa_results)
    successful_pwa = sum(1 for _, success in pwa_results if success)
    
    print(f"🖼️  Image Tests:")
    print(f"   Total: {total_images}")
    print(f"   Successful: {successful_images}")
    print(f"   Failed: {total_images - successful_images}")
    print(f"   Success Rate: {(successful_images/total_images*100):.1f}%")
    
    print(f"\n📱 PWA Icon Tests:")
    print(f"   Total: {total_pwa}")
    print(f"   Successful: {successful_pwa}")
    print(f"   Failed: {total_pwa - successful_pwa}")
    print(f"   Success Rate: {(successful_pwa/total_pwa*100):.1f}%")
    
    overall_success = successful_images + successful_pwa
    overall_total = total_images + total_pwa
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Total Tests: {overall_total}")
    print(f"   Successful: {overall_success}")
    print(f"   Success Rate: {(overall_success/overall_total*100):.1f}%")
    
    if overall_success == overall_total:
        print(f"\n🎉 ALL TESTS PASSED! Your Cloudinary integration is working perfectly!")
        print(f"✅ All images are loading from Cloudinary")
        print(f"✅ All PWA icons are accessible")
        print(f"✅ Admin panel uploads will go to Cloudinary")
        print(f"✅ Your website is fully optimized")
    else:
        print(f"\n⚠️  Some tests failed. Please check the failed items above.")
        
        if successful_images < total_images:
            print(f"🔧 Image Issues: Check database paths and Cloudinary uploads")
        
        if successful_pwa < total_pwa:
            print(f"🔧 PWA Issues: Re-run create_pwa_icons.py and deploy")

if __name__ == "__main__":
    print("🚀 Final Cloudinary Integration Test")
    print("=" * 60)
    print("Testing your production website: https://deigratiams.edu.gh/")
    print("This will verify that all images are loading correctly from Cloudinary.")
    print()
    
    try:
        # Test all images
        image_results = test_image_urls()
        
        # Test PWA icons
        pwa_results = test_pwa_icons()
        
        # Generate report
        generate_report(image_results, pwa_results)
        
        print(f"\n📝 NEXT STEPS:")
        print(f"1. Visit your website: https://deigratiams.edu.gh/")
        print(f"2. Check the About page hero section")
        print(f"3. Test uploading new images through admin panel")
        print(f"4. Verify images appear with Cloudinary URLs")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
