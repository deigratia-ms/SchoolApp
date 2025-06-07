#!/usr/bin/env python
"""
Simple Django performance test using Django's test client.
"""

import os
import sys
import django
import time
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

from django.test import Client
from django.core.cache import cache

def test_view_performance():
    """Test the performance of views using Django test client."""
    client = Client()
    
    print("=== Django Performance Test ===")
    print("Testing view performance after optimization...")
    print()
    
    # Clear cache to test cold performance
    cache.clear()
    print("Cache cleared for cold performance test")
    
    # Test home page (cold)
    print("Testing home page (cold cache)...")
    start_time = time.time()
    response = client.get('/')
    cold_time = time.time() - start_time
    print(f"Cold load time: {cold_time:.3f}s")
    print(f"Status code: {response.status_code}")
    
    # Test home page (warm cache)
    print("\nTesting home page (warm cache)...")
    start_time = time.time()
    response = client.get('/')
    warm_time = time.time() - start_time
    print(f"Warm load time: {warm_time:.3f}s")
    print(f"Status code: {response.status_code}")
    
    # Calculate improvement
    if cold_time > 0:
        improvement = ((cold_time - warm_time) / cold_time) * 100
        print(f"\nCache improvement: {improvement:.1f}%")
    
    # Test multiple requests to see average performance
    print("\nTesting 5 consecutive requests...")
    times = []
    for i in range(5):
        start_time = time.time()
        response = client.get('/')
        request_time = time.time() - start_time
        times.append(request_time)
        print(f"Request {i+1}: {request_time:.3f}s")
    
    avg_time = sum(times) / len(times)
    print(f"\nAverage time: {avg_time:.3f}s")
    
    # Performance assessment
    if avg_time < 0.1:
        print("✅ Performance is EXCELLENT!")
    elif avg_time < 0.3:
        print("✅ Performance is GOOD!")
    elif avg_time < 0.5:
        print("⚠️ Performance is ACCEPTABLE")
    else:
        print("❌ Performance needs improvement")
    
    return avg_time

def test_cache_effectiveness():
    """Test cache effectiveness."""
    print("\n=== Cache Effectiveness Test ===")
    
    # Clear cache
    cache.clear()
    
    # Test context processor caching
    from website.context_processors import site_settings
    from django.test import RequestFactory
    
    request = RequestFactory().get('/')
    
    # First call (should hit database)
    start_time = time.time()
    result1 = site_settings(request)
    first_call_time = time.time() - start_time
    
    # Second call (should hit cache)
    start_time = time.time()
    result2 = site_settings(request)
    second_call_time = time.time() - start_time
    
    print(f"First call (DB): {first_call_time:.4f}s")
    print(f"Second call (Cache): {second_call_time:.4f}s")
    
    if first_call_time > 0:
        speedup = first_call_time / second_call_time if second_call_time > 0 else float('inf')
        print(f"Cache speedup: {speedup:.1f}x")

if __name__ == "__main__":
    try:
        avg_time = test_view_performance()
        test_cache_effectiveness()
        
        print(f"\n=== SUMMARY ===")
        print(f"Average page load time: {avg_time:.3f}s")
        print("Performance optimizations applied:")
        print("✅ Context processor caching")
        print("✅ Settings caching")
        print("✅ Home page caching")
        print("✅ Template caching disabled in development")
        print("✅ Database connection optimization")
        
    except Exception as e:
        print(f"Error running performance test: {e}")
        import traceback
        traceback.print_exc()
