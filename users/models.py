from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    instead of username for authentication.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if email:
            email = self.normalize_email(email)
            # Check if email exists and is not None
            if self.filter(email=email).exists():
                raise ValueError('A user with that email already exists.')

        # Allow email to be None only for students
        if not email and extra_fields.get('role') != 'STUDENT':
            raise ValueError('The Email field must be set for non-student users.')

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    """
    Custom User model to handle all users in the system.
    Each user will have a specific role.
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        TEACHER = 'TEACHER', _('Teacher')
        STUDENT = 'STUDENT', _('Student')
        PARENT = 'PARENT', _('Parent')
        ACCOUNTANT = 'ACCOUNTANT', _('Accountant')
        SECRETARY = 'SECRETARY', _('Secretary')
        RECEPTIONIST = 'RECEPTIONIST', _('Receptionist')
        SECURITY = 'SECURITY', _('Security')
        JANITOR = 'JANITOR', _('Janitor')
        COOK = 'COOK', _('Cook')
        CLEANER = 'CLEANER', _('Cleaner')
        STAFF = 'STAFF', _('Other Staff')

    # Remove username field and use email as primary identifier
    username = None
    email = models.EmailField(_('email address'), unique=True)  # Keep email unique
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.STUDENT)
    is_verified = models.BooleanField(default=True)  # All users are verified by default
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_parent(self):
        return self.role == self.Role.PARENT

    @property
    def is_accountant(self):
        return self.role == self.Role.ACCOUNTANT

    @property
    def is_secretary(self):
        return self.role == self.Role.SECRETARY

    @property
    def is_receptionist(self):
        return self.role == self.Role.RECEPTIONIST

    @property
    def is_security(self):
        return self.role == self.Role.SECURITY

    @property
    def is_janitor(self):
        return self.role == self.Role.JANITOR

    @property
    def is_cook(self):
        return self.role == self.Role.COOK

    @property
    def is_cleaner(self):
        return self.role == self.Role.CLEANER

    @property
    def is_staff_member(self):
        return self.role == self.Role.STAFF

    @property
    def is_non_teaching_staff(self):
        """Check if user is any type of non-teaching staff"""
        return self.role in [
            self.Role.ACCOUNTANT, self.Role.SECRETARY, self.Role.RECEPTIONIST,
            self.Role.SECURITY, self.Role.JANITOR, self.Role.COOK,
            self.Role.CLEANER, self.Role.STAFF
        ]

    @property
    def student(self):
        """Convenience property to access student_profile with intuitive name"""
        if self.is_student:
            return self.student_profile
        return None

    @property
    def teacher(self):
        """Convenience property to access teacher_profile with intuitive name"""
        if self.is_teacher:
            return self.teacher_profile
        return None

    @property
    def parent(self):
        """Convenience property to access parent_profile with intuitive name"""
        if self.is_parent:
            return self.parent_profile
        return None

    @property
    def staff(self):
        """Convenience property to access staff_profile with intuitive name"""
        if self.is_non_teaching_staff:
            return self.staff_profile
        return None


class Teacher(models.Model):
    """
    Teacher model extending the CustomUser for teacher-specific data.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='teacher_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    qualification = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Teacher: {self.user.get_full_name() or self.user.email}"


class Student(models.Model):
    """
    Student model extending the CustomUser for student-specific data.
    """
    # Status choices for tracking student enrollment status
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        GRADUATED = 'GRADUATED', _('Graduated')
        TRANSFERRED = 'TRANSFERRED', _('Transferred')
        WITHDRAWN = 'WITHDRAWN', _('Withdrawn')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        ON_LEAVE = 'ON_LEAVE', _('On Leave')

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)  # For student login
    pin = models.CharField(max_length=5)  # 5-digit PIN for login
    date_of_birth = models.DateField(blank=True, null=True)
    grade = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)
    grade = models.ForeignKey('courses.Classroom', on_delete=models.SET_NULL, null=True, blank=True, related_name='grade_students')
    section = models.CharField(max_length=10, null=True, blank=True)
    additional_info = models.JSONField(blank=True, null=True)  # For storing address and other extra info
    chat_enabled = models.BooleanField(default=True, help_text="If disabled, student cannot send or receive messages (parental control)")

    # Fields for managing promotion, repetition, and completion
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current enrollment status of the student"
    )
    is_repeating = models.BooleanField(
        default=False,
        help_text="If True, student will repeat the current grade in the next academic year"
    )
    years_in_current_grade = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of years student has spent in the current grade"
    )
    last_promoted_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when student was last promoted to a new grade"
    )

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def save(self, *args, **kwargs):
        # Check if years_in_current_grade should be reset
        if self.pk is not None:
            old_instance = Student.objects.get(pk=self.pk)
            # If grade has changed and not a new record, reset years count
            if old_instance.grade != self.grade and self.grade is not None:
                self.years_in_current_grade = 1
                import datetime
                self.last_promoted_date = datetime.date.today()

        super().save(*args, **kwargs)

        # Update classroom students when grade is changed
        if self.grade:
            # Add the Student object (self) to the classroom's students collection
            self.grade.students.add(self)

            # Add the student to all ClassSubjects associated with the classroom
            from courses.models import ClassSubject  # Import here to avoid circular dependency

            # First, remove student from all subjects not associated with their current grade
            class_subjects_all = ClassSubject.objects.filter(students=self)
            for class_subject in class_subjects_all:
                if class_subject.classroom.id != self.grade.id:
                    class_subject.students.remove(self)

            # Then add student to all subjects in their current grade
            class_subjects = ClassSubject.objects.filter(classroom=self.grade)
            for class_subject in class_subjects:
                class_subject.students.add(self)

    class Meta:
        unique_together = ['student_id', 'pin']  # Ensure combination is unique


class Parent(models.Model):
    """
    Parent model extending the CustomUser for parent-specific data.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='parent_profile')
    children = models.ManyToManyField(Student, related_name='parents')
    occupation = models.CharField(max_length=100, blank=True, null=True)
    relationship = models.CharField(max_length=50, default='Parent')  # Parent, Guardian, etc.

    def __str__(self):
        return f"Parent: {self.user.get_full_name() or self.user.email}"


class StaffMember(models.Model):
    """
    StaffMember model extending the CustomUser for non-teaching staff-specific data.
    This includes roles like accountant, secretary, receptionist, security, etc.
    """
    class StaffType(models.TextChoices):
        ADMINISTRATIVE = 'ADMINISTRATIVE', _('Administrative')
        SUPPORT = 'SUPPORT', _('Support')
        MAINTENANCE = 'MAINTENANCE', _('Maintenance')
        SECURITY = 'SECURITY', _('Security')
        FOOD_SERVICE = 'FOOD_SERVICE', _('Food Service')
        OTHER = 'OTHER', _('Other')

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='staff_profile')
    employee_id = models.CharField(max_length=20, unique=True)
    staff_type = models.CharField(max_length=20, choices=StaffType.choices, default=StaffType.ADMINISTRATIVE)
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    date_joined = models.DateField(default=timezone.now)
    supervisor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    responsibilities = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_role_display()}: {self.user.get_full_name() or self.user.email}"

    @property
    def role_name(self):
        """Return the specific role name from the user model"""
        return self.user.get_role_display()

    class Meta:
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"


class SchoolSettings(models.Model):
    """
    Model to store school-wide settings like name, logo, etc.
    """
    school_name = models.CharField(max_length=255, default='Ricas School Management System')
    logo = models.ImageField(upload_to='school_logo/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    principal_name = models.CharField(max_length=100, blank=True, null=True)
    academic_year = models.CharField(max_length=20, blank=True, null=True)

    # SMTP settings for email notifications
    smtp_host = models.CharField(max_length=255, blank=True, null=True)
    smtp_port = models.PositiveIntegerField(blank=True, null=True)
    smtp_username = models.CharField(max_length=255, blank=True, null=True)
    smtp_password = models.CharField(max_length=255, blank=True, null=True)
    smtp_use_tls = models.BooleanField(default=True)

    # Notification settings
    notify_assignments = models.BooleanField(default=True)
    notify_grades = models.BooleanField(default=True)
    notify_attendance = models.BooleanField(default=True)
    notify_events = models.BooleanField(default=True)

    # Communication settings
    enable_messaging = models.BooleanField(default=True, help_text="Enable messaging system across the platform")
    enable_student_to_student_chat = models.BooleanField(default=True, help_text="Allow students to message other students in their class")

    # Appearance settings
    primary_color = models.CharField(max_length=20, default='#4e73df')
    dark_mode = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "School Settings"

    def __str__(self):
        return self.school_name


class IDCardTemplate(models.Model):
    """
    Model to store ID card templates for different user roles.
    """
    ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
        ('PARENT', 'Parent'),
        ('ADMIN', 'Admin'),
    ]

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    background_image = models.ImageField(upload_to='id_card_templates/', blank=True, null=True)
    header_text = models.CharField(max_length=255, default="School ID Card")
    card_width = models.PositiveIntegerField(default=1013)  # Width in pixels (CR80 landscape)
    card_height = models.PositiveIntegerField(default=638)  # Height in pixels (CR80 landscape)
    text_color = models.CharField(max_length=20, default="#000000")  # Default black
    background_color = models.CharField(max_length=20, default="#FFFFFF")  # Default white
    header_color = models.CharField(max_length=20, default="#4e73df")  # Default blue
    footer_color = models.CharField(max_length=20, default="#f8f9fc")  # Default light gray
    use_curved_design = models.BooleanField(default=False)  # Whether to use curved elements like in the sample
    footer_text = models.TextField(blank=True, null=True, help_text="Custom text for card footer. Use {school_name}, {school_address}, {school_phone} as placeholders.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_role_display()}"

    class Meta:
        verbose_name = "ID Card Template"
        verbose_name_plural = "ID Card Templates"


class IDCard(models.Model):
    """
    Model to store generated ID cards for users.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='id_cards')
    template = models.ForeignKey(IDCardTemplate, on_delete=models.CASCADE)
    card_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    barcode_data = models.CharField(max_length=255, blank=True, null=True)  # Data for barcode/QR code
    additional_info = models.JSONField(blank=True, null=True)  # For any additional dynamic fields
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ID Card: {self.user.get_full_name()} ({self.card_number})"

    class Meta:
        verbose_name = "ID Card"
        verbose_name_plural = "ID Cards"


class AdmissionLetterTemplate(models.Model):
    """
    Model to store admission letter templates.
    """
    name = models.CharField(max_length=100)
    header_text = models.CharField(max_length=255, default="Admission Letter")
    body_template = models.TextField(help_text="Use placeholders like {student_name}, {grade}, etc.")
    footer_text = models.TextField(blank=True, null=True)
    signature_image = models.ImageField(upload_to='signatures/', blank=True, null=True)
    signatory_name = models.CharField(max_length=100, blank=True, null=True)
    signatory_position = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Admission Letter Template"
        verbose_name_plural = "Admission Letter Templates"


class AdmissionLetter(models.Model):
    """
    Model to store generated admission letters for students.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='admission_letters')
    template = models.ForeignKey(AdmissionLetterTemplate, on_delete=models.CASCADE)
    reference_number = models.CharField(max_length=50, unique=True)
    admission_date = models.DateField()
    academic_year = models.CharField(max_length=20)
    grade_admitted = models.CharField(max_length=20)
    section_admitted = models.CharField(max_length=20, blank=True, null=True)
    fee_details = models.TextField(blank=True, null=True)
    additional_info = models.JSONField(blank=True, null=True)  # For any additional dynamic fields
    is_printed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Admission Letter: {self.student.user.get_full_name()} ({self.reference_number})"

    class Meta:
        verbose_name = "Admission Letter"
        verbose_name_plural = "Admission Letters"

class ClassRoom(models.Model):
    """
    Model to represent a classroom
    """
    name = models.CharField(max_length=100)
    grade = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_classrooms')
    students = models.ManyToManyField('Student', related_name='classrooms', blank=True)

    def __str__(self):
        return f"{self.name} ({self.grade} - {self.section})"

    class Meta:
        verbose_name = "Classroom"
        verbose_name_plural = "Classrooms"
