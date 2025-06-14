from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from website.models import SiteSettings
from users.models import SiteSettings
import os


class Command(BaseCommand):
    help = 'Create default site settings with school logo'

    def handle(self, *args, **options):
        # Get or create SiteSettings (use first if multiple exist)
        school_settings = SiteSettings.objects.first()
        created = False

        if not school_settings:
            school_settings = SiteSettings.objects.create(
                school_name='Deigratia Montessori School',
                address='Accra, Ghana',
                phone='+233 123 456 789',
                email='info@deigratiamontessori.edu.gh',
                principal_name='Principal',
                academic_year='2024/2025',
                enable_messaging=True,
                enable_student_to_student_chat=True,
                primary_color='#008080',
                dark_mode=False,
            )
            created = True
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created SiteSettings')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('SiteSettings already exists')
            )
        
        # Get or create SiteSettings (use first if multiple exist)
        site_settings = SiteSettings.objects.first()
        created = False

        if not site_settings:
            site_settings = SiteSettings.objects.create(
                contact_email='info@deigratiamontessori.edu.gh',
                contact_phone='+233 123 456 789',
                address='Accra, Ghana',
                facebook_url='https://facebook.com/deigratiamontessori',
                twitter_url='https://twitter.com/deigratiamontessori',
                instagram_url='https://instagram.com/deigratiamontessori',
                linkedin_url='https://linkedin.com/company/deigratiamontessori',
                youtube_url='https://youtube.com/@deigratiamontessori',
                about_text='Deigratia Montessori School is committed to providing quality education through the Montessori method.',
                mission_statement='To nurture and develop each child\'s potential through innovative Montessori education.',
                vision_statement='To be a leading Montessori school that prepares students for lifelong learning and success.',
                footer_text='© 2024 Deigratia Montessori School. All rights reserved.',
                enable_online_applications=True,
                enable_online_payments=True,
                enable_student_portal=True,
                enable_parent_portal=True,
                enable_teacher_portal=True,
                maintenance_mode=False,
            )
            created = True
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created SiteSettings')
            )

            # Set school logo from SiteSettings if available
            if school_settings.school_logo:
                site_settings.school_logo = school_settings.school_logo
                site_settings.save()
                self.stdout.write(
                    self.style.SUCCESS('Set school logo in SiteSettings from SiteSettings')
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('SiteSettings already exists')
            )

            # Update school logo if SiteSettings has one but SiteSettings doesn't
            if school_settings.school_logo and not site_settings.school_logo:
                site_settings.school_logo = school_settings.school_logo
                site_settings.save()
                self.stdout.write(
                    self.style.SUCCESS('Updated school logo in SiteSettings from SiteSettings')
                )
        
        # Clear cache to ensure new settings are loaded
        from django.core.cache import cache
        cache.delete('unified_site_settings')
        
        self.stdout.write(
            self.style.SUCCESS('Site settings setup completed successfully!')
        )
        self.stdout.write(
            self.style.SUCCESS('Favicon will now use the school logo as fallback.')
        )
