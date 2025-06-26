import csv
import io
import secrets
import string
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from .models import CustomUser, Student, Parent, Teacher, StaffMember
from .decorators import is_admin
from .utils import send_school_email


def generate_student_id():
    """Generate a unique student ID"""
    while True:
        student_id = f'DGMS{10000 + secrets.randbelow(90000)}'
        if not Student.objects.filter(student_id=student_id).exists():
            return student_id


def generate_pin():
    """Generate a 5-digit PIN for student login"""
    return ''.join(secrets.choice(string.digits) for _ in range(5))


def generate_employee_id(role):
    """Generate employee ID based on role"""
    prefixes = {
        'TEACHER': 'TCH',
        'ACCOUNTANT': 'ACC',
        'SECRETARY': 'SEC',
        'RECEPTIONIST': 'REC',
        'SECURITY': 'SCR',
        'JANITOR': 'JAN',
        'COOK': 'COK',
        'CLEANER': 'CLN',
        'STAFF': 'STF'
    }
    prefix = prefixes.get(role, 'STF')
    
    while True:
        employee_id = f'{prefix}{10000 + secrets.randbelow(90000)}'
        if not StaffMember.objects.filter(employee_id=employee_id).exists():
            return employee_id


def generate_password():
    """Generate a secure password"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))


@user_passes_test(is_admin)
def csv_upload_page(request):
    """Display the CSV upload page with templates"""
    return render(request, 'users/csv_upload.html')


@user_passes_test(is_admin)
def download_csv_template(request, user_type):
    """Download CSV template for specific user type"""
    templates = {
        'students': {
            'filename': 'students_template.csv',
            'headers': [
                'first_name', 'last_name', 'date_of_birth', 'grade', 'section',
                'parent_email', 'parent_first_name', 'parent_last_name',
                'parent_phone', 'parent_occupation', 'parent_relationship',
                'student_id', 'pin', 'additional_info'
            ],
            'sample_data': [
                'John', 'Doe', '2015-05-15', 'Grade 1', 'A',
                'jane.doe@example.com', 'Jane', 'Doe',
                '+233123456789', 'Engineer', 'Mother',
                'LEAVE_EMPTY_AUTO_GENERATE', 'LEAVE_EMPTY_AUTO_GENERATE', 'Excellent student'
            ]
        },
        'teachers': {
            'filename': 'teachers_template.csv',
            'headers': [
                'first_name', 'last_name', 'email', 'phone_number',
                'employee_id', 'subject_specialization', 'qualification',
                'experience_years', 'hire_date', 'salary', 'password'
            ],
            'sample_data': [
                'Mary', 'Smith', 'mary.smith@deigratiams.edu.gh', '+233987654321',
                'LEAVE_EMPTY_AUTO_GENERATE', 'Mathematics', 'BSc Mathematics', '5', '2024-01-15', '3000', 'LEAVE_EMPTY_AUTO_GENERATE'
            ]
        },
        'parents': {
            'filename': 'parents_template.csv',
            'headers': [
                'first_name', 'last_name', 'email', 'phone_number',
                'occupation', 'relationship', 'children_student_ids', 'password'
            ],
            'sample_data': [
                'Robert', 'Johnson', 'robert.johnson@example.com', '+233555666777',
                'Doctor', 'Father', 'STU12345,STU67890_OR_LEAVE_EMPTY', 'LEAVE_EMPTY_AUTO_GENERATE'
            ]
        },
        'staff': {
            'filename': 'staff_template.csv',
            'headers': [
                'first_name', 'last_name', 'email', 'phone_number', 'role',
                'employee_id', 'department', 'hire_date', 'salary', 'password'
            ],
            'sample_data': [
                'Alice', 'Brown', 'alice.brown@deigratiams.edu.gh', '+233444555666', 'RECEPTIONIST',
                'LEAVE_EMPTY_AUTO_GENERATE', 'Administration', '2024-01-15', '2500', 'LEAVE_EMPTY_AUTO_GENERATE'
            ]
        }
    }
    
    if user_type not in templates:
        return JsonResponse({'error': 'Invalid user type'}, status=400)
    
    template = templates[user_type]
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{template["filename"]}"'
    
    writer = csv.writer(response)
    writer.writerow(template['headers'])
    writer.writerow(template['sample_data'])
    
    return response


@user_passes_test(is_admin)
def process_csv_upload(request):
    """Process CSV file upload for bulk user creation with enhanced error handling and logging"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    csv_file = request.FILES.get('csv_file')
    user_type = request.POST.get('user_type')
    send_emails = request.POST.get('send_emails') == 'on'

    if not csv_file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'error': 'File must be a CSV'}, status=400)

    if user_type not in ['students', 'teachers', 'parents', 'staff']:
        return JsonResponse({'error': 'Invalid user type'}, status=400)

    try:
        # Read CSV file
        csv_data = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_data))

        # Count total rows for progress tracking
        rows = list(csv_reader)
        total_rows = len(rows)

        results = {
            'success_count': 0,
            'error_count': 0,
            'warning_count': 0,
            'total_rows': total_rows,
            'errors': [],
            'warnings': [],
            'created_users': [],
            'analytics': {
                'processing_time': 0,
                'email_success': 0,
                'email_failures': 0,
                'duplicate_emails': 0,
                'validation_errors': 0
            }
        }

        import time
        start_time = time.time()

        # Process each row with lenient error handling
        processed_count = 0
        for row_num, row in enumerate(rows, start=2):
            processed_count += 1

            try:
                # Create user based on type
                if user_type == 'students':
                    result = create_student_from_csv(row, send_emails)
                elif user_type == 'teachers':
                    result = create_teacher_from_csv(row, send_emails)
                elif user_type == 'parents':
                    result = create_parent_from_csv(row, send_emails)
                elif user_type == 'staff':
                    result = create_staff_from_csv(row, send_emails)

                if result['success']:
                    results['success_count'] += 1
                    results['created_users'].append(result['user_info'])

                    # Track email success
                    if send_emails:
                        results['analytics']['email_success'] += 1

                else:
                    # Categorize errors
                    error_msg = result['error'].lower()

                    if 'email' in error_msg and 'exists' in error_msg:
                        results['analytics']['duplicate_emails'] += 1
                        # Treat duplicate emails as warnings, not hard errors
                        results['warning_count'] += 1
                        results['warnings'].append({
                            'row': row_num,
                            'type': 'duplicate_email',
                            'message': result['error'],
                            'data': {k: v for k, v in row.items() if k in ['first_name', 'last_name', 'email']}
                        })
                    elif any(word in error_msg for word in ['required', 'missing', 'empty']):
                        results['analytics']['validation_errors'] += 1
                        results['error_count'] += 1
                        results['errors'].append({
                            'row': row_num,
                            'type': 'validation_error',
                            'error': result['error'],
                            'data': {k: v for k, v in row.items() if v.strip()}
                        })
                    else:
                        # Other errors
                        results['error_count'] += 1
                        results['errors'].append({
                            'row': row_num,
                            'type': 'general_error',
                            'error': result['error'],
                            'data': {k: v for k, v in row.items() if v.strip()}
                        })

            except Exception as e:
                # Handle unexpected errors gracefully
                error_msg = str(e)
                results['error_count'] += 1
                results['errors'].append({
                    'row': row_num,
                    'type': 'system_error',
                    'error': f'Unexpected error: {error_msg}',
                    'data': {k: v for k, v in row.items() if v.strip()}
                })

        # Calculate processing time
        end_time = time.time()
        results['analytics']['processing_time'] = round(end_time - start_time, 2)
        results['analytics']['email_failures'] = results['success_count'] - results['analytics']['email_success'] if send_emails else 0

        # Add summary statistics
        results['summary'] = {
            'total_processed': processed_count,
            'success_rate': round((results['success_count'] / total_rows) * 100, 1) if total_rows > 0 else 0,
            'error_rate': round((results['error_count'] / total_rows) * 100, 1) if total_rows > 0 else 0,
            'warning_rate': round((results['warning_count'] / total_rows) * 100, 1) if total_rows > 0 else 0
        }

        return JsonResponse(results)

    except UnicodeDecodeError:
        return JsonResponse({'error': 'File encoding error. Please ensure the CSV file is UTF-8 encoded.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Failed to process CSV: {str(e)}'}, status=500)


def create_student_from_csv(row, send_emails=True):
    """Create student from CSV row with enhanced admin-friendly features"""
    try:
        # Extract and clean data
        first_name = row.get('first_name', '').strip()
        last_name = row.get('last_name', '').strip()
        date_of_birth = row.get('date_of_birth', '').strip()
        grade = row.get('grade', '').strip()
        section = row.get('section', '').strip()
        provided_student_id = row.get('student_id', '').strip()
        provided_pin = row.get('pin', '').strip()

        # Parent info
        parent_email = row.get('parent_email', '').strip()
        parent_first_name = row.get('parent_first_name', '').strip()
        parent_last_name = row.get('parent_last_name', '').strip()
        parent_phone = row.get('parent_phone', '').strip()
        parent_occupation = row.get('parent_occupation', '').strip()
        parent_relationship = row.get('parent_relationship', '').strip() or 'Parent'

        # Validate required fields
        if not all([first_name, last_name]):
            return {'success': False, 'error': 'First name and last name are required'}

        # Smart Student ID handling
        student_id = provided_student_id
        if student_id:
            # Check if provided ID already exists
            if Student.objects.filter(student_id=student_id).exists():
                # Generate new ID and warn admin
                original_id = student_id
                student_id = generate_student_id()
                return {
                    'success': True,
                    'warning': f'Student ID "{original_id}" already exists. Generated new ID: {student_id}',
                    'user_info': {'note': 'ID was auto-generated due to duplicate'}
                }
        else:
            # Auto-generate if not provided
            student_id = generate_student_id()

        # Smart PIN handling
        pin = provided_pin
        if pin:
            # Validate PIN format (should be 5 digits)
            if not pin.isdigit() or len(pin) != 5:
                pin = generate_pin()  # Auto-fix invalid PIN
        else:
            pin = generate_pin()

        # Create student user
        email = f"{student_id}@school.internal"
        user = CustomUser.objects.create_user(
            email=email,
            password=pin,
            first_name=first_name,
            last_name=last_name,
            role=CustomUser.Role.STUDENT
        )
        
        # Create student profile
        student = Student.objects.create(
            user=user,
            student_id=student_id,
            pin=pin,
            date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None,
            grade=grade,
            section=section
        )
        
        # Enhanced parent creation/linking - fully automated for admins
        parent = None
        parent_created = False
        parent_linked = False

        if parent_email:
            try:
                # Try to find existing parent by email
                parent_user = CustomUser.objects.get(email=parent_email)
                if hasattr(parent_user, 'parent_profile'):
                    parent = parent_user.parent_profile
                    parent_linked = True
                else:
                    # User exists but not a parent - skip linking to avoid conflicts
                    parent = None
            except CustomUser.DoesNotExist:
                # Create new parent automatically if email provided
                if parent_first_name and parent_last_name:
                    try:
                        parent_password = generate_password()
                        parent_user = CustomUser.objects.create_user(
                            email=parent_email,
                            password=parent_password,
                            first_name=parent_first_name,
                            last_name=parent_last_name,
                            phone_number=parent_phone,
                            role=CustomUser.Role.PARENT
                        )
                        parent = Parent.objects.create(
                            user=parent_user,
                            occupation=parent_occupation,
                            relationship=parent_relationship
                        )
                        parent_created = True
                        parent_linked = True

                        # Send parent welcome email using existing system
                        if send_emails:
                            trigger_welcome_email(parent_user, parent_password)
                    except Exception as parent_error:
                        # If parent creation fails, continue with student creation
                        # This ensures student is still created even if parent fails
                        parent = None
                        print(f"Failed to create parent {parent_email}: {parent_error}")

            # Link student to parent if successful
            if parent:
                try:
                    parent.children.add(student)
                    parent_linked = True
                except Exception as link_error:
                    print(f"Failed to link student to parent: {link_error}")
                    parent_linked = False
        
        # Send student registration email to parent
        if send_emails and parent:
            try:
                send_student_registration_email(student, parent)
            except Exception as email_error:
                print(f"Failed to send student registration email: {email_error}")

        # Prepare detailed response for admin
        user_info = {
            'name': f"{first_name} {last_name}",
            'student_id': student_id,
            'pin': pin,
            'parent_email': parent_email if parent_email else 'Not provided',
            'parent_status': 'Not provided'
        }

        if parent_email:
            if parent_created:
                user_info['parent_status'] = f'✓ New parent created: {parent.user.get_full_name()}'
            elif parent_linked:
                user_info['parent_status'] = f'✓ Linked to existing parent: {parent.user.get_full_name()}'
            else:
                user_info['parent_status'] = '⚠ Parent linking failed (student still created)'

        return {
            'success': True,
            'user_info': user_info
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def create_teacher_from_csv(row, send_emails=True):
    """Create teacher from CSV row"""
    try:
        # Extract data
        first_name = row.get('first_name', '').strip()
        last_name = row.get('last_name', '').strip()
        email = row.get('email', '').strip()
        phone_number = row.get('phone_number', '').strip()
        employee_id = row.get('employee_id', '').strip() or generate_employee_id('TEACHER')
        subject_specialization = row.get('subject_specialization', '').strip()
        qualification = row.get('qualification', '').strip()
        experience_years = row.get('experience_years', '').strip()
        hire_date = row.get('hire_date', '').strip()
        salary = row.get('salary', '').strip()
        password = row.get('password', '').strip() or generate_password()
        
        # Validate required fields
        if not all([first_name, last_name, email]):
            return {'success': False, 'error': 'First name, last name, and email are required'}
        
        # Create user
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=CustomUser.Role.TEACHER
        )
        
        # Create teacher profile
        teacher = Teacher.objects.create(
            user=user,
            employee_id=employee_id,
            subject_specialization=subject_specialization,
            qualification=qualification,
            experience_years=int(experience_years) if experience_years.isdigit() else 0,
            hire_date=datetime.strptime(hire_date, '%Y-%m-%d').date() if hire_date else timezone.now().date(),
            salary=float(salary) if salary else 0.0
        )
        
        # Send welcome email using existing system
        if send_emails:
            trigger_welcome_email(user, password)
        
        return {
            'success': True,
            'user_info': {
                'name': f"{first_name} {last_name}",
                'email': email,
                'employee_id': employee_id,
                'password': password
            }
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def send_student_registration_email(student, parent):
    """Send student registration email to parent using existing template"""
    try:
        context = {
            'school_name': 'Deigratia Montessori School',
            'parent_name': parent.user.get_full_name(),
            'student_name': student.user.get_full_name(),
            'student_id': student.student_id,
            'pin': student.pin,
            'grade': student.grade,
            'section': student.section,
        }

        subject = f"Your Child Has Been Registered at {context['school_name']}"
        html_message = render_to_string('users/emails/student_registration.html', context)

        send_mail(
            subject=subject,
            message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[parent.user.email],
            html_message=html_message,
            fail_silently=False,
        )

    except Exception as e:
        print(f"Failed to send student registration email: {e}")


def trigger_welcome_email(user, password=None):
    """
    Trigger the existing welcome email system by setting the initial_password
    and letting the signal handle the email sending with proper templates
    """
    try:
        # Set the initial password for display in email
        if password:
            user.initial_password = password
            user.save(update_fields=['updated_at'])  # Trigger save without creating new user

        # The email will be sent by the existing signal system
        # which handles all user types with proper templates and conditional checks

    except Exception as e:
        print(f"Failed to trigger welcome email for {user.email}: {e}")


def create_parent_from_csv(row, send_emails=True):
    """Create parent from CSV row"""
    try:
        # Extract data
        first_name = row.get('first_name', '').strip()
        last_name = row.get('last_name', '').strip()
        email = row.get('email', '').strip()
        phone_number = row.get('phone_number', '').strip()
        occupation = row.get('occupation', '').strip()
        relationship = row.get('relationship', '').strip() or 'Parent'
        children_student_ids = row.get('children_student_ids', '').strip()
        password = row.get('password', '').strip() or generate_password()

        # Validate required fields
        if not all([first_name, last_name, email]):
            return {'success': False, 'error': 'First name, last name, and email are required'}

        # Create user
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=CustomUser.Role.PARENT
        )

        # Create parent profile
        parent = Parent.objects.create(
            user=user,
            occupation=occupation,
            relationship=relationship
        )

        # Link children if provided
        if children_student_ids:
            student_ids = [sid.strip() for sid in children_student_ids.split(',')]
            students = Student.objects.filter(student_id__in=student_ids)
            parent.children.add(*students)

        # Send welcome email using existing system
        if send_emails:
            trigger_welcome_email(user, password)

        return {
            'success': True,
            'user_info': {
                'name': f"{first_name} {last_name}",
                'email': email,
                'password': password,
                'children_count': parent.children.count()
            }
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def create_staff_from_csv(row, send_emails=True):
    """Create staff member from CSV row"""
    try:
        # Extract data
        first_name = row.get('first_name', '').strip()
        last_name = row.get('last_name', '').strip()
        email = row.get('email', '').strip()
        phone_number = row.get('phone_number', '').strip()
        role = row.get('role', '').strip().upper()
        employee_id = row.get('employee_id', '').strip() or generate_employee_id(role)
        department = row.get('department', '').strip()
        hire_date = row.get('hire_date', '').strip()
        salary = row.get('salary', '').strip()
        password = row.get('password', '').strip() or generate_password()

        # Validate required fields
        if not all([first_name, last_name, email, role]):
            return {'success': False, 'error': 'First name, last name, email, and role are required'}

        # Validate role
        valid_roles = [choice[0] for choice in CustomUser.Role.choices if choice[0] not in ['STUDENT', 'PARENT', 'TEACHER']]
        if role not in valid_roles:
            return {'success': False, 'error': f'Invalid role: {role}. Valid roles: {", ".join(valid_roles)}'}

        # Create user
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role=role
        )

        # Create staff profile
        staff = StaffMember.objects.create(
            user=user,
            employee_id=employee_id,
            department=department,
            hire_date=datetime.strptime(hire_date, '%Y-%m-%d').date() if hire_date else timezone.now().date(),
            salary=float(salary) if salary else 0.0
        )

        # Send welcome email using existing system
        if send_emails:
            trigger_welcome_email(user, password)

        return {
            'success': True,
            'user_info': {
                'name': f"{first_name} {last_name}",
                'email': email,
                'role': role,
                'employee_id': employee_id,
                'password': password
            }
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}



