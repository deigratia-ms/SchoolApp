from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import PageContent, JobPosition, JobApplication, FAQ

def career_list(request):
    """View to display available job positions"""
    # Get career page content
    career_hero = PageContent.objects.filter(
        page='career',
        section='career_hero',
        is_active=True
    ).first()

    career_intro = PageContent.objects.filter(
        page='career',
        section='career_intro',
        is_active=True
    ).first()

    # If no career hero image, try to use event hero as fallback
    event_hero = None
    if not career_hero or not career_hero.image:
        # Try to get event hero
        event_hero = PageContent.objects.filter(
            page='events',
            section='events_hero',
            is_active=True
        ).first()

        # If not found, try the contact hero
        if not event_hero or not event_hero.image:
            event_hero = PageContent.objects.filter(
                page='contact',
                section='contact_hero',
                is_active=True
            ).first()

    # Get active job positions
    active_positions = JobPosition.objects.filter(
        is_active=True,
        application_deadline__gte=timezone.now().date()
    ).order_by('department', '-date_posted')

    # Get filter choices
    department_choices = JobPosition.DEPARTMENT_CHOICES
    job_type_choices = JobPosition.JOB_TYPE_CHOICES

    # Get unique locations
    locations = JobPosition.objects.filter(
        is_active=True,
        application_deadline__gte=timezone.now().date()
    ).values_list('location', flat=True).distinct()

    context = {
        'career_hero': career_hero,
        'career_intro': career_intro,
        'event_hero': event_hero,
        'positions': active_positions,
        'department_choices': department_choices,
        'job_type_choices': job_type_choices,
        'locations': locations,
    }

    return render(request, 'website/career.html', context)

def job_detail(request, pk):
    """API view to get job details for the modal"""
    position = get_object_or_404(JobPosition, pk=pk)

    data = {
        'id': position.pk,
        'title': position.title,
        'department': position.get_department_display(),
        'job_type': position.get_job_type_display(),
        'location': position.location,
        'description': position.description,
        'responsibilities': position.responsibilities,
        'qualifications': position.qualifications,
        'salary_range': position.salary_range,
        'application_deadline': position.application_deadline.strftime('%B %d, %Y'),
        'days_until_deadline': position.days_until_deadline(),
        'date_posted': position.date_posted.strftime('%B %d, %Y'),
    }

    return JsonResponse(data)

def submit_application(request, pk):
    """View to handle job application submissions"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    position = get_object_or_404(JobPosition, pk=pk)

    # Check if position is still active and deadline hasn't passed
    if not position.is_active or position.is_expired():
        return JsonResponse({
            'status': 'error',
            'message': 'This position is no longer accepting applications'
        })

    # Process form data
    try:
        application = JobApplication(
            position=position,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            cover_letter=request.POST.get('cover_letter'),
            resume=request.FILES.get('resume'),
        )

        # Handle additional document if provided
        if 'additional_document' in request.FILES:
            application.additional_document = request.FILES.get('additional_document')

        # Save the application - this will trigger the post_save signal
        # which will automatically send the confirmation email
        application.save()

        # Note: We don't need to explicitly call send_confirmation_email() here
        # because it's handled by the post_save signal in signals.py

        return JsonResponse({
            'status': 'success',
            'message': 'Your application has been submitted successfully. You will receive a confirmation email shortly.'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred while submitting your application: {str(e)}'
        })

def school_calendar(request):
    """View for the school calendar page"""
    # Get calendar hero content
    calendar_hero = PageContent.objects.filter(
        page='calendar',
        section='calendar_hero',
        is_active=True
    ).first()

    # Get calendar content
    calendar_content = PageContent.objects.filter(
        page='calendar',
        section='calendar_content',
        is_active=True
    ).first()

    # If no calendar hero image, use contact hero as fallback
    contact_hero = None
    if not calendar_hero or not calendar_hero.image:
        # Try to get contact hero
        contact_hero = PageContent.objects.filter(
            page='contact',
            section='contact_hero',
            is_active=True
        ).first()

        # If not found, try the generic hero section (for backward compatibility)
        if not contact_hero or not contact_hero.image:
            contact_hero = PageContent.objects.filter(
                page='contact',
                section='hero',
                is_active=True
            ).first()

    context = {
        'calendar_hero': calendar_hero,
        'calendar_content': calendar_content,
        'contact_hero': contact_hero,
    }

    return render(request, 'website/calendar.html', context)

def privacy_policy(request):
    """View for the privacy policy page"""
    # Get privacy hero content
    privacy_hero = PageContent.objects.filter(
        page='privacy',
        section='privacy_hero',
        is_active=True
    ).first()

    # Get privacy content
    privacy_content = PageContent.objects.filter(
        page='privacy',
        section='privacy_content',
        is_active=True
    ).first()

    # If no privacy hero image, use contact hero as fallback
    contact_hero = None
    if not privacy_hero or not privacy_hero.image:
        # Try to get contact hero
        contact_hero = PageContent.objects.filter(
            page='contact',
            section='contact_hero',
            is_active=True
        ).first()

        # If not found, try the generic hero section (for backward compatibility)
        if not contact_hero or not contact_hero.image:
            contact_hero = PageContent.objects.filter(
                page='contact',
                section='hero',
                is_active=True
            ).first()

    context = {
        'privacy_hero': privacy_hero,
        'privacy_content': privacy_content,
        'contact_hero': contact_hero,
    }

    return render(request, 'website/privacy_policy.html', context)

def terms_of_service(request):
    """View for the terms of service page"""
    # Get terms hero content
    terms_hero = PageContent.objects.filter(
        page='terms',
        section='terms_hero',
        is_active=True
    ).first()

    # Get terms content
    terms_content = PageContent.objects.filter(
        page='terms',
        section='terms_content',
        is_active=True
    ).first()

    # If no terms hero image, use contact hero as fallback
    contact_hero = None
    if not terms_hero or not terms_hero.image:
        # Try to get contact hero
        contact_hero = PageContent.objects.filter(
            page='contact',
            section='contact_hero',
            is_active=True
        ).first()

        # If not found, try the generic hero section (for backward compatibility)
        if not contact_hero or not contact_hero.image:
            contact_hero = PageContent.objects.filter(
                page='contact',
                section='hero',
                is_active=True
            ).first()

    context = {
        'terms_hero': terms_hero,
        'terms_content': terms_content,
        'contact_hero': contact_hero,
    }

    return render(request, 'website/terms_of_service.html', context)

def faq_page(request):
    """View for the FAQ page"""
    faq_hero = PageContent.objects.filter(
        page='faq',
        section='faq_hero',
        is_active=True
    ).first()

    # Get all FAQs
    faqs = FAQ.objects.filter(is_active=True).order_by('order')

    context = {
        'faq_hero': faq_hero,
        'faqs': faqs,
    }

    return render(request, 'website/faq.html', context)
