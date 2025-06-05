from django.db import models
from django.conf import settings
from courses.models import ClassSubject, ClassRoom

class Message(models.Model):
    """
    Model to store direct messages between users.
    """
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=255)
    content = models.TextField()
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sender_name = self.sender.username if self.sender else "Unknown"
        recipient_name = self.recipient.username if self.recipient else "Unknown"
        return f"Message from {sender_name} to {recipient_name}: {self.subject}"


class Announcement(models.Model):
    """
    Model to store announcements that can be targeted to specific users or groups.
    """
    class AnnouncementTarget(models.TextChoices):
        ALL = 'ALL', 'All Users'
        TEACHERS = 'TEACHERS', 'All Teachers'
        STUDENTS = 'STUDENTS', 'All Students'
        PARENTS = 'PARENTS', 'All Parents'
        SPECIFIC_CLASS = 'CLASS', 'Specific Class'
        SPECIFIC_USER = 'USER', 'Specific User'

    title = models.CharField(max_length=255)
    content = models.TextField()

    # Target audience
    target_type = models.CharField(max_length=10, choices=AnnouncementTarget.choices)

    # Optional targets (based on target_type)
    target_class = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='announcements', blank=True, null=True)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_announcements', blank=True, null=True)

    # Optional attachment
    attachment = models.FileField(upload_to='announcement_attachments/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} for {self.get_target_type_display()}"


class Event(models.Model):
    """
    Model to store school events (holidays, exams, sports days, etc.).
    """
    class EventType(models.TextChoices):
        HOLIDAY = 'HOLIDAY', 'Holiday'
        EXAM = 'EXAM', 'Examination'
        SPORTS = 'SPORTS', 'Sports Day'
        MEETING = 'MEETING', 'Meeting'
        ACTIVITY = 'ACTIVITY', 'Activity'
        OTHER = 'OTHER', 'Other'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=10, choices=EventType.choices)

    start_date = models.DateField()
    end_date = models.DateField()
    all_day = models.BooleanField(default=True)
    start_time = models.TimeField(blank=True, null=True)  # If not all_day
    end_time = models.TimeField(blank=True, null=True)    # If not all_day

    # Target audience
    is_school_wide = models.BooleanField(default=True)
    specific_class = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='events', blank=True, null=True)
    specific_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='events', blank=True, null=True)

    location = models.CharField(max_length=255, blank=True, null=True)

    # Virtual event settings
    is_virtual = models.BooleanField(default=False)
    virtual_link = models.URLField(blank=True, null=True)

    # Attachment
    attachment = models.FileField(upload_to='events/', blank=True, null=True)

    # Website integration
    show_on_website = models.BooleanField(default=False, help_text='If checked, this event will also be displayed on the public website')

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_events', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'start_time']

    def __str__(self):
        return f"{self.title} ({self.start_date})"


class Notification(models.Model):
    """
    Model to store notifications for users.
    """
    class NotificationType(models.TextChoices):
        ASSIGNMENT = 'ASSIGNMENT', 'Assignment'
        QUIZ = 'QUIZ', 'Quiz'
        GRADE = 'GRADE', 'Grade'
        ATTENDANCE = 'ATTENDANCE', 'Attendance'
        MESSAGE = 'MESSAGE', 'Message'
        ANNOUNCEMENT = 'ANNOUNCEMENT', 'Announcement'
        EVENT = 'EVENT', 'Event'
        OTHER = 'OTHER', 'Other'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)

    title = models.CharField(max_length=255)
    message = models.TextField()

    # Links to related objects
    related_assignment = models.ForeignKey('assignments.Assignment', on_delete=models.SET_NULL, blank=True, null=True, related_name='notifications')
    related_message = models.ForeignKey(Message, on_delete=models.SET_NULL, blank=True, null=True, related_name='notifications')
    related_announcement = models.ForeignKey(Announcement, on_delete=models.SET_NULL, blank=True, null=True, related_name='notifications')
    related_event = models.ForeignKey(Event, on_delete=models.SET_NULL, blank=True, null=True, related_name='notifications')

    # Add a link field for quick access
    link = models.CharField(max_length=255, blank=True, null=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_name = self.user.username if self.user else "Unknown"
        return f"{self.notification_type} notification for {user_name}: {self.title}"