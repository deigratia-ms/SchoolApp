from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django import forms
from tinymce.widgets import TinyMCE

# Import career admin
from .admin_career import JobPositionAdmin, JobApplicationAdmin

from .models import (
    PageContent, FAQ, MontessoriMethodItem, SiteSettings,
    HeroSlide, Staff, Event, Announcement, AnnouncementCategory, NewsletterSubscriber, Gallery,
    TourLocation, TourImage, Testimonial, ContactMessage,
    AdmissionsInquiry, AcademicProgram, CurriculumApproach,
    SpecialProgram, AssessmentMethod
)

# Create a custom form for PageContent with TinyMCE widget
class PageContentAdminForm(forms.ModelForm):
    class Meta:
        model = PageContent
        fields = '__all__'
        widgets = {
            'content': TinyMCE(attrs={'cols': 80, 'rows': 30}),
        }

@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    form = PageContentAdminForm
    list_display = ('get_section_display', 'title', 'image_preview', 'is_active', 'preview_button')
    list_filter = ('page', 'is_active')
    search_fields = ('title', 'content')
    ordering = ('page', 'order')
    readonly_fields = ('image_preview_large', 'calendar_image_preview')

    def get_section_display(self, obj):
        section_descriptions = {
            # About Page Sections
            'about_hero': 'About Page - Hero Banner',
            'mission': 'About Page - Mission Statement',
            'vision': 'About Page - Vision Statement',
            'story': 'About Page - Our Story Section',
            'montessori_method': 'About Page - Montessori Method',

            # Admissions Page Sections
            'hero': 'Admissions Page - Hero Banner',
            'admission_process': 'Admissions Page - Process Steps',
            'fees': 'Admissions Page - Programs & Tuition',
            'requirements': 'Admissions Page - Required Documents',
            'scholarships': 'Admissions Page - Financial Aid & Scholarships',

            # Academics Page Sections
            'academics_hero': 'Academics Page - Hero Banner',
            'curriculum_image': 'Academics Page - Curriculum Image',
            'assessment_intro': 'Academics Page - Assessment Intro',
            'cta_section': 'Academics Page - Call to Action',

            # Events Page Sections
            'events_hero': 'Events Page - Hero Banner',
            'events_newsletter': 'Events Page - Newsletter Section',
            'events_cta': 'Events Page - Call to Action',
            'events_calendar': 'Events Page - Calendar Placeholder',

            # Staff Page Sections
            'staff_hero': 'Staff Page - Hero Banner',

            # Career Page Sections
            'career_hero': 'Career Page - Hero Banner',
            'career_intro': 'Career Page - Introduction',

            # Calendar Page Sections
            'calendar_hero': 'Calendar Page - Hero Banner',
            'calendar_content': 'Calendar Page - Calendar Content',

            # Privacy Policy Page Sections
            'privacy_hero': 'Privacy Policy - Hero Banner',
            'privacy_content': 'Privacy Policy - Main Content',

            # Terms of Service Page Sections
            'terms_hero': 'Terms of Service - Hero Banner',
            'terms_content': 'Terms of Service - Main Content',

            # FAQ Page Sections
            'faq_hero': 'FAQ Page - Hero Banner',
        }
        return section_descriptions.get(obj.section, obj.get_section_display())
    get_section_display.short_description = 'Section'

    def get_fieldsets(self, request, obj=None):
        if obj:
            if obj.section in ['hero', 'about_hero', 'academics_hero', 'events_hero', 'news_hero', 'contact_hero', 'staff_hero', 'career_hero', 'calendar_hero', 'privacy_hero', 'terms_hero', 'faq_hero']:
                section_name = {
                    'hero': 'Admissions Page Hero',
                    'about_hero': 'About Page Hero',
                    'academics_hero': 'Academics Page Hero',
                    'events_hero': 'Events Page Hero',
                    'news_hero': 'News Page Hero',
                    'contact_hero': 'Contact Page Hero',
                    'staff_hero': 'Staff Page Hero',
                    'career_hero': 'Career Page Hero',
                    'calendar_hero': 'Calendar Page Hero',
                    'privacy_hero': 'Privacy Policy Page Hero',
                    'terms_hero': 'Terms of Service Page Hero',
                    'faq_hero': 'FAQ Page Hero',
                }[obj.section]

                # Define fields based on section
                button_fields = []
                if obj.section == 'events_hero':
                    button_fields = ['button_text', 'button_link']

                return (
                    (None, {
                        'fields': ('page', 'section', 'title', 'is_active', 'order'),
                        'description': f'Configure the {section_name} banner section.'
                    }),
                    ('Banner Content', {
                        'fields': tuple(['content'] + button_fields),
                        'classes': ('wide',),
                        'description': 'Enter the text that will appear over the hero image.'
                    }),
                    ('Banner Image', {
                        'fields': ('image_preview_large', 'image'),
                        'description': 'Upload the banner image. Recommended size: 1920x600 pixels.',
                        'classes': ('wide',)
                    }),
                )
            elif obj.section in ['curriculum_image', 'story']:
                return (
                    (None, {
                        'fields': ('page', 'section', 'title', 'is_active', 'order')
                    }),
                    ('Content', {
                        'fields': ('content',),
                        'classes': ('wide',)
                    }),
                    ('Image', {
                        'fields': ('image_preview_large', 'image'),
                        'description': 'Upload an image. Recommended size: 800x600 pixels.',
                        'classes': ('wide',)
                    }),
                )
            elif obj.section in ['privacy_content', 'terms_content', 'calendar_content']:
                section_name = {
                    'privacy_content': 'Privacy Policy Content',
                    'terms_content': 'Terms of Service Content',
                    'calendar_content': 'Calendar Content',
                }[obj.section]

                return (
                    (None, {
                        'fields': ('page', 'section', 'title', 'is_active', 'order')
                    }),
                    (f'{section_name}', {
                        'fields': ('content',),
                        'description': 'Use the rich text editor below to create formatted content. You can add headings, lists, tables, and other formatting.',
                        'classes': ('wide',)
                    }),
                )
            elif obj.section == 'events_calendar':
                return (
                    (None, {
                        'fields': ('page', 'section', 'title', 'is_active', 'order')
                    }),
                    ('Calendar Placeholder Image', {
                        'fields': ('calendar_image_preview', 'calendar_placeholder_image'),
                        'description': 'Upload a placeholder image for the calendar widget.',
                        'classes': ('wide',)
                    }),
                )
        # For other sections that might need button fields
        button_fields = []
        if obj and obj.section in ['events_newsletter', 'events_cta']:
            button_fields = ['button_text', 'button_link']

        return (
            (None, {
                'fields': ('page', 'section', 'title', 'is_active', 'order')
            }),
            ('Content', {
                'fields': tuple(['content'] + button_fields),
                'classes': ('wide',)
            }),
            ('Media', {
                'fields': ('image_preview_large', 'image'),
                'classes': ('wide',)
            }),
        )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; cursor: pointer" onclick="window.open(this.src)"/>',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = 'Preview'

    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<div style="margin: 10px 0;">'
                '<img src="{}" style="max-width: 100%; max-height: 300px;" /><br>'
                '<small style="color: #666;">Current image - Upload a new one below to replace it</small>'
                '</div>',
                obj.image.url
            )
        return "No image uploaded yet"
    image_preview_large.short_description = 'Current Image'

    def calendar_image_preview(self, obj):
        if obj.calendar_placeholder_image:
            return format_html(
                '<div style="margin: 10px 0;">'
                '<img src="{}" style="max-width: 100%; max-height: 300px;" /><br>'
                '<small style="color: #666;">Current image - Upload a new one below to replace it</small>'
                '</div>',
                obj.calendar_placeholder_image.url
            )
        return "No image uploaded yet"
    calendar_image_preview.short_description = 'Calendar Image'

    def preview_button(self, obj):
        return format_html(
            '<button class="preview-btn" data-page="{}" data-id="{}">'
            'Preview</button>',
            obj.page,
            obj.id
        )
    preview_button.short_description = 'Preview'

@admin.register(AcademicProgram)
class AcademicProgramAdmin(admin.ModelAdmin):
    list_display = ('title', 'program_type', 'age_range', 'preview_image', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('program_type', 'is_active')
    search_fields = ('title', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'program_type', 'age_range', 'description')
        }),
        ('Features', {
            'fields': ('features',),
            'description': 'Enter features as a list, one per line. These will be displayed with checkmarks.'
        }),
        ('Display Settings', {
            'fields': ('preview_image', 'image', 'order', 'is_active')
        })
    )
    readonly_fields = ('preview_image',)

    def preview_image(self, obj):
        if obj.image:
            return format_html(
                '<div style="margin: 10px 0;">'
                '<img src="{}" style="max-width: 100%; max-height: 200px;" />'
                '</div>',
                obj.image.url
            )
        return "No image uploaded"
    preview_image.short_description = 'Current Image'

@admin.register(CurriculumApproach)
class CurriculumApproachAdmin(admin.ModelAdmin):
    list_display = ('title', 'content_preview', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'content')

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'

@admin.register(SpecialProgram)
class SpecialProgramAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon_preview', 'description_preview', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'description')
    fieldsets = (
        ('Program Information', {
            'fields': ('title', 'description')
        }),
        ('Display Settings', {
            'fields': ('icon', 'order', 'is_active'),
            'description': 'Choose an icon and set the display order.'
        })
    )

    def icon_preview(self, obj):
        return format_html(
            '<i class="fas fa-{} fa-2x"></i>',
            obj.icon
        )
    icon_preview.short_description = 'Icon'

    def description_preview(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_preview.short_description = 'Description'

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',)
        }

@admin.register(AssessmentMethod)
class AssessmentMethodAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon_preview', 'description_preview', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'description')

    def icon_preview(self, obj):
        return format_html(
            '<i class="fas fa-{} fa-2x"></i>',
            obj.icon
        )
    icon_preview.short_description = 'Icon'

    def description_preview(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_preview.short_description = 'Description'

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',)
        }

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'get_page_display', 'is_active', 'order')
    list_filter = ('page', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('question', 'answer')
    ordering = ('page', 'order')
    fieldsets = (
        ('Basic Information', {
            'fields': ('question', 'answer')
        }),
        ('Display Settings', {
            'fields': ('page', 'order', 'is_active')
        })
    )

    def get_page_display(self, obj):
        page_descriptions = {
            'about': 'About Page',
            'admissions': 'Admissions Page',
            'academics': 'Academics Page'
        }
        return page_descriptions.get(obj.page, obj.get_page_display())
    get_page_display.short_description = 'Page'

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'contact_email', 'contact_phone', 'preview_logo')
    fieldsets = (
        ('Basic Information', {
            'fields': ('school_logo', 'footer_logo')
        }),
        ('Contact Information', {
            'fields': (
                'contact_email', 'admissions_email', 'support_email',
                'contact_phone', 'admissions_phone', 'fax_number',
                'address', 'office_hours'
            )
        }),
        ('Google Maps Integration', {
            'fields': (
                'google_maps_api_key', 'google_maps_latitude',
                'google_maps_longitude', 'google_maps_zoom'
            ),
            'description': 'Configure Google Maps for the contact page. You need a valid API key for the map to work properly.'
        }),
        ('Social Media', {
            'fields': (
                'facebook_url', 'twitter_url', 'instagram_url',
                'linkedin_url', 'youtube_url'
            )
        }),
    )

    def preview_logo(self, obj):
        if obj.school_logo:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.school_logo.url)
        return "No Logo"
    preview_logo.short_description = 'Logo Preview'

@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'preview_image', 'order', 'is_active')
    list_editable = ('order', 'is_active')

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Preview'

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('name', 'staff_type', 'position', 'preview_image', 'order')
    list_filter = ('staff_type',)
    list_editable = ('order',)

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Preview'

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'preview_image', 'is_featured')
    list_filter = ('date', 'registration_required')
    list_editable = ('is_featured',)
    search_fields = ('title', 'description', 'location')

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Preview'

@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description_preview', 'announcement_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')

    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return "-"
    description_preview.short_description = 'Description'

    def announcement_count(self, obj):
        return obj.announcements.count()
    announcement_count.short_description = 'Posts'

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'date_subscribed', 'is_active')
    list_filter = ('date_subscribed', 'is_active')
    search_fields = ('email', 'name')
    list_editable = ('is_active',)
    actions = ['export_subscribers']

    def export_subscribers(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="newsletter_subscribers.csv"'

        writer = csv.writer(response)
        writer.writerow(['Email', 'Name', 'Date Subscribed', 'Active'])

        for subscriber in queryset:
            writer.writerow([
                subscriber.email,
                subscriber.name,
                subscriber.date_subscribed.strftime('%Y-%m-%d %H:%M:%S'),
                'Yes' if subscriber.is_active else 'No'
            ])

        return response
    export_subscribers.short_description = 'Export selected subscribers to CSV'

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date_posted', 'is_featured', 'preview_image')
    list_filter = ('date_posted', 'category', 'is_featured')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_featured',)

    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'content', 'image')
        }),
        ('Categorization', {
            'fields': ('category', 'is_featured')
        }),
        ('Publication', {
            'fields': ('date_posted',)
        }),
    )

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Preview'

@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'preview_image')
    list_filter = ('category',)

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Preview'

class TourImageInline(admin.TabularInline):
    model = TourImage
    extra = 1

@admin.register(TourLocation)
class TourLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'preview_image')
    inlines = [TourImageInline]

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Preview'

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'preview_image')
    list_filter = ('role',)

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Preview'

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'date_sent', 'is_read')
    list_filter = ('is_read', 'date_sent')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('date_sent',)

@admin.register(AdmissionsInquiry)
class AdmissionsInquiryAdmin(admin.ModelAdmin):
    list_display = ('child_name', 'program_interest', 'date_submitted', 'status')
    list_filter = ('program_interest', 'status', 'date_submitted')
    search_fields = ('child_name', 'name', 'email')
    readonly_fields = ('date_submitted',)