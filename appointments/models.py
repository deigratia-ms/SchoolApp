from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import CustomUser, Parent

# Create your models here.

class AppointmentSettings(models.Model):
    school_name = models.CharField(max_length=255)

    # Time slot settings
    appointment_duration = models.IntegerField(default=30, help_text="Duration in minutes")
    day_start_time = models.TimeField(default='09:00', help_text="Start time for appointments")
    day_end_time = models.TimeField(default='15:00', help_text="End time for appointments")
    excluded_hours = models.JSONField(default=list, blank=True, help_text="Hours to exclude from slot generation (e.g., lunch breaks)")
    days_to_generate = models.IntegerField(default=14, help_text="Number of days to generate slots for")
    slot_start_date = models.DateField(null=True, blank=True, help_text="Start date for slot generation (defaults to today if not set)")
    slot_end_date = models.DateField(null=True, blank=True, help_text="End date for slot generation (defaults to start_date + days_to_generate if not set)")
    excluded_days = models.JSONField(
        default=list,  # We'll set [5, 6] in a data migration
        help_text="Days of week to exclude (0=Monday, 6=Sunday)"
    )
    auto_confirm_appointments = models.BooleanField(default=False, help_text="Automatically confirm appointments when booked")
    default_appointment_purpose = models.CharField(
        max_length=255,
        default="Termly One-on-One Appointment",
        help_text="Default purpose for new appointments"
    )

    # Email settings
    reminder_days = models.IntegerField(default=1, help_text="Days before appointment to send reminder")
    system_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Appointment Settings'
        verbose_name_plural = 'Appointment Settings'

    def clean(self):
        if self.day_start_time >= self.day_end_time:
            raise ValidationError('Start time must be before end time')

        # Validate slot generation dates
        if self.slot_start_date and self.slot_end_date:
            if self.slot_start_date > self.slot_end_date:
                raise ValidationError('Slot generation start date must be before or equal to end date')

        # Validate excluded hours format
        if self.excluded_hours:
            if not isinstance(self.excluded_hours, list):
                raise ValidationError('Excluded hours must be a list')
            for hour in self.excluded_hours:
                if not isinstance(hour, dict) or 'start' not in hour or 'end' not in hour:
                    raise ValidationError('Each excluded hour must have start and end times')

        # Validate excluded days format (only if excluded_days is not None/empty)
        if self.excluded_days is not None and self.excluded_days != []:
            if not isinstance(self.excluded_days, list):
                raise ValidationError('Excluded days must be a list')
            for day in self.excluded_days:
                if not isinstance(day, int) or day < 0 or day > 6:
                    raise ValidationError('Excluded days must be integers from 0 to 6')

    def save(self, *args, **kwargs):
        # Set default excluded days if none are set (before validation)
        if not self.excluded_days:
            self.excluded_days = [5, 6]  # Saturday and Sunday
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Appointment Settings'

class TimeSlot(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, help_text="If false, the slot is inactive and won't be shown to parents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.date} {self.start_time} - {self.end_time}"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time')

        # Check for overlapping slots
        overlapping = TimeSlot.objects.filter(
            date=self.date
        ).exclude(
            id=self.id  # exclude self when updating
        ).filter(
            models.Q(start_time__lt=self.end_time, end_time__gt=self.start_time)
        )

        if overlapping.exists():
            raise ValidationError('This time slot overlaps with another slot')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name='appointments')
    time_slot = models.ForeignKey('TimeSlot', on_delete=models.CASCADE)
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_sent = models.BooleanField(default=False)
    reminder_3days_sent = models.BooleanField(default=False)
    reminder_1day_sent = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.parent} - {self.time_slot}"

    def clean(self):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()

    def save(self, *args, **kwargs):
        # Track changes
        changes = []
        if self.pk:  # If this is an existing appointment
            old_appointment = Appointment.objects.get(pk=self.pk)

            # Check for status change
            if old_appointment.status != self.status:
                changes.append(f"Status changed from {old_appointment.get_status_display()} to {self.get_status_display()}")

            # Check for time slot change
            if old_appointment.time_slot != self.time_slot:
                old_date = old_appointment.time_slot.date.strftime("%A, %B %d, %Y")
                old_time = old_appointment.time_slot.start_time.strftime("%I:%M %p")
                new_date = self.time_slot.date.strftime("%A, %B %d, %Y")
                new_time = self.time_slot.start_time.strftime("%I:%M %p")
                changes.append(f"Time changed from {old_date} {old_time} to {new_date} {new_time}")

                # Mark old time slot as available and new one as unavailable
                old_appointment.time_slot.is_available = True
                old_appointment.time_slot.save()
                self.time_slot.is_available = False
                self.time_slot.save()

            # Check for purpose change
            if old_appointment.purpose != self.purpose:
                changes.append("Purpose of the appointment was updated")

            # If there are changes, send notification
            if changes:
                try:
                    super().save(*args, **kwargs)  # Save first to ensure all changes are applied
                    from .notifications import send_appointment_update
                    send_appointment_update(self, changes)
                except Exception as e:
                    print(f"Failed to send appointment update notification: {e}")
            else:
                super().save(*args, **kwargs)
        else:  # New appointment
            if self.time_slot:
                self.time_slot.is_available = False
                self.time_slot.save()
            super().save(*args, **kwargs)


class AppointmentRequest(models.Model):
    """
    Model for parents to request custom appointment dates/times that need approval
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('scheduled', 'Scheduled'),
    ]

    parent = models.ForeignKey('users.Parent', on_delete=models.CASCADE, related_name='appointment_requests')
    requested_date = models.DateField()
    requested_start_time = models.TimeField()
    requested_end_time = models.TimeField()
    purpose = models.TextField()
    reason_for_custom_time = models.TextField(help_text="Why do you need a custom appointment time?")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes for approval/rejection")
    reviewed_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_appointment_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # If approved, this links to the created appointment
    created_appointment = models.OneToOneField('Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='from_request')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Appointment Request"
        verbose_name_plural = "Appointment Requests"

    def __str__(self):
        return f"{self.parent} - {self.requested_date} {self.requested_start_time} ({self.status})"

    def clean(self):
        if self.requested_start_time >= self.requested_end_time:
            raise ValidationError('End time must be after start time')

        # Check if requested date is in the past
        if self.requested_date < timezone.now().date():
            raise ValidationError('Cannot request appointments for past dates')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
