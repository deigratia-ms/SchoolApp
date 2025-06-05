from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from datetime import datetime
from .models import (
    HeroSlide,
    Announcement,
    AnnouncementCategory,
    NewsletterSubscriber,
    Event,
    Testimonial,
    Staff,
    Gallery,
    SiteSettings,
    TourLocation,
    TourImage,
    FAQ,
    PageContent,
    MontessoriMethodItem,
    AcademicProgram,
    CurriculumApproach,
    SpecialProgram,
    AssessmentMethod,
    EventCategory,
    PastEventHighlight,
    EventPageContent
)
from .forms import ContactForm, AdmissionsInquiryForm

def home(request):
    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    featured_gallery = Gallery.objects.filter(is_featured=True)

    context = {
        'settings': site_settings,
        'hero_slides': HeroSlide.objects.filter(is_active=True).order_by('order'),
        'announcements': Announcement.objects.filter(is_featured=True)[:3],
        'upcoming_events': Event.objects.filter(date__gte=timezone.now())[:3],
        'testimonials': Testimonial.objects.filter(is_featured=True)[:3],
        'featured_gallery': featured_gallery,
        'show_gallery_carousel': featured_gallery.count() > 3
    }
    return render(request, 'website/home.html', context)

def about(request):
    featured_staff = Staff.objects.filter(is_featured=True).order_by('order', 'name')

    # Get all about page content sections
    about_sections = PageContent.objects.filter(
        page='about',
        is_active=True
    ).order_by('order')

    # Convert to dictionary for easy access in template
    sections = {
        content.section: content
        for content in about_sections
    }

    # Get active Montessori method items
    montessori_items = MontessoriMethodItem.objects.filter(
        is_active=True
    ).order_by('order')

    context = {
        'staff_members': featured_staff,
        'testimonials': Testimonial.objects.filter(is_featured=True),
        'sections': sections,
        'montessori_items': montessori_items,
    }
    return render(request, 'website/about.html', context)

class StaffListView(ListView):
    model = Staff
    template_name = 'website/staff_list.html'
    context_object_name = 'staff_members'
    ordering = ['staff_type', 'order', 'name']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['staff_types'] = dict(Staff.STAFF_TYPES)

        # Get staff hero content if available
        staff_hero = PageContent.objects.filter(
            page='staff',
            section='staff_hero',
            is_active=True
        ).first()

        # If no staff hero content, use about hero image as fallback
        if not staff_hero:
            about_hero = PageContent.objects.filter(
                page='about',
                section='about_hero',
                is_active=True
            ).first()

            # If about hero exists, create a temporary PageContent object with just the image
            if about_hero and about_hero.image:
                from django.db.models.base import ModelBase
                staff_hero = type('PageContent', (object,), {'image': about_hero.image})

        context['staff_hero'] = staff_hero
        return context

class StaffDetailView(DetailView):
    model = Staff
    template_name = 'website/staff_detail.html'
    context_object_name = 'staff_member'

def get_staff_details(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    data = {
        'id': staff.pk,
        'name': staff.name,
        'position': staff.position,
        'staff_type': staff.get_staff_type_display(),
        'bio': staff.bio,
        'email': staff.email,
        'phone': staff.phone,
        'qualification': staff.qualification,
        'achievements': staff.achievements,
        'interests': staff.interests,
        'image_url': staff.image.url if staff.image else None,
    }
    return JsonResponse(data)

def virtual_tour(request):
    locations = TourLocation.objects.prefetch_related('images').all()
    context = {
        'tour_locations': locations,
    }
    return render(request, 'website/virtual_tour.html', context)

def tour_location_detail(request, pk):
    location = get_object_or_404(TourLocation, pk=pk)
    context = {
        'location': location,
        'images': location.images.all(),
    }
    return render(request, 'website/tour_location_detail.html', context)

class EventListView(ListView):
    model = Event
    template_name = 'website/events.html'
    context_object_name = 'events'
    paginate_by = 6

    def get_queryset(self):
        # Get all website events, including those linked to management events
        website_events = Event.objects.all()

        # Log the number of website events found
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Found {website_events.count()} website events")

        # Check for management events that should be shown but don't have website events yet
        from communications.models import Event as ManagementEvent
        from django.utils import timezone
        from itertools import chain
        from datetime import datetime

        # Get management events marked for website display
        management_events = ManagementEvent.objects.filter(show_on_website=True)
        logger.info(f"Found {management_events.count()} management events marked for website display")

        # Get IDs of management events that already have website events
        linked_mgmt_event_ids = [e.management_event_id for e in website_events if e.management_event_id is not None]
        logger.info(f"Found {len(linked_mgmt_event_ids)} management events already linked to website events")

        # Filter to only get management events that don't have website events yet
        unlinked_mgmt_events = management_events.exclude(id__in=linked_mgmt_event_ids)
        logger.info(f"Found {unlinked_mgmt_events.count()} management events not yet linked to website events")

        # Create temporary website event objects for display
        converted_events = []

        for mgmt_event in unlinked_mgmt_events:
            logger.info(f"Creating temporary event object for management event {mgmt_event.id}: {mgmt_event.title}")

            # Determine the event date
            if mgmt_event.all_day or not mgmt_event.start_time:
                # For all-day events or events without a specific time, use noon
                event_time = datetime.min.replace(hour=12, minute=0, second=0).time()
            else:
                event_time = mgmt_event.start_time

            event_date = timezone.make_aware(datetime.combine(mgmt_event.start_date, event_time))

            # Create the event object
            event = Event(
                id=f"mgmt_{mgmt_event.id}",  # Use a special ID format for management events
                title=mgmt_event.title,
                description=mgmt_event.description or '',
                date=event_date,
                location=mgmt_event.location or 'School Campus',
                management_event=mgmt_event
            )

            # If the management event has an attachment, use it as the image
            if mgmt_event.attachment:
                event.image = mgmt_event.attachment
                logger.info(f"Using attachment as image for event: {mgmt_event.attachment}")

            converted_events.append(event)
            logger.info(f"Added management event to display list: {event.title} on {event.date}")

        # Combine all events
        all_events = list(chain(website_events, converted_events))

        logger.info(f"Total events to display: {len(all_events)} (Website: {len(website_events)}, Management: {len(converted_events)})")

        # Filter by past or upcoming events
        show_param = self.request.GET.get('show')
        now = timezone.now()

        if show_param == 'past':
            all_events = [e for e in all_events if getattr(e, 'date', now) < now]
            # Sort by date descending for past events
            all_events.sort(key=lambda x: getattr(x, 'date', now), reverse=True)
        else:
            all_events = [e for e in all_events if getattr(e, 'date', now) >= now]
            # Sort by date ascending for upcoming events
            all_events.sort(key=lambda x: getattr(x, 'date', now))

        # Filter by category (website events only)
        category_slug = self.request.GET.get('category')
        if category_slug:
            all_events = [e for e in all_events if hasattr(e, 'category') and
                         e.category and e.category.slug == category_slug]

        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            search_query = search_query.lower()
            all_events = [e for e in all_events if
                         search_query in e.title.lower() or
                         search_query in (e.description or '').lower() or
                         search_query in (e.location or '').lower()]

        # Apply sorting
        sort_param = self.request.GET.get('sort')
        if sort_param == 'title':
            all_events.sort(key=lambda x: x.title)
        elif sort_param == 'category' and any(hasattr(e, 'category') for e in all_events):
            all_events.sort(key=lambda x: getattr(getattr(x, 'category', None), 'name', '') or '')

        return all_events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get page sections content
        page_sections = {
            section: PageContent.objects.filter(
                page='events',
                section=section,
                is_active=True
            ).first()
            for section in ['events_hero', 'events_newsletter', 'events_cta', 'events_calendar']
        }

        # Get event categories
        context['event_categories'] = EventCategory.objects.filter(is_active=True).order_by('order')

        # Get past events for the highlights section (if not already showing past events)
        if self.request.GET.get('show') != 'past':
            context['past_events'] = Event.objects.filter(
                date__lt=timezone.now()
            ).order_by('-date')[:3]

        # Add current date for the calendar
        context['now'] = timezone.now()

        context['sections'] = page_sections
        return context

class EventDetailView(DetailView):
    model = Event
    template_name = 'website/event_detail.html'
    context_object_name = 'event'

    def get_object(self, queryset=None):
        # Get the event by primary key
        pk = self.kwargs.get(self.pk_url_kwarg)

        # Import needed modules
        from communications.models import Event as ManagementEvent
        from django.utils import timezone
        from datetime import datetime
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Looking for event with pk: {pk}")

        # Check if this is a management event ID (starts with 'mgmt_')
        if isinstance(pk, str) and pk.startswith('mgmt_'):
            try:
                # Extract the actual management event ID
                mgmt_id = int(pk.split('_')[1])
                logger.info(f"Looking for management event with ID: {mgmt_id}")

                # Get the management event
                mgmt_event = ManagementEvent.objects.get(pk=mgmt_id)

                # Check if it's marked to show on website
                if not mgmt_event.show_on_website:
                    logger.warning(f"Management event {mgmt_id} is not marked for website display")
                    raise Http404("Event not found")

                logger.info(f"Found management event: {mgmt_event.title}")

                # Determine the event date
                if mgmt_event.all_day or not mgmt_event.start_time:
                    # For all-day events or events without a specific time, use noon
                    event_time = datetime.min.replace(hour=12, minute=0, second=0).time()
                else:
                    event_time = mgmt_event.start_time

                event_date = timezone.make_aware(datetime.combine(mgmt_event.start_date, event_time))

                # Create a temporary event object for display
                event = Event(
                    id=pk,  # Keep the special ID format
                    title=mgmt_event.title,
                    description=mgmt_event.description or '',
                    date=event_date,
                    location=mgmt_event.location or 'School Campus',
                    management_event=mgmt_event
                )

                # If the management event has an attachment, use it as the image
                if mgmt_event.attachment:
                    event.image = mgmt_event.attachment

                return event
            except (ManagementEvent.DoesNotExist, ValueError, IndexError) as e:
                logger.error(f"Error finding management event: {str(e)}")
                raise Http404("Event not found")

        # If not a management event ID, try to get a website event
        try:
            logger.info(f"Looking for website event with ID: {pk}")
            return Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            logger.warning(f"Website event with ID {pk} not found")
            raise Http404("Event not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get the current event
        event = context['event']

        # Check if this is a management event
        if hasattr(event, 'management_event') and event.management_event:
            # Add a flag to indicate this is a management event
            context['is_management_event'] = True

            # For virtual events, set registration info
            if hasattr(event.management_event, 'is_virtual') and event.management_event.is_virtual:
                context['event'].registration_required = True
                context['event'].registration_link = event.management_event.virtual_link

        # Get related events (3 most recent other events)
        related_events = Event.objects.exclude(pk=event.pk).order_by('-date')[:3]
        context['related_events'] = related_events

        # Add site settings
        from website.models import SiteSettings
        try:
            context['site_settings'] = SiteSettings.objects.first()
        except:
            # If no site settings exist, provide defaults
            from types import SimpleNamespace
            context['site_settings'] = SimpleNamespace(
                contact_phone='(123) 456-7890',
                contact_email='info@deigratia.edu'
            )
        # Add management event to context if available
        if hasattr(event, 'management_event') and event.management_event:
            context['management_event'] = event.management_event

            # Add virtual event info if applicable
            if hasattr(event.management_event, 'is_virtual') and event.management_event.is_virtual:
                context['is_virtual'] = True
                context['virtual_link'] = event.management_event.virtual_link

        return context

class AnnouncementListView(ListView):
    model = Announcement
    template_name = 'website/news.html'
    context_object_name = 'announcements'
    paginate_by = 6
    ordering = ['-date_posted']

    def get_queryset(self):
        queryset = super().get_queryset()
        category_slug = self.kwargs.get('category_slug')
        search_query = self.request.GET.get('search')

        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        if search_query:
            queryset = queryset.filter(
                models.Q(title__icontains=search_query) |
                models.Q(content__icontains=search_query) |
                models.Q(category__name__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all categories with counts
        categories = AnnouncementCategory.objects.annotate(
            post_count=models.Count('announcements')
        ).filter(post_count__gt=0)
        context['categories'] = categories

        # Get current category if filtering by category
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            context['current_category'] = get_object_or_404(AnnouncementCategory, slug=category_slug)

        # Get archive dates (months with posts)
        archive_dates = Announcement.objects.annotate(
            month=models.functions.TruncMonth('date_posted')
        ).values('month').annotate(
            count=models.Count('id')
        ).order_by('-month')
        context['archive_dates'] = archive_dates

        # Get current archive date if filtering by date
        month = self.request.GET.get('month')
        year = self.request.GET.get('year')
        if month and year:
            try:
                context['current_archive'] = datetime(int(year), int(month), 1)
            except (ValueError, TypeError):
                pass

        # Add search query to context if present
        search_query = self.request.GET.get('search')
        if search_query:
            context['search_query'] = search_query
            context['search_results_count'] = self.get_queryset().count()

        # Get news hero section content
        news_hero = PageContent.objects.filter(
            page='news',
            section='news_hero',
            is_active=True
        ).first()
        context['news_hero'] = news_hero

        # If no admin-selected hero image, use the first announcement's image
        if not news_hero or not news_hero.image:
            first_announcement = self.get_queryset().filter(image__isnull=False).first()
            if first_announcement and first_announcement.image:
                context['first_announcement_image'] = first_announcement.image

        return context

class AnnouncementCategoryView(AnnouncementListView):
    def get_queryset(self):
        queryset = super().get_queryset().filter(category__slug=self.kwargs['slug'])

        # Also apply search filter if present
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(title__icontains=search_query) |
                models.Q(content__icontains=search_query)
            )

        return queryset

class AnnouncementArchiveView(AnnouncementListView):
    def get_queryset(self):
        queryset = super().get_queryset()

        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        search_query = self.request.GET.get('search')

        if year and month:
            queryset = queryset.filter(
                date_posted__year=year,
                date_posted__month=month
            )

        if search_query:
            queryset = queryset.filter(
                models.Q(title__icontains=search_query) |
                models.Q(content__icontains=search_query) |
                models.Q(category__name__icontains=search_query)
            )

        return queryset

class AnnouncementDetailView(DetailView):
    model = Announcement
    template_name = 'website/announcement_detail.html'
    context_object_name = 'announcement'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get related announcements (same category, excluding current)
        announcement = self.get_object()
        if announcement.category:
            context['related_announcements'] = Announcement.objects.filter(
                category=announcement.category
            ).exclude(id=announcement.id)[:3]
        else:
            # If no category, get recent announcements
            context['related_announcements'] = Announcement.objects.exclude(
                id=announcement.id
            )[:3]

        # Get categories for sidebar
        categories = AnnouncementCategory.objects.annotate(
            post_count=models.Count('announcements')
        ).filter(post_count__gt=0)
        context['categories'] = categories

        # Get archive dates for sidebar
        archive_dates = Announcement.objects.annotate(
            month=models.functions.TruncMonth('date_posted')
        ).values('month').annotate(
            count=models.Count('id')
        ).order_by('-month')
        context['archive_dates'] = archive_dates

        return context

def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        name = request.POST.get('name', '')

        if email:
            # Check if already subscribed
            if not NewsletterSubscriber.objects.filter(email=email).exists():
                # Create new subscriber
                subscriber = NewsletterSubscriber(email=email, name=name)
                subscriber.save()
                messages.success(request, 'Thank you for subscribing to our newsletter!')
            else:
                # Already subscribed
                messages.info(request, 'You are already subscribed to our newsletter.')
        else:
            messages.error(request, 'Please provide a valid email address.')

    # Redirect back to the referring page or to the news page
    next_page = request.POST.get('next', request.META.get('HTTP_REFERER', 'website:news'))
    return redirect(next_page)

def academics(request):
    # Get page sections content
    page_sections = {
        section: PageContent.objects.filter(
            page='academics',
            section=section,
            is_active=True
        ).first()
        for section in ['academics_hero', 'curriculum_image', 'assessment_intro', 'cta_section']
    }

    # Get academic programs
    programs = AcademicProgram.objects.filter(is_active=True).order_by('order')

    # Get curriculum approach items
    curriculum_items = CurriculumApproach.objects.filter(is_active=True).order_by('order')

    # Get special programs
    special_programs = SpecialProgram.objects.filter(is_active=True).order_by('order')

    # Get assessment methods
    assessment_methods = AssessmentMethod.objects.filter(is_active=True).order_by('order')

    context = {
        'sections': page_sections,
        'programs': programs,
        'curriculum_items': curriculum_items,
        'special_programs': special_programs,
        'assessment_methods': assessment_methods,
    }

    return render(request, 'website/academics.html', context)

def admissions(request):
    if request.method == 'POST':
        form = AdmissionsInquiryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your inquiry has been submitted successfully. We will contact you soon.')
            return redirect('website:admissions')
    else:
        form = AdmissionsInquiryForm()

    # Get all admissions page content sections
    admissions_sections = PageContent.objects.filter(
        page='admissions',
        is_active=True
    ).order_by('order')

    # Convert to dictionary for easy access in template
    sections = {
        content.section: content
        for content in admissions_sections
    }

    # Get admissions FAQs
    faqs = FAQ.objects.filter(
        page='admissions',
        is_active=True
    ).order_by('order')

    context = {
        'form': form,
        'sections': sections,
        'faqs': faqs
    }

    return render(request, 'website/admissions.html', context)

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save(commit=False)
            # Set is_read to False by default
            contact_message.is_read = False
            contact_message.save()
            messages.success(request, 'Your message has been sent successfully. We will get back to you soon.')
            return redirect('website:contact')
    else:
        form = ContactForm()

    # Get site settings
    try:
        site_settings = SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        site_settings = None

    # Get FAQs for contact page
    faqs = FAQ.objects.filter(page='contact', is_active=True).order_by('order')

    # Get hero content for contact page
    # First try to find contact_hero section
    contact_hero = PageContent.objects.filter(
        page='contact',
        section='contact_hero',
        is_active=True
    ).first()

    # If not found, try the generic hero section (for backward compatibility)
    if not contact_hero:
        contact_hero = PageContent.objects.filter(
            page='contact',
            section='hero',
            is_active=True
        ).first()

    # Prepare Google Maps embed URL if coordinates are available
    google_maps_embed_url = None
    if site_settings and site_settings.google_maps_latitude and site_settings.google_maps_longitude:
        # Create a Google Maps embed URL with the coordinates
        lat = site_settings.google_maps_latitude
        lng = site_settings.google_maps_longitude
        zoom = site_settings.google_maps_zoom
        google_maps_embed_url = f"https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3000!2d{lng}!3d{lat}!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zM0PCsDU5JzI0LjAiTiA3NsKwMTUnMjQuMCJX!5e0!3m2!1sen!2sus!4v1234567890"

    return render(request, 'website/contact.html', {
        'form': form,
        'faqs': faqs,
        'settings': site_settings,
        'contact_hero': contact_hero,
        'google_maps_embed_url': google_maps_embed_url
    })

class GalleryListView(ListView):
    model = Gallery
    template_name = 'website/gallery.html'
    context_object_name = 'galleries'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get unique categories and sort them alphabetically
        context['categories'] = sorted(set(Gallery.objects.values_list('category', flat=True).distinct()))
        return context

    def get_queryset(self):
        queryset = Gallery.objects.all()
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset

class GalleryDetailView(DetailView):
    model = Gallery
    template_name = 'website/gallery_detail.html'
    context_object_name = 'gallery'

# Admin AJAX views
@staff_member_required
def get_page_content(request):
    page = request.GET.get('page')
    if not page:
        return JsonResponse({'error': 'Page parameter is required'}, status=400)

    content = PageContent.objects.filter(page=page).order_by('section')
    data = {
        'content': [
            {
                'id': item.id,
                'section': item.section,
                'title': item.title,
                'content': item.content,
                'image': item.image.url if item.image else None
            }
            for item in content
        ]
    }
    return JsonResponse(data)

@staff_member_required
def get_page_faqs(request):
    page = request.GET.get('page')
    if not page:
        return JsonResponse({'error': 'Page parameter is required'}, status=400)

    faqs = FAQ.objects.filter(page=page, is_active=True).order_by('order')
    data = {
        'faqs': [
            {
                'id': faq.id,
                'question': faq.question,
                'answer': faq.answer,
                'order': faq.order
            }
            for faq in faqs
        ]
    }
    return JsonResponse(data)
