from django.db import models
from django.conf import settings
from users.models import Student, Teacher
from courses.models import ClassRoom

class AttendanceRecord(models.Model):
    """
    Model to store attendance records for a specific date and class.
    """
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    taken_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='attendance_taken')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)
    excused_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('classroom', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"Attendance for {self.classroom} on {self.date}"


class AttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', 'Present'
    ABSENT = 'ABSENT', 'Absent'
    LATE = 'LATE', 'Late'
    EXCUSED = 'EXCUSED', 'Excused Absence'


class StudentAttendance(models.Model):
    """
    Model to store attendance status for individual students.
    """
    attendance_record = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name='student_attendance')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=10, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    remarks = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('attendance_record', 'student')
    
    def __str__(self):
        return f"{self.student.user.username}: {self.status} on {self.attendance_record.date}"


class AttendanceReport(models.Model):
    """
    Model to store aggregated attendance reports for a specific period.
    """
    class ReportPeriod(models.TextChoices):
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
        TERMLY = 'TERMLY', 'Termly'
        YEARLY = 'YEARLY', 'Yearly'

    REPORT_TYPES = [
        ('DAILY', 'Daily Report'),
        ('WEEKLY', 'Weekly Report'),
        ('MONTHLY', 'Monthly Report'),
        ('TERMLY', 'Termly Report'),
        ('YEARLY', 'Yearly Report'),
        ('CUSTOM', 'Custom Period Report'),
    ]
    
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='attendance_reports')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_reports', null=True, blank=True)
    period_type = models.CharField(max_length=10, choices=ReportPeriod.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Aggregated statistics
    total_days = models.PositiveIntegerField(default=0)
    days_present = models.PositiveIntegerField(default=0)
    days_absent = models.PositiveIntegerField(default=0)
    days_late = models.PositiveIntegerField(default=0)
    days_excused = models.PositiveIntegerField(default=0)
    
    # If student is null, this is a class-wide report
    is_class_report = models.BooleanField(default=False)
    
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='generated_attendance_reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        target = self.classroom.name if self.is_class_report else self.student.user.username
        return f"{self.period_type} Attendance Report for {target} ({self.start_date} to {self.end_date})"
    
    @property
    def attendance_percentage(self):
        """Calculate attendance percentage"""
        if self.total_days == 0:
            return 0
        return (self.days_present / self.total_days) * 100


class AttendanceNotification(models.Model):
    """
    Model to store notifications for excessive absences.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_notifications')
    message = models.TextField()
    sent_to_parent = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attendance Notification for {self.student.user.username} on {self.created_at.date()}"