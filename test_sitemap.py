#!/usr/bin/env python
"""
Test script to verify sitemap generation
"""

import os
import sys
from pathlib import Path
import django

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')

# Set production-like environment for testing
os.environ['DEBUG'] = 'False'
os.environ['ENVIRONMENT'] = 'production'

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

try:
    from django.contrib.sitemaps.views import sitemap
    from website.sitemaps import sitemaps
    print("✅ Sitemap imports successful")
    
    # Test each sitemap
    for name, sitemap_class in sitemaps.items():
        try:
            sitemap_instance = sitemap_class()
            items = sitemap_instance.items()
            print(f"✅ {name}: {len(items)} items")
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
    
    print("\n🔄 Testing sitemap generation...")
    
    # Create a mock request
    from django.test import RequestFactory
    factory = RequestFactory()
    request = factory.get('/sitemap.xml')
    
    # Test sitemap view
    response = sitemap(request, sitemaps=sitemaps)
    print(f"✅ Sitemap generated successfully - Status: {response.status_code}")
    print(f"✅ Content type: {response.get('Content-Type', 'unknown')}")
    
    # Show first few lines of sitemap
    content = response.content.decode('utf-8')
    lines = content.split('\n')[:10]
    print(f"\n📄 Sitemap preview:")
    for line in lines:
        print(f"  {line}")
    
    if len(lines) > 10:
        print(f"  ... and {len(content.split('</url>')) - 1} more URLs")
    
except Exception as e:
    print(f"❌ Sitemap test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 Sitemap test completed successfully!")
