from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import SchoolSettings, HeroSlide
from users.models import


class Command(BaseCommand):
    help = 'Fix Cloudinary image URLs in the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Fixing Cloudinary image URLs...'))
        
        # Fix SchoolSettings
        try:
            site_settings, created = SchoolSettings.objects.get_or_create(
                defaults={
                    'contact_email': 'info@deigratiamontessori.edu.gh',
                    'contact_phone': '+233 123 456 789',
                    'address': 'Accra, Ghana',
                    'about_text': 'Deigratia Montessori School is committed to providing quality education through the Montessori method.',
                    'mission_statement': 'To nurture and develop each child\'s potential through innovative Montessori education.',
                    'school_logo': 'media/site/dgm_logo.png',
                }
            )
            
            # Update the logo to use Cloudinary path
            site_settings.logo = 'media/site/dgm_logo.png'
            site_settings.save()
            
            if created:
                self.stdout.write(self.style.SUCCESS('✅ Created new SchoolSettings'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ Updated SchoolSettings school logo'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error updating SchoolSettings: {e}'))
        
        # Fix SchoolSettings
        try:
            school_settings, created = SchoolSettings.objects.get_or_create(
                defaults={
                    'school_name': 'Deigratia Montessori School',
                    'logo': 'media/school_logo/dgm_logo.png',
                    'address': 'Accra, Ghana',
                    'phone': '+233 123 456 789',
                    'email': 'info@deigratiamontessori.edu.gh',
                }
            )
            
            # Update the logo to use Cloudinary path
            school_settings.logo = 'media/school_logo/dgm_logo.png'
            school_settings.save()
            
            if created:
                self.stdout.write(self.style.SUCCESS('✅ Created new SchoolSettings'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ Updated SchoolSettings logo'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error updating SchoolSettings: {e}'))
        
        # Create some hero slides if they don't exist
        try:
            if not HeroSlide.objects.exists():
                hero_slides = [
                    {
                        'title': 'Welcome to Deigratia Montessori School',
                        'subtitle': 'Nurturing Excellence Through Montessori Education',
                        'image': 'media/hero_slides/about_montessori.jpg',
                        'order': 1,
                    },
                    {
                        'title': 'Discover the Montessori Method',
                        'subtitle': 'Child-centered learning that develops independence and creativity',
                        'image': 'media/hero_slides/gettyimages-1421987003-612x612.jpg',
                        'order': 2,
                    },
                    {
                        'title': 'Quality Education for Every Child',
                        'subtitle': 'Building strong foundations for lifelong learning',
                        'image': 'media/hero_slides/montessori-meta-study.webp',
                        'order': 3,
                    },
                ]
                
                for slide_data in hero_slides:
                    HeroSlide.objects.create(**slide_data)
                
                self.stdout.write(self.style.SUCCESS(f'✅ Created {len(hero_slides)} hero slides'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ Hero slides already exist'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error creating hero slides: {e}'))
        
        # Clear cache to ensure changes are reflected
        try:
            from django.core.cache import cache
            cache.clear()
            self.stdout.write(self.style.SUCCESS('✅ Cleared cache'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Could not clear cache: {e}'))
        
        self.stdout.write(self.style.SUCCESS('🎉 Cloudinary image URLs fixed successfully!'))
        self.stdout.write(self.style.SUCCESS('📝 Your images should now load from Cloudinary'))
