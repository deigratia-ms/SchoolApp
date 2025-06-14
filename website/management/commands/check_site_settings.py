from django.core.management.base import BaseCommand
from users.models import SchoolSettings
from users.models import


class Command(BaseCommand):
    help = 'Check current site settings and media files'

    def handle(self, *args, **options):
        self.stdout.write("=== SITE SETTINGS CHECK ===")
        
        # Check SchoolSettings
        site_settings = SchoolSettings.objects.first()
        if site_settings:
            self.stdout.write(self.style.SUCCESS("✅ SchoolSettings found"))
            if site_settings.logo:
                self.stdout.write(f"   School Logo: {site_settings.logo.url}")
                self.stdout.write(f"   Logo Path: {site_settings.logo.path}")
            else:
                self.stdout.write(self.style.WARNING("   ⚠️  No school logo uploaded"))
                
            if site_settings.favicon:
                self.stdout.write(f"   Favicon: {site_settings.favicon.url}")
            else:
                self.stdout.write("   No favicon uploaded")
        else:
            self.stdout.write(self.style.ERROR("❌ No SchoolSettings found"))
            
        # Check SchoolSettings
        from users.models import SchoolSettings

        school_settings = SchoolSettings.objects.first()
        if school_settings:
            self.stdout.write(self.style.SUCCESS("✅ SchoolSettings found"))
            if school_settings.logo:
                self.stdout.write(f"   School Logo: {school_settings.logo.url}")
                self.stdout.write(f"   Logo Path: {school_settings.logo.path}")
            else:
                self.stdout.write(self.style.WARNING("   ⚠️  No school logo uploaded"))
        else:
            self.stdout.write(self.style.ERROR("❌ No SchoolSettings found"))
            
        # Check hero slides
        from website.models import HeroSlide
        hero_slides = HeroSlide.objects.filter(is_active=True)
        if hero_slides.exists():
            self.stdout.write(f"✅ {hero_slides.count()} active hero slides found")
            for slide in hero_slides:
                if slide.image:
                    self.stdout.write(f"   Slide: {slide.title} - {slide.image.url}")
                else:
                    self.stdout.write(f"   Slide: {slide.title} - No image")
        else:
            self.stdout.write(self.style.WARNING("⚠️  No active hero slides found"))
            
        self.stdout.write("\n=== RECOMMENDATIONS ===")
        if not site_settings:
            self.stdout.write("1. Create SchoolSettings in Django Admin")
        if not (site_settings and site_settings.logo) and not (school_settings and school_settings.logo):
            self.stdout.write("2. Upload a school logo")
        if not hero_slides.exists():
            self.stdout.write("3. Create hero slides for the homepage")
