from django.core.mail import send_mail as django_send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.html import strip_tags
import logging
from .models import SchoolSettings
import smtplib

logger = logging.getLogger(__name__)

def send_school_email(subject, message, recipient_list, html_message=None, from_email=None, fail_silently=False, is_password_reset=False):
    """
    Enhanced utility function to send emails using the school's SMTP settings.
    
    Args:
        subject (str): The email subject
        message (str): The email text content
        recipient_list (list): List of recipient email addresses
        html_message (str, optional): HTML version of the message
        from_email (str, optional): Sender's email address. Defaults to the configured SMTP username.
        fail_silently (bool, optional): Whether to suppress exceptions. Defaults to False.
        is_password_reset (bool, optional): Whether this is a password reset email. Defaults to False.
    
    Returns:
        int: Number of emails successfully sent
    """
    try:
        # Get the school settings
        school_settings = SchoolSettings.objects.first()
        
        if not school_settings:
            logger.error("School settings not found. Cannot send email.")
            if fail_silently:
                return 0
            raise ValueError("School settings not found")
            
        # If SMTP settings are incomplete, log and handle the error
        if not (school_settings.smtp_host and school_settings.smtp_port and 
                school_settings.smtp_username and school_settings.smtp_password):
            logger.error("Incomplete SMTP settings. Cannot send email.")
            if fail_silently:
                return 0
            raise ValueError("Incomplete SMTP settings")
        
        # If no from_email specified, use the SMTP username from school settings
        if not from_email:
            from_email = school_settings.smtp_username
        
        # Get an SMTP connection with explicit settings from the database
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=school_settings.smtp_host,
            port=school_settings.smtp_port,
            username=school_settings.smtp_username,
            password=school_settings.smtp_password,
            use_tls=school_settings.smtp_use_tls,
            fail_silently=fail_silently
        )
        
        # Log SMTP configuration (without password)
        logger.debug(f"Using SMTP settings: host={school_settings.smtp_host}, port={school_settings.smtp_port}, "
                    f"username={school_settings.smtp_username}, use_tls={school_settings.smtp_use_tls}")
        
        # For password reset emails, use EmailMultiAlternatives for more control
        if is_password_reset and html_message:
            logger.info(f"Sending password reset email to {', '.join(recipient_list)}")
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
                connection=connection
            )
            email.attach_alternative(html_message, "text/html")
            return email.send(fail_silently=fail_silently)
        
        # For regular emails, use Django's send_mail with our explicit connection
        return django_send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            connection=connection,
            fail_silently=fail_silently
        )
    except Exception as e:
        # Use proper logging instead of print
        logger.error(f"Error sending email: {str(e)}")
        
        if fail_silently:
            # Return 0 to indicate no emails were sent
            return 0
        else:
            # Re-raise the exception to allow the caller to handle it
            raise

def generate_absolute_uri(request, path):
    """
    Generate an absolute URI for links in emails.
    
    Args:
        request: The HTTP request object
        path: The relative path
        
    Returns:
        str: The absolute URI
    """
    if request:
        return request.build_absolute_uri(path)
    else:
        # If no request provided, use the first site's domain or default to localhost
        from django.contrib.sites.models import Site
        try:
            current_site = Site.objects.get_current()
            base_url = f"http://{current_site.domain}"
        except:
            # Fallback to localhost if Site framework not configured
            base_url = "http://localhost:8000"
        
        # Ensure path starts with /
        if not path.startswith('/'):
            path = f"/{path}"
            
        return f"{base_url}{path}"