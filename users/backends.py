from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.conf import settings
import logging
from .models import SchoolSettings

logger = logging.getLogger(__name__)

class SchoolEmailBackend(EmailBackend):
    """
    Custom email backend that uses SMTP settings from SchoolSettings model.
    Updates settings from the database on each email send to ensure
    it always uses the latest configuration.
    
    Includes a fallback to Django's console email backend if SMTP fails.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_settings_from_db()
        # Create fallback backend
        self.fallback_backend = None
    
    def update_settings_from_db(self):
        """
        Update email settings from the SchoolSettings model.
        """
        try:
            settings_obj = SchoolSettings.objects.first()
            if settings_obj:
                self.host = settings_obj.smtp_host or ''
                self.port = settings_obj.smtp_port or 587
                self.username = settings_obj.smtp_username or ''
                self.password = settings_obj.smtp_password or ''
                self.use_tls = settings_obj.smtp_use_tls if settings_obj.smtp_use_tls is not None else True
                
                # Log SMTP configuration (without password)
                logger.debug(f"Using SMTP settings: host={self.host}, port={self.port}, username={self.username}, use_tls={self.use_tls}")
                
                # Check if we have valid SMTP settings
                if not (self.host and self.username and self.password):
                    logger.warning("Incomplete SMTP settings found in database, some emails may not be sent")
        except Exception as e:
            # Log the error
            logger.error(f"Error updating email settings from database: {str(e)}")
            # If there's any error, use default settings
            pass
    
    def send_messages(self, email_messages):
        """
        Override the send_messages method to update settings before sending.
        This ensures we always use the latest SMTP configuration from the database.
        
        If SMTP fails, falls back to the alternative email backend specified in settings.
        """
        if not email_messages:
            return 0
            
        # Update settings before sending
        self.update_settings_from_db()
        
        # Pre-process password reset emails to ensure correct URLs
        for message in email_messages:
            # Check if this is a password reset email
            if 'password reset' in message.subject.lower() or 'reset your password' in message.subject.lower():
                logger.info(f"Processing password reset email to {', '.join(message.to)}")
                # Make sure 'password_reset_confirm' URLs are correctly formatted
                for i, content in enumerate(message.alternatives):
                    if content[1] == 'text/html':
                        # Log that we're processing a password reset email
                        logger.debug("Processing HTML content in password reset email")
        
        # Try to send via SMTP
        try:
            # Check if we have valid SMTP settings
            if not self.host or not self.port or not self.username or not self.password:
                logger.warning("Incomplete SMTP settings, falling back to alternative backend")
                raise Exception("Incomplete SMTP settings")
                
            # Try sending via SMTP
            sent_count = super().send_messages(email_messages)
            logger.info(f"Successfully sent {sent_count} emails via SMTP")
            return sent_count
        except Exception as e:
            # Log the error
            logger.error(f"SMTP email sending failed: {str(e)}")
            
            # Fall back to alternative backend
            alternative_backend_path = getattr(settings, 'ALTERNATIVE_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
            
            # Log the fallback
            logger.info(f"Falling back to alternative email backend: {alternative_backend_path}")
            
            # Import the backend dynamically
            import importlib
            try:
                # Extract module path and class name
                module_path, class_name = alternative_backend_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                backend_class = getattr(module, class_name)
                
                # Initialize fallback backend
                self.fallback_backend = backend_class()
                
                # Send emails via fallback
                sent_count = self.fallback_backend.send_messages(email_messages)
                logger.info(f"Successfully sent {sent_count} emails via fallback backend")
                return sent_count
            except Exception as fallback_error:
                # If fallback also fails, log error
                logger.error(f"Fallback email backend failed: {str(fallback_error)}")
                return 0