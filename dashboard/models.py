from django.db import models
from django.conf import settings

class DashboardPreference(models.Model):
    """
    Model to store user preferences for dashboard layout and appearance.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_preference')

    # Theme preferences
    theme = models.CharField(max_length=50, default='default')
    color_scheme = models.CharField(max_length=50, default='navy')
    sidebar_collapsed = models.BooleanField(default=False)

    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    assignment_notifications = models.BooleanField(default=True)
    message_notifications = models.BooleanField(default=True)
    grade_notifications = models.BooleanField(default=True)
    attendance_notifications = models.BooleanField(default=True)

    # Dashboard layout
    widgets_order = models.JSONField(default=dict)
    hidden_widgets = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Dashboard Preferences"


class Widget(models.Model):
    """
    Model to define available widgets for dashboards.
    """
    class WidgetType(models.TextChoices):
        CALENDAR = 'CALENDAR', 'Calendar'
        ASSIGNMENTS = 'ASSIGNMENTS', 'Assignments'
        GRADES = 'GRADES', 'Grades'
        ATTENDANCE = 'ATTENDANCE', 'Attendance'
        MESSAGES = 'MESSAGES', 'Messages'
        ANNOUNCEMENTS = 'ANNOUNCEMENTS', 'Announcements'
        SUBJECTS = 'SUBJECTS', 'Subjects'
        STUDENTS = 'STUDENTS', 'Students'
        TEACHERS = 'TEACHERS', 'Teachers'

    name = models.CharField(max_length=50)
    widget_type = models.CharField(max_length=20, choices=WidgetType.choices)
    description = models.TextField(blank=True, null=True)

    # Allowed for specific user roles
    visible_to_admin = models.BooleanField(default=True)
    visible_to_teacher = models.BooleanField(default=True)
    visible_to_student = models.BooleanField(default=True)
    visible_to_parent = models.BooleanField(default=True)

    default_position = models.PositiveIntegerField(default=0)
    default_size = models.CharField(max_length=20, default='medium')  # small, medium, large

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_widget_type_display()})"


class UserWidget(models.Model):
    """
    Model to store user-specific widget settings.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='widgets')
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE, related_name='user_widgets')

    position = models.PositiveIntegerField()
    size = models.CharField(max_length=20, default='medium')  # small, medium, large
    is_visible = models.BooleanField(default=True)

    # Additional custom settings (e.g., time range for calendar)
    settings = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'widget')
        ordering = ['position']

    def __str__(self):
        return f"{self.user.username}'s {self.widget.name} Widget"


class SidebarMenu(models.Model):
    """
    Model to define sidebar menu items for different user roles.
    """
    class UserRole(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'
        PARENT = 'PARENT', 'Parent'

    name = models.CharField(max_length=50)
    url = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')

    user_role = models.CharField(max_length=10, choices=UserRole.choices)
    order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user_role', 'order']

    def __str__(self):
        return f"{self.name} ({self.get_user_role_display()})"