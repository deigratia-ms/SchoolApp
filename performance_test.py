#!/usr/bin/env python
"""
Simple performance test script to measure page load times.
Run this script to test the performance improvements.
"""

import time
import requests
import statistics
from django.core.management import execute_from_command_line
import os
import sys

def test_page_performance(url, num_requests=5):
    """Test the performance of a page by making multiple requests."""
    print(f"Testing {url} with {num_requests} requests...")
    
    times = []
    for i in range(num_requests):
        start_time = time.time()
        try:
            response = requests.get(url, timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                request_time = end_time - start_time
                times.append(request_time)
                print(f"Request {i+1}: {request_time:.3f}s")
            else:
                print(f"Request {i+1}: Failed with status {response.status_code}")
        except requests.RequestException as e:
            print(f"Request {i+1}: Error - {e}")
    
    if times:
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\nResults for {url}:")
        print(f"Average time: {avg_time:.3f}s")
        print(f"Min time: {min_time:.3f}s")
        print(f"Max time: {max_time:.3f}s")
        print(f"Successful requests: {len(times)}/{num_requests}")
        
        return avg_time
    else:
        print("No successful requests!")
        return None

def main():
    """Main function to run performance tests."""
    base_url = "http://127.0.0.1:5000"
    
    # Test different pages
    pages_to_test = [
        "/",  # Home page
        "/about/",  # About page
        "/contact/",  # Contact page
    ]
    
    print("=== Performance Test Results ===")
    print("Testing page load times after optimization...")
    print()
    
    results = {}
    for page in pages_to_test:
        url = base_url + page
        avg_time = test_page_performance(url, num_requests=3)
        if avg_time:
            results[page] = avg_time
        print("-" * 50)
    
    # Summary
    if results:
        print("\n=== SUMMARY ===")
        for page, avg_time in results.items():
            status = "GOOD" if avg_time < 1.0 else "SLOW" if avg_time < 3.0 else "VERY SLOW"
            print(f"{page}: {avg_time:.3f}s ({status})")
        
        overall_avg = statistics.mean(results.values())
        print(f"\nOverall average: {overall_avg:.3f}s")
        
        if overall_avg < 1.0:
            print("✅ Performance is EXCELLENT!")
        elif overall_avg < 2.0:
            print("✅ Performance is GOOD!")
        elif overall_avg < 3.0:
            print("⚠️ Performance is ACCEPTABLE but could be improved")
        else:
            print("❌ Performance is POOR - needs optimization")

if __name__ == "__main__":
    main()
