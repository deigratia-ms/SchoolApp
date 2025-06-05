from django.db import models
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from users.utils import send_school_email

class JobPosition(models.Model):
    """Model for job positions available at the school"""
    DEPARTMENT_CHOICES = [
        ('teaching', 'Teaching Staff'),
        ('administration', 'Administration'),
        ('support', 'Support Staff'),
        ('management', 'Management'),
        ('other', 'Other'),
    ]

    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('internship', 'Internship'),
    ]

    title = models.CharField(max_length=100)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    location = models.CharField(max_length=100, default="On-site")
    description = models.TextField()
    responsibilities = models.TextField()
    qualifications = models.TextField()
    salary_range = models.CharField(max_length=100, blank=True)
    application_deadline = models.DateField()
    is_active = models.BooleanField(default=True)
    date_posted = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date_posted']
        verbose_name = "Job Position"
        verbose_name_plural = "Job Positions"

    def __str__(self):
        return self.title

    def is_expired(self):
        return self.application_deadline < timezone.now().date()

    def days_until_deadline(self):
        delta = self.application_deadline - timezone.now().date()
        return delta.days if delta.days >= 0 else 0


class JobApplication(models.Model):
    """Model for job applications submitted by users"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewing', 'Under Review'),
        ('interview', 'Selected for Interview'),
        ('rejected', 'Application Rejected'),
        ('hired', 'Hired'),
    ]

    position = models.ForeignKey(JobPosition, on_delete=models.CASCADE, related_name='applications')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    cover_letter = models.TextField()
    resume = models.FileField(upload_to='applications/resumes/')
    additional_document = models.FileField(upload_to='applications/documents/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    admin_feedback = models.TextField(blank=True, help_text="Feedback to be sent to the applicant")

    date_applied = models.DateTimeField(default=timezone.now)
    date_reviewed = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_applied']
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.position.title}"

    def send_confirmation_email(self):
        """Send confirmation email to applicant"""
        from website.models import SiteSettings

        # Get site settings for the email template
        site_settings = SiteSettings.objects.first()

        subject = f"Application Received - {self.position.title}"
        html_message = render_to_string('website/emails/application_confirmation.html', {
            'application': self,
            'site_settings': site_settings,
        })

        # Use the school's email utility function
        send_school_email(
            subject=subject,
            message="Thank you for your application. We have received it and will review it shortly.",  # Plain text version
            recipient_list=[self.email],
            html_message=html_message,
            fail_silently=False,
        )

    def send_status_update_email(self):
        """Send status update email to applicant"""
        from website.models import SiteSettings

        # Get site settings for the email template
        site_settings = SiteSettings.objects.first()

        status_display = dict(self.STATUS_CHOICES)[self.status]

        subject = f"Application Status Update - {self.position.title}"
        html_message = render_to_string('website/emails/application_status_update.html', {
            'application': self,
            'status_display': status_display,
            'site_settings': site_settings,
        })

        # Use the school's email utility function
        send_school_email(
            subject=subject,
            message=f"Your application status has been updated to: {status_display}",  # Plain text version
            recipient_list=[self.email],
            html_message=html_message,
            fail_silently=False,
        )
