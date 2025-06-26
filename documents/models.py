from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import CustomUser, Student, Parent

# Create your models here.

class DocumentCategory(models.Model):
    """
    Categories for different types of documents
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    required_for_admission = models.BooleanField(default=False)
    required_for_students = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Document Category"
        verbose_name_plural = "Document Categories"

    def __str__(self):
        return self.name


class DocumentUpload(models.Model):
    """
    Model for document uploads by students/parents
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('needs_revision', 'Needs Revision'),
    ]

    UPLOADED_BY_CHOICES = [
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('admin', 'Admin'),
    ]

    # Document details
    title = models.CharField(max_length=200)
    category = models.ForeignKey(DocumentCategory, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='documents/%Y/%m/')
    description = models.TextField(blank=True, null=True)

    # Ownership
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    uploaded_by_type = models.CharField(max_length=20, choices=UPLOADED_BY_CHOICES)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='uploaded_documents')

    # Status and review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes for approval/rejection")
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_documents')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Document Upload"
        verbose_name_plural = "Document Uploads"

    def __str__(self):
        return f"{self.title} - {self.get_owner_name()} ({self.status})"

    def get_owner_name(self):
        if self.student:
            return f"Student: {self.student.user.get_full_name()}"
        elif self.parent:
            return f"Parent: {self.parent.user.get_full_name()}"
        return "Unknown"

    @property
    def safe_file_size(self):
        """Get file size safely, handling Cloudinary storage"""
        if not self.file:
            return None
        try:
            # For Cloudinary, try to get size from the file field
            # If it fails, we'll return None
            if hasattr(self.file, 'size') and self.file.size:
                return self.file.size
            # For Cloudinary files, size might not be available
            return None
        except (FileNotFoundError, OSError, AttributeError):
            return None

    def clean(self):
        # Ensure either student or parent is set, but not both
        if not self.student and not self.parent:
            raise ValidationError('Either student or parent must be specified')
        if self.student and self.parent:
            raise ValidationError('Cannot specify both student and parent')


class AdmissionEnquiry(models.Model):
    """
    Model for tracking admission enquiries
    """
    STATUS_CHOICES = [
        ('new', 'New Enquiry'),
        ('contacted', 'Contacted'),
        ('scheduled', 'Visit Scheduled'),
        ('visited', 'Visited'),
        ('applied', 'Application Submitted'),
        ('admitted', 'Admitted'),
        ('declined', 'Declined'),
        ('closed', 'Closed'),
    ]

    PROGRAM_CHOICES = [
        ('toddler', 'Toddler Program'),
        ('primary', 'Primary Program'),
        ('elementary', 'Elementary Program'),
    ]

    # Enquirer details
    parent_name = models.CharField(max_length=200)
    parent_email = models.EmailField()
    parent_phone = models.CharField(max_length=20)

    # Child details
    child_name = models.CharField(max_length=200)
    child_age = models.PositiveIntegerField()
    child_dob = models.DateField(null=True, blank=True)

    # Programme interest
    program_of_interest = models.CharField(max_length=20, choices=PROGRAM_CHOICES)
    preferred_start_date = models.DateField(null=True, blank=True)

    # Enquiry details
    message = models.TextField(help_text="Parent's message or specific questions")
    how_did_you_hear = models.CharField(max_length=200, blank=True, null=True)

    # Status and follow-up
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_enquiries')
    admin_notes = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Admission Enquiry"
        verbose_name_plural = "Admission Enquiries"

    def __str__(self):
        return f"{self.parent_name} - {self.child_name} ({self.get_status_display()})"


class VisitorLog(models.Model):
    """
    Model for tracking school visitors
    """
    VISITOR_TYPE_CHOICES = [
        ('parent', 'Parent'),
        ('prospective_parent', 'Prospective Parent'),
        ('vendor', 'Vendor/Supplier'),
        ('official', 'Government Official'),
        ('contractor', 'Contractor'),
        ('guest', 'Guest Speaker'),
        ('other', 'Other'),
    ]

    PURPOSE_CHOICES = [
        ('meeting', 'Meeting'),
        ('school_tour', 'School Tour'),
        ('pickup_dropoff', 'Pickup/Drop-off'),
        ('delivery', 'Delivery'),
        ('maintenance', 'Maintenance'),
        ('inspection', 'Inspection'),
        ('event', 'School Event'),
        ('other', 'Other'),
    ]

    # Visitor details
    visitor_name = models.CharField(max_length=200)
    visitor_phone = models.CharField(max_length=20, blank=True, null=True)
    visitor_email = models.EmailField(blank=True, null=True)
    visitor_type = models.CharField(max_length=20, choices=VISITOR_TYPE_CHOICES)
    company_organization = models.CharField(max_length=200, blank=True, null=True)

    # Visit details
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    purpose_description = models.TextField(blank=True, null=True)
    person_to_meet = models.CharField(max_length=200, blank=True, null=True)

    # Visit timing
    check_in_time = models.DateTimeField(auto_now_add=True)
    expected_duration = models.PositiveIntegerField(help_text="Expected duration in minutes", null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    # Staff handling
    received_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_visitors')
    notes = models.TextField(blank=True, null=True)

    # Security
    id_verified = models.BooleanField(default=False)
    visitor_badge_issued = models.BooleanField(default=False)

    class Meta:
        ordering = ['-check_in_time']
        verbose_name = "Visitor Log"
        verbose_name_plural = "Visitor Logs"

    def __str__(self):
        return f"{self.visitor_name} - {self.check_in_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def is_checked_out(self):
        return self.check_out_time is not None

    @property
    def duration_minutes(self):
        if self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            return int(delta.total_seconds() / 60)
        return None
