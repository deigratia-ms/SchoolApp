from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_GET
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView as DjangoPasswordResetConfirmView, PasswordResetCompleteView
from django.core.mail import send_mail, BadHeaderError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.views.generic.edit import FormView
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm

from .utils import send_school_email
from .models import (
    CustomUser, Teacher, Student, Parent, StaffMember, SchoolSettings,
    IDCardTemplate, IDCard, AdmissionLetterTemplate, AdmissionLetter
)
from courses.models import ClassRoom

import random
import string
import secrets

# Helper functions for role-based access
def is_admin(user):
    return user.is_authenticated and user.role == CustomUser.Role.ADMIN

def is_teacher(user):
    return user.is_authenticated and user.role == CustomUser.Role.TEACHER

def is_student(user):
    return user.is_authenticated and user.role == CustomUser.Role.STUDENT

def is_parent(user):
    return user.is_authenticated and user.role == CustomUser.Role.PARENT

# Authentication views
def custom_login(request):
    """Regular login for admins using email and password"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.is_verified:
                if user.is_admin:
                    return redirect('admin:index')  # Redirect admin users to the admin interface
                login(request, user)
                next_url = request.GET.get('next', 'dashboard:index')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account is not verified. Please contact the administrator.')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'users/login.html')

def student_login(request):
    """Special login for students using student ID and PIN with flexible ID format handling"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        pin = request.POST.get('pin')

        # Use the flexible student authentication backend
        user = authenticate(request, student_id=student_id, pin=pin)

        if user is not None:
            if user.is_verified:
                login(request, user)
                return redirect('dashboard:index')
            else:
                messages.error(request, 'Your account is not verified. Please contact the administrator.')
        else:
            messages.error(request, 'Invalid student ID or PIN. Please check your credentials and try again.')

    return render(request, 'users/student_login.html')

def teacher_login(request):
    """Special login for teachers using staff ID and password"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('password')

        try:
            teacher = Teacher.objects.get(employee_id=staff_id)
            # Get the teacher's user and authenticate directly with email and password
            user = authenticate(request, email=teacher.user.email, password=password)

            if user is not None and user.is_verified:
                if user.role == CustomUser.Role.TEACHER:
                    login(request, user)
                    return redirect('dashboard:index')
                else:
                    messages.error(request, 'Invalid credentials. Please use the appropriate login page for your role.')
            else:
                messages.error(request, 'Invalid credentials or your account is not verified.')
        except Teacher.DoesNotExist:
            messages.error(request, 'Invalid staff ID or password.')

    return render(request, 'users/teacher_login.html')

def parent_login(request):
    """Special login for parents using email and password"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Directly authenticate with email and password
        user = authenticate(request, email=email, password=password)

        if user is not None and user.is_verified:
            if user.role == CustomUser.Role.PARENT:
                login(request, user)
                return redirect('dashboard:index')
            else:
                messages.error(request, 'Please use the appropriate login page for your role.')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'users/parent_login.html')

def custom_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('users:login')

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Custom admin dashboard view"""
    return render(request, 'dashboard/admin_dashboard.html')

def admin_login(request):
    """Custom admin login view"""
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('dashboard:admin_dashboard')
        return redirect('dashboard:index')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None and user.is_admin:
            if user.is_verified:
                login(request, user)
                return redirect('dashboard:admin_dashboard')
            else:
                messages.error(request, 'Your account is not verified. Please contact the administrator.')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'users/admin_login.html')

@login_required
def profile(request):
    user = request.user

    if request.method == 'POST':
        # Update profile information
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.phone_number = request.POST.get('phone_number')

        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']

        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('users:profile')

    # Get role-specific profile information
    context = {'user': user}

    if user.is_teacher:
        try:
            teacher = Teacher.objects.select_related('user').get(user=user)
            context['teacher'] = teacher
        except Teacher.DoesNotExist:
            # Create a teacher profile if it doesn't exist
            if user.role == CustomUser.Role.TEACHER:
                teacher = Teacher.objects.create(
                    user=user,
                    employee_id=f"T{user.id:05d}",  # Default employee ID
                    department="",
                    qualification=""
                )
                context['teacher'] = teacher

    elif user.is_student:
        try:
            student = Student.objects.select_related('user').get(user=user)
            context['student'] = student
        except Student.DoesNotExist:
            # Create a student profile if it doesn't exist
            if user.role == CustomUser.Role.STUDENT:
                student = Student.objects.create(
                    user=user,
                    student_id=f"S{user.id:05d}",  # Default student ID
                    pin=''.join(random.choices(string.digits, k=5)),  # Random 5-digit PIN
                    grade="",
                    section=""
                )
                context['student'] = student

    elif user.is_parent:
        try:
            parent = Parent.objects.select_related('user').prefetch_related('children').get(user=user)
            context['parent'] = parent
            context['children'] = parent.children.all()
        except Parent.DoesNotExist:
            # Create a parent profile if it doesn't exist
            if user.role == CustomUser.Role.PARENT:
                parent = Parent.objects.create(
                    user=user,
                    relationship="Parent",
                    occupation=""
                )
                context['parent'] = parent
                context['children'] = []

    # Check if an ID card exists for student users
    if user.is_student and 'student' in context:
        try:
            id_card = IDCard.objects.filter(user=user, is_active=True).latest('created_at')
            context['student_id_card'] = id_card
        except IDCard.DoesNotExist:
            pass

    return render(request, 'users/profile.html', context)

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users:profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'users/change_password.html', {'form': form})

# Password Reset Views
class CustomPasswordResetView(PasswordResetView):
    """Custom password reset view that uses our templates and email templates"""
    template_name = 'users/request_password_reset.html'
    email_template_name = 'users/password_reset_email.txt'
    html_email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')

    def form_valid(self, form):
        # Add success message
        messages.success(self.request, 'Password reset email sent! Please check your inbox.')
        return super().form_valid(form)

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """Override the send_mail method to use our custom email utility"""
        # Get the subject
        subject = render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())

        # Get the plain text message
        message = render_to_string(email_template_name, context)

        # Get the HTML message if template exists
        html_message = None
        if html_email_template_name:
            html_message = render_to_string(html_email_template_name, context)

        # Use our custom email utility
        from .utils import send_school_email
        send_school_email(
            subject=subject,
            message=message,
            recipient_list=[to_email],
            html_message=html_message,
            from_email=from_email,
            is_password_reset=True
        )

class CustomPasswordResetDoneView(PasswordResetDoneView):
    """Custom password reset done view that uses our template"""
    template_name = 'users/password_reset_done.html'

class CustomPasswordResetConfirmView(DjangoPasswordResetConfirmView):
    """Custom password reset confirm view that uses our template"""
    template_name = 'users/password_reset_confirm.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('users:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Set New Password'
        return context

    def form_valid(self, form):
        # Add success message
        messages.success(self.request, 'Your password has been reset successfully. You can now log in with your new password.')
        return super().form_valid(form)

    # Make sure we're directly using Django's implementation for token validation
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """Custom password reset complete view that redirects to login"""
    template_name = 'registration/password_reset_complete.html'

# Legacy function kept for backward compatibility
# Now it just redirects to the class-based view
def request_password_reset(request):
    """Redirect to the class-based password reset view"""
    return redirect('users:password_reset')

# Legacy function kept for backward compatibility
# Now it just redirects to the class-based view
def password_reset_done(request):
    """Redirect to the class-based password reset done view"""
    return redirect('users:password_reset_done')

def request_pin_reset(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = Student.objects.get(student_id=student_id)
            # Generate a new PIN
            new_pin = ''.join(random.choices(string.digits, k=5))
            student.pin = new_pin
            student.save()

            # Get the parent's email
            parents = student.parents.all()
            if parents.exists():
                # Assuming we only email the first parent for simplicity
                parent = parents.first()
                parent_email = parent.user.email

                # Send email to parent
                subject = "Student PIN Reset"
                message = f"""
                Dear {parent.user.get_full_name()},

                The PIN for student {student.user.get_full_name()} (ID: {student.student_id}) has been reset.

                New PIN: {new_pin}

                Please ensure this is kept secure.

                Sincerely,
                The School Administration
                """
                send_school_email(subject, message, recipient_list=[parent_email])
                messages.success(request, f"PIN reset for student {student.user.get_full_name()}. Email sent to parent.")
            else:
                messages.error(request, f"No parent found for student {student.user.get_full_name()}.  PIN reset, but no email sent.")
            return redirect('users:user_management') # Or wherever is appropriate
        except Student.DoesNotExist:
            messages.error(request, "Invalid student ID.")
            form = PasswordResetForm()  # Create a new form instance
            return render(request, 'users/request_pin_reset.html', {'form': form}) # Re-render the form

    form = PasswordResetForm() # Create a form instance for GET requests
    return render(request, 'users/request_pin_reset.html', {'form': form})

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Custom admin dashboard view"""
    return render(request, 'dashboard/admin_dashboard.html')

# Admin views for user management
@user_passes_test(is_admin)
def school_settings(request):
    settings = SchoolSettings.objects.first()
    if not settings:
        # Create new settings with defaults
        settings = SchoolSettings.objects.create(
            school_name="Ricas School Management System",  # Default name
            # Include default SMTP settings
            smtp_host='smtp.gmail.com',
            smtp_port=587,
            smtp_username='skillnetservices@gmail.com',
            smtp_password='bvcj inbr xxix sqif',
            smtp_use_tls=True,
            # Enable messaging by default
            enable_messaging=True,
            enable_student_to_student_chat=True
        )
        messages.success(request, 'Initial school settings created with default email configuration.')
    else:
        # Check if existing settings need SMTP defaults
        smtp_updated = False
        if not settings.smtp_host:
            settings.smtp_host = 'smtp.gmail.com'
            smtp_updated = True
        if not settings.smtp_port:
            settings.smtp_port = 587
            smtp_updated = True
        if not settings.smtp_username:
            settings.smtp_username = 'skillnetservices@gmail.com'
            smtp_updated = True
        if not settings.smtp_password:
            settings.smtp_password = 'bvcj inbr xxix sqif'
            smtp_updated = True
        if not settings.smtp_use_tls:
            settings.smtp_use_tls = True
            smtp_updated = True

        # Ensure messaging settings are enabled by default
        messaging_updated = False
        if not settings.enable_messaging:
            settings.enable_messaging = True
            messaging_updated = True
        if not settings.enable_student_to_student_chat:
            settings.enable_student_to_student_chat = True
            messaging_updated = True

        # Save if we made any changes
        if smtp_updated or messaging_updated:
            settings.save()
            messages.info(request, 'Settings were updated with default values.')

    if request.method == 'POST':
        settings.school_name = request.POST.get('school_name') or 'Ricas School Management System'
        settings.address = request.POST.get('address')
        settings.phone = request.POST.get('phone')

        # Handle email and website fields - convert None to empty string
        settings.email = request.POST.get('email') or ''
        settings.website = request.POST.get('website') or ''

        # Academic information
        settings.academic_year = request.POST.get('academic_year', '')
        settings.principal_name = request.POST.get('principal_name', '')

        # SMTP settings
        settings.smtp_host = request.POST.get('smtp_host', '')
        # Handle empty or non-numeric smtp_port value
        smtp_port = request.POST.get('smtp_port', '')
        if smtp_port and smtp_port.isdigit():
            settings.smtp_port = int(smtp_port)
        else:
            settings.smtp_port = None  # Use None instead of empty string for numeric field
        settings.smtp_username = request.POST.get('smtp_username', '')
        # Only update password if provided (to avoid clearing existing password)
        new_password = request.POST.get('smtp_password')
        if new_password:
            settings.smtp_password = new_password
        settings.smtp_use_tls = 'smtp_use_tls' in request.POST

        # Process all form fields with explicit transaction handling
        from django.db import transaction

        # First print what data we're getting from the form for all checkboxes
        print(f"Form data received - TLS checkbox: {'smtp_use_tls' in request.POST}")
        print(f"Form data received - notify_assignments: {'notify_assignments' in request.POST}")
        print(f"Form data received - notify_grades: {'notify_grades' in request.POST}")
        print(f"Form data received - notify_attendance: {'notify_attendance' in request.POST}")
        print(f"Form data received - notify_events: {'notify_events' in request.POST}")

        # Use Django's transaction.atomic to ensure all changes are saved together
        with transaction.atomic():
            # Process all checkboxes explicitly with boolean values
            # Communication settings
            settings.enable_messaging = 'enable_messaging' in request.POST and request.POST['enable_messaging'] == 'on'
            settings.enable_student_to_student_chat = 'enable_student_to_student_chat' in request.POST and request.POST['enable_student_to_student_chat'] == 'on'

            # Security settings
            settings.smtp_use_tls = 'smtp_use_tls' in request.POST and request.POST['smtp_use_tls'] == 'on'

            # Notification settings
            settings.notify_assignments = 'notify_assignments' in request.POST and request.POST['notify_assignments'] == 'on'
            settings.notify_grades = 'notify_grades' in request.POST and request.POST['notify_grades'] == 'on'
            settings.notify_attendance = 'notify_attendance' in request.POST and request.POST['notify_attendance'] == 'on'
            settings.notify_events = 'notify_events' in request.POST and request.POST['notify_events'] == 'on'

            # Log what values we're setting
            print(f"Setting notify_assignments to: {settings.notify_assignments}")
            print(f"Setting notify_grades to: {settings.notify_grades}")
            print(f"Setting notify_attendance to: {settings.notify_attendance}")
            print(f"Setting notify_events to: {settings.notify_events}")
            print(f"Setting enable_messaging to: {settings.enable_messaging}")
            print(f"Setting enable_student_to_student_chat to: {settings.enable_student_to_student_chat}")
            print(f"Setting smtp_use_tls to: {settings.smtp_use_tls}")

            # Appearance settings - also convert to boolean
            settings.primary_color = request.POST.get('primary_color', '#4e73df')
            settings.dark_mode = 'dark_mode' in request.POST and request.POST['dark_mode'] == 'on'

            # Handle logo upload
            if 'logo' in request.FILES:
                settings.logo = request.FILES['logo']
            elif 'remove_logo' in request.POST:
                settings.logo = None

            # Save settings to database within transaction
            # Save twice to ensure Django actually commits the changes
            settings.save(update_fields=[
                'school_name', 'logo', 'address', 'phone', 'email', 'website',
                'academic_year', 'principal_name', 'smtp_host', 'smtp_port',
                'smtp_username', 'smtp_password', 'smtp_use_tls',
                'enable_messaging', 'enable_student_to_student_chat',
                'notify_assignments', 'notify_grades', 'notify_attendance', 'notify_events',
                'primary_color', 'dark_mode'
            ])

        # After transaction commits, explicitly reload the settings
        try:
            # Force a database refresh by getting a fresh instance
            fresh_settings = SchoolSettings.objects.get(id=settings.id)

            # Print debug information to verify database state
            print(f"After save database verification - TLS: {fresh_settings.smtp_use_tls}")
            print(f"After save database verification - notify_assignments: {fresh_settings.notify_assignments}")
            print(f"After save database verification - notify_grades: {fresh_settings.notify_grades}")
            print(f"After save database verification - notify_attendance: {fresh_settings.notify_attendance}")
            print(f"After save database verification - notify_events: {fresh_settings.notify_events}")

            messages.success(request, 'School settings updated successfully.')
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')
            print(f"Error saving settings: {str(e)}")

        # Redirect to the base URL without fragments - tabs will be handled by JavaScript
        # This avoids the NoReverseMatch error when fragments are used in URL names
        return redirect('users:school_settings')

    # Convert None values to empty strings for the template
    context = {
        'settings': settings
    }

    return render(request, 'users/school_settings.html', context)

@user_passes_test(is_admin)
def backup_settings(request):
    """Generate and download a backup of school settings"""
    import json
    from django.http import HttpResponse

    settings = SchoolSettings.objects.first()
    if not settings:
        messages.error(request, 'No settings found to backup.')
        return redirect('users:school_settings')

    # Create a dictionary of all settings fields
    settings_data = {
        'school_name': settings.school_name,
        'address': settings.address,
        'phone': settings.phone,
        'email': settings.email,
        'website': settings.website,
        'academic_year': settings.academic_year if hasattr(settings, 'academic_year') else '',
        'principal_name': settings.principal_name if hasattr(settings, 'principal_name') else '',
        'smtp_host': settings.smtp_host,
        'smtp_port': settings.smtp_port,
        'smtp_username': settings.smtp_username,
        # Don't include password in the backup for security
        'smtp_use_tls': settings.smtp_use_tls,
        'notify_assignments': settings.notify_assignments if hasattr(settings, 'notify_assignments') else False,
        'notify_grades': settings.notify_grades if hasattr(settings, 'notify_grades') else False,
        'notify_attendance': settings.notify_attendance if hasattr(settings, 'notify_attendance') else False,
        'notify_events': settings.notify_events if hasattr(settings, 'notify_events') else False,
        'primary_color': settings.primary_color if hasattr(settings, 'primary_color') else '#4e73df',
        'dark_mode': settings.dark_mode if hasattr(settings, 'dark_mode') else False,
        # Logo is a file and can't be serialized to JSON
        'backup_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Create the JSON file
    json_data = json.dumps(settings_data, indent=4)

    # Create the HTTP response with the JSON file
    response = HttpResponse(json_data, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="school_settings_backup_{timezone.now().strftime("%Y%m%d%H%M%S")}.json"'

    return response

@user_passes_test(is_admin)
def restore_settings(request):
    """Restore school settings from a backup file"""
    import json
    import logging

    logger = logging.getLogger(__name__)

    if request.method != 'POST' or 'settings_file' not in request.FILES:
        messages.error(request, 'No settings file provided.')
        return redirect('users:school_settings')

    settings_file = request.FILES['settings_file']

    # Check if file is empty
    if settings_file.size == 0:
        messages.error(request, 'The settings file is empty. Please upload a valid backup file.')
        return redirect('users:school_settings')

    try:
        # Read the file content
        file_content = settings_file.read().decode('utf-8').strip()

        # Check if content is empty after stripping whitespace
        if not file_content:
            messages.error(request, 'The settings file is empty. Please upload a valid backup file.')
            return redirect('users:school_settings')

        # Log content for debugging (first 100 chars)
        logger.debug(f"Parsing JSON content: {file_content[:100]}...")

        # Parse the JSON
        settings_data = json.loads(file_content)

        # Validate the JSON structure
        required_fields = ['school_name']
        for field in required_fields:
            if field not in settings_data:
                messages.error(request, f'Invalid backup file format: Missing required field "{field}".')
                return redirect('users:school_settings')

        # Get or create SchoolSettings
        settings = SchoolSettings.objects.first()
        if not settings:
            settings = SchoolSettings.objects.create(
                school_name="School Management System"
            )

        # Update settings with values from the backup
        settings.school_name = settings_data.get('school_name', settings.school_name)
        settings.address = settings_data.get('address', settings.address)
        settings.phone = settings_data.get('phone', settings.phone)
        settings.email = settings_data.get('email', settings.email)
        settings.website = settings_data.get('website', settings.website)

        # Update academic information if available
        if 'academic_year' in settings_data and hasattr(settings, 'academic_year'):
            settings.academic_year = settings_data['academic_year']
        if 'principal_name' in settings_data and hasattr(settings, 'principal_name'):
            settings.principal_name = settings_data['principal_name']

        # Update SMTP settings
        settings.smtp_host = settings_data.get('smtp_host', settings.smtp_host)
        settings.smtp_port = settings_data.get('smtp_port', settings.smtp_port)
        settings.smtp_username = settings_data.get('smtp_username', settings.smtp_username)
        # Don't restore password from backup for security reasons
        settings.smtp_use_tls = settings_data.get('smtp_use_tls', settings.smtp_use_tls)

        # Update notification settings if available
        if 'notify_assignments' in settings_data and hasattr(settings, 'notify_assignments'):
            settings.notify_assignments = settings_data['notify_assignments']
        if 'notify_grades' in settings_data and hasattr(settings, 'notify_grades'):
            settings.notify_grades = settings_data['notify_grades']
        if 'notify_attendance' in settings_data and hasattr(settings, 'notify_attendance'):
            settings.notify_attendance = settings_data['notify_attendance']
        if 'notify_events' in settings_data and hasattr(settings, 'notify_events'):
            settings.notify_events = settings_data['notify_events']

        # Update appearance settings if available
        if 'primary_color' in settings_data and hasattr(settings, 'primary_color'):
            settings.primary_color = settings_data['primary_color']
        if 'dark_mode' in settings_data and hasattr(settings, 'dark_mode'):
            settings.dark_mode = settings_data['dark_mode']

        # Save the updated settings
        settings.save()

        messages.success(request, 'School settings restored successfully.')
    except json.JSONDecodeError as e:
        # More specific error for JSON parsing issues
        line_col = f" at line {e.lineno}, column {e.colno}" if hasattr(e, 'lineno') and hasattr(e, 'colno') else ""
        error_msg = f"Invalid JSON format in backup file{line_col}. Please ensure you're uploading a valid backup file."
        logger.error(f"JSON decode error: {str(e)}")
        messages.error(request, error_msg)
    except Exception as e:
        logger.error(f"Error restoring settings: {str(e)}")
        messages.error(request, f'Error restoring settings: {str(e)}')

    return redirect('users:school_settings')

@require_GET
def api_user_search(request):
    """API endpoint for searching users"""
    search_query = request.GET.get('q', '')

    if not search_query:
        return JsonResponse({'error': 'Search query parameter "q" is required'}, status=400)

    # Search users by email, first name, or last name
    users = CustomUser.objects.filter(
        Q(email__icontains=search_query) |
        Q(first_name__icontains=search_query) |
        Q(last_name__icontains=search_query)
    )

    # Prepare response data in expected format
    response_data = []
    for user in users:
        initials = (user.first_name[0] + user.last_name[0]).upper() if user.first_name and user.last_name else '??'
        full_name = f"{user.first_name} {user.last_name}".strip()
        role_display = dict(CustomUser.Role.choices).get(user.role, user.role)

        response_data.append({
            'user_id': user.id,
            'email': user.email,
            'initials': initials,
            'full_name': full_name,
            'role': user.role,
            'role_display': role_display
        })

    return JsonResponse(response_data, safe=False)

@user_passes_test(is_admin)
def test_email(request):
    """Test the SMTP email configuration"""
    from .utils import send_school_email

    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('users:school_settings')

    # Get the test email details
    test_email = request.POST.get('test_email')
    test_subject = request.POST.get('test_subject')
    test_content = request.POST.get('test_content')

    if not (test_email and test_subject and test_content):
        messages.error(request, 'All fields are required.')
        return redirect('users:school_settings')

    # Get the school settings
    school_settings = SchoolSettings.objects.first()
    if not school_settings:
        messages.error(request, 'School settings not found.')
        return redirect('users:school_settings')

    # Check if SMTP settings are configured
    if not (school_settings.smtp_host and school_settings.smtp_port and
            school_settings.smtp_username and school_settings.smtp_password):
        messages.error(request, 'SMTP settings are not fully configured.')
        return redirect('users:school_settings')

    try:
        # Send the test email using our utility function
        send_school_email(
            subject=test_subject,
            message=test_content,
            recipient_list=[test_email],
            from_email=school_settings.smtp_username
        )

        messages.success(request, f'Test email sent successfully to {test_email}.')
    except Exception as e:
        messages.error(request, f'Error sending test email: {str(e)}')

    return redirect('users:school_settings')

@user_passes_test(is_admin)
def user_management(request):
    """View and manage users"""
    role_filter = request.GET.get('role', None)
    search_query = request.GET.get('search', None)

    # Use select_related to preload related teacher, student, and parent data
    users = CustomUser.objects.all().select_related('teacher_profile', 'student_profile', 'parent_profile')

    if role_filter:
        users = users.filter(role=role_filter)

    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    return render(request, 'users/user_management.html', {
        'users': users,
        'role_filter': role_filter,
        'search_query': search_query,
    })

@user_passes_test(is_admin)
def teacher_management(request):
    """View and manage teachers"""
    search_query = request.GET.get('search', None)
    department_filter = request.GET.get('department', None)
    status_filter = request.GET.get('status', None)

    # Get all teachers with related user and classroom data
    teachers = Teacher.objects.all().select_related('user').prefetch_related('assigned_classrooms', 'assigned_classrooms__students')

    # Apply filters
    if search_query:
        teachers = teachers.filter(
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        )

    if department_filter:
        teachers = teachers.filter(department=department_filter)

    if status_filter:
        if status_filter == 'active':
            teachers = teachers.filter(user__is_active=True)
        elif status_filter == 'inactive':
            teachers = teachers.filter(user__is_active=False)

    # Get unique departments for filter dropdown
    departments = Teacher.objects.values_list('department', flat=True).distinct()
    departments = [dept for dept in departments if dept]  # Remove None/empty values

    return render(request, 'users/teacher_management.html', {
        'teachers': teachers,
        'departments': departments,
        'search_query': search_query,
        'department_filter': department_filter,
        'status_filter': status_filter,
    })

@user_passes_test(is_admin)
def student_management(request):
    """View and manage students"""
    search_query = request.GET.get('search', None)
    grade_level = request.GET.get('grade_level', None)
    status_filter = request.GET.get('status', None)

    # Get all students with related user and classroom data
    students = Student.objects.all().select_related('user').prefetch_related(
        'classrooms',
        'parents',
        'parents__user',
        'enrolled_subjects',
        'enrolled_subjects__subject',
        'enrolled_subjects__classroom'
    )

    # Apply filters
    if search_query:
        students = students.filter(
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(student_id__icontains=search_query)
        )

    # Filter by grade level (classroom)
    if grade_level and grade_level.isdigit():
        grade_level_int = int(grade_level)

        # Get all classrooms with the selected grade level
        filtered_classrooms = ClassRoom.objects.filter(grade_level=grade_level_int)

        # Get a list of IDs for students who are in these classrooms
        # This includes both ForeignKey 'grade' relationship and M2M 'classrooms' relationship
        filtered_student_ids = []

        # First check students directly assigned to these classrooms (ForeignKey)
        for student in Student.objects.filter(grade__in=filtered_classrooms):
            filtered_student_ids.append(student.id)

        # Then check students associated through M2M relationship
        for classroom in filtered_classrooms:
            for student in classroom.students.all():
                if student.id not in filtered_student_ids:
                    filtered_student_ids.append(student.id)

        # Now filter the student queryset to only include these students
        if filtered_student_ids:
            students = students.filter(id__in=filtered_student_ids)
        else:
            # If no students found for this grade level, return an empty queryset
            students = Student.objects.none()

    if status_filter:
        if status_filter == 'active':
            students = students.filter(user__is_active=True)
        elif status_filter == 'inactive':
            students = students.filter(user__is_active=False)

    # Get all classrooms for filter dropdown
    classrooms = ClassRoom.objects.all().order_by('grade_level', 'name')

    # Get unique grade levels for filter dropdown
    grade_levels = ClassRoom.objects.values_list('grade_level', flat=True).distinct().order_by('grade_level')

    return render(request, 'users/student_management.html', {
        'students': students,
        'classrooms': classrooms,
        'grade_levels': grade_levels,
        'search_query': search_query,
        'grade_filter': grade_level,  # Use grade_level for consistency with template
        'status_filter': status_filter,
    })

@user_passes_test(is_admin)
def parent_management(request):
    """View and manage parents"""
    search_query = request.GET.get('search', None)
    relationship_filter = request.GET.get('relationship', None)
    status_filter = request.GET.get('status', None)

    # Get all parents with related user data
    parents = Parent.objects.all().select_related('user').prefetch_related('children', 'children__user')

    # Apply filters
    if search_query:
        parents = parents.filter(
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__phone_number__icontains=search_query)
        )

    if relationship_filter:
        parents = parents.filter(relationship=relationship_filter)

    if status_filter:
        if status_filter == 'active':
            parents = parents.filter(user__is_active=True)
        elif status_filter == 'inactive':
            parents = parents.filter(user__is_active=False)

    return render(request, 'users/parent_management.html', {
        'parents': parents,
        'search_query': search_query,
        'relationship_filter': relationship_filter,
        'status_filter': status_filter,
    })

@user_passes_test(is_admin)
def create_user(request):
    """Create a new user"""
    if request.method == 'POST':
        role = request.POST.get('role')

        # Handle student creation differently
        if role == CustomUser.Role.STUDENT:
            try:
                # Generate student ID and PIN if not provided
                student_id = request.POST.get('student_id', '') or generate_student_id()
                pin = request.POST.get('pin', '') or generate_pin()

                # Create a unique email for the student using student ID
                email = f"{student_id}@school.internal"

                # Create user with student role
                user = CustomUser.objects.create_user(
                    email=email,
                    password=pin,  # Use PIN as password
                    first_name=request.POST.get('first_name'),
                    last_name=request.POST.get('last_name'),
                    role=CustomUser.Role.STUDENT
                )

                # Create student profile
                student = Student.objects.create(
                    user=user,
                    student_id=student_id,
                    pin=pin,
                    date_of_birth=request.POST.get('date_of_birth')
                )

                # Handle classroom assignment
                classroom_id = request.POST.get('classroom')
                if classroom_id:
                    try:
                        classroom = ClassRoom.objects.get(id=classroom_id)
                        student.grade = classroom
                        student.save()
                        messages.success(request, f'Student assigned to classroom: {classroom.name}')
                    except ClassRoom.DoesNotExist:
                        messages.error(request, 'Selected classroom not found.')

                # Link parent if provided
                parent_id = request.POST.get('parent_id')
                if parent_id:
                    try:
                        parent = Parent.objects.get(id=parent_id)
                        parent.children.add(student)

                        # Send email to parent
                        school_settings = SchoolSettings.objects.first()
                        context = {
                            'parent_name': parent.user.get_full_name(),
                            'student_name': student.user.get_full_name(),
                            'student_id': student.student_id,
                            'pin': student.pin,
                            'school_name': school_settings.school_name if school_settings else 'Our School'
                        }

                        email_subject = f"Your Child Has Been Registered at {context['school_name']}"
                        email_body = render_to_string('users/emails/student_registration.html', context)

                        send_mail(
                            subject=email_subject,
                            message=email_body,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[parent.user.email],
                            html_message=email_body,
                            fail_silently=False,
                        )

                    except Parent.DoesNotExist:
                        messages.warning(request, 'Parent not found. Student registered without parent link.')
                    except Exception as e:
                        messages.warning(request, f'Student registered but email notification failed: {str(e)}')

                messages.success(request, f'Student registered successfully. ID: {student_id}, PIN: {pin}')
                return redirect('users:user_management')

            except Exception as e:
                messages.error(request, f'Error registering student: {str(e)}')
                classrooms = ClassRoom.objects.all()
                parents = Parent.objects.all()
                return render(request, 'users/create_user.html', {'parents': parents, 'classrooms': classrooms})

        # Handle other roles (Teacher, Parent) as before...
        else:
            email = request.POST.get('email')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            phone_number = request.POST.get('phone_number')

            # Get email notification preference - default is to send email unless skip is checked
            skip_welcome_email = 'skip_welcome_email' in request.POST
            send_welcome_email = not skip_welcome_email

            # Debug print to check form data
            print(f"Form data received - Email: {email}, Role: {role}, Skip welcome email: {skip_welcome_email}")

            # Check if email already exists
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('users:create_user')

            # Create user
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                phone_number=phone_number,
                is_verified=True
            )

            # Handle Teacher role
            if role == CustomUser.Role.TEACHER:
                employee_id = request.POST.get('employee_id')
                department = request.POST.get('department')
                qualification = request.POST.get('qualification')

                Teacher.objects.create(
                    user=user,
                    employee_id=employee_id,
                    department=department,
                    qualification=qualification
                )

                # Send email notification to teacher
                if send_welcome_email:
                    try:
                        # Get school settings for email details
                        school_settings = SchoolSettings.objects.first()
                        school_name = school_settings.school_name if school_settings else "School Management System"

                        # Prepare welcome email content
                        subject = f"Welcome to {school_name}"
                        message = f"""
                        Dear {first_name} {last_name},

                        Welcome to {school_name}! Your teacher account has been created successfully.

                        Your login credentials:
                        Email: {email}
                        Password: {password}
                        Employee ID: {employee_id}

                        You can log in at: {request.build_absolute_uri('/users/teacher-login/')}

                        For security reasons, please change your password after your first login.

                        Best regards,
                        The Administration Team
                        {school_name}
                        """

                        # Create HTML version of the email with better formatting
                        school_settings = SchoolSettings.objects.first()
                        school_name = school_settings.school_name if school_settings and school_settings.school_name else "School Management System"

                        # Add logo handling
                        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
                        logo_html = ""
                        if school_settings and school_settings.logo:
                            logo_html = f'<div style="text-align: center; margin-bottom: 20px;"><img src="{base_url}{school_settings.logo.url}" alt="{school_name} Logo" style="max-width: 200px; max-height: 100px;"></div>'

                        current_year = timezone.now().year
                        html_message = f"""
                        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                            <div style="text-align: center; margin-bottom: 20px;">
                                <h2 style="color: #4e73df; margin-bottom: 5px;">{school_name}</h2>
                                <p style="color: #666; font-size: 14px; margin-top: 0;">School Management System</p>
                            </div>

                            {logo_html}

                            <div style="border-top: 3px solid #4e73df; margin-bottom: 20px;"></div>

                            <p>Dear <strong>{first_name} {last_name}</strong>,</p>

                            <p>We are pleased to welcome you to our school community! Your teacher account has been created successfully.</p>

                            <div style="background-color: #f8f9fc; padding: 15px; border-radius: 5px; margin: 15px 0;">
                                <h3 style="margin-top: 0; color: #333;">Your Login Credentials</h3>
                                <p><strong>Email:</strong> {email}</p>
                                <p><strong>Password:</strong> {password}</p>
                                <p><strong>Employee ID:</strong> {employee_id}</p>
                                <p><strong>Login URL:</strong> <a href="{request.build_absolute_uri('/users/teacher-login/')}">{request.build_absolute_uri('/users/teacher-login/')}</a></p>
                            </div>

                            <p>For security reasons, please change your password after your first login.</p>

                            <p>If you have any questions or need assistance, please don't hesitate to contact us.</p>

                            <p>Best regards,<br>
                            The Administration Team<br>
                            {school_name}</p>

                            <div style="border-top: 1px solid #ddd; margin-top: 20px; padding-top: 10px; text-align: center; color: #888; font-size: 12px;">
                                © {current_year} {school_name}. All rights reserved.
                            </div>
                        </div>
                        """

                        # Send welcome email
                        from .utils import send_school_email
                        send_school_email(
                            subject=subject,
                            message=message,
                            recipient_list=[email],
                            html_message=html_message
                        )

                    except Exception as e:
                        messages.warning(request, f"Teacher account created but welcome email failed: {str(e)}")

            # Handle Parent role
            elif role == CustomUser.Role.PARENT:
                occupation = request.POST.get('occupation')
                relationship = request.POST.get('relationship')

                Parent.objects.create(
                    user=user,
                    occupation=occupation,
                    relationship=relationship
                )

            # Handle Staff roles (non-teaching staff)
            elif role in [CustomUser.Role.ACCOUNTANT, CustomUser.Role.SECRETARY,
                         CustomUser.Role.RECEPTIONIST, CustomUser.Role.SECURITY,
                         CustomUser.Role.JANITOR, CustomUser.Role.COOK,
                         CustomUser.Role.CLEANER, CustomUser.Role.STAFF]:
                employee_id = request.POST.get('employee_id')
                staff_type = request.POST.get('staff_type')
                department = request.POST.get('department')
                position = request.POST.get('position')
                date_joined = request.POST.get('date_joined') or timezone.now().date()
                responsibilities = request.POST.get('responsibilities')

                # Map role to staff type if not provided
                if not staff_type:
                    if role == CustomUser.Role.ACCOUNTANT:
                        staff_type = 'ADMINISTRATIVE'
                    elif role in [CustomUser.Role.SECRETARY, CustomUser.Role.RECEPTIONIST]:
                        staff_type = 'SUPPORT'
                    elif role in [CustomUser.Role.JANITOR, CustomUser.Role.CLEANER]:
                        staff_type = 'MAINTENANCE'
                    elif role == CustomUser.Role.SECURITY:
                        staff_type = 'SECURITY'
                    elif role == CustomUser.Role.COOK:
                        staff_type = 'FOOD_SERVICE'
                    else:
                        staff_type = 'OTHER'

                # Create staff member profile
                StaffMember.objects.create(
                    user=user,
                    employee_id=employee_id,
                    staff_type=staff_type,
                    department=department,
                    position=position,
                    date_joined=date_joined,
                    responsibilities=responsibilities
                )

            if send_welcome_email:
                messages.success(request, f'{role.capitalize()} created successfully. Welcome email sent.')
            else:
                messages.success(request, f'{role.capitalize()} created successfully. No welcome email sent.')

            return redirect('users:user_management')

    # For GET request, display the form
    classrooms = ClassRoom.objects.all()
    parents = Parent.objects.all()
    staff_members = StaffMember.objects.all()

    # Get current date for default date fields
    today = timezone.now()

    return render(request, 'users/create_user.html', {
        'classrooms': classrooms,
        'parents': parents,
        'staff_members': staff_members,
        'today': today
    })

@user_passes_test(is_admin)
def edit_user(request, user_id):
    """Edit an existing user"""
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        # Update user information
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone_number = request.POST.get('phone_number')

        # Only admin can change roles
        if is_admin(request.user):
            user.role = request.POST.get('role')

        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']

        # Update password if provided
        password = request.POST.get('password')
        if password:
            user.set_password(password)

        user.save()

        # Update role-specific information
        if user.is_teacher:
            try:
                teacher = Teacher.objects.get(user=user)
                teacher.employee_id = request.POST.get('employee_id')
                teacher.department = request.POST.get('department')
                teacher.qualification = request.POST.get('qualification')
                teacher.save()
            except Teacher.DoesNotExist:
                pass

        elif user.is_student:
            try:
                student = Student.objects.get(user=user)
                student.student_id = request.POST.get('student_id')
                student.pin = request.POST.get('pin')
                student.save()

                # Handle classroom assignment - a student can only belong to one class
                classroom_id = request.POST.get('classroom')
                if classroom_id:
                    try:
                        new_classroom = ClassRoom.objects.get(id=classroom_id)

                        # Store current classroom for comparison
                        old_classroom = student.grade

                        # Set the student's grade (ForeignKey to classroom)
                        student.grade = new_classroom
                        student.save()

                        # Update the classroom's students collection if needed
                        if old_classroom != new_classroom:
                            messages.success(request, f'Student assigned to classroom: {new_classroom.name}')

                    except ClassRoom.DoesNotExist:
                        messages.error(request, 'Selected classroom not found.')

                # Update parent assignment
                parent_id = request.POST.get('parent_id')
                if parent_id:
                    try:
                        parent = Parent.objects.get(id=parent_id)
                        parent.children.add(student)
                        parent.save()
                    except Parent.DoesNotExist:
                        messages.warning(request, 'Selected parent not found.')
            except Student.DoesNotExist:
                pass

        elif user.is_parent:
            try:
                parent = Parent.objects.get(user=user)
                parent.occupation = request.POST.get('occupation')
                parent.relationship = request.POST.get('relationship')
                parent.save()
            except Parent.DoesNotExist:
                pass

        # Handle Staff roles (non-teaching staff)
        elif user.is_non_teaching_staff:
            try:
                staff = StaffMember.objects.get(user=user)
                staff.employee_id = request.POST.get('employee_id')
                staff.staff_type = request.POST.get('staff_type')
                staff.department = request.POST.get('department')
                staff.position = request.POST.get('position')

                if request.POST.get('date_joined'):
                    staff.date_joined = request.POST.get('date_joined')

                staff.responsibilities = request.POST.get('responsibilities')

                # Handle supervisor assignment if provided
                supervisor_id = request.POST.get('supervisor')
                if supervisor_id:
                    try:
                        supervisor = StaffMember.objects.get(id=supervisor_id)
                        staff.supervisor = supervisor
                    except StaffMember.DoesNotExist:
                        messages.warning(request, 'Selected supervisor not found.')
                else:
                    staff.supervisor = None

                staff.save()
            except StaffMember.DoesNotExist:
                pass

        messages.success(request, 'User updated successfully.')
        return redirect('users:user_management')

    # For GET request, display the form with user data
    context = {'user': user}

    # Add staff members for supervisor selection
    staff_members = StaffMember.objects.all()
    context['staff_members'] = staff_members

    # Get current date for default date fields
    context['today'] = timezone.now()

    if user.is_teacher:
        try:
            context['teacher'] = Teacher.objects.get(user=user)
        except Teacher.DoesNotExist:
            pass

    elif user.is_student:
        try:
            student = Student.objects.get(user=user)
            context['student'] = student
            context['student_parent_ids'] = list(student.parents.values_list('id', flat=True))
        except Student.DoesNotExist:
            pass

    elif user.is_parent:
        try:
            context['parent'] = Parent.objects.get(user=user)
        except Parent.DoesNotExist:
            pass

    classrooms = ClassRoom.objects.all()
    parents = Parent.objects.all()
    context['classrooms'] = classrooms
    context['parents'] = parents

    return render(request, 'users/edit_user.html', context)

@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Delete a user"""
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('users:user_management')

    return render(request, 'users/delete_user.html', {'user_to_delete': user})

@user_passes_test(is_admin)
def reset_password(request, user_id):
    """Reset password for a user"""
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        send_email = 'send_reset_email' in request.POST

        if not new_password:
            messages.error(request, 'New password is required.')
            return redirect('users:edit_user', user_id=user.id)

        # Set the new password
        user.set_password(new_password)
        user.save()

        # Send email notification if requested
        if send_email and user.email:
            try:
                from .utils import send_school_email

                # Get school settings
                school_settings = SchoolSettings.objects.first()
                school_name = school_settings.school_name if school_settings else "School Management System"

                subject = f"Password Reset - {school_name}"
                message = f"""
                Dear {user.get_full_name()},

                Your password has been reset by an administrator.

                Your new password is: {new_password}

                Please log in with this password and change it immediately for security reasons.

                Best regards,
                {school_name} Administration
                """

                send_school_email(
                    subject=subject,
                    message=message,
                    recipient_list=[user.email],
                )

                messages.success(request, f'Password reset successfully. Email notification sent to {user.email}.')
            except Exception as e:
                messages.warning(request, f'Password reset successfully, but failed to send email notification: {str(e)}')
        else:
            messages.success(request, f'Password reset successfully to: {new_password}')

        return redirect('users:edit_user', user_id=user.id)

    # If not POST, redirect to edit page
    return redirect('users:edit_user', user_id=user.id)

# Helper functions to generate IDs and PINs
def generate_student_id():
    """Generate a unique student ID using cryptographically secure random number generator"""
    while True:
        # Use secrets.randbelow to generate a secure random number between 0 and 89999
        # Then add 10000 to ensure 5-digit number between 10000 and 99999
        student_id = f'STU{10000 + secrets.randbelow(90000)}'
        if not Student.objects.filter(student_id=student_id).exists():
            return student_id

def generate_pin():
    """Generate a 5-digit PIN for student login using cryptographically secure random generator"""
    # Generate 5 secure random digits
    return ''.join(secrets.choice(string.digits) for _ in range(5))

# Teacher registration views
@user_passes_test(is_admin)
def register_teacher(request):
    """Register a new teacher"""
    if request.method == 'POST':
        # Extract form data and create teacher
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        employee_id = request.POST.get('employee_id')
        department = request.POST.get('department')
        qualification = request.POST.get('qualification')

        # Get email notification preference - default is to send email unless skip is checked
        skip_welcome_email = 'skip_welcome_email' in request.POST

        # Create user with teacher role
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=CustomUser.Role.TEACHER,
            is_verified=True
        )

        # Create teacher profile
        Teacher.objects.create(
            user=user,
            employee_id=employee_id,
            department=department,
            qualification=qualification
        )

        # Handle welcome email unless skip checkbox is checked
        if not skip_welcome_email:
            try:
                # Get school settings for email details
                school_settings = SchoolSettings.objects.first()
                school_name = school_settings.school_name if school_settings else "Ricas School Management System"

                # Prepare welcome email content
                subject = f"Welcome to {school_name}"
                message = f"""
                Dear {first_name} {last_name},

                Welcome to {school_name}! Your teacher account has been created successfully.

                Your login credentials:
                Email: {email}
                Password: {password}
                Employee ID: {employee_id}

                You can log in at: {request.build_absolute_uri('/users/teacher-login/')}

                For security reasons, please change your password after your first login.

                Best regards,
                The Administration Team
                {school_name}
                """

                # Create HTML version of the email with better formatting
                # Get school settings for logo and name
                school_settings = SchoolSettings.objects.first()
                school_name = school_settings.school_name if school_settings and school_settings.school_name else "School Management System"

                # Add logo handling
                base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
                logo_html = ""
                if school_settings and school_settings.logo:
                    logo_html = f'<div style="text-align: center; margin-bottom: 20px;"><img src="{base_url}{school_settings.logo.url}" alt="{school_name} Logo" style="max-width: 200px; max-height: 100px;"></div>'

                current_year = timezone.now().year
                html_message = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #4e73df; margin-bottom: 5px;">{school_name}</h2>
                        <p style="color: #666; font-size: 14px; margin-top: 0;">School Management System</p>
                    </div>

                    {logo_html}

                    <div style="border-top: 3px solid #4e73df; margin-bottom: 20px;"></div>

                    <p>Dear <strong>{first_name} {last_name}</strong>,</p>

                    <p>We are pleased to welcome you to our school community! Your teacher account has been created successfully.</p>

                    <div style="background-color: #f8f9fc; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <h3 style="margin-top: 0; color: #333;">Your Login Credentials</h3>
                        <p><strong>Email:</strong> {email}</p>
                        <p><strong>Password:</strong> {password}</p>
                        <p><strong>Employee ID:</strong> {employee_id}</p>
                        <p><strong>Login URL:</strong> <a href="{request.build_absolute_uri('/users/teacher-login/')}">{request.build_absolute_uri('/users/teacher-login/')}</a></p>
                    </div>

                    <p>For security reasons, please change your password after your first login.</p>

                    <p>If you have any questions or need assistance, please don't hesitate to contact us.</p>

                    <p>Best regards,<br>
                    The Administration Team<br>
                    {school_name}</p>

                    <div style="border-top: 1px solid #ddd; margin-top: 20px; padding-top: 10px; text-align: center; color: #888; font-size: 12px;">
                        © {current_year} {school_name}. All rights reserved.
                    </div>
                </div>
                """

                # Send welcome email
                from .utils import send_school_email
                send_school_email(
                    subject=subject,
                    message=message,
                    recipient_list=[email],
                    html_message=html_message
                )

            except Exception as e:
                messages.warning(request, f"Teacher registered but welcome email failed: {str(e)}")

        if not skip_welcome_email:
            messages.success(request, 'Teacher registered successfully. Welcome email sent with login credentials.')
        else:
            messages.success(request, 'Teacher registered successfully. No welcome email sent.')

        return redirect('users:user_management')

    return render(request, 'users/register_teacher.html')

# Student registration views
@user_passes_test(is_admin)
def register_student(request):
    """Register a new student"""
    if request.method == 'POST':
        try:
            # Generate student ID and PIN if not provided
            student_id = request.POST.get('student_id', '') or generate_student_id()
            pin = request.POST.get('pin', '') or generate_pin()

            # Create a unique email for the student using student ID
            email = f"{student_id}@school.internal"

            # Create user with student role
            user = CustomUser.objects.create_user(
                email=email,
                password=pin,  # Use PIN as password
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                role=CustomUser.Role.STUDENT
            )

            # Create student profile
            student = Student.objects.create(
                user=user,
                student_id=student_id,
                pin=pin,
                date_of_birth=request.POST.get('date_of_birth')
            )

            # Handle classroom assignment
            classroom_id = request.POST.get('classroom')
            if classroom_id:
                    try:
                        classroom = ClassRoom.objects.get(id=classroom_id)
                        student.grade = classroom
                        student.save()
                        messages.success(request, f'Student assigned to classroom: {classroom.name}')
                    except ClassRoom.DoesNotExist:
                        messages.error(request, 'Selected classroom not found.')

            # Link parent if provided
            parent_id = request.POST.get('parent_id')
            if parent_id:
                    try:
                        parent = Parent.objects.get(id=parent_id)
                        parent.children.add(student)

                        # Send email to parent
                        school_settings = SchoolSettings.objects.first()
                        context = {
                            'parent_name': parent.user.get_full_name(),
                            'student_name': student.user.get_full_name(),
                            'student_id': student.student_id,
                            'pin': student.pin,
                            'school_name': school_settings.school_name if school_settings else 'Our School',
                            'grade': student.classrooms.first().grade_level if student.classrooms.exists() else '',
                            'section': student.section
                        }

                        # Render email content from template
                        email_subject = f"Your Child Has Been Registered at {context['school_name']}"
                        email_body = render_to_string('users/emails/student_registration.html', context)

                        # Send email
                        send_mail(
                            subject=email_subject,
                            message=email_body,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[parent.user.email],
                            html_message=email_body,
                            fail_silently=False,
                        )

                    except Parent.DoesNotExist:
                        messages.warning(request, 'Parent not found. Student registered without parent link.')
                    except Exception as e:
                        messages.warning(request, f'Student registered but email notification failed: {str(e)}')

            messages.success(request, f'Student registered successfully. ID: {student_id}, PIN: {pin}')
            return redirect('users:student_management')

        except Exception as e:
            messages.error(request, f'Error registering student: {str(e)}')
            classrooms = ClassRoom.objects.all()
            parents = Parent.objects.all()
            return render(request, 'users/register_student.html', {'parents': parents, 'classrooms': classrooms})

    # GET request - display form
    classrooms = ClassRoom.objects.all()
    parents = Parent.objects.all()
    return render(request, 'users/register_student.html', {'parents': parents, 'classrooms': classrooms})

# Parent registration views
@user_passes_test(is_admin)
def register_parent(request):
    """Register a new parent"""
    if request.method == 'POST':
        # Extract form data
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        occupation = request.POST.get('occupation')
        relationship = request.POST.get('relationship', 'Parent')

        # Always set to True since we handle email sending here
        send_welcome_email = True

        try:
            # Create CustomUser object
            user = CustomUser(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=CustomUser.Role.PARENT,
                is_verified=True
            )
            user.set_password(password)
            # Store initial password for welcome email
            user.initial_password = password
            # Don't skip welcome email
            user.skip_welcome_email = False
            user.save()

            # Rest of the registration code...
            # Create parent profile
            parent = Parent.objects.create(
                user=user,
                occupation=occupation,
                relationship=relationship
            )

            # Link children if provided
            children_ids = request.POST.getlist('children')
            linked_children = []
            if children_ids:
                students = Student.objects.filter(id__in=children_ids)
                parent.children.add(*students)
                linked_children = list(students)

            # Send welcome email directly
            if send_welcome_email:
                try:
                    # Get school settings for email details
                    school_settings = SchoolSettings.objects.first()
                    school_name = school_settings.school_name if school_settings and school_settings.school_name else "Deigratia Montessori School"

                    # Add logo handling
                    base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
                    logo_html = ""
                    if school_settings and school_settings.logo:
                        logo_html = f'<div style="text-align: center; margin-bottom: 20px;"><img src="{base_url}{school_settings.logo.url}" alt="{school_name} Logo" style="max-width: 200px; max-height: 100px;"></div>'

                    # Create children info with login credentials
                    children_info = ""
                    children_html = ""

                    if linked_children or parent.children.exists():
                        children_to_show = linked_children or parent.children.all()

                        # Create text version (for plain text email)
                        children_info = "\nYour Linked Children and Their Login Credentials:\n"
                        for i, student in enumerate(children_to_show, 1):
                            children_info += f"{i}. {student.user.get_full_name()}\n"
                            children_info += f"   - Student ID: {student.student_id}\n"
                            children_info += f"   - PIN: {student.pin}\n"
                            if hasattr(student, 'grade') and student.grade:
                                children_info += f"   - Grade: {student.grade}\n"
                            if hasattr(student, 'classrooms') and student.classrooms.exists():
                                children_info += f"   - Grade: {student.classrooms.first().grade_level}\n"

                        # Create HTML version with table
                        children_html = """
                        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #1cc88a;">
                            <h3 style="margin-top: 0; color: #1cc88a;">Your Linked Children and Their Login Credentials</h3>
                            <div style="margin-bottom: 15px;">
                                <p>Your children can log in at: <a href="{request.build_absolute_uri('/users/student-login/')}" style="color: #4e73df;">{request.build_absolute_uri('/users/student-login/')}</a></p>
                            </div>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr style="background-color: #eef2ff; text-align: left;">
                                    <th style="padding: 8px; border-bottom: 1px solid #ddd;">Name</th>
                                    <th style="padding: 8px; border-bottom: 1px solid #ddd;">Student ID</th>
                                    <th style="padding: 8px; border-bottom: 1px solid #ddd;">PIN</th>
                                    <th style="padding: 8px; border-bottom: 1px solid #ddd;">Grade</th>
                                </tr>
                        """

                        for student in children_to_show:
                            # Get grade info from classrooms if available
                            if hasattr(student, 'classrooms') and student.classrooms.exists():
                                grade_info = student.classrooms.first().grade_level
                            else:
                                grade_info = student.grade if hasattr(student, 'grade') and student.grade else "Not assigned"

                            children_html += f"""
                                <tr>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{student.user.get_full_name()}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{student.student_id}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{student.pin}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{grade_info}</td>
                                </tr>
                            """

                        children_html += """
                            </table>
                        </div>
                        """
                    else:
                        children_info = "\nYou currently have no linked children. Contact the school administration to link your children to your account."
                        children_html = """
                        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #f6c23e;">
                            <h3 style="margin-top: 0; color: #f6c23e;">No Linked Children</h3>
                            <p>You currently have no linked children. Contact the school administration to link your children to your account.</p>
                        </div>
                        """

                    # Prepare welcome email content - plain text version
                    subject = f"Welcome to {school_name} - Parent Account Created"
                    message = f"""
Dear {first_name} {last_name},

Welcome to the {school_name} Management System! Your account has been created successfully.

You have been registered as a Parent/Guardian in our school management system.

YOUR PARENT ACCOUNT LOGIN CREDENTIALS:
Email: {email}
Password: {password}
Login URL: {request.build_absolute_uri('/users/parent-login/')}

Please change your password after your first login for security reasons.
{children_info}
Through your parent account, you can:
- View your children's academic progress
- Check attendance records
- Communicate with teachers
- Stay updated on school events and announcements

If you have any questions or need assistance, please contact the system administrator.

Best regards,
{school_name} Administration

© {school_name}. All rights reserved.
                    """

                    # Create HTML version of the email with better formatting
                    current_year = timezone.now().year
                    html_message = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                        <div style="text-align: center; margin-bottom: 20px;">
                            <h2 style="color: #4e73df; margin-bottom: 5px;">{school_name}</h2>
                            <p style="color: #666; font-size: 14px; margin-top: 0;">School Management System</p>
                        </div>

                        {logo_html}

                        <div style="border-top: 3px solid #4e73df; margin-bottom: 20px;"></div>

                        <p>Dear <strong>{first_name} {last_name}</strong>,</p>

                        <p>Welcome to the <strong>{school_name} Management System</strong>! Your account has been created successfully.</p>

                        <p>You have been registered as a <strong>Parent/Guardian</strong> in our school management system.</p>

                        <div style="background-color: #f8f9fc; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #4e73df;">
                            <h3 style="margin-top: 0; color: #4e73df;">Your Parent Account Login Credentials</h3>
                            <p><strong>Email:</strong> {email}</p>
                            <p><strong>Password:</strong> {password}</p>
                            <p><strong>Login URL:</strong> <a href="{request.build_absolute_uri('/users/parent-login/')}" style="color: #4e73df;">{request.build_absolute_uri('/users/parent-login/')}</a></p>
                            <p style="color: #666; font-size: 13px; margin-bottom: 0;">Please save these credentials securely. For security reasons, please change your password after your first login.</p>
                            <p style="color: #666; font-size: 13px; margin-top: 10px;">You can access your children's academic records, attendance, and communicate with teachers through your parent account.</p>
                        </div>

                        {children_html}

                        <div style="background-color: #f8f9fc; padding: 15px; border-radius: 5px; margin: 15px 0;">
                            <h3 style="margin-top: 0; color: #333;">Parent Portal Features</h3>
                            <ul style="padding-left: 20px; margin-bottom: 0;">
                                <li>View your children's academic progress and grades</li>
                                <li>Track attendance records and receive absence notifications</li>
                                <li>Communicate with teachers through secure messaging</li>
                                <li>Access school announcements, events, and calendars</li>
                                <li>View and download report cards</li>
                            </ul>
                        </div>

                        <p>If you have any questions or need assistance, please contact the system administrator.</p>

                        <p>Best regards,<br>
                        <strong>{school_name} Administration</strong></p>

                        <div style="border-top: 1px solid #ddd; margin-top: 20px; padding-top: 10px; text-align: center; color: #888; font-size: 12px;">
                            © {current_year} {school_name}. All rights reserved.
                        </div>
                    </div>
                    """

                    # Send welcome email
                    from .utils import send_school_email
                    send_school_email(
                        subject=subject,
                        message=message,
                        recipient_list=[email],
                        html_message=html_message
                    )

                    messages.success(request, 'Parent registered successfully. Welcome email sent with login credentials.')
                except Exception as e:
                    messages.warning(request, f"Parent registered but welcome email failed: {str(e)}")
            else:
                messages.success(request, 'Parent registered successfully. No welcome email sent.')

            return redirect('users:user_management')

        except Exception as e:
            messages.error(request, f'Error creating parent account: {str(e)}')
            return render(request, 'users/register_parent.html', {'students': Student.objects.all()})

    # GET request - display the registration form
    students = Student.objects.all()
    return render(request, 'users/register_parent.html', {'students': students})

@user_passes_test(is_admin)
def link_parent_to_child(request):
    """Link a parent to a child (student)"""
    if request.method == 'POST':
        parent_id = request.POST.get('parent_id')
        student_id = request.POST.get('student_id')

        try:
            parent = Parent.objects.get(id=parent_id)
            student = Student.objects.get(id=student_id)

            parent.children.add(student)
            parent.save()

            messages.success(request, f'Successfully linked {student.user.get_full_name()} to {parent.user.get_full_name()}.')
        except (Parent.DoesNotExist, Student.DoesNotExist):
            messages.error(request, 'Parent or student not found.')

        return redirect('users:user_management')

    parents = Parent.objects.all()
    students = Student.objects.all()
    return render(request, 'users/link_parent_child.html', {
        'parents': parents,
        'students': students
    })

@user_passes_test(is_admin)
def search_parent(request):
    """Search for a parent to link to a child"""
    query = request.GET.get('query', '')

    if query:
        parents = CustomUser.objects.filter(
            role=CustomUser.Role.PARENT
        ).filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone_number__icontains=query)
        )
    else:
        parents = CustomUser.objects.none()

    return render(request, 'users/search_parent.html', {
        'parents': parents,
        'query': query
    })

@user_passes_test(is_admin)
def unlink_parent_child(request):
    """Unlink a child (student) from a parent"""
    if request.method == 'POST':
        parent_id = request.POST.get('parent_id')
        child_id = request.POST.get('child_id')

        try:
            parent = Parent.objects.get(id=parent_id)
            student = Student.objects.get(id=child_id)

            if student in parent.children.all():
                parent.children.remove(student)
                messages.success(request, f'Successfully unlinked {student.user.get_full_name()} from {parent.user.get_full_name()}.')
            else:
                messages.error(request, f'{student.user.get_full_name()} is not linked to this parent.')

            # Redirect back to the edit user page for the parent
            return redirect('users:edit_user', user_id=parent.user.id)

        except (Parent.DoesNotExist, Student.DoesNotExist):
            messages.error(request, 'Parent or student not found.')

    # If not POST or if there was an error, redirect to user management
    return redirect('users:user_management')

# ID Cards and Admission Letters

# Legacy functions kept for backward compatibility
@user_passes_test(is_admin)
def generate_id_card(request, user_id):
    """Legacy function: Generate and display ID card for a user"""
    user = get_object_or_404(CustomUser, id=user_id)

    # Get role-specific data
    context = {'user': user}

    if user.is_teacher:
        try:
            teacher = Teacher.objects.get(user=user)
            context['teacher'] = teacher
        except Teacher.DoesNotExist:
            pass

    elif user.is_student:
        try:
            student = Student.objects.get(user=user)
            context['student'] = student
        except Student.DoesNotExist:
            pass

    elif user.is_parent:
        try:
            parent = Parent.objects.get(user=user)
            context['parent'] = parent
        except Parent.DoesNotExist:
            pass

    # Get school settings for logo and name
    try:
        school_settings = SchoolSettings.objects.first()
        context['school_settings'] = school_settings
    except:
        pass

    return render(request, 'users/id_card.html', context)

@user_passes_test(is_admin)
def generate_admission_letter(request, student_id):
    """Legacy function: Generate and display admission letter for a student"""
    student = get_object_or_404(Student, id=student_id)

    # Get school settings for logo and name
    school_settings = SchoolSettings.objects.first()

    # Create a default letter or get an existing one
    try:
        # Try to find an existing letter for this student
        letter = AdmissionLetter.objects.filter(student=student).latest('created_at')
    except AdmissionLetter.DoesNotExist:
        # Create a default letter if none exists
        template = AdmissionLetterTemplate.objects.filter(is_active=True).first()
        if not template:
            messages.error(request, "No active admission letter template found. Please create one first.")
            return redirect('users:admission_letter_template_list')

        academic_year = f"{timezone.now().year}-{timezone.now().year + 1}"
        reference_number = f"ADM-{academic_year}-{int(timezone.now().timestamp())}"

        letter = AdmissionLetter.objects.create(
            student=student,
            template=template,
            reference_number=reference_number,
            admission_date=timezone.now().date(),
            academic_year=academic_year,
            grade_admitted=student.grade,
            section_admitted=student.section,
            is_printed=False
        )

    # Process the template with student data for preview
    user = student.user

    # Prepare context data for template processing
    context_data = {
        'letter': letter,
        'student': student,
        'student_name': user.get_full_name(),
        'student_id': student.student_id,
        'grade': student.grade,
        'section': student.section,
        'pin': student.pin,  # Add PIN for login credentials
        'academic_year': letter.academic_year,
        'admission_date': letter.admission_date.strftime('%B %d, %Y'),
        'reference_number': letter.reference_number,
        'current_date': timezone.now().strftime('%B %d, %Y'),
        'start_date': (timezone.now() + timedelta(days=14)).strftime('%B %d, %Y'),  # Example start date
        'school_settings': school_settings,
    }

    # Add any additional fields from the letter
    if letter.additional_info:
        for key, value in letter.additional_info.items():
            context_data[key] = value

    # Process the template body
    from string import Template
    try:
        body_template = Template(letter.template.body_template)
        processed_body = body_template.safe_substitute(**context_data)
    except Exception as e:
        processed_body = f"Error processing template: {str(e)}"

    context_data['processed_body'] = processed_body

    return render(request, 'users/admission_letter_detail.html', context_data)

# ID Card Template Management Views
@user_passes_test(is_admin)
def id_card_template_list(request):
    """List all ID card templates"""
    templates = IDCardTemplate.objects.all().order_by('-is_active', 'role', 'name')

    # Check if there are no templates, and create default ones if needed
    if not templates.exists():
        create_default_templates()
        templates = IDCardTemplate.objects.all().order_by('-is_active', 'role', 'name')
        messages.success(request, 'Default ID card templates have been created.')

    # Filter by role if requested
    role_filter = request.GET.get('role', None)
    if role_filter:
        templates = templates.filter(role=role_filter)

    return render(request, 'users/id_card_template_list.html', {
        'templates': templates,
        'role_filter': role_filter,
    })

def create_default_templates():
    """Create default ID card templates for students, teachers, and parents"""
    # Default templates to create
    templates = [
        # Student template - Blue theme
        {
            'name': 'Standard Student ID Card',
            'role': 'STUDENT',
            'header_text': 'STUDENT IDENTIFICATION CARD',
            'card_width': 1000,
            'card_height': 600,
            'text_color': '#FFFFFF',
            'background_color': '#3498db',  # Blue
            'is_active': True,
        },

        # Teacher template - Green theme
        {
            'name': 'Professional Teacher ID Card',
            'role': 'TEACHER',
            'header_text': 'STAFF IDENTIFICATION CARD',
            'card_width': 1000,
            'card_height': 600,
            'text_color': '#FFFFFF',
            'background_color': '#27ae60',  # Green
            'is_active': True,
        },

        # Parent template - Purple theme
        {
            'name': 'Standard Parent ID Card',
            'role': 'PARENT',
            'header_text': 'PARENT/GUARDIAN IDENTIFICATION CARD',
            'card_width': 1000,
            'card_height': 600,
            'text_color': '#FFFFFF',
            'background_color': '#8e44ad',  # Purple
            'is_active': True,
        },
    ]

    # Create each template if it doesn't already exist
    for template_data in templates:
        role = template_data['role']
        name = template_data['name']

        # Check if similar template exists
        if not IDCardTemplate.objects.filter(Q(name=name) | Q(role=role, header_text=template_data['header_text'])).exists():
            IDCardTemplate.objects.create(**template_data)

@user_passes_test(is_admin)
def id_card_template_create(request):
    """Create a new ID card template"""
    if request.method == 'POST':
        name = request.POST.get('name')
        role = request.POST.get('role')
        header_text = request.POST.get('header_text')
        card_width = request.POST.get('card_width', 1000)
        card_height = request.POST.get('card_height', 600)
        text_color = request.POST.get('text_color', '#000000')
        background_color = request.POST.get('background_color', '#FFFFFF')
        is_active = 'is_active' in request.POST

        # Create the template
        template = IDCardTemplate.objects.create(
            name=name,
            role=role,
            header_text=header_text,
            card_width=card_width,
            card_height=card_height,
            text_color=text_color,
            background_color=background_color,
            is_active=is_active
        )

        # Handle background image if provided
        if 'background_image' in request.FILES:
            template.background_image = request.FILES['background_image']
            template.save()

        messages.success(request, 'ID card template created successfully.')
        return redirect('users:id_card_template_list')

    # For GET request, display the form
    return render(request, 'users/id_card_template_create.html')

@user_passes_test(is_admin)
def id_card_template_detail(request, template_id):
    """View details of an ID card template"""
    template = get_object_or_404(IDCardTemplate, id=template_id)

    # Get a preview of how the template looks
    if template.role == 'STUDENT':
        sample_users = Student.objects.all()[:5]
    elif template.role == 'TEACHER':
        sample_users = Teacher.objects.all()[:5]
    elif template.role == 'PARENT':
        sample_users = Parent.objects.all()[:5]
    else:
        sample_users = CustomUser.objects.filter(role=template.role)[:5]

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    return render(request, 'users/id_card_template_detail.html', {
        'template': template,
        'sample_users': sample_users,
        'school_settings': school_settings
    })

@user_passes_test(is_admin)
def id_card_template_update(request, template_id):
    """Update an existing ID card template"""
    template = get_object_or_404(IDCardTemplate, id=template_id)

    if request.method == 'POST':
        template.name = request.POST.get('name')
        template.role = request.POST.get('role')
        template.header_text = request.POST.get('header_text')
        template.card_width = request.POST.get('card_width', 1000)
        template.card_height = request.POST.get('card_height', 600)
        template.text_color = request.POST.get('text_color', '#000000')
        template.background_color = request.POST.get('background_color', '#FFFFFF')
        template.is_active = 'is_active' in request.POST

        # Handle background image if provided
        if 'background_image' in request.FILES:
            template.background_image = request.FILES['background_image']

        template.save()
        messages.success(request, 'ID card template updated successfully.')
        return redirect('users:id_card_template_detail', template_id=template.id)

    # For GET request, display the form with current values
    return render(request, 'users/id_card_template_update.html', {
        'template': template
    })

@user_passes_test(is_admin)
def id_card_template_delete(request, template_id):
    """Delete an ID card template"""
    template = get_object_or_404(IDCardTemplate, id=template_id)

    if request.method == 'POST':
        # Check if any ID cards use this template
        if IDCard.objects.filter(template=template).exists():
            messages.error(request, 'Cannot delete this template as it is being used by one or more ID cards.')
            return redirect('users:id_card_template_detail', template_id=template.id)

        template.delete()
        messages.success(request, 'ID card template deleted successfully.')
        return redirect('users:id_card_template_list')

    # For GET request, display the confirmation page
    return render(request, 'users/id_card_template_delete.html', {
        'template': template
    })

# ID Card Generation and Management Views
@user_passes_test(is_admin)
def id_card_list(request):
    """List all generated ID cards"""
    id_cards = IDCard.objects.all().order_by('-is_active', '-created_at')

    # Filter by role if requested
    role_filter = request.GET.get('role', None)
    if role_filter:
        id_cards = id_cards.filter(user__role=role_filter)

    # Filter by template if requested
    template_filter = request.GET.get('template', None)
    if template_filter:
        id_cards = id_cards.filter(template_id=template_filter)

    # Filter by search query
    search_query = request.GET.get('search', None)
    if search_query:
        id_cards = id_cards.filter(
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(card_number__icontains=search_query)
        )

    # Pagination
    templates = IDCardTemplate.objects.all()

    return render(request, 'users/id_card_list.html', {
        'id_cards': id_cards,
        'templates': templates,
        'role_filter': role_filter,
        'template_filter': template_filter,
        'search_query': search_query
    })

@user_passes_test(is_admin)
def id_card_generate(request):
    """Generate a new ID card for a user"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        template_id = request.POST.get('template_id')
        issue_date = request.POST.get('issue_date')
        expiry_date = request.POST.get('expiry_date')
        barcode_data = request.POST.get('barcode_data', '')
        additional_info = {}

        # Collect additional fields
        for key, value in request.POST.items():
            if key.startswith('additional_'):
                field_name = key.replace('additional_', '')
                additional_info[field_name] = value

        # Validate required fields
        if not (user_id and template_id and issue_date and expiry_date):
            messages.error(request, 'All required fields must be provided.')
            return redirect('users:id_card_generate')

        try:
            user = CustomUser.objects.get(id=user_id)
            template = IDCardTemplate.objects.get(id=template_id)

            # Generate a unique card number
            card_number = f"ID-{user.role}-{user.id}-{int(timezone.now().timestamp())}"

            # Create the ID card
            id_card = IDCard.objects.create(
                user=user,
                template=template,
                card_number=card_number,
                issue_date=issue_date,
                expiry_date=expiry_date,
                barcode_data=barcode_data,
                additional_info=additional_info,
                is_active=True
            )

            messages.success(request, f'ID card for {user.get_full_name()} generated successfully.')
            return redirect('users:id_card_detail', card_id=id_card.id)

        except (CustomUser.DoesNotExist, IDCardTemplate.DoesNotExist):
            messages.error(request, 'User or template not found.')
            return redirect('users:id_card_generate')

    # For GET request, display the form
    users = CustomUser.objects.all().order_by('role', 'email')
    templates = IDCardTemplate.objects.filter(is_active=True)

    return render(request, 'users/id_card_generate.html', {
        'users': users,
        'templates': templates,
        'today': timezone.now().date(),
        'next_year': (timezone.now() + timedelta(days=365)).date()
    })

@user_passes_test(is_admin)
def id_card_batch_generate(request):
    """Generate ID cards for multiple users in batch"""
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        role = request.POST.get('role')
        issue_date = request.POST.get('issue_date')
        expiry_date = request.POST.get('expiry_date')
        user_ids = request.POST.getlist('user_ids')

        # Validate required fields
        if not (template_id and role and issue_date and expiry_date):
            messages.error(request, 'All required fields must be provided.')
            return redirect('users:id_card_batch_generate')

        try:
            template = IDCardTemplate.objects.get(id=template_id)

            # Get users to generate cards for
            if user_ids:
                users = CustomUser.objects.filter(id__in=user_ids)
            else:
                users = CustomUser.objects.filter(role=role)

            if not users:
                messages.error(request, 'No users found with the selected criteria.')
                return redirect('users:id_card_batch_generate')

            # Generate cards for each user
            cards_generated = 0
            for user in users:
                # Skip if already has an active card
                if IDCard.objects.filter(user=user, is_active=True).exists():
                    continue

                # Generate a unique card number
                card_number = f"ID-{user.role}-{user.id}-{int(timezone.now().timestamp())}"

                # Create the ID card
                IDCard.objects.create(
                    user=user,
                    template=template,
                    card_number=card_number,
                    issue_date=issue_date,
                    expiry_date=expiry_date,
                    is_active=True
                )
                cards_generated += 1

            messages.success(request, f'{cards_generated} ID cards generated successfully.')
            return redirect('users:id_card_list')

        except IDCardTemplate.DoesNotExist:
            messages.error(request, 'Template not found.')
            return redirect('users:id_card_batch_generate')

    # For GET request, display the form
    templates = IDCardTemplate.objects.filter(is_active=True)

    # Get users by role for selection
    students = CustomUser.objects.filter(role=CustomUser.Role.STUDENT).order_by('email')
    teachers = CustomUser.objects.filter(role=CustomUser.Role.TEACHER).order_by('email')
    parents = CustomUser.objects.filter(role=CustomUser.Role.PARENT).order_by('email')
    admins = CustomUser.objects.filter(role=CustomUser.Role.ADMIN).order_by('email')

    return render(request, 'users/id_card_batch_generate.html', {
        'templates': templates,
        'students': students,
        'teachers': teachers,
        'parents': parents,
        'admins': admins,
        'today': timezone.now().date(),
        'next_year': (timezone.now() + timedelta(days=365)).date()
    })

@user_passes_test(is_admin)
def id_card_detail(request, card_id):
    """View details of an ID card"""
    # Use select_related to ensure student/teacher/parent data is prefetched
    id_card = get_object_or_404(
        IDCard.objects.select_related(
            'user',
            'user__student_profile',
            'user__teacher_profile',
            'user__parent_profile'
        ),
        id=card_id
    )

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    # Add today's date for expiry comparison
    today = timezone.now().date()

    # Get available templates for regeneration
    templates = IDCardTemplate.objects.filter(
        is_active=True,
        role=id_card.user.role
    )

    # Calculate next year's date for default expiry when regenerating
    next_year = today + timedelta(days=365)

    return render(request, 'users/id_card_detail.html', {
        'id_card': id_card,
        'school_settings': school_settings,
        'today': today,
        'templates': templates,
        'next_year': next_year
    })

@user_passes_test(is_admin)
def id_card_print(request, card_id):
    """Print/download an ID card"""
    id_card = get_object_or_404(IDCard, id=card_id)

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    return render(request, 'users/id_card_print.html', {
        'id_card': id_card,
        'school_settings': school_settings,
        'print_mode': True
    })

# Admission Letter Template Management Views
@user_passes_test(is_admin)
def admission_letter_template_list(request):
    """List all admission letter templates"""
    templates = AdmissionLetterTemplate.objects.all().order_by('-is_active', 'name')

    return render(request, 'users/admission_letter_template_list.html', {
        'templates': templates,
    })

@user_passes_test(is_admin)
def admission_letter_template_create(request):
    """Create a new admission letter template"""
    if request.method == 'POST':
        name = request.POST.get('name')
        header_text = request.POST.get('header_text')
        body_template = request.POST.get('body_template')
        footer_text = request.POST.get('footer_text')
        signatory_name = request.POST.get('signatory_name')
        signatory_position = request.POST.get('signatory_position')
        is_active = 'is_active' in request.POST

        # Create the template
        template = AdmissionLetterTemplate.objects.create(
            name=name,
            header_text=header_text,
            body_template=body_template,
            footer_text=footer_text,
            signatory_name=signatory_name,
            signatory_position=signatory_position,
            is_active=is_active
        )

        # Handle signature image if provided
        if 'signature_image' in request.FILES:
            template.signature_image = request.FILES['signature_image']
            template.save()

        messages.success(request, 'Admission letter template created successfully.')
        return redirect('users:admission_letter_template_list')

    # For GET request, display the form
    # Include some placeholder template text to help users get started
    placeholder_template = """Dear {student_name},

We are pleased to inform you that you have been admitted to {grade} in our school for the academic year {academic_year}.

The school session will commence on {start_date}. Please bring the following documents on your first day:
1. Previous academic records
2. Birth certificate
3. Two passport-sized photographs

We look forward to welcoming you to our school community.

Sincerely,
"""

    return render(request, 'users/admission_letter_template_create.html', {
        'placeholder_template': placeholder_template
    })

@user_passes_test(is_admin)
def admission_letter_template_detail(request, template_id):
    """View details of an admission letter template"""
    template = get_object_or_404(AdmissionLetterTemplate, id=template_id)

    # Get a preview of how the template looks with sample student data
    sample_students = Student.objects.all()[:3]

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    return render(request, 'users/admission_letter_template_detail.html', {
        'template': template,
        'sample_students': sample_students,
        'school_settings': school_settings
    })

@user_passes_test(is_admin)
def admission_letter_template_update(request, template_id):
    """Update an existing admission letter template"""
    template = get_object_or_404(AdmissionLetterTemplate, id=template_id)

    if request.method == 'POST':
        template.name = request.POST.get('name')
        template.header_text = request.POST.get('header_text')
        template.body_template = request.POST.get('body_template')
        template.footer_text = request.POST.get('footer_text')
        template.signatory_name = request.POST.get('signatory_name')
        template.signatory_position = request.POST.get('signatory_position')
        template.is_active = 'is_active' in request.POST

        # Handle signature image if provided
        if 'signature_image' in request.FILES:
            template.signature_image = request.FILES['signature_image']

        template.save()
        messages.success(request, 'Admission letter template updated successfully.')
        return redirect('users:admission_letter_template_detail', template_id=template.id)

    # For GET request, display the form with current values
    from .forms import AdmissionLetterTemplateForm

    if request.method == 'POST':
        form = AdmissionLetterTemplateForm(request.POST, request.FILES, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Admission letter template updated successfully.')
            return redirect('users:admission_letter_template_detail', template_id=template.id)
    else:
        form = AdmissionLetterTemplateForm(instance=template)

    return render(request, 'users/admission_letter_template_update.html', {
        'template': template,
        'form': form
    })

@user_passes_test(is_admin)
def admission_letter_template_delete(request, template_id):
    """Delete an admission letter template"""
    template = get_object_or_404(AdmissionLetterTemplate, id=template_id)

    if request.method == 'POST':
        # Check if any admission letters use this template
        if AdmissionLetter.objects.filter(template=template).exists():
            messages.error(request, 'Cannot delete this template as it is being used by one or more admission letters.')
            return redirect('users:admission_letter_template_detail', template_id=template.id)

        template.delete()
        messages.success(request, 'Admission letter template deleted successfully.')
        return redirect('users:admission_letter_template_list')

    # For GET request, display the confirmation page
    return render(request, 'users/admission_letter_template_delete.html', {
        'template': template
    })

@user_passes_test(is_admin)
def admission_letter_template_duplicate(request, template_id):
    """Duplicate an existing admission letter template"""
    template = get_object_or_404(AdmissionLetterTemplate, id=template_id)

    if request.method == 'POST':
        try:
            # Create a copy of the template
            new_template = AdmissionLetterTemplate.objects.create(
                name=f"{template.name} (Copy)",
                header_text=template.header_text,
                body_template=template.body_template,
                footer_text=template.footer_text,
                signatory_name=template.signatory_name,
                signatory_position=template.signatory_position,
                is_active=False  # Keep the duplicate inactive by default
            )

            # Copy the signature image if it exists
            if template.signature_image:
                new_template.signature_image = template.signature_image
                new_template.save()

            messages.success(request, 'Template duplicated successfully. Please review and activate the new template.')
            return redirect('users:admission_letter_template_detail', template_id=new_template.id)

        except Exception as e:
            messages.error(request, f'Error duplicating template: {str(e)}')
            return redirect('users:admission_letter_template_detail', template_id=template.id)

    # For GET request, display confirmation page
    return render(request, 'users/admission_letter_template_duplicate.html', {
        'template': template
    })

@user_passes_test(is_admin)
def admission_letter_template_import(request):
    """Import an admission letter template from a JSON file"""
    if request.method == 'POST':
        if 'template_file' not in request.FILES:
            messages.error(request, 'No file selected for import.')
            return redirect('users:admission_letter_template_list')

        import_file = request.FILES['template_file']

        try:
            import json
            from django.core.files.base import ContentFile

            # Read and parse the JSON file
            file_content = import_file.read().decode('utf-8')
            template_data = json.loads(file_content)

            # Validate required fields
            required_fields = ['name', 'header_text', 'body_template', 'footer_text']
            if not all(field in template_data for field in required_fields):
                messages.error(request, 'Invalid template file format. Missing required fields.')
                return redirect('users:admission_letter_template_list')

            # Create new template
            new_template = AdmissionLetterTemplate.objects.create(
                name=template_data['name'],
                header_text=template_data.get('header_text', ''),
                body_template=template_data.get('body_template', ''),
                footer_text=template_data.get('footer_text', ''),
                signatory_name=template_data.get('signatory_name', ''),
                signatory_position=template_data.get('signatory_position', ''),
                is_active=False  # Keep imported templates inactive by default
            )

            # Handle signature image if included in the import
            if 'signature_image' in template_data and template_data['signature_image']:
                signature_data = template_data['signature_image']
                if signature_data.get('file_name') and signature_data.get('content'):
                    try:
                        import base64
                        from django.core.files.base import ContentFile

                        # Decode base64 image data
                        file_data = base64.b64decode(signature_data['content'])
                        file_name = signature_data['file_name']

                        # Save the signature image
                        new_template.signature_image.save(
                            file_name,
                            ContentFile(file_data),
                            save=True
                        )
                    except Exception as e:
                        messages.warning(request, f'Could not import signature image: {str(e)}')

            messages.success(request, f'Template "{new_template.name}" imported successfully. Please review and activate it.')
            return redirect('users:admission_letter_template_detail', template_id=new_template.id)

        except json.JSONDecodeError:
            messages.error(request, 'Invalid JSON file format.')
        except Exception as e:
            messages.error(request, f'Error importing template: {str(e)}')

        return redirect('users:admission_letter_template_list')

    # For GET request, redirect to template list
    return redirect('users:admission_letter_template_list')

@user_passes_test(is_admin)
def admission_letter_list(request):
    """List all generated admission letters"""
    letters = AdmissionLetter.objects.all().order_by('-created_at')

    # Filter by academic year if requested
    academic_year_filter = request.GET.get('academic_year', None)
    if academic_year_filter:
        letters = letters.filter(academic_year=academic_year_filter)

    # Filter by grade if requested
    grade_filter = request.GET.get('grade_admitted', None)
    if grade_filter:
        letters = letters.filter(grade_admitted=grade_filter)

    # Filter by search query
    search_query = request.GET.get('search', None)
    if search_query:
        letters = letters.filter(
            Q(student__user__email__icontains=search_query) |
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(reference_number__icontains=search_query)
        )

    # Get unique academic years and grades for filtering
    academic_years = AdmissionLetter.objects.values_list('academic_year', flat=True).distinct()
    grades = AdmissionLetter.objects.values_list('grade_admitted', flat=True).distinct()

    return render(request, 'users/admission_letter_list.html', {
        'letters': letters,
        'academic_years': academic_years,
        'grades': grades,
        'academic_year_filter': academic_year_filter,
        'grade_filter': grade_filter,
        'search_query': search_query
    })

@user_passes_test(is_admin)
def admission_letter_generate(request):
    """Generate a new admission letter for a student"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        template_id = request.POST.get('template_id')
        reference_number = request.POST.get('reference_number', '')
        admission_date = request.POST.get('admission_date')
        academic_year = request.POST.get('academic_year')
        grade_admitted = request.POST.get('grade_admitted')
        section_admitted = request.POST.get('section_admitted', '')
        fee_details = request.POST.get('fee_details', '')
        additional_info = {}

        # Collect additional fields
        for key, value in request.POST.items():
            if key.startswith('additional_'):
                field_name = key.replace('additional_', '')
                additional_info[field_name] = value

        # Generate reference number if not provided
        if not reference_number:
            reference_number = f"ADM-{academic_year}-{int(timezone.now().timestamp())}"

        # Validate required fields
        if not (student_id and template_id and admission_date and academic_year and grade_admitted):
            messages.error(request, 'All required fields must be provided.')
            return redirect('users:admission_letter_generate')

        try:
            student = Student.objects.get(id=student_id)
            template = AdmissionLetterTemplate.objects.get(id=template_id)

            # Create the admission letter
            letter = AdmissionLetter.objects.create(
                student=student,
                template=template,
                reference_number=reference_number,
                admission_date=admission_date,
                academic_year=academic_year,
                grade_admitted=grade_admitted,
                section_admitted=section_admitted,
                fee_details=fee_details,
                additional_info=additional_info,
                is_printed=False
            )

            messages.success(request, f'Admission letter for {student.user.get_full_name()} generated successfully.')
            return redirect('users:admission_letter_detail', letter_id=letter.id)

        except (Student.DoesNotExist, AdmissionLetterTemplate.DoesNotExist):
            messages.error(request, 'Student or template not found.')
            return redirect('users:admission_letter_generate')

    # For GET request, display the form
    students = Student.objects.all().order_by('user__first_name', 'user__last_name')
    templates = AdmissionLetterTemplate.objects.filter(is_active=True)

    # Get all grades and sections from existing students
    grades = Student.objects.values_list('grade', flat=True).distinct()
    sections = Student.objects.values_list('section', flat=True).distinct()

    # Get current year for academic year suggestion
    current_year = timezone.now().year
    academic_year_suggestion = f"{current_year}-{current_year + 1}"

    return render(request, 'users/admission_letter_generate.html', {
        'students': students,
        'templates': templates,
        'grades': grades,
        'sections': sections,
        'today': timezone.now().date(),
        'academic_year_suggestion': academic_year_suggestion
    })

@user_passes_test(is_admin)
def admission_letter_batch_generate(request):
    """Generate admission letters for multiple students in batch"""
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        academic_year = request.POST.get('academic_year')
        admission_date = request.POST.get('admission_date')
        grade_admitted = request.POST.get('grade_admitted')
        section_admitted = request.POST.get('section_admitted', '')
        student_ids = request.POST.getlist('student_ids')

        # Validate required fields
        if not (template_id and academic_year and admission_date and grade_admitted):
            messages.error(request, 'All required fields must be provided.')
            return redirect('users:admission_letter_batch_generate')

        try:
            template = AdmissionLetterTemplate.objects.get(id=template_id)

            # Get students to generate letters for
            if student_ids:
                students = Student.objects.filter(id__in=student_ids)
            else:
                # If no specific students selected, use all students in a specific grade
                current_grade = request.POST.get('current_grade')
                if current_grade:
                    students = Student.objects.filter(grade=current_grade)
                else:
                    messages.error(request, 'Either select specific students or specify a current grade.')
                    return redirect('users:admission_letter_batch_generate')

            if not students:
                messages.error(request, 'No students found with the selected criteria.')
                return redirect('users:admission_letter_batch_generate')

            # Generate letters for each student
            letters_generated = 0
            for student in students:
                # Generate a unique reference number
                reference_number = f"ADM-{academic_year}-{student.id}-{int(timezone.now().timestamp())}"

                # Create the admission letter
                AdmissionLetter.objects.create(
                    student=student,
                    template=template,
                    reference_number=reference_number,
                    admission_date=admission_date,
                    academic_year=academic_year,
                    grade_admitted=grade_admitted,
                    section_admitted=section_admitted,
                    is_printed=False
                )
                letters_generated += 1

            messages.success(request, f'{letters_generated} admission letters generated successfully.')
            return redirect('users:admission_letter_list')

        except AdmissionLetterTemplate.DoesNotExist:
            messages.error(request, 'Template not found.')
            return redirect('users:admission_letter_batch_generate')

    # For GET request, display the form
    templates = AdmissionLetterTemplate.objects.filter(is_active=True)

    # Get all students, grades, and sections
    students = Student.objects.all().order_by('grade', 'user__first_name', 'user__last_name')
    grades = Student.objects.values_list('grade', flat=True).distinct()
    sections = Student.objects.values_list('section', flat(True)).distinct()

    # Get current year for academic year suggestion
    current_year = timezone.now().year
    academic_year_suggestion = f"{current_year}-{current_year + 1}"

    return render(request, 'users/admission_letter_batch_generate.html', {
        'templates': templates,
        'students': students,
        'grades': grades,
        'sections': sections,
        'today': timezone.now().date(),
        'academic_year_suggestion': academic_year_suggestion
    })

@user_passes_test(is_admin)
def admission_letter_detail(request, letter_id):
    """View details of an admission letter"""
    letter = get_object_or_404(AdmissionLetter, id=letter_id)

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    # Helper function to generate letter content
    def generate_letter_body(letter, request=None):
        """Generate formatted letter body from template"""
        student = letter.student
        user = student.user
        school_settings = SchoolSettings.objects.first()

        # Login credentials block
        login_url = ''
        if request:
            login_url = f"<li><strong>Login URL:</strong> {request.build_absolute_uri('/')[:-1]}/users/student-login/</li>"

        login_credentials = f"""
        <div style="border: 1px solid #ddd; padding: 15px; margin: 20px 0; background-color: #f9f9f9;">
            <h4 style="margin-top: 0;">Student Login Credentials</h4>
            <p>Please use the following credentials to log into the student portal:</p>
            <ul>
                <li><strong>Student ID:</strong> {student.student_id}</li>
                <li><strong>PIN:</strong> {student.pin}</li>
                {login_url}
            </ul>
            <p>Please keep these credentials secure and do not share them with others.</p>
        </div>
        """

        # Intro paragraph
        intro_paragraph = f"""
        <p>Dear {user.get_full_name()},</p>
        <p>We are pleased to inform you that you have been admitted to Grade {letter.grade_admitted} at {school_settings.school_name if school_settings else 'our school'} for the academic year {letter.academic_year}. On behalf of the faculty and staff, I would like to extend a warm welcome to you as you begin your educational journey with us.</p>
        <p>Your admission reflects our confidence in your abilities and potential for academic excellence. We look forward to providing you with quality education in a nurturing environment.</p>
        """

        # Context data for template
        context_data = {
            'school_name': school_settings.school_name if school_settings else "School Management System",
            'student_name': user.get_full_name(),
            'student_id': student.student_id,
            'grade': letter.grade_admitted,
            'section': letter.section_admitted,
            'academic_year': letter.academic_year,
            'admission_date': letter.admission_date.strftime('%B %d, %Y'),
            'current_date': timezone.now().strftime('%B %d, %Y'),
            'reference_number': letter.reference_number,
            'pin': student.pin,
            'start_date': (letter.admission_date + timedelta(days=14)).strftime('%B %d, %Y'),
            'school_address': school_settings.address if school_settings else '',
            'school_phone': school_settings.phone if school_settings else '',
            'school_email': school_settings.email if school_settings else '',
            'principal_name': school_settings.principal_name if school_settings and hasattr(school_settings, 'principal_name') else 'School Principal',
            'login_credentials': login_credentials,
            'intro_paragraph': intro_paragraph
        }

        # Add additional info if present
        if letter.additional_info:
            context_data.update(letter.additional_info)

        # Attempt to format the template with our data
        try:
            # If the template doesn't already have intro paragraph, prepend it
            if not "{intro_paragraph}" in letter.template.body_template:
                enhanced_template = "{intro_paragraph}\n\n" + letter.template.body_template

                # If login credentials aren't in template, append them
                if not "{login_credentials}" in letter.template.body_template:
                    enhanced_template += "\n\n{login_credentials}"
            else:
                enhanced_template = letter.template.body_template

            return enhanced_template.format(**context_data)
        except KeyError as e:
            return f"Error processing template: Missing field {str(e)}"
        except Exception as e:
            return f"Error processing template: {str(e)}"

    # Process the template with student data for preview
    student = letter.student
    user = student.user

    # Use the helper function to generate the letter body
    processed_body = generate_letter_body(letter, request)

    return render(request, 'users/admission_letter_detail.html', {
        'letter': letter,
        'school_settings': school_settings,
        'processed_body': processed_body
    })

@user_passes_test(is_admin)
def admission_letter_print(request, letter_id):
    """Print/download an admission letter"""
    letter = get_object_or_404(AdmissionLetter, id=letter_id)

    # Mark as printed if not already
    if not letter.is_printed:
        letter.is_printed = True
        letter.save()

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    # Process the template with student data
    student = letter.student
    user = student.user

    # Prepare context data for template processing
    context_data = {
        'student_name': user.get_full_name(),
        'student_id': student.student_id,
        'grade': letter.grade_admitted,
        'section': letter.section_admitted,
        'academic_year': letter.academic_year,
        'admission_date': letter.admission_date.strftime('%B %d, %Y'),
        'current_date': timezone.now().strftime('%B %d, %Y')
    }

    # Also add any fields from additional_info
    if letter.additional_info:
        for key, value in letter.additional_info.items():
            context_data[key] = value

    # Process the template body
    from string import Template
    try:
        body_template = Template(letter.template.body_template)
        processed_body = body_template.safe_substitute(**context_data)
    except Exception as e:
        processed_body = f"Error processing template: {str(e)}"

    return render(request, 'users/admission_letter_print.html', {
        'letter': letter,
        'school_settings': school_settings,
        'processed_body': processed_body,
        'print_mode': True
    })

@login_required
def admission_letter_template_export(request):
    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        try:
            template = AdmissionLetterTemplate.objects.get(id=template_id)
            template_data = {
                'name': template.name,
                'header_text': template.header_text,
                'body_template': template.body_template,
                'footer_text': template.footer_text,
                'signatory_name': template.signatory_name,
                'signatory_position': template.signatory_position,
                'is_active': template.is_active,
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat()
            }

            # Handle signature image if it exists
            if template.signature_image:
                template_data['signature_image_url'] = template.signature_image.url

            return JsonResponse(template_data)
        except AdmissionLetterTemplate.DoesNotExist:
            return JsonResponse({'error': 'Template not found'}, status=404)
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@user_passes_test(is_admin)
def email_admission_letter(request, letter_id):
    """Email an admission letter to a parent or guardian with HTML formatting"""
    from django.http import JsonResponse
    from django.template.loader import render_to_string
    from .utils import send_school_email
    import logging

    # Get logger for better error tracking
    logger = logging.getLogger(__name__)

    try:
        letter = get_object_or_404(AdmissionLetter, id=letter_id)
        student = letter.student

        if request.method == 'POST':
            recipient_email = request.POST.get('recipient')
            subject = request.POST.get('subject')
            message = request.POST.get('emailBody')

            if not recipient_email or not subject or not message:
                error_msg = "Missing required email fields"
                messages.error(request, error_msg)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': error_msg
                    })
                return redirect('users:admission_letter_detail', letter_id=letter_id)

            # Get school settings
            school_settings = SchoolSettings.objects.first()

            # Process the template with student data for HTML email
            user = student.user

            # Create a styled HTML email with the admission letter content
            try:
                # Prepare context for letter template
                context = {
                    'letter': letter,
                    'student': student,
                    'school_settings': school_settings,
                    'processed_body': letter.get_processed_content() if hasattr(letter, 'get_processed_content') else "",
                    'email_format': True  # Flag to indicate email formatting
                }

                # Create HTML email content based on a simpler email template version of the letter
                html_email_template = """
                <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
                    <!-- Email Header with School Info -->
                    <div style="text-align: center; padding: 20px; border-bottom: 2px solid #ddd; margin-bottom: 20px;">
                        <h1 style="color: #333; margin: 0 0 10px 0;">{school_name}</h1>
                        <p style="color: #666; margin: 0;">{school_address}</p>
                        <p style="color: #666; margin: 5px 0;">
                            {school_contact}
                        </p>
                    </div>

                    <!-- Reference Number & Date -->
                    <div style="margin-bottom: 20px; overflow: hidden;">
                        <div style="float: left; width: 50%;">
                            <strong>Reference:</strong> {reference_number}
                        </div>
                        <div style="float: right; width: 50%; text-align: right;">
                            <strong>Date:</strong> {date}
                        </div>
                    </div>

                    <!-- Letter Content -->
                    <div style="line-height: 1.6; margin-bottom: 20px;">
                        {letter_body}
                    </div>

                    <!-- Student Login Information -->
                    <div style="background-color: #f5f5f5; border-left: 4px solid #4e73df; padding: 15px; margin: 20px 0;">
                        <h3 style="color: #4e73df; margin-top: 0;">Student Login Information</h3>
                        <div style="overflow: hidden;">
                            <div style="float: left; width: 50%;">
                                <strong>Student ID:</strong> {student_id}
                            </div>
                            <div style="float: left; width: 50%;">
                                <strong>PIN:</strong> {pin}
                            </div>
                        </div>
                        <p style="margin-top: 10px; color: #666; font-size: 0.9em;">
                            Students can log in using these credentials on the student login page.
                        </p>
                    </div>

                    <!-- Signature -->
                    <div style="margin-top: 30px; margin-bottom: 20px;">
                        <p style="margin-bottom: 5px;"><strong>{signatory_name}</strong></p>
                        <p style="color: #666; font-style: italic; margin-top: 0;">{signatory_position}</p>
                    </div>

                    <!-- Footer -->
                    <div style="border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px; text-align: center; color: #777; font-size: 0.8em;">
                        {footer_text}
                    </div>
                </div>
                """

                # Format the HTML email template with context data
                school_name = school_settings.school_name if school_settings else "School Management System"
                school_address = school_settings.address if school_settings else "School Address"
                school_contact = ""
                if school_settings:
                    contact_parts = []
                    if school_settings.phone:
                        contact_parts.append(f"Tel: {school_settings.phone}")
                    if school_settings.email:
                        contact_parts.append(f"Email: {school_settings.email}")
                    if school_settings.website:
                        contact_parts.append(f"Website: {school_settings.website}")
                    school_contact = " | ".join(contact_parts)

                # Get the formatted letter body - either from model method or from the context
                letter_body = context['processed_body']
                if not letter_body:
                    # If we don't have processed content, create a simple version using template fields
                    letter_body = f"""
                    <p>Dear {student.user.get_full_name()},</p>
                    <p>We are pleased to inform you that you have been admitted to Grade {letter.grade_admitted}
                    at {school_name} for the academic year {letter.academic_year}.</p>
                    <p>Please find below the details of your admission:</p>
                    <ul>
                        <li><strong>Admission Date:</strong> {letter.admission_date.strftime('%B %d, %Y')}</li>
                        <li><strong>Grade Admitted:</strong> {letter.grade_admitted}</li>
                        <li><strong>Section:</strong> {letter.section_admitted or 'To be assigned'}</li>
                    </ul>
                    <p>We look forward to welcoming you to our school community.</p>
                    """

                # Complete HTML email by formatting the template
                html_email_content = html_email_template.format(
                    school_name=school_name,
                    school_address=school_address,
                    school_contact=school_contact,
                    reference_number=letter.reference_number,
                    date=letter.created_at.strftime('%B %d, %Y'),
                    letter_body=letter_body,
                    student_id=student.student_id,
                    pin=student.pin,
                    signatory_name=letter.template.signatory_name or "School Principal",
                    signatory_position=letter.template.signatory_position or "Principal",
                    footer_text=letter.template.footer_text or f"This is an official document from {school_name}. Please keep this information for your records."
                )

                # Add the user's email message above the formatted letter content
                full_html_email = f"""
                <div style="font-family: Arial, sans-serif; margin-bottom: 30px;">
                    {message}
                </div>
                <hr style="border: 0; height: 1px; background-color: #ddd; margin: 30px 0;">
                {html_email_content}
                """

                # Send email using the utility function
                sent = send_school_email(
                    subject=subject,
                    message=message,  # Plain text version
                    recipient_list=[recipient_email],
                    html_message=full_html_email,  # HTML version with formatted letter
                    from_email=school_settings.smtp_username if school_settings else None
                )

                if sent:
                    success_msg = f"Admission letter sent to {recipient_email}"
                    messages.success(request, success_msg)

                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': success_msg
                        })
                else:
                    error_msg = "Failed to send admission letter. Please check email settings."
                    messages.error(request, error_msg)

                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'message': error_msg
                        })

            except Exception as e:
                logger.error(f"Email sending error: {str(e)}")
                error_msg = f"Error sending email: {str(e)}"
                messages.error(request, error_msg)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': error_msg
                    })

            # If not an AJAX request, redirect to the detail page
            return redirect('users:admission_letter_detail', letter_id=letter_id)

        # For GET request, just redirect to the detail page
        return redirect('users:admission_letter_detail', letter_id=letter_id)

    except AdmissionLetter.DoesNotExist:
        error_msg = "Admission letter not found"
        messages.error(request, error_msg)

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_msg
            })

        return redirect('users:admission_letter_list')
    except Exception as e:
        logger.error(f"Unexpected error in email_admission_letter: {str(e)}")
        error_msg = f"Error: {str(e)}"
        messages.error(request, error_msg)

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_msg
            })

        return redirect('users:admission_letter_list')

@user_passes_test(is_admin)
def id_card_deactivate(request, card_id):
    """Deactivate an ID card"""
    id_card = get_object_or_404(IDCard, id=card_id)

    if request.method == 'POST':
        id_card.is_active = False
        id_card.save()
        messages.success(request, f"ID card for {id_card.user.get_full_name()} has been deactivated.")

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"ID card deactivated successfully."
            })

        return redirect('users:id_card_detail', card_id=id_card.id)

    # If not POST, redirect to detail page
    return redirect('users:id_card_detail', card_id=id_card.id)

@user_passes_test(is_admin)
def id_card_activate(request, card_id):
    """Activate an ID card"""
    id_card = get_object_or_404(IDCard, id=card_id)

    if request.method == 'POST':
        id_card.is_active = True
        id_card.save()
        messages.success(request, f"ID card for {id_card.user.get_full_name()} has been activated.")

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"ID card activated successfully."
            })

        return redirect('users:id_card_detail', card_id=id_card.id)

    # If not POST, redirect to detail page
    return redirect('users:id_card_detail', card_id=id_card.id)

@user_passes_test(is_admin)
def id_card_regenerate(request, card_id):
    """Regenerate an ID card with new details"""
    old_card = get_object_or_404(IDCard, id=card_id)

    if request.method == 'POST':
        # Get form data
        template_id = request.POST.get('template_id')
        expiry_date = request.POST.get('expiry_date')

        try:
            # Get template
            template = IDCardTemplate.objects.get(id=template_id)

            # Generate a new card number
            card_number = f"ID-{old_card.user.role}-{old_card.user.id}-{int(timezone.now().timestamp())}"

            # Create new card with updated details
            new_card = IDCard.objects.create(
                user=old_card.user,
                template=template,
                card_number=card_number,
                issue_date=timezone.now().date(),
                expiry_date=expiry_date,
                barcode_data=old_card.barcode_data,
                additional_info=old_card.additional_info,
                is_active=True
            )

            # Deactivate old card
            old_card.is_active = False
            old_card.save()

            messages.success(request, f"ID card for {old_card.user.get_full_name()} has been regenerated successfully.")
            return redirect('users:id_card_detail', card_id=new_card.id)

        except IDCardTemplate.DoesNotExist:
            messages.error(request, "Template not found.")
            return redirect('users:id_card_detail', card_id=old_card.id)
        except Exception as e:
            messages.error(request, f"Error regenerating ID card: {str(e)}")
            return redirect('users:id_card_detail', card_id=old_card.id)

    # If not POST, redirect to detail page
    return redirect('users:id_card_detail', card_id=old_card.id)

@user_passes_test(is_admin)
def id_card_delete(request, card_id):
    """Delete an ID card"""
    id_card = get_object_or_404(IDCard, id=card_id)

    if request.method == 'POST':
        user_name = id_card.user.get_full_name()
        id_card.delete()
        messages.success(request, f"ID card for {user_name} has been deleted successfully.")

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"ID card for {user_name} deleted successfully."
            })

        return redirect('users:id_card_list')

    # If not POST method, redirect to detail page
    return redirect('users:id_card_detail', card_id=id_card.id)

@user_passes_test(is_admin)
def admission_letter_delete(request, letter_id):
    """Delete an admission letter"""
    letter = get_object_or_404(AdmissionLetter, id=letter_id)

    if request.method == 'POST':
        student_name = letter.student.user.get_full_name()
        letter.delete()
        messages.success(request, f"Admission letter for {student_name} has been deleted successfully.")

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Admission letter for {student_name} deleted successfully."
            })

        return redirect('users:admission_letter_list')

    # If not POST method, redirect to detail page
    return redirect('users:admission_letter_detail', letter_id=letter_id)

@user_passes_test(is_admin)
def id_card_deactivate(request, card_id):
    """Deactivate an ID card"""
    id_card = get_object_or_404(IDCard, id=card_id)

    if request.method == 'POST':
        id_card.is_active = False
        id_card.save()
        messages.success(request, f"ID card for {id_card.user.get_full_name()} has been deactivated.")

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"ID card deactivated successfully."
            })

        return redirect('users:id_card_detail', card_id=id_card.id)

    # If not POST, redirect to detail page
    return redirect('users:id_card_detail', card_id=id_card.id)

@user_passes_test(is_admin)
def id_card_activate(request, card_id):
    """Activate an ID card"""
    id_card = get_object_or_404(IDCard, id=card_id)

    if request.method == 'POST':
        id_card.is_active = True
        id_card.save()
        messages.success(request, f"ID card for {id_card.user.get_full_name()} has been activated.")

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"ID card activated successfully."
            })

        return redirect('users:id_card_detail', card_id=id_card.id)

    # If not POST, redirect to detail page
    return redirect('users:id_card_detail', card_id=id_card.id)

@user_passes_test(is_admin)
def id_card_regenerate(request, card_id):
    """Regenerate an ID card with new details"""
    old_card = get_object_or_404(IDCard, id=card_id)

    if request.method == 'POST':
        # Get form data
        template_id = request.POST.get('template_id')
        expiry_date = request.POST.get('expiry_date')

        try:
            # Get template
            template = IDCardTemplate.objects.get(id=template_id)

            # Generate a new card number
            card_number = f"ID-{old_card.user.role}-{old_card.user.id}-{int(timezone.now().timestamp())}"

            # Create new card with updated details
            new_card = IDCard.objects.create(
                user=old_card.user,
                template=template,
                card_number=card_number,
                issue_date=timezone.now().date(),
                expiry_date=expiry_date,
                barcode_data=old_card.barcode_data,
                additional_info=old_card.additional_info,
                is_active=True
            )

            # Deactivate old card
            old_card.is_active = False
            old_card.save()

            messages.success(request, f"ID card for {old_card.user.get_full_name()} has been regenerated successfully.")
            return redirect('users:id_card_detail', card_id=new_card.id)

        except IDCardTemplate.DoesNotExist:
            messages.error(request, "Template not found.")
            return redirect('users:id_card_detail', card_id=old_card.id)
        except Exception as e:
            messages.error(request, f"Error regenerating ID card: {str(e)}")
            return redirect('users:id_card_detail', card_id=old_card.id)

    # If not POST, redirect to detail page
    return redirect('users:id_card_detail', card_id=old_card.id)

# Update test_email view to handle AJAX requests
@user_passes_test(is_admin)
def test_email(request):
    """Test the SMTP email configuration"""
    from .utils import send_school_email
    from django.http import JsonResponse

    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('users:school_settings')

    # Get the test email details
    test_email = request.POST.get('test_email')
    test_subject = request.POST.get('test_subject')
    test_content = request.POST.get('test_content')

    if not (test_email and test_subject and test_content):
        messages.error(request, 'All fields are required.')
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': "All fields are required."
            })
        return redirect('users:school_settings')

    # Get the school settings
    school_settings = SchoolSettings.objects.first()
    if not school_settings:
        messages.error(request, 'School settings not found.')
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': "School settings not found."
            })
        return redirect('users:school_settings')

    # Check if SMTP settings are configured
    if not (school_settings.smtp_host and school_settings.smtp_port and
            school_settings.smtp_username and school_settings.smtp_password):
        messages.error(request, 'SMTP settings are not fully configured.')
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': "SMTP settings are not fully configured."
            })
        return redirect('users:school_settings')

    try:
        # Send the test email using our utility function
        sent = send_school_email(
            subject=test_subject,
            message=test_content,
            recipient_list=[test_email],
            html_message=f"<p>{test_content}</p>",
            from_email=school_settings.smtp_username
        )

        if sent:
            messages.success(request, f'Test email sent successfully to {test_email}.')
            # Check if AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f"Test email sent successfully to {test_email}."
                })
        else:
            messages.error(request, 'Failed to send test email. Please check your SMTP settings.')
            # Check if AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': "Failed to send test email. Please check your SMTP settings."
                })
    except Exception as e:
        messages.error(request, f'Error sending test email: {str(e)}')
        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f"Error sending test email: {str(e)}"
            })

    return redirect('users:school_settings')

