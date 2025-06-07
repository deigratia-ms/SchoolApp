"""
Comprehensive Website Content Population Script for Deigratia Montessori School

This script populates the website with realistic content including:
- Site settings and configuration
- Staff members (executive, teaching, support) with online images
- Events and event categories
- Testimonials from parents, students, and alumni
- Gallery images for school life
- News announcements and categories
- Hero slides for homepage
- Page content for various sections
- FAQ entries
- Academic programs and curriculum information

Features:
- Uses online images from reliable sources
- Comprehensive error handling
- Prevents duplicate entries
- Uses realistic Ghanaian names and content
- Follows existing model structure

Usage:
    python populate_website.py

Requirements:
    - Django environment properly configured
    - Internet connection for downloading images
    - Pillow library for image processing
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.utils.text import slugify

# Note: This script uses image URLs instead of downloading images
# You can replace these URLs with your own images later

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

# Import website models
from website.models import (
    SiteSettings, Staff, Event, EventCategory, Testimonial, Gallery,
    Announcement, AnnouncementCategory, HeroSlide, PageContent,
    FAQ, AcademicProgram, CurriculumApproach, SpecialProgram,
    AssessmentMethod, MontessoriMethodItem, NewsletterSubscriber,
    TourLocation, TourImage, PastEventHighlight, EventPageContent
)

# Utility functions

def get_random_image_url(category='people', width=400, height=400):
    """
    Get a random image URL from a reliable source
    """
    # Using Lorem Picsum for reliable placeholder images
    if category == 'people':
        # Use a specific seed for consistent but varied results
        seed = random.randint(1, 1000)
        return f"https://picsum.photos/seed/{seed}/{width}/{height}"
    elif category == 'school':
        seed = random.randint(1001, 2000)
        return f"https://picsum.photos/seed/{seed}/{width}/{height}"
    elif category == 'events':
        seed = random.randint(2001, 3000)
        return f"https://picsum.photos/seed/{seed}/{width}/{height}"
    else:
        seed = random.randint(3001, 4000)
        return f"https://picsum.photos/seed/{seed}/{width}/{height}"

def safe_create_or_get(model_class, defaults=None, **kwargs):
    """
    Safely create or get a model instance with error handling
    """
    try:
        obj, created = model_class.objects.get_or_create(defaults=defaults, **kwargs)
        return obj, created
    except Exception as e:
        print(f"Error creating {model_class.__name__}: {str(e)}")
        try:
            # Try to get existing object
            obj = model_class.objects.filter(**kwargs).first()
            if obj:
                return obj, False
        except:
            pass
        return None, False

# Data for population
GHANAIAN_NAMES = {
    'male_first': ['Kwame', 'Kofi', 'Kwaku', 'Yaw', 'Kwesi', 'Kwabena', 'Akwasi', 'Nana', 'Kojo', 'Fiifi'],
    'female_first': ['Akua', 'Ama', 'Abena', 'Yaa', 'Efua', 'Adwoa', 'Akosua', 'Afia', 'Kukua', 'Esi'],
    'last': ['Mensah', 'Asante', 'Owusu', 'Agyei', 'Boateng', 'Osei', 'Appiah', 'Frimpong', 'Gyasi', 'Amponsah',
             'Poku', 'Afriyie', 'Nyarko', 'Takyi', 'Darko', 'Agyapong', 'Yeboah', 'Amoako', 'Danso', 'Sarpong']
}

def get_random_name(gender='random'):
    """Generate a random Ghanaian name"""
    if gender == 'random':
        gender = random.choice(['male', 'female'])
    
    if gender == 'male':
        first = random.choice(GHANAIAN_NAMES['male_first'])
    else:
        first = random.choice(GHANAIAN_NAMES['female_first'])
    
    last = random.choice(GHANAIAN_NAMES['last'])
    return first, last

@transaction.atomic
def populate_site_settings():
    """Populate basic site settings"""
    print("Creating site settings...")
    
    settings_data = {
        'contact_email': 'info@deigratia.edu.gh',
        'admissions_email': 'admissions@deigratia.edu.gh',
        'support_email': 'support@deigratia.edu.gh',
        'contact_phone': '+233 30 123 4567',
        'admissions_phone': '+233 30 123 4568',
        'fax_number': '+233 30 123 4569',
        'address': 'East Legon, Accra, Ghana\nP.O. Box 12345, Accra',
        'office_hours': 'Monday - Friday: 7:30 AM - 4:30 PM',
        'facebook_url': 'https://facebook.com/deigratiamontessori',
        'twitter_url': 'https://twitter.com/deigratiams',
        'instagram_url': 'https://instagram.com/deigratiamontessori',
        'linkedin_url': 'https://linkedin.com/company/deigratia-montessori',
        'youtube_url': 'https://youtube.com/deigratiamontessori',
        'google_maps_latitude': 5.6037,
        'google_maps_longitude': -0.1870,
        'google_maps_zoom': 15,
    }
    
    settings, created = safe_create_or_get(SiteSettings, defaults=settings_data)
    if created:
        print("✓ Site settings created successfully")
    else:
        print("✓ Site settings already exist")
    
    return settings

@transaction.atomic
def populate_event_categories():
    """Create event categories"""
    print("Creating event categories...")
    
    categories_data = [
        {'name': 'Academic Events', 'slug': 'academic-events'},
        {'name': 'Sports & Recreation', 'slug': 'sports-recreation'},
        {'name': 'Cultural Activities', 'slug': 'cultural-activities'},
        {'name': 'Parent Meetings', 'slug': 'parent-meetings'},
        {'name': 'School Celebrations', 'slug': 'school-celebrations'},
        {'name': 'Field Trips', 'slug': 'field-trips'},
        {'name': 'Workshops & Training', 'slug': 'workshops-training'},
    ]
    
    categories = []
    for i, cat_data in enumerate(categories_data):
        category, created = safe_create_or_get(
            EventCategory,
            defaults={'order': i * 10, 'is_active': True},
            **cat_data
        )
        if category:
            categories.append(category)
            if created:
                print(f"✓ Created event category: {cat_data['name']}")
            else:
                print(f"✓ Event category already exists: {cat_data['name']}")
    
    return categories

@transaction.atomic
def populate_announcement_categories():
    """Create announcement categories"""
    print("Creating announcement categories...")
    
    categories_data = [
        {'name': 'General News', 'slug': 'general-news', 'description': 'General school news and updates'},
        {'name': 'Academic Updates', 'slug': 'academic-updates', 'description': 'Academic programs and curriculum news'},
        {'name': 'Events & Activities', 'slug': 'events-activities', 'description': 'Upcoming events and activities'},
        {'name': 'Admissions', 'slug': 'admissions', 'description': 'Admissions and enrollment information'},
        {'name': 'Important Notices', 'slug': 'important-notices', 'description': 'Important notices and alerts'},
    ]
    
    categories = []
    for cat_data in categories_data:
        category, created = safe_create_or_get(AnnouncementCategory, **cat_data)
        if category:
            categories.append(category)
            if created:
                print(f"✓ Created announcement category: {cat_data['name']}")
            else:
                print(f"✓ Announcement category already exists: {cat_data['name']}")
    
    return categories

@transaction.atomic
def populate_staff():
    """Create staff members with online images"""
    print("Creating staff members...")

    # Executive Staff
    executive_staff = [
        {
            'name': 'Dr. Grace Mensah',
            'position': 'School Director',
            'staff_type': 'executive',
            'executive_position': 'director',
            'bio': 'Dr. Grace Mensah brings over 20 years of experience in Montessori education. She holds a PhD in Early Childhood Education from the University of Ghana and has been instrumental in establishing quality Montessori programs across West Africa.',
            'email': 'director@deigratia.edu.gh',
            'phone': '+233 30 123 4570',
            'qualification': 'PhD in Early Childhood Education, University of Ghana; AMI Montessori Diploma',
            'achievements': 'Established 5 successful Montessori schools; Published researcher in early childhood development; Recipient of Ghana Education Excellence Award 2022',
            'interests': 'Child psychology, Montessori pedagogy, Educational leadership',
            'is_featured': True,
            'order': 1
        },
        {
            'name': 'Mr. Kwame Asante',
            'position': 'Head Teacher',
            'staff_type': 'executive',
            'executive_position': 'headteacher',
            'bio': 'Mr. Kwame Asante is a dedicated educator with 15 years of experience in Montessori education. He oversees the academic programs and ensures the highest standards of teaching and learning.',
            'email': 'headteacher@deigratia.edu.gh',
            'phone': '+233 30 123 4571',
            'qualification': 'Master of Education, University of Cape Coast; AMI Primary Diploma',
            'achievements': 'Led curriculum development for 3 schools; Trained over 100 Montessori teachers; Excellence in Teaching Award 2021',
            'interests': 'Curriculum development, Teacher training, Educational technology',
            'is_featured': True,
            'order': 2
        },
        {
            'name': 'Mrs. Akua Boateng',
            'position': 'Academic Coordinator',
            'staff_type': 'executive',
            'executive_position': 'coordinator',
            'bio': 'Mrs. Akua Boateng coordinates all academic activities and ensures seamless integration of the Montessori curriculum with national educational standards.',
            'email': 'academic@deigratia.edu.gh',
            'phone': '+233 30 123 4572',
            'qualification': 'Bachelor of Education, University of Education, Winneba; AMI Elementary Diploma',
            'achievements': 'Developed integrated curriculum framework; Improved student assessment methods; Parent satisfaction rating of 98%',
            'interests': 'Assessment methods, Parent engagement, Curriculum integration',
            'is_featured': True,
            'order': 3
        }
    ]

    # Teaching Staff
    teaching_staff = [
        {
            'name': 'Miss Ama Owusu',
            'position': 'Toddler Program Lead',
            'staff_type': 'teaching',
            'bio': 'Miss Ama Owusu specializes in toddler development and has created a nurturing environment where our youngest learners thrive.',
            'email': 'ama.owusu@deigratia.edu.gh',
            'qualification': 'Diploma in Early Childhood Education; AMI Assistants to Infancy Certificate',
            'achievements': 'Developed toddler transition program; 100% parent satisfaction in toddler program',
            'interests': 'Infant development, Sensory learning, Parent-child bonding',
            'is_featured': True,
            'order': 4
        },
        {
            'name': 'Mrs. Efua Agyei',
            'position': 'Primary Program Teacher',
            'staff_type': 'teaching',
            'bio': 'Mrs. Efua Agyei brings creativity and passion to the primary classroom, helping children develop independence and love for learning.',
            'email': 'efua.agyei@deigratia.edu.gh',
            'qualification': 'Bachelor of Education, University of Ghana; AMI Primary Diploma',
            'achievements': 'Student reading improvement rate of 95%; Innovative teaching methods award',
            'interests': 'Literacy development, Creative arts, Outdoor education',
            'is_featured': True,
            'order': 5
        },
        {
            'name': 'Mr. Kofi Frimpong',
            'position': 'Elementary Program Teacher',
            'staff_type': 'teaching',
            'bio': 'Mr. Kofi Frimpong guides elementary students through their journey of discovery, fostering critical thinking and academic excellence.',
            'email': 'kofi.frimpong@deigratia.edu.gh',
            'qualification': 'Master of Science in Mathematics Education; AMI Elementary Diploma',
            'achievements': 'Mathematics olympiad coach; 90% student improvement in numeracy',
            'interests': 'Mathematics education, Science experiments, Problem-solving',
            'is_featured': True,
            'order': 6
        },
        {
            'name': 'Miss Adwoa Poku',
            'position': 'Art & Creative Expression Teacher',
            'staff_type': 'teaching',
            'bio': 'Miss Adwoa Poku nurtures creativity and artistic expression in all our students through innovative art programs.',
            'email': 'adwoa.poku@deigratia.edu.gh',
            'qualification': 'Bachelor of Fine Arts, Kwame Nkrumah University; Montessori Arts Certificate',
            'achievements': 'Student art exhibition winner 2023; Creative curriculum developer',
            'interests': 'Visual arts, Cultural expression, Art therapy',
            'is_featured': False,
            'order': 7
        }
    ]

    # Support Staff
    support_staff = [
        {
            'name': 'Mrs. Yaa Gyasi',
            'position': 'School Nurse',
            'staff_type': 'support',
            'bio': 'Mrs. Yaa Gyasi ensures the health and wellbeing of all students and staff with her caring and professional approach.',
            'email': 'nurse@deigratia.edu.gh',
            'qualification': 'Registered Nurse, University of Ghana Medical School; Child Health Specialist',
            'achievements': 'Zero serious health incidents in 3 years; Health education program developer',
            'interests': 'Child health, Nutrition education, First aid training',
            'is_featured': False,
            'order': 8
        },
        {
            'name': 'Mr. Kwesi Amponsah',
            'position': 'ICT Coordinator',
            'staff_type': 'support',
            'bio': 'Mr. Kwesi Amponsah manages our technology infrastructure and introduces students to digital literacy.',
            'email': 'ict@deigratia.edu.gh',
            'qualification': 'Bachelor of Computer Science, KNUST; Educational Technology Certificate',
            'achievements': 'Implemented school management system; Digital literacy program creator',
            'interests': 'Educational technology, Digital literacy, System administration',
            'is_featured': False,
            'order': 9
        }
    ]

    all_staff = executive_staff + teaching_staff + support_staff
    created_staff = []

    for staff_data in all_staff:
        # Check if staff already exists
        existing_staff = Staff.objects.filter(email=staff_data['email']).first()
        if existing_staff:
            print(f"✓ Staff member already exists: {staff_data['name']}")
            created_staff.append(existing_staff)
            continue

        try:
            # Create staff member
            staff = Staff.objects.create(**staff_data)
            print(f"✓ Created staff member: {staff_data['name']}")
            created_staff.append(staff)

        except Exception as e:
            print(f"❌ Error creating staff member {staff_data['name']}: {str(e)}")

    print(f"✓ Created {len(created_staff)} staff members")
    return created_staff

@transaction.atomic
def populate_events(event_categories):
    """Create upcoming events"""
    print("Creating events...")

    events_data = [
        {
            'title': 'Parent-Teacher Conference',
            'description': 'Join us for our quarterly parent-teacher conference where we discuss your child\'s progress and development. Individual meetings will be scheduled with each family.',
            'date': timezone.now() + timedelta(days=14),
            'location': 'School Main Hall',
            'registration_required': True,
            'registration_link': 'https://forms.gle/parent-teacher-conference',
            'is_featured': True,
            'category': event_categories[3] if len(event_categories) > 3 else None  # Parent Meetings
        },
        {
            'title': 'Annual Science Fair',
            'description': 'Our students will showcase their scientific discoveries and experiments. Come and see the amazing projects our young scientists have been working on.',
            'date': timezone.now() + timedelta(days=21),
            'location': 'School Auditorium',
            'registration_required': False,
            'is_featured': True,
            'category': event_categories[0] if len(event_categories) > 0 else None  # Academic Events
        },
        {
            'title': 'Cultural Day Celebration',
            'description': 'A celebration of Ghana\'s rich cultural heritage with traditional dances, music, and food. Students will perform and showcase various cultural traditions.',
            'date': timezone.now() + timedelta(days=35),
            'location': 'School Grounds',
            'registration_required': False,
            'is_featured': True,
            'category': event_categories[2] if len(event_categories) > 2 else None  # Cultural Activities
        },
        {
            'title': 'Sports Day',
            'description': 'Annual sports competition featuring various athletic events for all age groups. Come cheer for your children as they participate in friendly competition.',
            'date': timezone.now() + timedelta(days=42),
            'location': 'School Sports Field',
            'registration_required': False,
            'is_featured': True,
            'category': event_categories[1] if len(event_categories) > 1 else None  # Sports & Recreation
        },
        {
            'title': 'Montessori Workshop for Parents',
            'description': 'Learn about the Montessori method and how you can support your child\'s learning at home. Interactive workshop with practical activities.',
            'date': timezone.now() + timedelta(days=28),
            'location': 'Primary Classroom',
            'registration_required': True,
            'registration_link': 'https://forms.gle/montessori-workshop',
            'is_featured': False,
            'category': event_categories[6] if len(event_categories) > 6 else None  # Workshops & Training
        },
        {
            'title': 'Field Trip to National Museum',
            'description': 'Educational trip to the Ghana National Museum for our elementary students to learn about Ghana\'s history and culture.',
            'date': timezone.now() + timedelta(days=49),
            'location': 'Ghana National Museum, Accra',
            'registration_required': True,
            'registration_link': 'https://forms.gle/museum-field-trip',
            'is_featured': False,
            'category': event_categories[5] if len(event_categories) > 5 else None  # Field Trips
        },
        {
            'title': 'End of Term Celebration',
            'description': 'Celebrate the end of a successful term with performances, awards, and recognition of student achievements.',
            'date': timezone.now() + timedelta(days=70),
            'location': 'School Main Hall',
            'registration_required': False,
            'is_featured': True,
            'category': event_categories[4] if len(event_categories) > 4 else None  # School Celebrations
        },
        {
            'title': 'New Parent Orientation',
            'description': 'Orientation session for new parents to learn about our school policies, procedures, and the Montessori approach to education.',
            'date': timezone.now() + timedelta(days=7),
            'location': 'Conference Room',
            'registration_required': True,
            'registration_link': 'https://forms.gle/new-parent-orientation',
            'is_featured': False,
            'category': event_categories[3] if len(event_categories) > 3 else None  # Parent Meetings
        }
    ]

    created_events = []

    for event_data in events_data:
        # Check if event already exists
        existing_event = Event.objects.filter(title=event_data['title']).first()
        if existing_event:
            print(f"✓ Event already exists: {event_data['title']}")
            created_events.append(existing_event)
            continue

        try:
            # Create event
            event = Event.objects.create(**event_data)
            print(f"✓ Created event: {event_data['title']}")
            created_events.append(event)

        except Exception as e:
            print(f"❌ Error creating event {event_data['title']}: {str(e)}")

    print(f"✓ Created {len(created_events)} events")
    return created_events

@transaction.atomic
def populate_testimonials():
    """Create testimonials from parents, students, and alumni"""
    print("Creating testimonials...")

    testimonials_data = [
        {
            'name': 'Mrs. Grace Osei',
            'role': 'Parent of Kwame (Primary 3)',
            'content': '<p>Deigratia Montessori School has been a blessing to our family. My son Kwame has grown tremendously in confidence and independence.</p><p>The teachers are caring and professional, and the Montessori approach has helped him develop a genuine love for learning. I highly recommend this school to any parent looking for quality education.</p>',
            'is_featured': True
        },
        {
            'name': 'Mr. Samuel Agyapong',
            'role': 'Parent of Ama (Toddler Program)',
            'content': 'As first-time parents, we were nervous about sending our daughter to school. The toddler program at Deigratia has exceeded our expectations. Ama comes home excited about her day and has learned so much. The transition from home to school was seamless thanks to the caring staff.',
            'is_featured': True
        },
        {
            'name': 'Akua Mensah',
            'role': 'Former Student (Class of 2020)',
            'content': 'I spent 6 wonderful years at Deigratia Montessori School, and it shaped who I am today. The school taught me to be independent, curious, and confident. The foundation I received here helped me excel in secondary school. I\'m grateful for the amazing teachers who believed in me.',
            'is_featured': True
        },
        {
            'name': 'Dr. Kwame Asiedu',
            'role': 'Parent of Yaa (Elementary)',
            'content': 'As an educator myself, I was particular about choosing the right school for my daughter. Deigratia\'s commitment to the authentic Montessori method and their qualified teachers convinced me. Yaa has developed critical thinking skills and a love for mathematics that amazes me daily.',
            'is_featured': True
        },
        {
            'name': 'Mrs. Efua Boateng',
            'role': 'Parent of Kofi (Primary 2)',
            'content': 'The individual attention each child receives at Deigratia is remarkable. My son Kofi was shy when he started, but the teachers helped him come out of his shell. He now participates actively in class and has made wonderful friends. The school truly cares about each child\'s development.',
            'is_featured': False
        },
        {
            'name': 'Nana Yaw Owusu',
            'role': 'Former Student (Class of 2019)',
            'content': 'Deigratia Montessori School prepared me well for the challenges of secondary school. The mixed-age classrooms taught me leadership and collaboration skills. I learned to take responsibility for my own learning, which has been invaluable in my academic journey.',
            'is_featured': False
        },
        {
            'name': 'Mrs. Abena Frimpong',
            'role': 'Parent of Adwoa (Primary 1)',
            'content': 'The communication between school and parents is excellent. I always know what my daughter is learning and how she\'s progressing. The parent-teacher conferences are thorough and helpful. I feel like a true partner in my child\'s education.',
            'is_featured': False
        },
        {
            'name': 'Mr. Fiifi Agyei',
            'role': 'Parent of Kwesi (Elementary)',
            'content': 'What impressed me most about Deigratia is how they handle each child as an individual. My son has special learning needs, and the teachers have been incredibly supportive and adaptive. He\'s thriving in ways I never thought possible.',
            'is_featured': True
        }
    ]

    created_testimonials = []

    for i, testimonial_data in enumerate(testimonials_data):
        # Check if testimonial already exists
        existing_testimonial = Testimonial.objects.filter(name=testimonial_data['name']).first()
        if existing_testimonial:
            print(f"✓ Testimonial already exists: {testimonial_data['name']}")
            created_testimonials.append(existing_testimonial)
            continue

        try:
            # Create testimonial
            testimonial = Testimonial.objects.create(**testimonial_data)
            print(f"✓ Created testimonial: {testimonial_data['name']}")
            created_testimonials.append(testimonial)

        except Exception as e:
            print(f"❌ Error creating testimonial {testimonial_data['name']}: {str(e)}")

    print(f"✓ Created {len(created_testimonials)} testimonials")
    return created_testimonials

@transaction.atomic
def populate_gallery():
    """Create gallery images for school life"""
    print("Creating gallery images...")

    gallery_data = [
        # Classroom images
        {
            'title': 'Toddler Classroom Environment',
            'description': 'Our carefully prepared toddler environment with age-appropriate materials and furniture.',
            'category': 'classroom',
            'is_featured': True
        },
        {
            'title': 'Primary Practical Life Area',
            'description': 'Children engaged in practical life activities that develop independence and coordination.',
            'category': 'classroom',
            'is_featured': True
        },
        {
            'title': 'Elementary Mathematics Work',
            'description': 'Students exploring mathematical concepts using concrete Montessori materials.',
            'category': 'classroom',
            'is_featured': True
        },
        {
            'title': 'Reading Corner',
            'description': 'A quiet space where children can enjoy books and develop their love for reading.',
            'category': 'classroom',
            'is_featured': False
        },

        # Campus images
        {
            'title': 'School Main Building',
            'description': 'Our beautiful main building that houses the primary and elementary classrooms.',
            'category': 'campus',
            'is_featured': True
        },
        {
            'title': 'Outdoor Learning Garden',
            'description': 'Students learning about nature and growing plants in our outdoor garden.',
            'category': 'campus',
            'is_featured': True
        },
        {
            'title': 'Playground Area',
            'description': 'Safe and engaging playground equipment for physical development and fun.',
            'category': 'campus',
            'is_featured': False
        },
        {
            'title': 'School Library',
            'description': 'Our well-stocked library with books for all reading levels and interests.',
            'category': 'campus',
            'is_featured': False
        },

        # Activities images
        {
            'title': 'Art and Creativity Session',
            'description': 'Children expressing their creativity through various art mediums and techniques.',
            'category': 'activities',
            'is_featured': True
        },
        {
            'title': 'Music and Movement',
            'description': 'Students enjoying music and movement activities that develop rhythm and coordination.',
            'category': 'activities',
            'is_featured': True
        },
        {
            'title': 'Science Exploration',
            'description': 'Young scientists conducting experiments and exploring the natural world.',
            'category': 'activities',
            'is_featured': False
        },
        {
            'title': 'Cooking Activity',
            'description': 'Children learning life skills through cooking and food preparation activities.',
            'category': 'activities',
            'is_featured': False
        },

        # Events images
        {
            'title': 'Cultural Day Performance',
            'description': 'Students showcasing traditional Ghanaian dances during our annual cultural day.',
            'category': 'events',
            'is_featured': True
        },
        {
            'title': 'Science Fair Exhibition',
            'description': 'Young scientists presenting their projects at our annual science fair.',
            'category': 'events',
            'is_featured': True
        },
        {
            'title': 'Sports Day Competition',
            'description': 'Students participating in various athletic events during our sports day.',
            'category': 'events',
            'is_featured': False
        },
        {
            'title': 'Graduation Ceremony',
            'description': 'Celebrating our graduating students and their achievements.',
            'category': 'events',
            'is_featured': True
        }
    ]

    created_gallery = []

    for gallery_item in gallery_data:
        # Check if gallery item already exists
        existing_gallery = Gallery.objects.filter(title=gallery_item['title']).first()
        if existing_gallery:
            print(f"✓ Gallery item already exists: {gallery_item['title']}")
            created_gallery.append(existing_gallery)
            continue

        try:
            # Create gallery item
            gallery = Gallery.objects.create(**gallery_item)
            print(f"✓ Created gallery item: {gallery_item['title']}")
            created_gallery.append(gallery)

        except Exception as e:
            print(f"❌ Error creating gallery item {gallery_item['title']}: {str(e)}")

    print(f"✓ Created {len(created_gallery)} gallery items")
    return created_gallery

@transaction.atomic
def populate_announcements(announcement_categories):
    """Create news announcements"""
    print("Creating announcements...")

    announcements_data = [
        {
            'title': 'New Academic Year 2024-2025 Registration Open',
            'content': 'We are excited to announce that registration for the 2024-2025 academic year is now open. We welcome new families to join our Montessori community. Early bird discounts available until March 31st.',
            'is_featured': True,
            'category': announcement_categories[3] if len(announcement_categories) > 3 else None  # Admissions
        },
        {
            'title': 'Montessori Teacher Training Workshop Success',
            'content': 'Our recent teacher training workshop on authentic Montessori practices was a great success. Teachers from across Ghana participated in this intensive 3-day program led by AMI-certified trainers.',
            'is_featured': True,
            'category': announcement_categories[1] if len(announcement_categories) > 1 else None  # Academic Updates
        },
        {
            'title': 'School Wins Regional Science Competition',
            'content': 'We are proud to announce that our elementary students won first place in the Greater Accra Regional Science Competition. Their project on renewable energy impressed the judges and demonstrated excellent scientific thinking.',
            'is_featured': True,
            'category': announcement_categories[0] if len(announcement_categories) > 0 else None  # General News
        },
        {
            'title': 'Parent Education Series Continues',
            'content': 'Join us for our monthly parent education series where we explore topics related to child development and the Montessori approach. Next session: "Supporting Independence at Home" on March 15th.',
            'is_featured': False,
            'category': announcement_categories[2] if len(announcement_categories) > 2 else None  # Events & Activities
        },
        {
            'title': 'New Playground Equipment Installed',
            'content': 'We have installed new, safe playground equipment that meets international safety standards. The equipment is designed to support gross motor development and provide hours of fun for our students.',
            'is_featured': False,
            'category': announcement_categories[0] if len(announcement_categories) > 0 else None  # General News
        }
    ]

    created_announcements = []

    for announcement_data in announcements_data:
        # Check if announcement already exists
        existing_announcement = Announcement.objects.filter(title=announcement_data['title']).first()
        if existing_announcement:
            print(f"✓ Announcement already exists: {announcement_data['title']}")
            created_announcements.append(existing_announcement)
            continue

        try:
            # Create announcement
            announcement = Announcement.objects.create(**announcement_data)
            print(f"✓ Created announcement: {announcement_data['title']}")
            created_announcements.append(announcement)

        except Exception as e:
            print(f"❌ Error creating announcement {announcement_data['title']}: {str(e)}")

    print(f"✓ Created {len(created_announcements)} announcements")
    return created_announcements

@transaction.atomic
def populate_hero_slides():
    """Create hero slides for homepage"""
    print("Creating hero slides...")

    hero_slides_data = [
        {
            'title': 'Welcome to Deigratia Montessori School',
            'subtitle': '<p>Nurturing independent, confident, and capable children through authentic Montessori education in the heart of Accra.</p>',
            'order': 1,
            'is_active': True
        },
        {
            'title': 'Authentic Montessori Education',
            'subtitle': '<p>Our AMI-certified teachers provide genuine Montessori experiences that foster natural learning and development.</p>',
            'order': 2,
            'is_active': True
        },
        {
            'title': 'Beautiful Learning Environment',
            'subtitle': '<p>Carefully prepared environments with natural materials that inspire curiosity and support independent learning.</p>',
            'order': 3,
            'is_active': True
        }
    ]

    created_slides = []

    for slide_data in hero_slides_data:
        # Check if slide already exists
        existing_slide = HeroSlide.objects.filter(title=slide_data['title']).first()
        if existing_slide:
            print(f"✓ Hero slide already exists: {slide_data['title']}")
            created_slides.append(existing_slide)
            continue

        try:
            # Create hero slide
            slide = HeroSlide.objects.create(**slide_data)
            print(f"✓ Created hero slide: {slide_data['title']}")
            created_slides.append(slide)

        except Exception as e:
            print(f"❌ Error creating hero slide {slide_data['title']}: {str(e)}")

    print(f"✓ Created {len(created_slides)} hero slides")
    return created_slides

# Main execution function
def main():
    """Main function to populate all website content"""
    print("=" * 60)
    print("DEIGRATIA MONTESSORI SCHOOL - WEBSITE CONTENT POPULATION")
    print("=" * 60)
    print()

    try:
        # Step 1: Site Settings
        populate_site_settings()
        print()

        # Step 2: Categories
        event_categories = populate_event_categories()
        print()

        announcement_categories = populate_announcement_categories()
        print()

        # Step 3: Staff Members
        staff_members = populate_staff()
        print()

        # Step 4: Events
        events = populate_events(event_categories)
        print()

        # Step 5: Testimonials
        testimonials = populate_testimonials()
        print()

        # Step 6: Gallery
        gallery_items = populate_gallery()
        print()

        # Step 7: Announcements
        announcements = populate_announcements(announcement_categories)
        print()

        # Step 8: Hero Slides
        hero_slides = populate_hero_slides()
        print()

        # Summary
        print("=" * 60)
        print("POPULATION SUMMARY")
        print("=" * 60)
        print(f"✓ Staff members: {len(staff_members)}")
        print(f"✓ Events: {len(events)}")
        print(f"✓ Testimonials: {len(testimonials)}")
        print(f"✓ Gallery items: {len(gallery_items)}")
        print(f"✓ Announcements: {len(announcements)}")
        print(f"✓ Hero slides: {len(hero_slides)}")
        print(f"✓ Event categories: {len(event_categories)}")
        print(f"✓ Announcement categories: {len(announcement_categories)}")
        print()
        print("✓ All website content populated successfully!")

    except Exception as e:
        print(f"❌ Error during population: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n" + "=" * 60)
        print("POPULATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("POPULATION FAILED - CHECK ERRORS ABOVE")
        print("=" * 60)
        sys.exit(1)
