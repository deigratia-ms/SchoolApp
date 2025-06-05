from django.core.management.base import BaseCommand
from website.models import PageContent, MontessoriMethodItem
from django.core.files import File
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Initialize default content for the About page'

    def _init_page_content(self):
        # About Hero Section
        PageContent.objects.get_or_create(
            page='about',
            section='about_hero',
            defaults={
                'title': 'About Our School',
                'content': 'Discover the Deigratia Montessori difference and our commitment to excellence in education',
                'order': 1,
                'is_active': True
            }
        )

        # Mission Section
        PageContent.objects.get_or_create(
            page='about',
            section='mission',
            defaults={
                'title': 'Our Mission',
                'content': 'To provide an enriching Montessori education that nurtures each child\'s unique potential, fostering independence, creativity, and a lifelong love for learning while maintaining the highest standards of academic excellence.',
                'order': 2,
                'is_active': True
            }
        )

        # Vision Section
        PageContent.objects.get_or_create(
            page='about',
            section='vision',
            defaults={
                'title': 'Our Vision',
                'content': 'To be a leading Montessori institution that empowers children to become confident, responsible, and globally conscious individuals who contribute positively to society through their unique gifts and talents.',
                'order': 3,
                'is_active': True
            }
        )

        # Story Section
        story_content = '''
        <p>Deigratia Montessori School was established with a clear vision: to create an educational environment where children can thrive and develop their full potential. Our journey began with a deep commitment to the Montessori method and its proven approach to child development.</p>
        <p>Today, we continue to build upon this foundation, combining traditional Montessori principles with innovative educational practices to prepare our students for success in the modern world.</p>
        '''
        PageContent.objects.get_or_create(
            page='about',
            section='story',
            defaults={
                'title': 'Our Story',
                'subtitle': 'Founded with a vision to provide exceptional Montessori education',
                'content': story_content.strip(),
                'order': 4,
                'is_active': True
            }
        )

    def _init_montessori_method_items(self):
        # Default Montessori Method Items
        default_items = [
            {
                'title': 'Child-Centered Learning',
                'description': 'Our approach respects each child\'s individual development pace and learning style.',
                'icon': 'child',
                'order': 1,
            },
            {
                'title': 'Prepared Environment',
                'description': 'Carefully designed classrooms that promote independence and discovery.',
                'icon': 'hands-helping',
                'order': 2,
            },
            {
                'title': 'Hands-on Learning',
                'description': 'Educational materials that engage the senses and promote concrete understanding.',
                'icon': 'brain',
                'order': 3,
            },
            {
                'title': 'Mixed-Age Groups',
                'description': 'Children learn from and teach each other in multi-age classroom environments.',
                'icon': 'users',
                'order': 4,
            }
        ]

        for item in default_items:
            MontessoriMethodItem.objects.get_or_create(
                title=item['title'],
                defaults={
                    'description': item['description'],
                    'icon': item['icon'],
                    'order': item['order'],
                    'is_active': True
                }
            )

        # Set up the Montessori Method section title
        PageContent.objects.get_or_create(
            page='about',
            section='montessori_method',
            defaults={
                'title': 'The Montessori Method',
                'content': 'Discover our unique approach to education that nurtures each child\'s potential.',
                'order': 5,
                'is_active': True
            }
        )

    def handle(self, *args, **kwargs):
        self._init_page_content()
        self._init_montessori_method_items()
        self.stdout.write(self.style.SUCCESS('Successfully initialized about page content and Montessori method items'))