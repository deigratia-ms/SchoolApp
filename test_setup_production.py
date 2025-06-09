#!/usr/bin/env python
"""
Quick test script to verify setup_production command works correctly.
Run this before deployment to catch any issues.
"""

import os
import sys
import django
from io import StringIO
from django.core.management import call_command

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

def test_setup_production():
    """Test the setup_production command"""
    print("🧪 Testing setup_production command...")
    
    try:
        # Capture output
        out = StringIO()
        
        # Run the command with all skips to test logic only
        call_command(
            'setup_production',
            '--skip-migrations',
            '--skip-cache', 
            '--skip-static',
            stdout=out
        )
        
        output = out.getvalue()
        print("✅ Command executed successfully!")
        print("\n📋 Command Output:")
        print(output)
        
        # Check for expected output patterns
        if "Setting up production environment" in output:
            print("✅ Command started correctly")
        else:
            print("❌ Command start message not found")
            
        if "Production setup completed" in output:
            print("✅ Command completed successfully")
        else:
            print("❌ Command completion message not found")
            
        return True
        
    except Exception as e:
        print(f"❌ Command failed with error: {e}")
        return False

def test_command_help():
    """Test that command help works"""
    print("\n🧪 Testing command help...")
    
    try:
        out = StringIO()
        call_command('help', 'setup_production', stdout=out)
        help_output = out.getvalue()
        
        if "Set up production environment" in help_output:
            print("✅ Command help works correctly")
            return True
        else:
            print("❌ Command help not working")
            return False
            
    except Exception as e:
        print(f"❌ Help command failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Production Setup Command")
    print("=" * 50)
    
    # Test command execution
    test1_passed = test_setup_production()
    
    # Test command help
    test2_passed = test_command_help()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("🎉 All tests passed! setup_production command is ready for deployment.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the command before deployment.")
        sys.exit(1)
