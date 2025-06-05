import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from website.models import (
    PageContent,
    MontessoriMethodItem,
    FAQ,
    AcademicProgram,
    CurriculumApproach,
    SpecialProgram,
    AssessmentMethod
)

def copy_default_image(source_name, dest_path):
    """Copy default image from static to media directory"""
    static_dir = os.path.join(settings.BASE_DIR, 'website', 'static', 'website', 'images', 'defaults')
    source_path = os.path.join(static_dir, source_name)
    media_path = os.path.join(settings.MEDIA_ROOT, dest_path)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(media_path), exist_ok=True)
    
    # Only copy if destination doesn't exist
    if not os.path.exists(media_path) and os.path.exists(source_path):
        shutil.copy2(source_path, media_path)

class Command(BaseCommand):
    help = 'Initialize default content for all website pages'

    def _init_about_page(self):
        # Copy default images
        copy_default_image('about-hero.jpg', 'hero_slides/default-about-hero.jpg')
        copy_default_image('story.jpg', 'page_content/default-story-image.jpg')

        # About Hero Section
        PageContent.objects.get_or_create(
            page='about',
            section='about_hero',
            defaults={
                'title': 'About Our School',
                'content': 'Discover the Deigratia Montessori difference and our commitment to excellence in education',
                'order': 1,
                'is_active': True,
                'image': 'hero_slides/default-about-hero.jpg'
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
                'content': story_content.strip(),
                'order': 4,
                'is_active': True
            }
        )

        # Montessori Method Items
        method_items = [
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

        for item in method_items:
            MontessoriMethodItem.objects.get_or_create(
                title=item['title'],
                defaults=item
            )

    def _init_admissions_page(self):
        # Copy default admissions hero image
        copy_default_image('admissions-hero.jpg', 'hero_slides/default-admissions-hero.jpg')

        # Hero Section
        PageContent.objects.get_or_create(
            page='admissions',
            section='hero',
            defaults={
                'title': 'Join Our Community',
                'content': 'Begin your child\'s journey towards excellence in education',
                'order': 1,
                'is_active': True,
                'image': 'hero_slides/default-admissions-hero.jpg'
            }
        )

        # Admission Process Section
        process_content = '''
        <div class="row gy-4">
            <div class="col-md-3">
                <div class="card h-100 border-0 shadow-sm">
                    <div class="card-body text-center">
                        <div class="text-primary mb-3">
                            <i class="fas fa-file-alt fa-3x"></i>
                        </div>
                        <h3 class="h5">1. Submit Inquiry</h3>
                        <p class="card-text">Complete our online inquiry form to begin the admission process.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card h-100 border-0 shadow-sm">
                    <div class="card-body text-center">
                        <div class="text-primary mb-3">
                            <i class="fas fa-building fa-3x"></i>
                        </div>
                        <h3 class="h5">2. School Tour</h3>
                        <p class="card-text">Visit our campus and meet with our admissions team.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card h-100 border-0 shadow-sm">
                    <div class="card-body text-center">
                        <div class="text-primary mb-3">
                            <i class="fas fa-clipboard-check fa-3x"></i>
                        </div>
                        <h3 class="h5">3. Application</h3>
                        <p class="card-text">Submit formal application with required documents.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card h-100 border-0 shadow-sm">
                    <div class="card-body text-center">
                        <div class="text-primary mb-3">
                            <i class="fas fa-check-circle fa-3x"></i>
                        </div>
                        <h3 class="h5">4. Enrollment</h3>
                        <p class="card-text">Receive acceptance and complete enrollment process.</p>
                    </div>
                </div>
            </div>
        </div>
        '''
        PageContent.objects.get_or_create(
            page='admissions',
            section='admission_process',
            defaults={
                'title': 'Our Admission Process',
                'content': process_content.strip(),
                'order': 2,
                'is_active': True
            }
        )

        # Tuition Section
        tuition_content = '''
        <div class="row gy-4">
            <div class="col-md-4">
                <div class="card h-100 border-0 shadow-sm">
                    <div class="card-body">
                        <h3 class="h5 card-title">Toddler Program</h3>
                        <h6 class="text-muted mb-3">Ages 18 months - 3 years</h6>
                        <ul class="list-unstyled mb-4">
                            <li><i class="fas fa-check text-primary me-2"></i>Half Day: $800/month</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Full Day: $1,200/month</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Extended Care Available</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Includes Materials</li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100 border-0 shadow-sm">
                    <div class="card-body">
                        <h3 class="h5 card-title">Primary Program</h3>
                        <h6 class="text-muted mb-3">Ages 3 - 6 years</h6>
                        <ul class="list-unstyled mb-4">
                            <li><i class="fas fa-check text-primary me-2"></i>Half Day: $900/month</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Full Day: $1,400/month</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Extended Care Available</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Includes Materials</li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card h-100 border-0 shadow-sm">
                    <div class="card-body">
                        <h3 class="h5 card-title">Elementary Program</h3>
                        <h6 class="text-muted mb-3">Ages 6 - 12 years</h6>
                        <ul class="list-unstyled mb-4">
                            <li><i class="fas fa-check text-primary me-2"></i>Full Day: $1,600/month</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Extended Care Available</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Includes Materials</li>
                            <li><i class="fas fa-check text-primary me-2"></i>Field Trips Included</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        '''
        PageContent.objects.get_or_create(
            page='admissions',
            section='fees',
            defaults={
                'title': 'Programs & Tuition',
                'content': tuition_content.strip(),
                'order': 3,
                'is_active': True
            }
        )

        # Required Documents Section
        docs_content = '''
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card border-0 shadow-sm">
                    <div class="card-body p-4">
                        <div class="row gy-4">
                            <div class="col-md-6">
                                <h5><i class="fas fa-file-medical text-primary me-2"></i>Medical Records</h5>
                                <ul class="list-unstyled">
                                    <li>- Immunization Records</li>
                                    <li>- Health Assessment Form</li>
                                    <li>- Emergency Contact Info</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h5><i class="fas fa-id-card text-primary me-2"></i>Identification</h5>
                                <ul class="list-unstyled">
                                    <li>- Birth Certificate</li>
                                    <li>- Parent/Guardian ID</li>
                                    <li>- Proof of Address</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h5><i class="fas fa-graduation-cap text-primary me-2"></i>Academic Records</h5>
                                <ul class="list-unstyled">
                                    <li>- Previous School Records</li>
                                    <li>- Progress Reports</li>
                                    <li>- Teacher Recommendations</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h5><i class="fas fa-file-contract text-primary me-2"></i>Additional Forms</h5>
                                <ul class="list-unstyled">
                                    <li>- Enrollment Agreement</li>
                                    <li>- Financial Agreement</li>
                                    <li>- Permission Forms</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
        PageContent.objects.get_or_create(
            page='admissions',
            section='requirements',
            defaults={
                'title': 'Required Documents',
                'content': docs_content.strip(),
                'order': 4,
                'is_active': True
            }
        )

        # Financial Aid Section
        aid_content = '''
        <div class="row justify-content-center">
            <div class="col-lg-8 text-center">
                <p class="lead mb-4">We believe that quality education should be accessible to all families.</p>
            <div class="row gy-4">
                <div class="col-md-6">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="card-body">
                            <i class="fas fa-hand-holding-usd fa-3x text-primary mb-3"></i>
                            <h5>Need-Based Aid</h5>
                            <p>Financial assistance available based on family income and circumstances.</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card h-100 border-0 shadow-sm">
                        <div class="card-body">
                            <i class="fas fa-award fa-3x text-primary mb-3"></i>
                            <h5>Merit Scholarships</h5>
                            <p>Scholarships available for exceptional students and special circumstances.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
        PageContent.objects.get_or_create(
            page='admissions',
            section='scholarships',
            defaults={
                'title': 'Financial Aid & Scholarships',
                'content': aid_content.strip(),
                'order': 5,
                'is_active': True
            }
        )

        # Initialize Admissions FAQs
        faqs = [
            {
                'question': 'When should I apply?',
                'answer': 'We accept applications year-round, but encourage early submission as spaces are limited. Priority enrollment for the following school year begins in January.'
            },
            {
                'question': 'Is previous Montessori experience required?',
                'answer': 'No, previous Montessori experience is not required. Our teachers are experienced in helping children transition into the Montessori environment.'
            },
            {
                'question': 'What is the student-teacher ratio?',
                'answer': 'Our student-teacher ratios are maintained at optimal levels: 6:1 for toddlers, 10:1 for primary, and 12:1 for elementary programs.'
            }
        ]

        for i, faq in enumerate(faqs, 1):
            FAQ.objects.get_or_create(
                page='admissions',
                question=faq['question'],
                defaults={
                    'answer': faq['answer'],
                    'order': i,
                    'is_active': True
                }
            )

    def _init_academics_page(self):
        # Copy default images
        copy_default_image('academics-hero.jpg', 'hero_slides/default-academics-hero.jpg')
        copy_default_image('curriculum-image.jpg', 'page_content/default-curriculum-image.jpg')

        # Hero Section
        PageContent.objects.get_or_create(
            page='academics',
            section='academics_hero',
            defaults={
                'title': 'Academic Excellence',
                'content': 'Discover our comprehensive Montessori curriculum designed to nurture every child\'s potential',
                'image': 'hero_slides/default-academics-hero.jpg',
                'order': 1,
                'is_active': True
            }
        )

        # Curriculum Image Section
        PageContent.objects.get_or_create(
            page='academics',
            section='curriculum_image',
            defaults={
                'image': 'page_content/default-curriculum-image.jpg',
                'order': 2,
                'is_active': True
            }
        )

        # Assessment Intro Section
        PageContent.objects.get_or_create(
            page='academics',
            section='assessment_intro',
            defaults={
                'content': 'We believe in assessing children\'s progress in a way that respects their individual development and maintains the joy of learning.',
                'order': 3,
                'is_active': True
            }
        )

        # CTA Section
        PageContent.objects.get_or_create(
            page='academics',
            section='cta_section',
            defaults={
                'title': 'Ready to Begin Your Child\'s Journey?',
                'content': 'Experience the difference of a Montessori education at Deigratia Montessori School.',
                'order': 4,
                'is_active': True
            }
        )

        # Initialize Academic Programs
        programs = [
            {
                'title': 'Toddler Program',
                'program_type': 'toddler',
                'age_range': 'Ages 18 months - 3 years',
                'description': 'Our toddler program provides a nurturing environment where young children begin their journey of discovery and independence.',
                'features': [
                    'Practical Life Skills',
                    'Sensorial Development',
                    'Language Development',
                    'Motor Skills'
                ],
                'order': 1
            },
            {
                'title': 'Primary Program',
                'program_type': 'primary',
                'age_range': 'Ages 3 - 6 years',
                'description': 'The primary program builds upon the foundation of early learning while introducing more complex concepts and materials.',
                'features': [
                    'Mathematics',
                    'Language Arts',
                    'Cultural Studies',
                    'Science & Nature'
                ],
                'order': 2
            },
            {
                'title': 'Elementary Program',
                'program_type': 'elementary',
                'age_range': 'Ages 6 - 12 years',
                'description': 'Our elementary program offers a rich curriculum that encourages critical thinking and deeper understanding.',
                'features': [
                    'Advanced Mathematics',
                    'Literature & Writing',
                    'History & Geography',
                    'Scientific Research'
                ],
                'order': 3
            }
        ]

        for program in programs:
            AcademicProgram.objects.get_or_create(
                program_type=program['program_type'],
                defaults={
                    'title': program['title'],
                    'age_range': program['age_range'],
                    'description': program['description'],
                    'features': program['features'],
                    'order': program['order'],
                    'is_active': True
                }
            )

        # Initialize Curriculum Approach Items
        curriculum_items = [
            {
                'title': 'Individualized Learning',
                'content': 'Each child progresses at their own pace, following their natural curiosity and interests while being guided by trained Montessori teachers.',
                'order': 1
            },
            {
                'title': 'Hands-on Learning',
                'content': 'Children learn through manipulation of specially designed Montessori materials that make abstract concepts concrete and understandable.',
                'order': 2
            },
            {
                'title': 'Integrated Curriculum',
                'content': 'Subjects are not taught in isolation but are interconnected, helping children understand the relationships between different areas of study.',
                'order': 3
            }
        ]

        for item in curriculum_items:
            CurriculumApproach.objects.get_or_create(
                title=item['title'],
                defaults={
                    'content': item['content'],
                    'order': item['order'],
                    'is_active': True
                }
            )

        # Initialize Special Programs
        special_programs = [
            {
                'title': 'Music & Movement',
                'description': 'Weekly music classes introducing rhythm, singing, and basic instruments.',
                'icon': 'music',
                'order': 1
            },
            {
                'title': 'Art & Creativity',
                'description': 'Regular art sessions exploring various mediums and techniques.',
                'icon': 'palette',
                'order': 2
            },
            {
                'title': 'Garden & Nature',
                'description': 'Hands-on experience with plants and nature in our school garden.',
                'icon': 'seedling',
                'order': 3
            },
            {
                'title': 'Cultural Studies',
                'description': 'Learning about different cultures, languages, and traditions.',
                'icon': 'globe',
                'order': 4
            }
        ]

        for program in special_programs:
            SpecialProgram.objects.get_or_create(
                title=program['title'],
                defaults={
                    'description': program['description'],
                    'icon': program['icon'],
                    'order': program['order'],
                    'is_active': True
                }
            )

        # Initialize Assessment Methods
        assessment_methods = [
            {
                'title': 'Observation Based',
                'description': 'Teachers maintain detailed records of each child\'s activities and progress through careful daily observation.',
                'icon': 'clipboard-check',
                'order': 1
            },
            {
                'title': 'Regular Communication',
                'description': 'Parent-teacher conferences are held regularly to discuss your child\'s development and achievements.',
                'icon': 'comments',
                'order': 2
            },
            {
                'title': 'Portfolio Development',
                'description': 'Each child maintains a portfolio of work that demonstrates their progress and achievements.',
                'icon': 'book-reader',
                'order': 3
            },
            {
                'title': 'Progress Reports',
                'description': 'Detailed progress reports are provided twice a year, highlighting your child\'s growth in all areas.',
                'icon': 'chart-line',
                'order': 4
            }
        ]

        for method in assessment_methods:
            AssessmentMethod.objects.get_or_create(
                title=method['title'],
                defaults={
                    'description': method['description'],
                    'icon': method['icon'],
                    'order': method['order'],
                    'is_active': True
                }
            )

    def _init_events_page(self):
        # Copy default images
        copy_default_image('events-hero.jpg', 'hero_slides/default-events-hero.jpg')
        copy_default_image('calendar-placeholder.png', 'page_content/default-calendar-placeholder.png')

        # Hero Section
        PageContent.objects.get_or_create(
            page='events',
            section='events_hero',
            defaults={
                'title': 'Our Exciting Events',
                'content': 'Join us for a variety of engaging events throughout the year!',
                'image': 'hero_slides/default-events-hero.jpg',
                'order': 1,
                'is_active': True
            }
        )

        # Newsletter Section
        PageContent.objects.get_or_create(
            page='events',
            section='events_newsletter',
            defaults={
                'title': 'Stay Updated',
                'content': 'Subscribe to our newsletter to receive updates on upcoming events.',
                'button_text': 'Subscribe',
                'order': 2,
                'is_active': True
            }
        )

        # Call to Action Section
        PageContent.objects.get_or_create(
            page='events',
            section='events_cta',
            defaults={
                'title': 'Get Involved',
                'content': 'Volunteer at our events and be a part of our vibrant community.',
                'button_text': 'Volunteer',
                'button_link': '#',
                'order': 3,
                'is_active': True
            }
        )

        # Calendar Placeholder Section
        PageContent.objects.get_or_create(
            page='events',
            section='events_calendar',
            defaults={
                'title': 'Calendar',
                'calendar_placeholder_image': 'page_content/default-calendar-placeholder.png',
                'order': 4,
                'is_active': True
            }
        )

    def handle(self, *args, **kwargs):
        self._init_about_page()
        self._init_admissions_page()
        self._init_academics_page()
        self._init_events_page()
        self.stdout.write(self.style.SUCCESS('Successfully initialized website content'))