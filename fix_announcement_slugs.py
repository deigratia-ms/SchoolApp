import os
import django
import sys

# Set up Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

from django.utils.text import slugify
from website.models import Announcement

def fix_slugs():
    print("Starting slug fix process...")

    # Get all announcements
    announcements = Announcement.objects.all()
    print(f"Found {announcements.count()} announcements without slugs")

    for announcement in announcements:
        # Skip if already has a valid slug
        if announcement.slug:
            print(f"Announcement ID {announcement.id} already has slug: '{announcement.slug}'")
            continue

        # Create a base slug from the title
        base_slug = slugify(announcement.title)

        # Make sure the slug is unique
        slug = base_slug
        counter = 1

        # Keep checking until we find a unique slug
        while Announcement.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Set the slug and save
        announcement.slug = slug
        announcement.save()
        print(f"Fixed announcement ID {announcement.id}: '{announcement.title}' → '{slug}'")

    print("Slug fix process completed!")

if __name__ == "__main__":
    fix_slugs()
