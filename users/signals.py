from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.utils.html import mark_safe
from django.db import transaction
import logging
from .utils import send_school_email
from .models import SchoolSettings, Teacher, Student, Parent, StaffMember
from courses.models import ClassRoom, ClassSubject

# Get logger for better error tracking
logger = logging.getLogger(__name__)

User = get_user_model()

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """Send a welcome email with login credentials when a user is created."""
    # Check if this is a new user AND they have an email address
    if created and instance.email:
        # Always skip welcome email for parent roles since it's handled by registration view
        if instance.role == 'PARENT' or instance.is_parent:
            logger.info(f"Skipping welcome email for parent {instance.email} - handled by registration view")
            return

        # Check if the welcome email should be skipped
        if hasattr(instance, 'skip_welcome_email') and instance.skip_welcome_email:
            logger.info(f"Skipping welcome email for user {instance.email} as requested")
            return

        # Check SMTP settings before attempting to send
        school_settings = SchoolSettings.objects.first()
        if not school_settings or not all([
            school_settings.smtp_host,
            school_settings.smtp_port,
            school_settings.smtp_username,
            school_settings.smtp_password
        ]):
            logger.warning("Cannot send welcome email: SMTP settings not fully configured")
            return

        try:
            # Get school name and logo information
            school_name = school_settings.school_name if school_settings else "School Management System"
            school_logo_url = ''
            if school_settings and school_settings.logo:
                school_logo_url = school_settings.logo.url

            # Base URL for login links
            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')

            # Create role-specific content
            role_specific_content = ""
            login_url = ""

            if instance.is_admin:
                # Admin-specific content - admins use email to login
                login_url = f"{base_url}/users/login/"
                credentials_html = f"""
                <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9;">
                    <h3 style="margin-top: 0; color: #333;">Your Admin Login Credentials</h3>
                    <ul style="padding-left: 20px;">
                        <li><strong>Email:</strong> {instance.email}</li>
                        <li><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></li>
                    </ul>
                    <p style="margin-bottom: 0;">Please login with the password you were provided during account creation.</p>
                </div>
                """
                role_specific_content = f"""
                <p>You have been registered as an <strong>Administrator</strong> in the {school_name} management system.</p>
                <p>As an administrator, you have access to all features of the system, including user management,
                course administration, attendance tracking, and reporting features.</p>
                {credentials_html}
                """

            elif instance.is_teacher:
                # Teacher-specific content - teachers use staff ID, no username needed
                login_url = f"{base_url}/users/teacher-login/"

                # Get teacher profile info if it exists
                try:
                    teacher = Teacher.objects.get(user=instance)
                    credentials_html = f"""
                    <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9;">
                        <h3 style="margin-top: 0; color: #333;">Your Teacher Login Credentials</h3>
                        <ul style="padding-left: 20px;">
                            <li><strong>Staff ID:</strong> {teacher.employee_id}</li>
                            <li><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></li>
                        </ul>
                        <p style="margin-bottom: 0;">Please login with the password you were provided during account creation.</p>
                    </div>
                    """

                    department_info = f"<p>You have been assigned to the <strong>{teacher.department}</strong> department.</p>" if teacher.department else ""

                    role_specific_content = f"""
                    <p>You have been registered as a <strong>Teacher</strong> in the {school_name} management system.</p>
                    {department_info}
                    <p>As a teacher, you can manage your classes, record student attendance, create and grade assignments,
                    and communicate with students and parents.</p>
                    {credentials_html}
                    """
                except Teacher.DoesNotExist:
                    role_specific_content = f"""
                    <p>You have been registered as a <strong>Teacher</strong> in the {school_name} management system.</p>
                    <p>Your profile setup is incomplete. Please contact the system administrator for your complete login credentials.</p>
                    """

            elif instance.is_student:
                # Student-specific content - students use student ID and PIN, no username needed
                login_url = f"{base_url}/users/student-login/"

                # Get student profile info if it exists
                try:
                    student = Student.objects.get(user=instance)
                    credentials_html = f"""
                    <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9;">
                        <h3 style="margin-top: 0; color: #333;">Your Student Login Credentials</h3>
                        <ul style="padding-left: 20px;">
                            <li><strong>Student ID:</strong> {student.student_id}</li>
                            <li><strong>PIN:</strong> {student.pin}</li>
                            <li><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></li>
                        </ul>
                        <p style="margin-bottom: 0; color: #d35400;"><strong>Important:</strong> Please keep your PIN secure and do not share it with others.</p>
                    </div>
                    """

                    grade_info = f"<p>You have been enrolled in <strong>Grade {student.grade}</strong>" + (f", Section {student.section}.</p>" if student.section else ".</p>")

                    role_specific_content = f"""
                    <p>You have been registered as a <strong>Student</strong> in the {school_name} management system.</p>
                    {grade_info}
                    <p>As a student, you can view your assignments, submit your work, check your grades,
                    view your attendance records, and communicate with your teachers.</p>
                    {credentials_html}
                    """
                except Student.DoesNotExist:
                    role_specific_content = f"""
                    <p>You have been registered as a <strong>Student</strong> in the {school_name} management system.</p>
                    <p>Your profile setup is incomplete. Please contact the system administrator for your complete login credentials.</p>
                    """

            elif instance.is_non_teaching_staff:
                # Non-teaching staff content - staff use employee ID, no username needed
                login_url = f"{base_url}/users/login/"

                # Get staff profile info if it exists
                try:
                    staff = StaffMember.objects.get(user=instance)
                    credentials_html = f"""
                    <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9;">
                        <h3 style="margin-top: 0; color: #333;">Your Staff Login Credentials</h3>
                        <ul style="padding-left: 20px;">
                            <li><strong>Staff ID:</strong> {staff.employee_id}</li>
                            <li><strong>Email:</strong> {instance.email}</li>
                            <li><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></li>
                        </ul>
                        <p style="margin-bottom: 0;">Please login with the password you were provided during account creation.</p>
                    </div>
                    """

                    department_info = f"<p>You have been assigned to the <strong>{staff.department}</strong> department.</p>" if staff.department else ""
                    position_info = f"<p>Your position is <strong>{staff.position}</strong>.</p>" if staff.position else ""

                    role_specific_content = f"""
                    <p>You have been registered as a <strong>{instance.get_role_display()}</strong> in the {school_name} management system.</p>
                    {department_info}
                    {position_info}
                    <p>You can access your dashboard, view your schedule, and use the system features relevant to your role.</p>
                    {credentials_html}
                    """
                except StaffMember.DoesNotExist:
                    role_specific_content = f"""
                    <p>You have been registered as a <strong>{instance.get_role_display()}</strong> in the {school_name} management system.</p>
                    <p>Your profile setup is incomplete. Please contact the system administrator for your complete login credentials.</p>
                    """

            elif instance.is_parent:
                # Parent-specific content - parents use email, no username needed
                login_url = f"{base_url}/users/parent-login/"

                # Get parent profile info if it exists
                try:
                    parent = Parent.objects.get(user=instance)
                    # Get the password from the instance's initial_password attribute if it exists
                    password_display = getattr(instance, 'initial_password', 'Use the password you received during registration')

                    credentials_html = f"""
                    <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9;">
                        <h3 style="margin-top: 0; color: #333;">Your Parent Login Credentials</h3>
                        <ul style="padding-left: 20px;">
                            <li><strong>Email:</strong> {instance.email}</li>
                            <li><strong>Password:</strong> {password_display}</li>
                            <li><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></li>
                        </ul>
                        <p style="margin-bottom: 0; color: #d35400;"><strong>Security Note:</strong> Please change your password after your first login.</p>
                    </div>
                    """

                    # If parent has children associated, list them and their login info
                    children = parent.children.all()
                    children_html = ""

                    if children:
                        children_html = "<h3>Your Children's Information</h3>"
                        for child in children:
                            child_user = child.user
                            # Use full name instead of username
                            child_name = child_user.get_full_name()
                            if not child_name:
                                child_name = f"Student #{child.student_id}"

                            children_html += f"""
                            <div style="margin: 10px 0; padding: 15px; border: 1px solid #eee; background-color: #f5f5f5;">
                                <h4 style="margin-top: 0; color: #333;">{child_name}</h4>
                                <ul style="padding-left: 20px;">
                                    <li><strong>Student ID:</strong> {child.student_id}</li>
                                    <li><strong>PIN:</strong> {child.pin}</li>
                                    <li><strong>Grade:</strong> {child.grade or 'Not assigned'}</li>
                                    <li><strong>Section:</strong> {child.section or 'Not assigned'}</li>
                                    <li><strong>Login URL:</strong> <a href="{base_url}/users/student-login/">{base_url}/users/student-login/</a></li>
                                </ul>
                                <p style="font-size: 12px; color: #666;">*Your child can log in using their Student ID and PIN</p>
                            </div>
                            """

                    role_specific_content = f"""
                    <p>You have been registered as a <strong>Parent/Guardian</strong> in the {school_name} management system.</p>
                    <p>As a parent, you can view your child's assignments, grades, attendance records, and
                    communicate with their teachers.</p>
                    {credentials_html}
                    {children_html}
                    """
                except Parent.DoesNotExist:
                    # Even when Parent doesn't exist, we can still provide the email login info
                    credentials_html = f"""
                    <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9;">
                        <h3 style="margin-top: 0; color: #333;">Your Parent Account Login Credentials</h3>
                        <ul style="padding-left: 20px;">
                            <li><strong>Email:</strong> {instance.email}</li>
                            <li><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></li>
                        </ul>
                        <p style="margin-bottom: 0;">Please login with the password you were provided during account creation.</p>
                    </div>
                    """

                    role_specific_content = f"""
                    <p>You have been registered as a <strong>Parent/Guardian</strong> in the {school_name} management system.</p>
                    <p>As a parent, you can view your child's assignments, grades, attendance records, and
                    communicate with their teachers.</p>
                    {credentials_html}
                    <p>Your children will be linked to your account by the system administrator.</p>
                    """

            # Add school logo if available
            logo_html = ""
            if school_logo_url:
                logo_html = f'<div style="text-align: center; margin-bottom: 20px;"><img src="{base_url}{school_logo_url}" alt="{school_name} Logo" style="max-width: 200px; max-height: 100px;"></div>'

            # Common HTML template for all roles with improved styling
            html_message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="text-align: center; padding: 20px; background-color: #4e73df; color: white;">
                    <h2 style="margin: 0; color: white;">Welcome to {school_name}</h2>
                </div>

                {logo_html}

                <div style="padding: 20px; line-height: 1.5;">
                    <p>Dear {instance.get_full_name()},</p>

                    <p>Welcome to the {school_name} Management System! Your account has been created successfully.</p>

                    {role_specific_content}

                    <p>If you have any questions or need assistance, please contact the system administrator.</p>

                    <p>Best regards,<br>
                    {school_name} Administration</p>
                </div>

                <div style="padding: 15px; background-color: #f1f1f1; text-align: center; font-size: 12px; color: #666;">
                    <p>&copy; {school_name}. All rights reserved.</p>
                </div>
            </div>
            """

            # Plain text version for email clients that don't support HTML
            if instance.is_admin:
                login_id_text = f"Email: {instance.email}"
            elif instance.is_teacher:
                teacher = Teacher.objects.get(user=instance)
                login_id_text = f"Staff ID: {teacher.employee_id}"
            elif instance.is_student:
                student = Student.objects.get(user=instance)
                login_id_text = f"Student ID: {student.student_id}\nPIN: {student.pin}"
            elif instance.is_parent:
                login_id_text = f"Email: {instance.email}"
            elif instance.is_non_teaching_staff:
                # For non-teaching staff (accountant, security, etc.)
                try:
                    staff = StaffMember.objects.get(user=instance)
                    login_id_text = f"Staff ID: {staff.employee_id}\nEmail: {instance.email}"
                except StaffMember.DoesNotExist:
                    login_id_text = f"Email: {instance.email}"
            else:
                login_id_text = ""

            plain_message = f"""
Welcome to {school_name}!

Dear {instance.get_full_name()},

Welcome to the {school_name} Management System! Your account has been created successfully.

Your login information:
{login_id_text}
Login URL: {login_url}

Please use the password provided to you during account creation to log in.

If you have any questions or need assistance, please contact the system administrator.

Best regards,
{school_name} Administration
            """

            # Log attempt to send welcome email
            logger.info(f"Sending welcome email to {instance.email} (role: {instance.role})")

            # Send the welcome email
            subject = f'Welcome to {school_name} - Your Account Details'
            send_school_email(
                subject=subject,
                message=plain_message,
                recipient_list=[instance.email],
                html_message=html_message,
            )

            logger.info(f"Welcome email sent successfully to {instance.email}")

        except Exception as e:
            # Log the error with more detail
            logger.error(f"Error sending welcome email to {instance.email}: {str(e)}", exc_info=True)

@receiver(post_save, sender=User)
def send_password_reset_email(sender, instance, **kwargs):
    """Send password reset email when a user's verification status changes."""
    # This would typically be triggered by a password reset request, not directly on user save
    if instance.is_active and not instance.is_verified and hasattr(instance, 'password_reset_token'):
        try:
            # Get school settings
            school_settings = SchoolSettings.objects.first()
            school_name = school_settings.school_name if school_settings else "School Management System"

            # This is a placeholder for a proper token-based reset system
            # In a real implementation, you'd use Django's PasswordResetTokenGenerator
            # For now, we're checking if the instance has a token attribute that was set elsewhere

            reset_url = reverse('password_reset_confirm', kwargs={
                'uidb64': instance.pk,
                'token': instance.password_reset_token
            })

            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            full_reset_url = f"{base_url}{reset_url}"

            # Add school logo if available
            logo_html = ""
            if school_settings and school_settings.logo:
                logo_html = f'<div style="text-align: center; margin-bottom: 20px;"><img src="{base_url}{school_settings.logo.url}" alt="{school_name} Logo" style="max-width: 200px; max-height: 100px;"></div>'

            # HTML email content with improved styling
            html_message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="text-align: center; padding: 20px; background-color: #4e73df; color: white;">
                    <h2 style="margin: 0; color: white;">Password Reset</h2>
                </div>

                {logo_html}

                <div style="padding: 20px; line-height: 1.5;">
                    <p>Dear {instance.get_full_name()},</p>

                    <p>You requested a password reset for your account at {school_name}.</p>

                    <div style="margin: 20px 0; text-align: center;">
                        <a href="{full_reset_url}" style="padding: 12px 24px; background-color: #4e73df; color: white; text-decoration: none; border-radius: 4px;">Reset Password</a>
                    </div>

                    <p>If you did not request a password reset, please ignore this email or contact the administrator if you have concerns.</p>

                    <p>This link will expire in 24 hours.</p>

                    <p>Best regards,<br>
                    {school_name} Administration</p>
                </div>

                <div style="padding: 15px; background-color: #f1f1f1; text-align: center; font-size: 12px; color: #666;">
                    <p>&copy; {school_name}. All rights reserved.</p>
                </div>
            </div>
            """

            # Plain text version
            plain_message = f"""
Password Reset Request

Dear {instance.get_full_name()},

You requested a password reset for your account at {school_name}.

Please visit the following link to reset your password:
{full_reset_url}

If you did not request a password reset, please ignore this email or contact the administrator if you have concerns.

This link will expire in 24 hours.

Best regards,
{school_name} Administration
            """

            # Log attempt to send reset email
            logger.info(f"Sending password reset email to {instance.email}")

            # Send the email
            subject = f'Password Reset - {school_name}'
            send_school_email(
                subject=subject,
                message=plain_message,
                recipient_list=[instance.email],
                html_message=html_message,
            )

            logger.info(f"Password reset email sent successfully to {instance.email}")

        except Exception as e:
            # Log the error with more detail
            logger.error(f"Error sending password reset email to {instance.email}: {str(e)}", exc_info=True)

@receiver(post_save, sender=Student)
def sync_student_enrollments(sender, instance, **kwargs):
    """
    Synchronize student enrollments when a student's grade changes.
    This ensures ClassRoom.students and ClassSubject.students stay in sync.
    """
    try:
        with transaction.atomic():
            # Only proceed if the student has a grade assigned
            if instance.grade:
                logger.debug(f"Synchronizing enrollments for student {instance} in grade {instance.grade}")

                # 1. Remove student from all classroom.students collections except current grade
                for classroom in ClassRoom.objects.exclude(id=instance.grade.id):
                    if instance in classroom.students.all():
                        classroom.students.remove(instance)
                        logger.debug(f"Removed student from {classroom}")

                # 2. Add student to current grade's classroom.students collection
                if instance not in instance.grade.students.all():
                    instance.grade.students.add(instance)
                    logger.debug(f"Added student to {instance.grade}")

                # 3. Remove student from all subjects not in their grade
                for subject in ClassSubject.objects.exclude(classroom=instance.grade):
                    if instance in subject.students.all():
                        subject.students.remove(instance)
                        logger.debug(f"Removed student from subject {subject.subject} in {subject.classroom}")

                # 4. Add student to all subjects in their grade
                for subject in ClassSubject.objects.filter(classroom=instance.grade):
                    if instance not in subject.students.all():
                        subject.students.add(instance)
                        logger.debug(f"Added student to subject {subject.subject} in {subject.classroom}")
    except Exception as e:
        logger.error(f"Error synchronizing student enrollments: {str(e)}", exc_info=True)