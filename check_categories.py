import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

from fees.models import FeeCategory

# Get all active fee categories
categories = FeeCategory.objects.filter(is_active=True)

print(f"Found {categories.count()} active fee categories:")
for category in categories:
    print(f"- {category.name} (Type: {category.category_type})")

if categories.count() == 0:
    print("No active fee categories found. Please create at least one fee category.")
