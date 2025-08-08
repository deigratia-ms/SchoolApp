from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import datetime, timedelta

from .models import CustomUser, Student, Parent
from .decorators import is_admin
from appointments.models import Appointment, AppointmentRequest, TimeSlot
from documents.models import DocumentUpload, DocumentCategory, AdmissionEnquiry, VisitorLog


@login_required
@user_passes_test(is_admin)
def admin_dashboard_extended(request):
    """Extended admin dashboard with new features"""
    # Get counts for dashboard stats
    pending_appointment_requests = AppointmentRequest.objects.filter(status='pending').count()
    pending_documents = DocumentUpload.objects.filter(status='pending').count()
    new_enquiries = AdmissionEnquiry.objects.filter(status='new').count()
    active_visitors = VisitorLog.objects.filter(check_out_time__isnull=True).count()
    
    # Recent activity
    recent_appointment_requests = AppointmentRequest.objects.select_related(
        'parent', 'parent__user'
    ).order_by('-created_at')[:5]
    
    recent_documents = DocumentUpload.objects.select_related(
        'category', 'uploaded_by', 'student', 'parent'
    ).order_by('-created_at')[:5]
    
    recent_enquiries = AdmissionEnquiry.objects.order_by('-created_at')[:5]
    
    context = {
        'pending_appointment_requests': pending_appointment_requests,
        'pending_documents': pending_documents,
        'new_enquiries': new_enquiries,
        'active_visitors': active_visitors,
        'recent_appointment_requests': recent_appointment_requests,
        'recent_documents': recent_documents,
        'recent_enquiries': recent_enquiries,
    }
    
    return render(request, 'users/admin/dashboard_extended.html', context)


@login_required
@user_passes_test(is_admin)
def manage_appointment_requests(request):
    """Manage appointment requests from parents"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Base query
    requests = AppointmentRequest.objects.select_related(
        'parent', 'parent__user', 'reviewed_by', 'created_appointment'
    )
    
    # Apply filters
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    if search_query:
        requests = requests.filter(
            Q(parent__user__first_name__icontains=search_query) |
            Q(parent__user__last_name__icontains=search_query) |
            Q(purpose__icontains=search_query)
        )
    
    # Order by status priority and date
    requests = requests.order_by(
        '-status',  # pending first
        '-created_at'
    )
    
    # Pagination
    paginator = Paginator(requests, 20)
    page = request.GET.get('page')
    requests = paginator.get_page(page)
    
    context = {
        'requests': requests,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'users/admin/appointment_requests.html', context)


@login_required
@user_passes_test(is_admin)
def approve_appointment_request(request, request_id):
    """Approve an appointment request and create time slot"""
    appointment_request = get_object_or_404(AppointmentRequest, id=request_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'approve':
            try:
                # Create time slot
                time_slot = TimeSlot.objects.create(
                    date=appointment_request.requested_date,
                    start_time=appointment_request.requested_start_time,
                    end_time=appointment_request.requested_end_time,
                    is_available=False,  # Immediately book it
                    is_active=True
                )
                
                # Create appointment
                appointment = Appointment.objects.create(
                    parent=appointment_request.parent,
                    time_slot=time_slot,
                    purpose=appointment_request.purpose,
                    status='confirmed'
                )
                
                # Update request
                appointment_request.status = 'approved'
                appointment_request.admin_notes = admin_notes
                appointment_request.reviewed_by = request.user
                appointment_request.reviewed_at = timezone.now()
                appointment_request.created_appointment = appointment
                appointment_request.save()
                
                messages.success(request, f"Appointment request approved and scheduled for {appointment_request.parent.user.get_full_name()}")
                
            except Exception as e:
                messages.error(request, f"Error approving appointment: {str(e)}")
                
        elif action == 'reject':
            appointment_request.status = 'rejected'
            appointment_request.admin_notes = admin_notes
            appointment_request.reviewed_by = request.user
            appointment_request.reviewed_at = timezone.now()
            appointment_request.save()
            
            messages.success(request, f"Appointment request rejected for {appointment_request.parent.user.get_full_name()}")
        
        return redirect('users:manage_appointment_requests')
    
    context = {
        'appointment_request': appointment_request,
    }
    
    return render(request, 'users/admin/approve_appointment_request.html', context)


@login_required
@user_passes_test(is_admin)
def manage_documents(request):
    """Manage document uploads"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('search', '')
    
    # Base query
    documents = DocumentUpload.objects.select_related(
        'category', 'student', 'parent', 'uploaded_by', 'reviewed_by'
    )
    
    # Apply filters
    if status_filter:
        documents = documents.filter(status=status_filter)
    
    if category_filter:
        documents = documents.filter(category_id=category_filter)
    
    if search_query:
        documents = documents.filter(
            Q(title__icontains=search_query) |
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(parent__user__first_name__icontains=search_query) |
            Q(parent__user__last_name__icontains=search_query)
        )
    
    # Order by status priority and date
    documents = documents.order_by('-status', '-created_at')
    
    # Pagination
    paginator = Paginator(documents, 20)
    page = request.GET.get('page')
    documents = paginator.get_page(page)
    
    # Get categories for filter
    categories = DocumentCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'documents': documents,
        'categories': categories,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
    }
    
    return render(request, 'users/admin/documents.html', context)


@login_required
@user_passes_test(is_admin)
def review_document(request, document_id):
    """Review and approve/reject a document"""
    document = get_object_or_404(DocumentUpload, id=document_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action in ['approved', 'rejected', 'needs_revision']:
            document.status = action
            document.admin_notes = admin_notes
            document.reviewed_by = request.user
            document.reviewed_at = timezone.now()
            document.save()
            
            messages.success(request, f"Document {action} for {document.get_owner_name()}")
        
        return redirect('users:manage_documents')
    
    context = {
        'document': document,
    }
    
    return render(request, 'users/admin/review_document.html', context)


@login_required
@user_passes_test(is_admin)
def manage_admission_enquiries(request):
    """Manage admission enquiries"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    program_filter = request.GET.get('program', '')
    search_query = request.GET.get('search', '')
    
    # Base query
    enquiries = AdmissionEnquiry.objects.select_related('assigned_to')
    
    # Apply filters
    if status_filter:
        enquiries = enquiries.filter(status=status_filter)
    
    if program_filter:
        enquiries = enquiries.filter(program_of_interest=program_filter)
    
    if search_query:
        enquiries = enquiries.filter(
            Q(parent_name__icontains=search_query) |
            Q(child_name__icontains=search_query) |
            Q(parent_email__icontains=search_query) |
            Q(parent_phone__icontains=search_query)
        )
    
    # Order by status priority and date
    enquiries = enquiries.order_by('-status', '-created_at')
    
    # Pagination
    paginator = Paginator(enquiries, 20)
    page = request.GET.get('page')
    enquiries = paginator.get_page(page)
    
    context = {
        'enquiries': enquiries,
        'status_filter': status_filter,
        'program_filter': program_filter,
        'search_query': search_query,
    }
    
    return render(request, 'users/admin/admission_enquiries.html', context)


@login_required
@user_passes_test(is_admin)
def manage_visitor_logs(request):
    """Manage visitor logs"""
    # Get filter parameters
    date_filter = request.GET.get('date', '')
    visitor_type_filter = request.GET.get('visitor_type', '')
    purpose_filter = request.GET.get('purpose', '')
    search_query = request.GET.get('search', '')
    
    # Base query
    visitors = VisitorLog.objects.select_related('received_by')
    
    # Apply filters
    if date_filter:
        try:
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            visitors = visitors.filter(check_in_time__date=date_obj)
        except ValueError:
            pass
    
    if visitor_type_filter:
        visitors = visitors.filter(visitor_type=visitor_type_filter)
    
    if purpose_filter:
        visitors = visitors.filter(purpose=purpose_filter)
    
    if search_query:
        visitors = visitors.filter(
            Q(visitor_name__icontains=search_query) |
            Q(company_organization__icontains=search_query) |
            Q(person_to_meet__icontains=search_query)
        )
    
    # Order by most recent first
    visitors = visitors.order_by('-check_in_time')
    
    # Pagination
    paginator = Paginator(visitors, 20)
    page = request.GET.get('page')
    visitors = paginator.get_page(page)
    
    context = {
        'visitors': visitors,
        'date_filter': date_filter,
        'visitor_type_filter': visitor_type_filter,
        'purpose_filter': purpose_filter,
        'search_query': search_query,
    }
    
    return render(request, 'users/admin/visitor_logs.html', context)


@login_required
@user_passes_test(is_admin)
def edit_visitor_admin(request, visitor_id):
    """Edit visitor information (Admin)"""
    from django.http import JsonResponse

    visitor = get_object_or_404(VisitorLog, id=visitor_id)

    if request.method == 'POST':
        try:
            # Get form data
            visitor.visitor_name = request.POST.get('visitor_name', visitor.visitor_name)
            visitor.visitor_phone = request.POST.get('visitor_phone', visitor.visitor_phone)
            visitor.visitor_email = request.POST.get('visitor_email', visitor.visitor_email)
            visitor.visitor_type = request.POST.get('visitor_type', visitor.visitor_type)
            visitor.company_organization = request.POST.get('company_organization', visitor.company_organization)
            visitor.purpose = request.POST.get('purpose', visitor.purpose)
            visitor.purpose_description = request.POST.get('purpose_description', visitor.purpose_description)
            visitor.person_to_meet = request.POST.get('person_to_meet', visitor.person_to_meet)
            visitor.notes = request.POST.get('notes', visitor.notes)

            # Handle expected duration
            expected_duration = request.POST.get('expected_duration')
            if expected_duration:
                visitor.expected_duration = int(expected_duration)

            # Handle boolean fields
            visitor.id_verified = request.POST.get('id_verified') == 'on'
            visitor.visitor_badge_issued = request.POST.get('visitor_badge_issued') == 'on'

            visitor.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Visitor information updated successfully'})
            else:
                messages.success(request, 'Visitor information updated successfully')
                return redirect('users:manage_visitor_logs')

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            else:
                messages.error(request, f'Error updating visitor: {str(e)}')
                return redirect('users:manage_visitor_logs')

    # For GET requests, return visitor data as JSON for modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        visitor_data = {
            'id': visitor.id,
            'visitor_name': visitor.visitor_name,
            'visitor_phone': visitor.visitor_phone or '',
            'visitor_email': visitor.visitor_email or '',
            'visitor_type': visitor.visitor_type,
            'company_organization': visitor.company_organization or '',
            'purpose': visitor.purpose,
            'purpose_description': visitor.purpose_description or '',
            'person_to_meet': visitor.person_to_meet or '',
            'expected_duration': visitor.expected_duration or '',
            'notes': visitor.notes or '',
            'id_verified': visitor.id_verified,
            'visitor_badge_issued': visitor.visitor_badge_issued,
        }
        return JsonResponse(visitor_data)

    return redirect('users:manage_visitor_logs')


@login_required
@user_passes_test(is_admin)
def delete_visitor_admin(request, visitor_id):
    """Delete visitor record (Admin)"""
    from django.http import JsonResponse

    visitor = get_object_or_404(VisitorLog, id=visitor_id)

    if request.method == 'POST':
        try:
            visitor_name = visitor.visitor_name
            visitor.delete()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f'Visitor {visitor_name} deleted successfully'})
            else:
                messages.success(request, f'Visitor {visitor_name} deleted successfully')
                return redirect('users:manage_visitor_logs')

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            else:
                messages.error(request, f'Error deleting visitor: {str(e)}')
                return redirect('users:manage_visitor_logs')

    return redirect('users:manage_visitor_logs')


@login_required
@user_passes_test(is_admin)
def checkout_visitor_admin(request, visitor_id):
    """Check out a visitor (Admin)"""
    from django.http import JsonResponse

    visitor = get_object_or_404(VisitorLog, id=visitor_id)

    if request.method == 'POST':
        try:
            # Check if visitor is already checked out
            if visitor.check_out_time:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Visitor is already checked out'})
                else:
                    messages.error(request, 'Visitor is already checked out')
                    return redirect('users:manage_visitor_logs')

            # Check out the visitor
            visitor.check_out_time = timezone.now()
            checkout_notes = request.POST.get('checkout_notes', '')
            if checkout_notes:
                visitor.notes = (visitor.notes or '') + f'\nCheckout notes: {checkout_notes}'
            visitor.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Visitor {visitor.visitor_name} checked out successfully',
                    'checkout_time': visitor.check_out_time.strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                messages.success(request, f'Visitor {visitor.visitor_name} checked out successfully')
                return redirect('users:manage_visitor_logs')

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            else:
                messages.error(request, f'Error checking out visitor: {str(e)}')
                return redirect('users:manage_visitor_logs')

    return redirect('users:manage_visitor_logs')
