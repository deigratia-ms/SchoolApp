from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import CustomUser, Student, Teacher, Parent, StaffMember
from communications.models import Message, Announcement, Event
from documents.models import VisitorLog, AdmissionEnquiry
from appointments.models import Appointment
from courses.models import ClassRoom

# Helper function for receptionist check
def is_receptionist(user):
    return user.is_authenticated and user.role == 'RECEPTIONIST'

@login_required
@user_passes_test(is_receptionist)
def admission_inquiries(request):
    """Handle admission inquiries for receptionists"""
    if request.method == 'POST':
        # Handle new inquiry submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        grade_interested = request.POST.get('grade_interested')
        message_text = request.POST.get('message')
        child_name = request.POST.get('child_name')
        child_age_raw = request.POST.get('child_age')
        preferred_start_date_raw = request.POST.get('preferred_start_date')
        how_did_you_hear = request.POST.get('how_did_you_hear')
        
        # For now, we'll store this as a message to admin
        # In a full implementation, you'd have an AdmissionInquiry model
        try:
            admin_users = CustomUser.objects.filter(role='ADMIN')
            if admin_users.exists():
                admin = admin_users.first()
                
                # Create a message to admin about the inquiry
                inquiry_message = f"""
New Admission Inquiry Received:

Name: {name}
Email: {email}
Phone: {phone}
Grade Interested: {grade_interested}
Message: {message_text}

Received by: {request.user.get_full_name()} (Receptionist)
Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                Message.objects.create(
                    sender=request.user,
                    recipient=admin,
                    subject=f"[INQUIRY] New Admission Inquiry - {name}",
                    content=inquiry_message.strip()
                )

                # Persist to structured AdmissionEnquiry (safe defaults)
                try:
                    # Parse child_age safely
                    try:
                        child_age = int(child_age_raw) if child_age_raw not in (None, "") else None
                    except ValueError:
                        child_age = None

                    # Map grade_interested to program_of_interest choices
                    # Valid choices: toddler, primary, elementary
                    program_map = {
                        'toddler': 'toddler',
                        'nursery': 'toddler',
                        'kg': 'toddler',
                        'kindergarten': 'toddler',
                        'primary': 'primary',
                        'basic': 'primary',
                        'elementary': 'elementary',
                        'jhs': 'elementary',
                        'junior high': 'elementary',
                    }
                    gi = (grade_interested or '').strip().lower()
                    program_of_interest = 'primary'
                    for key, val in program_map.items():
                        if key in gi:
                            program_of_interest = val
                            break

                    # Parse preferred start date
                    preferred_start_date = None
                    if preferred_start_date_raw:
                        try:
                            preferred_start_date = datetime.strptime(preferred_start_date_raw, '%Y-%m-%d').date()
                        except Exception:
                            preferred_start_date = None

                    if child_name and child_age is not None:
                        AdmissionEnquiry.objects.create(
                            parent_name=name or 'Unknown',
                            parent_email=email or '',
                            parent_phone=phone or '',
                            child_name=child_name,
                            child_age=child_age,
                            program_of_interest=program_of_interest,
                            preferred_start_date=preferred_start_date,
                            message=message_text or '',
                            how_did_you_hear=how_did_you_hear or None,
                            assigned_to=None,
                        )
                    else:
                        messages.warning(request, "Inquiry recorded, but structured record needs child's name and age.")
                except Exception as e:
                    messages.warning(request, f"Inquiry recorded, but saving structured record failed: {str(e)}")
                
                messages.success(request, f"Admission inquiry for {name} has been recorded and sent to administration.")
            else:
                messages.error(request, "No admin users found to send inquiry to.")
                
        except Exception as e:
            messages.error(request, f"Error recording inquiry: {str(e)}")
            
        return redirect('users:admission_inquiries')
    
    # Get recent inquiries (messages with INQUIRY in subject)
    recent_inquiries = Message.objects.filter(
        subject__icontains='[INQUIRY]',
        sender=request.user
    ).order_by('-created_at')[:10]
    
    # Get available grades for the form
    grades = ClassRoom.objects.all().order_by('name')
    
    context = {
        'recent_inquiries': recent_inquiries,
        'grades': grades,
    }
    
    return render(request, 'users/receptionist/admission_inquiries.html', context)

@login_required
@user_passes_test(is_receptionist)
def visitor_log(request):
    """Handle visitor logging for receptionists"""
    if request.method == 'POST':
        # Handle new visitor entry
        visitor_name = request.POST.get('visitor_name')
        visitor_phone = request.POST.get('visitor_phone')
        visitor_email = request.POST.get('visitor_email')
        purpose = request.POST.get('purpose')
        person_to_visit = request.POST.get('person_to_visit')
        time_in = request.POST.get('time_in')
        
        # For now, we'll store this as a message to admin
        # In a full implementation, you'd have a VisitorLog model
        try:
            admin_users = CustomUser.objects.filter(role='ADMIN')
            if admin_users.exists():
                admin = admin_users.first()
                
                visitor_message = f"""
New Visitor Logged:

Visitor Name: {visitor_name}
Phone: {visitor_phone or 'Not provided'}
Email: {visitor_email or 'Not provided'}
Purpose: {purpose}
Person to Visit: {person_to_visit}
Time In: {time_in}

Logged by: {request.user.get_full_name()} (Receptionist)
Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                Message.objects.create(
                    sender=request.user,
                    recipient=admin,
                    subject=f"[VISITOR] Visitor Log - {visitor_name}",
                    content=visitor_message.strip()
                )

                # Also persist to VisitorLog model (safe defaults)
                # Map free-text purpose to choice or default to 'other'
                purpose_value = (purpose or '').strip().lower()
                valid_purposes = {
                    'meeting': 'meeting',
                    'school_tour': 'school_tour',
                    'tour': 'school_tour',
                    'pickup': 'pickup_dropoff',
                    'dropoff': 'pickup_dropoff',
                    'pickup_dropoff': 'pickup_dropoff',
                    'delivery': 'delivery',
                    'maintenance': 'maintenance',
                    'inspection': 'inspection',
                    'event': 'event',
                    'other': 'other',
                }
                mapped_purpose = valid_purposes.get(purpose_value, 'other')

                # Default visitor_type safely
                # If purpose hints admissions, set prospective_parent otherwise 'other'
                if 'admission' in purpose_value or 'enquiry' in purpose_value or 'inquiry' in purpose_value:
                    visitor_type = 'prospective_parent'
                else:
                    visitor_type = 'other'

                try:
                    VisitorLog.objects.create(
                        visitor_name=visitor_name or 'Unknown Visitor',
                        visitor_phone=visitor_phone or None,
                        visitor_email=visitor_email or None,
                        visitor_type=visitor_type,
                        purpose=mapped_purpose,
                        purpose_description=purpose if purpose else None,
                        person_to_meet=person_to_visit or None,
                        received_by=request.user,
                        notes=None,
                        id_verified=False,
                        visitor_badge_issued=False,
                    )
                except Exception as e:
                    # Do not fail the request; log a warning message for staff
                    messages.warning(request, f"Visitor logged, but saving structured record failed: {str(e)}")
                
                messages.success(request, f"Visitor {visitor_name} has been logged successfully.")
            else:
                messages.error(request, "No admin users found to send visitor log to.")
                
        except Exception as e:
            messages.error(request, f"Error logging visitor: {str(e)}")
            
        return redirect('users:visitor_log')
    
    # Get recent visitor logs (newest first) - only active ones (not checked out)
    recent_visitors = Message.objects.filter(
        subject__icontains='[VISITOR]',
        sender=request.user
    ).exclude(
        subject__icontains='[CHECKED_OUT]'
    ).order_by('-created_at')[:20]

    context = {
        'recent_visitors': recent_visitors,
    }

    return render(request, 'users/receptionist/visitor_log.html', context)


@login_required
@user_passes_test(is_receptionist)
def checkout_visitor_message(request, visitor_id):
    """Check out a visitor message and send thank you email if email is provided"""
    if request.method == 'POST':
        try:
            # Get the visitor message
            visitor_message = Message.objects.get(id=visitor_id, sender=request.user)

            # Extract visitor details from the message
            visitor_name = visitor_message.subject.replace('[VISITOR] Visitor Log - ', '')
            visitor_email = None

            # Parse email from message content if available
            content_lines = visitor_message.content.split('\n')
            for line in content_lines:
                line = line.strip()
                if line.lower().startswith('email:') and 'not provided' not in line.lower():
                    visitor_email = line.replace('Email:', '').replace('email:', '').strip()
                    if visitor_email and '@' in visitor_email:  # Basic email validation
                        break
                    else:
                        visitor_email = None

            # Update the message subject to indicate checkout
            visitor_message.subject = f"[CHECKED_OUT] {visitor_message.subject}"
            visitor_message.content += f"\n\nChecked out at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            visitor_message.save()

            # Send thank you email if email is provided
            email_sent = False
            email_error = None

            if visitor_email and visitor_email != 'Not provided' and '@' in visitor_email:
                try:
                    from users.utils import send_school_email
                    from users.models import SchoolSettings
                    from django.template.loader import render_to_string

                    # Get school settings for proper email configuration
                    school_settings = SchoolSettings.objects.first()
                    school_name = school_settings.school_name if school_settings else 'Deigratia Montessori School'

                    # Parse visitor details from message content
                    content_lines = visitor_message.content.split('\n')
                    purpose = 'Not specified'
                    person_to_visit = 'Not specified'

                    for line in content_lines:
                        line = line.strip()
                        if line.lower().startswith('purpose:'):
                            purpose = line.replace('Purpose:', '').replace('purpose:', '').strip()
                        elif line.lower().startswith('person to visit:'):
                            person_to_visit = line.replace('Person to Visit:', '').replace('person to visit:', '').strip()

                    # Prepare email context
                    email_context = {
                        'visitor_name': visitor_name,
                        'school_name': school_name,
                        'school_logo': school_settings.logo.url if school_settings and school_settings.logo else None,
                        'school_email': school_settings.email if school_settings else 'info@deigratiams.edu.gh',
                        'school_phone': school_settings.phone if school_settings else '+233 123 456 789',
                        'school_website': 'https://deigratiams.edu.gh',
                        'school_address': school_settings.address if school_settings else 'Oyibi, Greater Accra Region, Ghana',
                        'visit_date': timezone.now().strftime('%B %d, %Y'),
                        'checkout_time': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
                        'purpose': purpose,
                        'person_to_visit': person_to_visit if person_to_visit != 'Not specified' else None,
                    }

                    # Render HTML email template
                    html_message = render_to_string('users/emails/visitor_thank_you.html', email_context)

                    # Plain text version
                    plain_message = f"""Dear {visitor_name},

Thank you for visiting {school_name} today. We hope you had a pleasant experience.

Visit Details:
- Date: {email_context['visit_date']}
- Purpose: {purpose}
{f"- Person Visited: {person_to_visit}" if person_to_visit != 'Not specified' else ""}

If you have any questions or need further assistance, please don't hesitate to contact us.

Best regards,
{school_name} Team

---
{school_name}
{email_context['school_address']}
{email_context['school_phone']} | {email_context['school_email']}
{email_context['school_website']}"""

                    subject = f"Thank you for visiting {school_name}"

                    # Use the school's email utility function with HTML
                    sent_count = send_school_email(
                        subject=subject,
                        message=plain_message.strip(),
                        recipient_list=[visitor_email],
                        html_message=html_message,
                        fail_silently=False
                    )

                    if sent_count > 0:
                        email_sent = True
                    else:
                        email_error = "Email could not be sent (SMTP configuration issue)"

                except Exception as e:
                    email_error = f"Error sending thank you email: {str(e)}"
                    print(f"Email error: {e}")  # For debugging

            # Prepare response message
            response_message = f'Visitor {visitor_name} checked out successfully'

            if visitor_email and visitor_email != 'Not provided' and '@' in visitor_email:
                if email_sent:
                    response_message += f' and thank you email sent to {visitor_email}'
                elif email_error:
                    response_message += f' but email failed: {email_error}'
                else:
                    response_message += ' but email could not be sent'
            elif visitor_email and visitor_email != 'Not provided':
                response_message += ' (invalid email address provided)'
            else:
                response_message += ' (no email address provided)'

            return JsonResponse({
                'success': True,
                'message': response_message,
                'email_sent': email_sent,
                'email_error': email_error
            })

        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Visitor log not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error checking out visitor: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
@user_passes_test(is_receptionist)
def edit_visitor_message(request, visitor_id):
    """Edit a visitor log message"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)

            # Get the visitor message
            visitor_message = Message.objects.get(id=visitor_id, sender=request.user)

            visitor_name = data.get('visitor_name')
            visitor_email = data.get('visitor_email', '')
            purpose = data.get('purpose')

            # Update the message
            visitor_message.subject = f"[VISITOR] Visitor Log - {visitor_name}"

            # Update the content
            content_lines = visitor_message.content.split('\n')
            new_content = f"""
New Visitor Logged:

Visitor Name: {visitor_name}
Phone: {content_lines[3].replace('Phone:', '').strip() if len(content_lines) > 3 else 'Not provided'}
Email: {visitor_email or 'Not provided'}
Purpose: {purpose}
Person to Visit: {content_lines[6].replace('Person to Visit:', '').strip() if len(content_lines) > 6 else 'Not specified'}
Time In: {content_lines[7].replace('Time In:', '').strip() if len(content_lines) > 7 else 'Not specified'}

Logged by: {request.user.get_full_name()} (Receptionist)
Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            visitor_message.content = new_content.strip()
            visitor_message.save()

            return JsonResponse({'success': True, 'message': 'Visitor log updated successfully'})

        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Visitor log not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error updating visitor log: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
@user_passes_test(is_receptionist)
def delete_visitor_message(request, visitor_id):
    """Delete a visitor log message"""
    if request.method == 'POST':
        try:
            # Get the visitor message
            visitor_message = Message.objects.get(id=visitor_id, sender=request.user)
            visitor_name = visitor_message.subject.replace('[VISITOR] Visitor Log - ', '')

            # Delete the message
            visitor_message.delete()

            return JsonResponse({'success': True, 'message': f'Visitor log for {visitor_name} deleted successfully'})

        except Message.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Visitor log not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error deleting visitor log: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
@user_passes_test(is_receptionist)
def search_parents_ajax(request):
    """Search for parents to auto-fill visitor information"""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'parents': []})

    try:
        from users.models import Parent

        # Search for parents by name, email, or phone
        parents = Parent.objects.select_related('user').filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(user__phone_number__icontains=query)
        )[:10]  # Limit to 10 results

        parent_data = []
        for parent in parents:
            parent_data.append({
                'name': parent.user.get_full_name(),
                'email': parent.user.email or '',
                'phone': parent.user.phone_number or '',
            })

        return JsonResponse({'parents': parent_data})

    except Exception as e:
        return JsonResponse({'parents': [], 'error': str(e)})


@login_required
@user_passes_test(is_receptionist)
def visitor_history(request):
    """View all checked-out visitors with pagination and search"""
    from django.core.paginator import Paginator
    from datetime import datetime, timedelta

    # Get search parameters
    search_query = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Get checked-out visitor messages
    visitor_history = Message.objects.filter(
        subject__icontains='[CHECKED_OUT]',
        sender=request.user
    ).order_by('-created_at')

    # Apply search filter
    if search_query:
        visitor_history = visitor_history.filter(
            Q(subject__icontains=search_query) |
            Q(content__icontains=search_query)
        )

    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            visitor_history = visitor_history.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            visitor_history = visitor_history.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass

    # Calculate statistics
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    total_visitors = Message.objects.filter(
        subject__icontains='[CHECKED_OUT]',
        sender=request.user
    ).count()

    today_visitors = Message.objects.filter(
        subject__icontains='[CHECKED_OUT]',
        sender=request.user,
        created_at__date=today
    ).count()

    week_visitors = Message.objects.filter(
        subject__icontains='[CHECKED_OUT]',
        sender=request.user,
        created_at__date__gte=week_start
    ).count()

    month_visitors = Message.objects.filter(
        subject__icontains='[CHECKED_OUT]',
        sender=request.user,
        created_at__date__gte=month_start
    ).count()

    # Pagination
    paginator = Paginator(visitor_history, 20)  # 20 records per page
    page_number = request.GET.get('page')
    visitor_history_page = paginator.get_page(page_number)

    context = {
        'visitor_history': visitor_history_page,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_visitors': total_visitors,
        'today_visitors': today_visitors,
        'week_visitors': week_visitors,
        'month_visitors': month_visitors,
    }

    return render(request, 'users/receptionist/visitor_history.html', context)

@login_required
@user_passes_test(is_receptionist)
def document_requests(request):
    """Handle document requests for receptionists"""
    if request.method == 'POST':
        # Handle new document request
        student_name = request.POST.get('student_name')
        document_type = request.POST.get('document_type')
        requester_name = request.POST.get('requester_name')
        requester_phone = request.POST.get('requester_phone')
        urgency = request.POST.get('urgency', 'normal')
        
        try:
            admin_users = CustomUser.objects.filter(role='ADMIN')
            if admin_users.exists():
                admin = admin_users.first()
                
                document_message = f"""
New Document Request:

Student Name: {student_name}
Document Type: {document_type}
Requester Name: {requester_name}
Requester Phone: {requester_phone}
Urgency: {urgency}

Processed by: {request.user.get_full_name()} (Receptionist)
Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                Message.objects.create(
                    sender=request.user,
                    recipient=admin,
                    subject=f"[DOCUMENT] {document_type} Request for {student_name}",
                    content=document_message.strip()
                )
                
                messages.success(request, f"Document request for {student_name} has been submitted successfully.")
            else:
                messages.error(request, "No admin users found to send document request to.")
                
        except Exception as e:
            messages.error(request, f"Error submitting document request: {str(e)}")
            
        return redirect('users:document_requests')
    
    # Get recent document requests
    recent_requests = Message.objects.filter(
        subject__icontains='[DOCUMENT]',
        sender=request.user
    ).order_by('-created_at')[:15]
    
    # Document types
    document_types = [
        'Bonafide Certificate',
        'Transfer Certificate',
        'Character Certificate',
        'Academic Transcript',
        'Fee Receipt',
        'Attendance Certificate',
        'Other'
    ]
    
    context = {
        'recent_requests': recent_requests,
        'document_types': document_types,
    }
    
    return render(request, 'users/receptionist/document_requests.html', context)

@login_required
@user_passes_test(is_receptionist)
def student_directory_receptionist(request):
    """Student directory view for receptionists (read-only) with efficient pagination"""
    from django.core.paginator import Paginator

    search_query = request.GET.get('search', '')
    grade_filter = request.GET.get('grade', '')
    status_filter = request.GET.get('status', '')

    # Base query with select_related for efficiency
    students = Student.objects.select_related('user', 'grade').all()

    # Apply search filter
    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(student_id__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Apply grade filter
    if grade_filter:
        students = students.filter(grade_id=grade_filter)

    # Apply status filter
    if status_filter:
        students = students.filter(user__is_active=(status_filter == 'active'))

    # Order by name for consistent pagination
    students = students.order_by('user__first_name', 'user__last_name')

    # Get total count before pagination
    total_students = students.count()

    # Pagination - 50 students per page for optimal performance
    paginator = Paginator(students, 50)
    page = request.GET.get('page')
    students = paginator.get_page(page)

    # Get available grades for filter
    from courses.models import ClassRoom
    grades = ClassRoom.objects.all().order_by('name')

    context = {
        'students': students,
        'search_query': search_query,
        'grade_filter': grade_filter,
        'status_filter': status_filter,
        'grades': grades,
        'total_students': total_students,
    }

    return render(request, 'users/receptionist/student_directory.html', context)

@login_required
@user_passes_test(is_receptionist)
def staff_directory_receptionist(request):
    """Staff directory view for receptionists (read-only) with efficient pagination"""
    from django.core.paginator import Paginator

    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    # Base query for staff members
    staff = CustomUser.objects.filter(
        role__in=['ADMIN', 'TEACHER', 'SECRETARY', 'ACCOUNTANT', 'RECEPTIONIST', 'SECURITY', 'JANITOR', 'COOK', 'CLEANER', 'STAFF']
    ).select_related()

    # Apply search filter
    if search_query:
        staff = staff.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Apply role filter
    if role_filter:
        staff = staff.filter(role=role_filter)

    # Apply status filter
    if status_filter:
        staff = staff.filter(is_active=(status_filter == 'active'))

    # Order by name for consistent pagination
    staff = staff.order_by('first_name', 'last_name')

    # Get total count before pagination
    total_staff = staff.count()

    # Pagination - 50 staff per page for optimal performance
    paginator = Paginator(staff, 50)
    page = request.GET.get('page')
    staff = paginator.get_page(page)

    # Get available roles for filter
    roles = CustomUser.Role.choices

    context = {
        'staff': staff,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': roles,
        'total_staff': total_staff,
    }

    return render(request, 'users/receptionist/staff_directory.html', context)

@login_required
@user_passes_test(is_receptionist)
def search_staff_ajax(request):
    """AJAX endpoint for searching staff members"""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:  # Require at least 2 characters
        return JsonResponse({'results': [], 'query': query})

    # Search staff members
    staff = CustomUser.objects.filter(
        role__in=['ADMIN', 'TEACHER', 'SECRETARY', 'ACCOUNTANT', 'RECEPTIONIST', 'SECURITY', 'JANITOR', 'COOK', 'CLEANER', 'STAFF']
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).order_by('first_name', 'last_name')[:20]  # Limit to 20 results

    results = []
    for staff_member in staff:
        # Get role display - handle the case where get_role_display might not be recognized by static analysis
        role_display = getattr(staff_member, 'get_role_display', lambda: staff_member.role)()
        results.append({
            'id': staff_member.id,
            'text': f"{staff_member.get_full_name()} ({role_display})",
            'name': staff_member.get_full_name(),
            'role': role_display,
            'email': staff_member.email
        })

    # Add cache-busting headers
    response = JsonResponse({'results': results, 'query': query, 'count': len(results)})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

@login_required
@user_passes_test(is_receptionist)
def check_student_fees(request):
    """Check student fees - read-only for receptionists"""
    from fees.models import StudentFee, Term, FeeCategory
    from courses.models import ClassRoom
    from django.core.paginator import Paginator
    from django.db.models import Sum

    # Get filter parameters
    term_id = request.GET.get('term')
    classroom_id = request.GET.get('classroom')
    category_id = request.GET.get('fee_category')
    status = request.GET.get('status')
    search_query = request.GET.get('search')

    # Base query
    student_fees = StudentFee.objects.select_related(
        'student', 'student__user', 'class_fee', 'class_fee__classroom',
        'class_fee__fee_category', 'class_fee__term'
    )

    # Apply filters
    if term_id:
        student_fees = student_fees.filter(class_fee__term_id=term_id)

    if classroom_id:
        student_fees = student_fees.filter(class_fee__classroom_id=classroom_id)

    if category_id:
        student_fees = student_fees.filter(class_fee__fee_category_id=category_id)

    if status:
        student_fees = student_fees.filter(status=status)

    if search_query:
        student_fees = student_fees.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)
        )

    # Calculate totals
    total_amount = student_fees.aggregate(total=Sum('amount'))['total'] or 0
    total_paid = student_fees.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_balance = total_amount - total_paid
    collection_rate = (total_paid / total_amount * 100) if total_amount > 0 else 0

    # Order by due date and status
    student_fees = student_fees.order_by('due_date', '-status')

    # Pagination
    paginator = Paginator(student_fees, 25)  # Show 25 fees per page
    page = request.GET.get('page')
    student_fees = paginator.get_page(page)

    # Get filter options for dropdowns
    terms = Term.objects.all().order_by('-academic_year', 'name')
    classrooms = ClassRoom.objects.all().order_by('name')
    fee_categories = FeeCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'student_fees': student_fees,
        'terms': terms,
        'classrooms': classrooms,
        'fee_categories': fee_categories,
        'selected_term': term_id,
        'selected_classroom': classroom_id,
        'selected_category': category_id,
        'selected_status': status,
        'search_query': search_query,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'collection_rate': collection_rate,
    }

    return render(request, 'users/receptionist/check_fees.html', context)

@login_required
@user_passes_test(is_receptionist)
def payment_history(request):
    """View payment history - read-only for receptionists"""
    from fees.models import Payment, Term, FeeCategory
    from django.core.paginator import Paginator
    from django.db.models import Sum
    from datetime import timedelta

    # Get filter parameters
    term_id = request.GET.get('term')
    category_id = request.GET.get('fee_category')
    payment_method = request.GET.get('payment_method')
    date_range = request.GET.get('date_range')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_query = request.GET.get('search')

    # Base query
    payments = Payment.objects.select_related(
        'student_fee', 'student_fee__student', 'student_fee__student__user',
        'student_fee__class_fee', 'student_fee__class_fee__fee_category',
        'student_fee__class_fee__term', 'receipt', 'received_by'
    )

    # Apply filters
    if term_id:
        payments = payments.filter(student_fee__class_fee__term_id=term_id)

    if category_id:
        payments = payments.filter(student_fee__class_fee__fee_category_id=category_id)

    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    if search_query:
        payments = payments.filter(
            Q(student_fee__student__user__first_name__icontains=search_query) |
            Q(student_fee__student__user__last_name__icontains=search_query) |
            Q(student_fee__student__student_id__icontains=search_query) |
            Q(receipt__receipt_number__icontains=search_query)
        )

    # Date filtering
    if date_range == 'today':
        payments = payments.filter(created_at__date=timezone.now().date())
    elif date_range == 'week':
        week_ago = timezone.now() - timedelta(days=7)
        payments = payments.filter(created_at__gte=week_ago)
    elif date_range == 'month':
        month_ago = timezone.now() - timedelta(days=30)
        payments = payments.filter(created_at__gte=month_ago)
    elif date_range == 'custom' and start_date and end_date:
        payments = payments.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

    # Calculate totals
    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0

    # Order by most recent first
    payments = payments.order_by('-created_at')

    # Pagination
    paginator = Paginator(payments, 25)  # Show 25 payments per page
    page = request.GET.get('page')
    payments = paginator.get_page(page)

    # Get filter options for dropdowns
    terms = Term.objects.all().order_by('-academic_year', 'name')
    fee_categories = FeeCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'payments': payments,
        'terms': terms,
        'fee_categories': fee_categories,
        'selected_term': term_id,
        'selected_category': category_id,
        'selected_payment_method': payment_method,
        'selected_date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'total_amount': total_amount,
    }

    return render(request, 'users/receptionist/payment_history.html', context)

@login_required
@user_passes_test(is_receptionist)
def new_appointment(request):
    """Create new appointment for parents - receptionist can help schedule"""
    from appointments.models import TimeSlot, Appointment
    from users.models import Parent
    from django.core.paginator import Paginator

    if request.method == 'POST':
        # Handle appointment creation
        parent_id = request.POST.get('parent_id')
        slot_id = request.POST.get('slot_id')
        purpose = request.POST.get('purpose')

        try:
            parent = Parent.objects.get(id=parent_id)
            time_slot = TimeSlot.objects.get(id=slot_id, is_available=True)

            # Create appointment
            appointment = Appointment.objects.create(
                parent=parent,
                time_slot=time_slot,
                purpose=purpose,
                status='confirmed',  # Receptionist can directly confirm
                created_by=request.user
            )

            # Mark time slot as unavailable
            time_slot.is_available = False
            time_slot.save()

            messages.success(request, f"Appointment scheduled successfully for {parent.user.get_full_name()}")
            return redirect('users:view_appointments')

        except Exception as e:
            messages.error(request, f"Error scheduling appointment: {str(e)}")

    # Get available time slots
    available_slots = TimeSlot.objects.filter(
        date__gte=timezone.now().date(),
        is_available=True,
        is_active=True
    ).order_by('date', 'start_time')[:20]  # Limit to next 20 slots

    # Get all parents
    parents = Parent.objects.select_related('user').all().order_by('user__first_name', 'user__last_name')

    context = {
        'available_slots': available_slots,
        'parents': parents,
    }

    return render(request, 'users/receptionist/new_appointment.html', context)

@login_required
@user_passes_test(is_receptionist)
def view_appointments(request):
    """View all appointments - read-only for receptionists"""
    from appointments.models import Appointment
    from django.core.paginator import Paginator

    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    search_query = request.GET.get('search', '')

    # Base query
    appointments = Appointment.objects.select_related(
        'parent', 'parent__user', 'time_slot'
    ).all()

    # Apply filters
    if status_filter:
        appointments = appointments.filter(status=status_filter)

    if date_filter:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            appointments = appointments.filter(time_slot__date=date_obj)
        except ValueError:
            pass

    if search_query:
        appointments = appointments.filter(
            Q(parent__user__first_name__icontains=search_query) |
            Q(parent__user__last_name__icontains=search_query) |
            Q(purpose__icontains=search_query)
        )

    # Order by date and time
    appointments = appointments.order_by('-time_slot__date', '-time_slot__start_time')

    # Pagination
    paginator = Paginator(appointments, 20)
    page = request.GET.get('page')
    appointments = paginator.get_page(page)

    context = {
        'appointments': appointments,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search_query': search_query,
    }

    return render(request, 'users/receptionist/view_appointments.html', context)

@login_required
def manage_visitor_logs(request):
    """Manage visitor check-in/check-out"""
    # Check if user has permission (receptionist or admin)
    if not (request.user.role in ['RECEPTIONIST', 'ADMIN']):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard:index')

    from documents.models import VisitorLog
    from django.core.paginator import Paginator

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'check_in':
            # Handle visitor check-in
            visitor_name = request.POST.get('visitor_name')
            visitor_phone = request.POST.get('visitor_phone', '')
            visitor_email = request.POST.get('visitor_email', '')
            visitor_type = request.POST.get('visitor_type')
            company_organization = request.POST.get('company_organization', '')
            purpose = request.POST.get('purpose')
            purpose_description = request.POST.get('purpose_description', '')
            person_to_meet = request.POST.get('person_to_meet', '')
            expected_duration = request.POST.get('expected_duration')
            id_verified = request.POST.get('id_verified') == 'on'
            visitor_badge_issued = request.POST.get('visitor_badge_issued') == 'on'

            try:
                visitor_log = VisitorLog.objects.create(
                    visitor_name=visitor_name,
                    visitor_phone=visitor_phone,
                    visitor_email=visitor_email,
                    visitor_type=visitor_type,
                    company_organization=company_organization,
                    purpose=purpose,
                    purpose_description=purpose_description,
                    person_to_meet=person_to_meet,
                    expected_duration=int(expected_duration) if expected_duration else None,
                    received_by=request.user,
                    id_verified=id_verified,
                    visitor_badge_issued=visitor_badge_issued
                )

                messages.success(request, f"Visitor {visitor_name} checked in successfully")
                return redirect('users:manage_visitor_logs')

            except Exception as e:
                messages.error(request, f"Error checking in visitor: {str(e)}")

        elif action == 'check_out':
            # Handle visitor check-out
            visitor_id = request.POST.get('visitor_id')
            notes = request.POST.get('notes', '')

            try:
                visitor_log = VisitorLog.objects.get(id=visitor_id)
                visitor_log.check_out_time = timezone.now()
                visitor_log.notes = notes
                visitor_log.save()

                messages.success(request, f"Visitor {visitor_log.visitor_name} checked out successfully")
                return redirect('users:manage_visitor_logs')

            except Exception as e:
                messages.error(request, f"Error checking out visitor: {str(e)}")

    # Get filter parameters
    date_filter = request.GET.get('date', '')
    visitor_type_filter = request.GET.get('visitor_type', '')
    status_filter = request.GET.get('status', 'all')  # all, checked_in, checked_out
    search_query = request.GET.get('search', '')

    # Base query
    visitors = VisitorLog.objects.select_related('received_by')

    # Apply filters
    if date_filter:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            visitors = visitors.filter(check_in_time__date=date_obj)
        except ValueError:
            pass
    else:
        # Default to today's visitors
        visitors = visitors.filter(check_in_time__date=timezone.now().date())

    if visitor_type_filter:
        visitors = visitors.filter(visitor_type=visitor_type_filter)

    if status_filter == 'checked_in':
        visitors = visitors.filter(check_out_time__isnull=True)
    elif status_filter == 'checked_out':
        visitors = visitors.filter(check_out_time__isnull=False)

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
        'status_filter': status_filter,
        'search_query': search_query,
    }

    return render(request, 'users/receptionist/visitor_logs.html', context)


@login_required
@user_passes_test(is_receptionist)
def edit_visitor(request, visitor_id):
    """Edit visitor information"""
    from documents.models import VisitorLog
    from django.http import JsonResponse
    import json

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
@user_passes_test(is_receptionist)
def delete_visitor(request, visitor_id):
    """Delete visitor record"""
    from documents.models import VisitorLog
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
@user_passes_test(is_receptionist)
def checkout_visitor(request, visitor_id):
    """Check out a visitor"""
    from documents.models import VisitorLog
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
                    'checkout_time': visitor.check_out_time.strftime('%Y-%m-%d %H:%M:%S') if visitor.check_out_time else ''
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


@login_required
@user_passes_test(is_receptionist)
def send_thank_you_email(request, visitor_id):
    """Send thank you email to visitor"""
    from documents.models import VisitorLog
    from django.http import JsonResponse
    from users.models import SchoolSettings
    from users.utils import send_school_email

    visitor = get_object_or_404(VisitorLog, id=visitor_id)

    if request.method == 'POST':
        try:
            # Check if visitor has email
            if not visitor.visitor_email:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Visitor does not have an email address'})
                else:
                    messages.error(request, 'Visitor does not have an email address')
                    return redirect('users:manage_visitor_logs')

            # Get school settings
            school_settings = SchoolSettings.objects.first()
            if not school_settings or not school_settings.enable_visitor_thank_you_emails:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Thank you emails are disabled'})
                else:
                    messages.error(request, 'Thank you emails are disabled')
                    return redirect('users:manage_visitor_logs')

            # Get custom message or use professional template
            custom_message = request.POST.get('custom_message', '').strip()

            if custom_message:
                # Use custom message as plain text
                email_content = custom_message
                html_message = None
            else:
                # Use professional HTML template
                from django.template.loader import render_to_string

                email_context = {
                    'visitor_name': visitor.visitor_name,
                    'school_name': school_settings.school_name,
                    'school_logo': school_settings.logo.url if school_settings and school_settings.logo else None,
                    'school_email': school_settings.email if school_settings else 'info@deigratiams.edu.gh',
                    'school_phone': school_settings.phone if school_settings else '+233 123 456 789',
                    'school_website': 'https://deigratiams.edu.gh',
                    'school_address': school_settings.address if school_settings else 'Oyibi, Greater Accra Region, Ghana',
                    'visit_date': visitor.check_in_time.strftime('%B %d, %Y') if visitor.check_in_time else timezone.now().strftime('%B %d, %Y'),
                    'checkout_time': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
                    'purpose': visitor.purpose or 'Not specified',
                    'person_to_visit': visitor.person_to_meet if hasattr(visitor, 'person_to_meet') else None,
                }

                # Render HTML email template
                html_message = render_to_string('users/emails/visitor_thank_you.html', email_context)

                # Plain text version
                email_content = f"""Dear {visitor.visitor_name},

Thank you for visiting {school_settings.school_name} today. We hope you had a pleasant experience.

Visit Details:
- Date: {email_context['visit_date']}
- Purpose: {email_context['purpose']}
{f"- Person Visited: {email_context['person_to_visit']}" if email_context['person_to_visit'] else ""}

If you have any questions or need further assistance, please don't hesitate to contact us.

Best regards,
{school_settings.school_name} Team"""

            # Send email
            subject = f"Thank you for visiting {school_settings.school_name}"
            send_school_email(
                subject=subject,
                message=email_content,
                recipient_list=[visitor.visitor_email],
                html_message=html_message,
                fail_silently=False
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f'Thank you email sent to {visitor.visitor_email}'})
            else:
                messages.success(request, f'Thank you email sent to {visitor.visitor_email}')
                return redirect('users:manage_visitor_logs')

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            else:
                messages.error(request, f'Error sending thank you email: {str(e)}')
                return redirect('users:manage_visitor_logs')

    # For GET requests, return visitor data and email template
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        school_settings = SchoolSettings.objects.first()
        template = school_settings.visitor_thank_you_email_template if school_settings else "Dear {visitor_name},\n\nThank you for visiting {school_name} today. We appreciate your time and hope you had a pleasant experience.\n\nBest regards,\n{school_name} Team"

        # Ensure template is not None before calling format
        if template:
            default_message = template.format(
                visitor_name=visitor.visitor_name,
                school_name=school_settings.school_name if school_settings else "Our School",
                visit_date=visitor.check_in_time.strftime('%B %d, %Y') if visitor.check_in_time else "today"
            )
        else:
            default_message = f"Dear {visitor.visitor_name},\n\nThank you for visiting our school today. We appreciate your time and hope you had a pleasant experience.\n\nBest regards,\nSchool Team"

        return JsonResponse({
            'visitor_name': visitor.visitor_name,
            'visitor_email': visitor.visitor_email or '',
            'default_message': default_message,
            'has_email': bool(visitor.visitor_email),
            'emails_enabled': school_settings.enable_visitor_thank_you_emails if school_settings else False
        })

    return redirect('users:manage_visitor_logs')

@login_required
@user_passes_test(is_receptionist)
def view_documents(request):
    """View document uploads - read-only for receptionists"""
    from documents.models import DocumentUpload, DocumentCategory
    from django.core.paginator import Paginator

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

    # Order by most recent first
    documents = documents.order_by('-created_at')

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

    return render(request, 'users/receptionist/documents.html', context)


@login_required
@user_passes_test(is_receptionist)
def receptionist_enquiries(request):
    """Read-only list of AdmissionEnquiry with filters and pagination for receptionists"""
    from django.core.paginator import Paginator
    from django.db.models import Q

    status = request.GET.get('status', '')
    program = request.GET.get('program', '')
    search = request.GET.get('search', '')

    enquiries = AdmissionEnquiry.objects.select_related('assigned_to').all()

    if status:
        enquiries = enquiries.filter(status=status)
    if program:
        enquiries = enquiries.filter(program_of_interest=program)
    if search:
        enquiries = enquiries.filter(
            Q(parent_name__icontains=search) |
            Q(child_name__icontains=search) |
            Q(parent_email__icontains=search) |
            Q(parent_phone__icontains=search)
        )

    enquiries = enquiries.order_by('-created_at')

    paginator = Paginator(enquiries, 20)
    page = request.GET.get('page')
    enquiries_page = paginator.get_page(page)

    context = {
        'enquiries': enquiries_page,
        'status_filter': status,
        'program_filter': program,
        'search_query': search,
    }

    return render(request, 'users/receptionist/enquiries_list.html', context)
