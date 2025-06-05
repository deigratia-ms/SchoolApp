from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

# Import career models
from .models_career import JobPosition, JobApplication

class SiteSettings(models.Model):
    # Basic Information
    school_logo = models.ImageField(upload_to='site/', help_text="Main school logo displayed in the header")
    footer_logo = models.ImageField(upload_to='site/', null=True, blank=True, help_text="Optional different logo for footer")

    # Contact Information
    contact_email = models.EmailField(help_text="Main contact email address")
    admissions_email = models.EmailField(blank=True, help_text="Email for admissions inquiries")
    support_email = models.EmailField(blank=True, help_text="Email for technical support")
    contact_phone = models.CharField(max_length=20, help_text="Main contact phone number")
    admissions_phone = models.CharField(max_length=20, blank=True, help_text="Phone for admissions inquiries")
    fax_number = models.CharField(max_length=20, blank=True, help_text="Fax number if available")
    address = models.TextField(help_text="School's physical address")
    office_hours = models.CharField(max_length=100, default="Mon-Fri: 8:00 AM - 4:00 PM", help_text="Office hours")

    # Google Maps Integration
    google_maps_api_key = models.CharField(max_length=255, blank=True, help_text="Google Maps API key for map integration")
    google_maps_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, help_text="Latitude coordinate for Google Maps")
    google_maps_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, help_text="Longitude coordinate for Google Maps")
    google_maps_zoom = models.PositiveSmallIntegerField(default=15, help_text="Zoom level for Google Maps (1-20)")

    # Social Media
    facebook_url = models.URLField(blank=True, help_text="Facebook page URL")
    twitter_url = models.URLField(blank=True, help_text="Twitter profile URL")
    instagram_url = models.URLField(blank=True, help_text="Instagram profile URL")
    linkedin_url = models.URLField(blank=True, help_text="LinkedIn profile URL")
    youtube_url = models.URLField(blank=True, help_text="YouTube channel URL")

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        if SiteSettings.objects.exists() and not self.pk:
            raise ValidationError('There can only be one SiteSettings instance')
        return super(SiteSettings, self).save(*args, **kwargs)

class FAQ(models.Model):
    PAGE_CHOICES = [
        ('home', 'Home Page'),
        ('about', 'About Us'),
        ('academics', 'Academics'),
        ('admissions', 'Admissions'),
        ('events', 'Events'),
        ('news', 'News'),
        ('contact', 'Contact'),
    ]

    page = models.CharField(max_length=20, choices=PAGE_CHOICES)
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page', 'order']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return f"{self.get_page_display()} - {self.question}"

class AcademicProgram(models.Model):
    PROGRAM_TYPES = [
        ('toddler', 'Toddler Program'),
        ('primary', 'Primary Program'),
        ('elementary', 'Elementary Program'),
    ]

    title = models.CharField(max_length=100)
    program_type = models.CharField(max_length=20, choices=PROGRAM_TYPES)
    age_range = models.CharField(max_length=50)
    description = models.TextField()
    image = models.ImageField(upload_to='academics/programs/', null=True, blank=True)
    features = models.JSONField(default=list, help_text="List of program features")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Academic Program"
        verbose_name_plural = "Academic Programs"

    def __str__(self):
        return self.title

class CurriculumApproach(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Curriculum Approach Item"
        verbose_name_plural = "Curriculum Approach Items"

    def __str__(self):
        return self.title

class SpecialProgram(models.Model):
    ICON_CHOICES = [
        ('music', 'Music'),
        ('palette', 'Art'),
        ('seedling', 'Garden'),
        ('globe', 'Cultural'),
        ('microscope', 'Science'),
        ('book', 'Language'),
        ('robot', 'Technology'),
        ('heart', 'Social-Emotional'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=20, choices=ICON_CHOICES)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Special Program"
        verbose_name_plural = "Special Programs"

    def __str__(self):
        return self.title

class AssessmentMethod(models.Model):
    ICON_CHOICES = [
        ('clipboard-check', 'Observation'),
        ('comments', 'Communication'),
        ('book-reader', 'Portfolio'),
        ('chart-line', 'Progress'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=20, choices=ICON_CHOICES)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Assessment Method"
        verbose_name_plural = "Assessment Methods"

    def __str__(self):
        return self.title

class PageContent(models.Model):
    PAGE_CHOICES = [
        ('home', 'Home Page'),
        ('about', 'About Us'),
        ('academics', 'Academics'),
        ('admissions', 'Admissions'),
        ('events', 'Events'),
        ('news', 'News & Announcements'),
        ('contact', 'Contact Us'),
        ('staff', 'Our Staff'),
        ('career', 'Careers'),
        ('calendar', 'School Calendar'),
        ('privacy', 'Privacy Policy'),
        ('terms', 'Terms of Service'),
        ('faq', 'FAQs'),
    ]

    SECTION_CHOICES = [
        # Home Page Sections
        ('hero', 'Hero Section'),
        ('about_preview', 'About Preview'),
        ('featured_programs', 'Featured Programs'),
        ('why_choose_us', 'Why Choose Us'),

        # About Page Sections
        ('about_hero', 'About Hero Section'),
        ('mission', 'Mission Statement'),
        ('vision', 'Vision Statement'),
        ('story', 'Our Story'),
        ('montessori_method', 'Montessori Method'),
        ('values', 'Our Values'),

        # Academics Page Sections
        ('academics_hero', 'Academics Hero Section'),
        ('curriculum_image', 'Curriculum Approach Image'),
        ('assessment_intro', 'Assessment Introduction'),
        ('cta_section', 'Academics Call to Action'),

        # Admissions Page Sections
        ('admission_process', 'Admission Process'),
        ('requirements', 'Requirements'),
        ('fees', 'Fees and Tuition'),
        ('scholarships', 'Scholarships'),

        # Events Page Sections
        ('events_hero', 'Events Hero Section'),
        ('events_newsletter', 'Events Newsletter Section'),
        ('events_cta', 'Events Call to Action'),
        ('events_calendar', 'Events Calendar Placeholder'),

        # News Page Sections
        ('news_hero', 'News Hero Section'),

        # Contact Page Sections
        ('contact_hero', 'Contact Hero Section'),

        # Staff Page Sections
        ('staff_hero', 'Staff Hero Section'),

        # Career Page Sections
        ('career_hero', 'Career Hero Section'),
        ('career_intro', 'Career Introduction'),

        # Calendar Page Sections
        ('calendar_hero', 'Calendar Hero Section'),
        ('calendar_content', 'Calendar Content'),

        # Policy Pages Sections
        ('privacy_hero', 'Privacy Policy Hero Section'),
        ('privacy_content', 'Privacy Policy Content'),
        ('terms_hero', 'Terms of Service Hero Section'),
        ('terms_content', 'Terms of Service Content'),
        ('faq_hero', 'FAQ Hero Section'),
    ]

    page = models.CharField(max_length=20, choices=PAGE_CHOICES)
    section = models.CharField(max_length=50, choices=SECTION_CHOICES)
    title = models.CharField(max_length=200, help_text="Title for this section")
    content = models.TextField(help_text="Main content text for this section", blank=True)
    def get_upload_path(instance, filename):
        """Determine the upload path based on the section type"""
        if instance.section in ['hero', 'about_hero', 'academics_hero', 'events_hero', 'news_hero', 'contact_hero', 'staff_hero', 'career_hero', 'calendar_hero', 'privacy_hero', 'terms_hero', 'faq_hero']:
            return f'hero_slides/{filename}'
        elif instance.section == 'curriculum_image':
            return f'academics/curriculum/{filename}'
        elif instance.section == 'story':
            return f'about/story/{filename}'
        return f'page_content/{filename}'

    image = models.ImageField(
        upload_to=get_upload_path,
        null=True,
        blank=True,
        help_text="Image for this section."
    )
    calendar_placeholder_image = models.ImageField(
        upload_to='page_content/',
        null=True,
        blank=True,
        help_text="Placeholder image for the calendar widget"
    )
    button_text = models.CharField(max_length=50, blank=True, null=True)
    button_link = models.CharField(max_length=200, blank=True, null=True)

    def get_image_help_text(self):
        """Get context-specific help text for the image field"""
        if self.section == 'story':
            return "Main image shown beside the story text. Recommended size: 800x600 pixels."
        elif self.section in ['hero', 'about_hero', 'academics_hero', 'events_hero', 'news_hero', 'contact_hero', 'staff_hero', 'career_hero', 'calendar_hero', 'privacy_hero', 'terms_hero', 'faq_hero']:
            return "Banner/hero image displayed at the top of the page. Recommended size: 1920x600 pixels."
        return "Image for this section. Use high-quality images appropriate for their purpose."

    def save(self, *args, **kwargs):
        # Only set default images for new objects (not when updating)
        if not self.pk and not self.image:
            # Set default images based on section
            if self.section == 'hero':
                self.image = 'hero_slides/default-admissions-hero.jpg'
            elif self.section == 'about_hero':
                self.image = 'hero_slides/default-about-hero.jpg'
            elif self.section == 'academics_hero':
                self.image = 'hero_slides/default-academics-hero.jpg'
            elif self.section == 'events_hero':
                self.image = 'hero_slides/default-events-hero.jpg'
            elif self.section == 'news_hero':
                self.image = 'hero_slides/default-news-hero.jpg'
            elif self.section == 'contact_hero':
                self.image = 'hero_slides/default-contact-hero.jpg'
            elif self.section == 'staff_hero':
                self.image = 'hero_slides/default-staff-hero.jpg'
            elif self.section == 'career_hero':
                self.image = 'hero_slides/default-career-hero.jpg'
            elif self.section == 'calendar_hero':
                self.image = 'hero_slides/default-calendar-hero.jpg'
            elif self.section == 'privacy_hero':
                self.image = 'hero_slides/default-privacy-hero.jpg'
            elif self.section == 'terms_hero':
                self.image = 'hero_slides/default-terms-hero.jpg'
            elif self.section == 'faq_hero':
                self.image = 'hero_slides/default-faq-hero.jpg'
            elif self.section == 'story':
                self.image = 'page_content/default-story-image.jpg'
        super().save(*args, **kwargs)
    order = models.PositiveIntegerField(default=0, help_text="Order in which this section appears on the page")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page', 'order']
        unique_together = ['page', 'section']
        verbose_name = "Page Content"
        verbose_name_plural = "Page Contents"

    def __str__(self):
        return f"{self.get_page_display()} - {self.get_section_display()}"

class HeroSlide(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    image = models.ImageField(upload_to='hero_slides/')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    date_subscribed = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"
        ordering = ['-date_subscribed']

    def __str__(self):
        return self.email

class AnnouncementCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Announcement Category"
        verbose_name_plural = "Announcement Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('website:news-category', kwargs={'slug': self.slug})

    def announcement_count(self):
        return self.announcements.count()

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, null=False, blank=False)  # Explicitly required
    content = models.TextField()
    image = models.ImageField(upload_to='announcements/', null=True, blank=True)
    date_posted = models.DateTimeField(default=timezone.now)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey(AnnouncementCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')

    def save(self, *args, **kwargs):
        # Generate a unique slug if one isn't provided
        if not self.slug:
            # Start with the title slugified
            base_slug = slugify(self.title)
            # If the slug is already taken, append a number
            slug = base_slug
            n = 1
            while Announcement.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date_posted']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('website:announcement-detail', kwargs={'slug': self.slug})



class TourLocation(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='tour_locations/')
    video_url = models.URLField(blank=True, help_text='URL to a video tour (e.g., YouTube)')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('tour-location-detail', kwargs={'pk': self.pk})

class TourImage(models.Model):
    location = models.ForeignKey(TourLocation, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='tour_images/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.location.name}"

class MontessoriMethodItem(models.Model):
    ICON_CHOICES = [
        ('child', 'Child (Child-Centered Learning)'),
        ('hands-helping', 'Hands Helping (Prepared Environment)'),
        ('brain', 'Brain (Hands-on Learning)'),
        ('users', 'Users (Mixed-Age Groups)'),
        ('star', 'Star'),
        ('heart', 'Heart'),
        ('lightbulb', 'Lightbulb'),
        ('book', 'Book'),
        ('graduation-cap', 'Graduation Cap'),
        ('seedling', 'Seedling'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=20, choices=ICON_CHOICES)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Montessori Method Item"
        verbose_name_plural = "Montessori Method Items"

    def __str__(self):
        return self.title

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_sent']

    def __str__(self):
        return f"{self.name} - {self.subject}"

class AdmissionsInquiry(models.Model):
    GRADE_CHOICES = [
        ('toddler', 'Toddler Program (18 months - 3 years)'),
        ('primary', 'Primary Program (3 - 6 years)'),
        ('elementary', 'Elementary Program (6 - 12 years)'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    child_name = models.CharField(max_length=100)
    child_age = models.IntegerField()
    program_interest = models.CharField(max_length=20, choices=GRADE_CHOICES)
    start_date = models.DateField()
    message = models.TextField(blank=True)
    date_submitted = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], default='new')

    class Meta:
        ordering = ['-date_submitted']
        verbose_name_plural = "Admissions Inquiries"

    def __str__(self):
        return f"{self.child_name} - {self.program_interest}"

class Staff(models.Model):
    STAFF_TYPE_CHOICES = [
        ('executive', 'Executive Staff'),
        ('teaching', 'Teaching Staff'),
        ('support', 'Support Staff'),
    ]

    STAFF_TYPES = dict(STAFF_TYPE_CHOICES)

    EXECUTIVE_POSITION_CHOICES = [
        ('director', 'School Director'),
        ('headteacher', 'Head Teacher'),
        ('administrator', 'Administrator'),
        ('supervisor', 'Supervisor'),
        ('coordinator', 'Coordinator'),
        ('other', 'Other Executive'),
    ]

    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    staff_type = models.CharField(max_length=20, choices=STAFF_TYPE_CHOICES)
    executive_position = models.CharField(max_length=20, choices=EXECUTIVE_POSITION_CHOICES,
                                        null=True, blank=True,
                                        help_text='Only applicable for Executive Staff')
    bio = models.TextField()
    image = models.ImageField(upload_to='staff/')
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, help_text='Optional contact number')
    qualification = models.TextField(blank=True, help_text='Academic and professional qualifications')
    achievements = models.TextField(blank=True, help_text='Notable achievements and contributions')
    interests = models.TextField(blank=True, help_text='Professional interests and specializations')
    is_featured = models.BooleanField(default=False, help_text='Featured staff will be shown on the home and about pages')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['staff_type', 'order', 'name']

    def __str__(self):
        return self.name

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=200)
    image = models.ImageField(upload_to='events/', null=True, blank=True)
    registration_required = models.BooleanField(default=False)
    registration_link = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey('EventCategory', on_delete=models.SET_NULL, null=True, blank=True, related_name='events')

    # Link to management system event
    management_event = models.ForeignKey('communications.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='website_event')

    class Meta:
        ordering = ['date']

    def __str__(self):
        return self.title

class Gallery(models.Model):
    CATEGORY_CHOICES = [
        ('classroom', 'Classroom'),
        ('events', 'Events'),
        ('activities', 'Activities'),
        ('campus', 'Campus'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='gallery/')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    date_added = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Galleries'
        ordering = ['-date_added']

    def __str__(self):
        return self.title

class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, help_text='e.g., Parent, Student, Alumni')
    content = models.TextField()
    image = models.ImageField(upload_to='testimonials/', null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_added']

    def __str__(self):
        return self.name

class EventCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Event Categories'
        ordering = ['order']

    def __str__(self):
        return self.name

class PastEventHighlight(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='events/highlights/')
    date = models.DateField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date', 'order']

    def __str__(self):
        return self.title

class EventPageContent(models.Model):
    SECTION_CHOICES = [
        ('hero', 'Hero Section'),
        ('newsletter', 'Newsletter Section'),
        ('cta', 'Call to Action Section'),
    ]

    section = models.CharField(max_length=50, choices=SECTION_CHOICES, unique=True)
    title = models.CharField(max_length=200)
    subtitle = models.TextField(blank=True)
    background_image = models.ImageField(upload_to='events/sections/', null=True, blank=True, help_text='Background image for hero section')
    calendar_placeholder_image = models.ImageField(upload_to='events/sections/', null=True, blank=True, help_text='Placeholder image for the calendar widget')
    content = models.TextField(blank=True)
    button_text = models.CharField(max_length=50, blank=True)
    button_link = models.CharField(max_length=200, blank=True)
    additional_button_text = models.CharField(max_length=50, blank=True)
    additional_button_link = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Event Page Section'
        verbose_name_plural = 'Event Page Sections'

    def __str__(self):
        return f"Event Page - {self.get_section_display()}"
