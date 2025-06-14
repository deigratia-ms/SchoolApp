from django.core.management.base import BaseCommand
from website.models import HeroSlide


class Command(BaseCommand):
    help = 'Setup default button values for existing hero slides'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable-buttons',
            action='store_true',
            help='Enable buttons on all slides and set default values',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        slides = HeroSlide.objects.all()
        
        if not slides.exists():
            self.stdout.write(
                self.style.WARNING('No hero slides found.')
            )
            return

        self.stdout.write(f'Found {slides.count()} hero slide(s)')
        
        changes_made = 0
        
        for slide in slides:
            changes = []
            
            # Check if we need to set default button values
            if not slide.primary_button_text:
                if options['dry_run']:
                    changes.append('Set primary_button_text to "Apply Now"')
                else:
                    slide.primary_button_text = "Apply Now"
                    
            if not slide.primary_button_url:
                if options['dry_run']:
                    changes.append('Set primary_button_url to "/admissions/"')
                else:
                    slide.primary_button_url = "/admissions/"
                    
            if not slide.secondary_button_text:
                if options['dry_run']:
                    changes.append('Set secondary_button_text to "Contact Us"')
                else:
                    slide.secondary_button_text = "Contact Us"
                    
            if not slide.secondary_button_url:
                if options['dry_run']:
                    changes.append('Set secondary_button_url to "/contact/"')
                else:
                    slide.secondary_button_url = "/contact/"
            
            # Enable buttons if requested
            if options['enable_buttons'] and not slide.show_buttons:
                if options['dry_run']:
                    changes.append('Enable show_buttons')
                else:
                    slide.show_buttons = True
            
            if changes:
                changes_made += 1
                if options['dry_run']:
                    self.stdout.write(
                        f'Slide "{slide.title}": {", ".join(changes)}'
                    )
                else:
                    slide.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated slide "{slide.title}": {", ".join(changes)}'
                        )
                    )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would update {changes_made} slide(s). '
                    'Run without --dry-run to apply changes.'
                )
            )
        else:
            if changes_made > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully updated {changes_made} slide(s) with default button values.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('All slides already have button values set.')
                )
        
        # Show current status
        self.stdout.write('\nCurrent slide status:')
        for slide in HeroSlide.objects.all():
            status = "✓ Buttons enabled" if slide.show_buttons else "✗ Buttons disabled"
            primary = f'"{slide.primary_button_text}" → {slide.primary_button_url}' if slide.primary_button_text else "Not set"
            secondary = f'"{slide.secondary_button_text}" → {slide.secondary_button_url}' if slide.secondary_button_text else "Not set"
            
            self.stdout.write(f'  • {slide.title}: {status}')
            self.stdout.write(f'    Primary: {primary}')
            self.stdout.write(f'    Secondary: {secondary}')
