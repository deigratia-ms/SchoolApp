from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import Subject, ClassRoom, ClassSubject, CourseMaterial, YouTubeVideo, Schedule


# Custom widget for file uploads with Cloudinary feedback
class CloudinaryFileWidget(forms.ClearableFileInput):
    def format_value(self, value):
        if value:
            # Check if it's a file with URL
            if hasattr(value, 'url'):
                url = value.url
                filename = getattr(value, 'name', 'Unknown file')
                # Extract just the filename from the path
                if '/' in filename:
                    filename = filename.split('/')[-1]

                # Check if it's stored in Cloudinary
                if 'cloudinary.com' in url:
                    return format_html(
                        '<div style="margin: 10px 0; padding: 10px; background: #e8f5e8; border: 1px solid #4caf50; border-radius: 4px;">'
                        '<span style="color: #2e7d32; font-weight: bold;">✅ Stored in Cloudinary: {}</span><br>'
                        '<a href="{}" target="_blank" style="color: #2e7d32; text-decoration: none;">🔗 View/Download</a>'
                        '<br><small style="color: #666;">Fast CDN delivery enabled</small>'
                        '</div>',
                        filename, url
                    )
                else:
                    return format_html(
                        '<div style="margin: 10px 0; padding: 10px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;">'
                        '<span style="color: #856404; font-weight: bold;">📁 Local file: {}</span><br>'
                        '<a href="{}" target="_blank" style="color: #856404; text-decoration: none;">🔗 View/Download</a>'
                        '</div>',
                        filename, url
                    )
        return super().format_value(value)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code', 'description')
    list_filter = ('created_at',)


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'section', 'capacity', 'class_teacher')
    search_fields = ('name', 'section')
    list_filter = ('capacity',)


@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = ('subject', 'classroom', 'teacher')
    search_fields = ('subject__name', 'classroom__name', 'teacher__user__username')
    list_filter = ('subject', 'classroom')
    filter_horizontal = ('students',)


# Custom form for CourseMaterial with better file handling
class CourseMaterialAdminForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = '__all__'
        widgets = {
            'file': CloudinaryFileWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].help_text = (
            "Upload files (PDF, Word, PowerPoint, images, etc.). "
            "Maximum file size: 10MB. Files are automatically uploaded to Cloudinary for fast, reliable access."
        )


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    form = CourseMaterialAdminForm
    list_display = ('title', 'class_subject', 'created_by', 'created_at')
    search_fields = ('title', 'description', 'class_subject__subject__name')
    list_filter = ('created_at', 'class_subject__subject')
    date_hierarchy = 'created_at'


@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_subject', 'is_general', 'created_by', 'created_at')
    search_fields = ('title', 'description', 'youtube_url')
    list_filter = ('is_general', 'created_at', 'class_subject__subject')
    date_hierarchy = 'created_at'


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('class_subject', 'day_of_week', 'start_time', 'end_time')
    search_fields = ('class_subject__subject__name', 'class_subject__classroom__name')
    list_filter = ('day_of_week',)