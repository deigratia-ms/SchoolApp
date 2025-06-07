#!/usr/bin/env python
"""
Development server helper script
This script helps start the Django development server with proper settings
and provides instructions for clearing browser cache if needed.
"""

import os
import sys
import subprocess
from pathlib import Path

def print_banner():
    print("=" * 60)
    print("🚀 DEIGRATIA MONTESSORI SCHOOL - DEVELOPMENT SERVER")
    print("=" * 60)

def check_environment():
    """Check if we're in the right directory and virtual environment"""
    if not Path('manage.py').exists():
        print("❌ Error: manage.py not found. Please run this from the project root.")
        return False
    
    if not Path('ricas_school_manager').exists():
        print("❌ Error: Project directory not found.")
        return False
    
    return True

def print_instructions():
    """Print helpful instructions"""
    print("\n📋 DEVELOPMENT SERVER INSTRUCTIONS:")
    print("-" * 40)
    print("✅ Server will start on: http://127.0.0.1:8000/")
    print("✅ Use HTTP (not HTTPS) for development")
    print("✅ Admin panel: http://127.0.0.1:8000/admin/")
    print("✅ Dashboard: http://127.0.0.1:8000/dashboard/")
    
    print("\n🔧 IF YOU GET HTTPS ERRORS:")
    print("-" * 30)
    print("1. Clear browser cache and cookies")
    print("2. Try incognito/private mode")
    print("3. For Chrome: Go to chrome://net-internals/#hsts")
    print("   - Delete domain security policies for 'localhost' and '127.0.0.1'")
    print("4. For Firefox: Clear all browsing data")
    print("5. Always use HTTP URLs: http://127.0.0.1:8000/")
    
    print("\n🎯 QUICK ACCESS URLS:")
    print("-" * 20)
    print("• Homepage: http://127.0.0.1:8000/")
    print("• Admin: http://127.0.0.1:8000/admin/")
    print("• Dashboard: http://127.0.0.1:8000/dashboard/")
    print("• Site Settings: http://127.0.0.1:8000/admin/website/sitesettings/")

def start_server():
    """Start the Django development server"""
    print("\n🚀 Starting Django development server...")
    print("Press Ctrl+C to stop the server")
    print("-" * 40)
    
    try:
        # Set environment variables for development
        os.environ['DEBUG'] = 'True'
        os.environ['FORCE_HTTPS'] = 'False'
        
        # Start the server
        subprocess.run([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000'])
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Thank you for using Deigratia School Management System!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("Make sure you've activated your virtual environment and installed dependencies.")

def main():
    print_banner()
    
    if not check_environment():
        sys.exit(1)
    
    print_instructions()
    
    # Ask user if they want to continue
    print("\n" + "=" * 60)
    response = input("Press Enter to start the server (or 'q' to quit): ").strip().lower()
    
    if response == 'q':
        print("👋 Goodbye!")
        sys.exit(0)
    
    start_server()

if __name__ == '__main__':
    main()
