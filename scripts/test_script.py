"""
Simple test script to verify Django shell script execution
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

# Import a model
from users.models import CustomUser

# Print a message
print("Test script is running!")
print(f"Number of users in database: {CustomUser.objects.count()}")

# This will run when the script is executed directly
if __name__ == "__main__":
    print("Script executed directly")
