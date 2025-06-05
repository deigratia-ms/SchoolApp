from django.db import models
from django.conf import settings
from users.models import Teacher, Student

class Subject(models.Model):
    """
    Model to store subjects taught in the school.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassRoom(models.Model):
    """
    Model to store classes (e.g., Grade 1A, Grade 2B, etc.).
    """
    name = models.CharField(max_length=50)
    section = models.CharField(max_length=10, blank=True, null=True)
    grade_level = models.IntegerField(default=0, help_text="Grade level (e.g., 1 for Grade 1)")
    capacity = models.PositiveIntegerField(default=30)
    class_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        related_name='class_teacher_of',
        blank=True,
        null=True
    )
    students = models.ManyToManyField('users.Student', related_name='course_classrooms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Class Rooms"

    def __str__(self):
        return f"{self.name} {self.section}" if self.section else self.name

    def get_students(self):
        """
        Returns all students associated with this classroom.
        Used by dashboard views to retrieve students for reports and analytics.
        """
        return self.students.all()


class ClassSubject(models.Model):
    """
    Model to associate subjects with classes and teachers.
    A subject can be taught in multiple classes by different teachers.
    """
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='classes')
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        related_name='teaching_subjects',
        null=True,
        blank=True
    )
    students = models.ManyToManyField(Student, related_name='enrolled_subjects', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('classroom', 'subject')
        verbose_name_plural = "Class Subjects"

    def __str__(self):
        teacher_name = f"taught by {self.teacher.user.username}" if self.teacher else "no teacher assigned"
        return f"{self.subject.name} for {self.classroom.name} {teacher_name}"


class CourseMaterial(models.Model):
    """
    Model to store course materials uploaded by teachers for specific subjects.
    Can include both rich text notes and file attachments.
    """
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True, help_text="Rich text content for notes")
    file = models.FileField(upload_to='course_materials/', blank=True, null=True)
    is_draft = models.BooleanField(default=False, help_text="Save as draft before publishing")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_materials')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if not self.class_subject or not self.class_subject.subject:
            return f"{self.title} - No subject assigned"
        return f"{self.title} - {self.class_subject.subject.name}"

    @property
    def has_content(self):
        """Check if the material has rich text content"""
        return bool(self.content and self.content.strip())

    @property
    def has_file(self):
        """Check if the material has a file attachment"""
        return bool(self.file)


class YouTubeVideo(models.Model):
    """
    Model to store YouTube videos embedded by teachers for specific subjects.
    """
    class_subject = models.ForeignKey(
        ClassSubject,
        on_delete=models.CASCADE,
        related_name='videos',
        null=True,  # Allow null for general videos
        blank=True  # Allow blank in forms
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    youtube_url = models.URLField()
    is_general = models.BooleanField(default=False)  # If True, the video is for all classes
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_videos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.is_general and self.class_subject:
            raise ValidationError("General videos should not be associated with a specific class subject")
        if not self.is_general and not self.class_subject:
            raise ValidationError("Non-general videos must be associated with a class subject")

    def __str__(self):
        if self.is_general or not self.class_subject:
            return f"{self.title} - General"
        return f"{self.title} - {self.class_subject.subject.name}"


class Schedule(models.Model):
    """
    Model to store class schedules for subjects.
    """
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=(
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ))
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ('class_subject', 'day_of_week', 'start_time')

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time}-{self.end_time} - {self.class_subject}"