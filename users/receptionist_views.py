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
Phone: {visitor_phone}
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
                
                messages.success(request, f"Visitor {visitor_name} has been logged successfully.")
            else:
                messages.error(request, "No admin users found to send visitor log to.")
                
        except Exception as e:
            messages.error(request, f"Error logging visitor: {str(e)}")
            
        return redirect('users:visitor_log')
    
    # Get recent visitor logs
    recent_visitors = Message.objects.filter(
        subject__icontains='[VISITOR]',
        sender=request.user
    ).order_by('-created_at')[:20]
    
    context = {
        'recent_visitors': recent_visitors,
    }
    
    return render(request, 'users/receptionist/visitor_log.html', context)

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
        results.append({
            'id': staff_member.id,
            'text': f"{staff_member.get_full_name()} ({staff_member.get_role_display()})",
            'name': staff_member.get_full_name(),
            'role': staff_member.get_role_display(),
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
@user_passes_test(is_receptionist)
def manage_visitor_logs(request):
    """Manage visitor check-in/check-out"""
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
