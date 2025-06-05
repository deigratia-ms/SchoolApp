from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django import forms
from tinymce.widgets import TinyMCE

from .models_career import JobPosition, JobApplication

# Create a custom form for JobPosition with TinyMCE widget
class JobPositionAdminForm(forms.ModelForm):
    class Meta:
        model = JobPosition
        fields = '__all__'
        widgets = {
            'description': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'responsibilities': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'qualifications': TinyMCE(attrs={'cols': 80, 'rows': 30}),
        }

@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    form = JobPositionAdminForm
    list_display = ('title', 'department', 'job_type', 'location', 'application_deadline', 'days_until_deadline', 'is_active', 'applications_count')
    list_filter = ('department', 'job_type', 'is_active')
    search_fields = ('title', 'description', 'responsibilities', 'qualifications')
    date_hierarchy = 'date_posted'
    readonly_fields = ('date_posted',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'department', 'job_type', 'location', 'is_active')
        }),
        ('Job Details', {
            'fields': ('description', 'responsibilities', 'qualifications', 'salary_range')
        }),
        ('Dates', {
            'fields': ('application_deadline', 'date_posted')
        }),
    )

    def days_until_deadline(self, obj):
        if obj.application_deadline < timezone.now().date():
            return format_html('<span style="color: red;">Expired</span>')
        delta = obj.application_deadline - timezone.now().date()
        return format_html('<span style="color: green;">{} days</span>', delta.days)
    days_until_deadline.short_description = 'Deadline'

    def applications_count(self, obj):
        count = obj.applications.count()
        url = reverse('admin:website_jobapplication_changelist') + f'?position__id__exact={obj.id}'
        return format_html('<a href="{}">{} applications</a>', url, count)
    applications_count.short_description = 'Applications'

# Create a custom form for JobApplication with TinyMCE widget
class JobApplicationAdminForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = '__all__'
        widgets = {
            'cover_letter': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'admin_notes': TinyMCE(attrs={'cols': 80, 'rows': 20}),
            'admin_feedback': TinyMCE(attrs={'cols': 80, 'rows': 20}),
        }

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    form = JobApplicationAdminForm
    list_display = ('applicant_name', 'position', 'status', 'date_applied', 'has_resume', 'has_additional_document')
    list_filter = ('status', 'position', 'date_applied')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'position__title')
    date_hierarchy = 'date_applied'
    readonly_fields = ('date_applied', 'resume_link', 'additional_document_link')
    fieldsets = (
        ('Applicant Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'address')
        }),
        ('Application Details', {
            'fields': ('position', 'cover_letter', 'resume', 'resume_link', 'additional_document', 'additional_document_link')
        }),
        ('Status', {
            'fields': ('status', 'admin_notes', 'admin_feedback', 'date_applied', 'date_reviewed')
        }),
    )

    def applicant_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    applicant_name.short_description = 'Applicant'

    def has_resume(self, obj):
        return bool(obj.resume)
    has_resume.boolean = True
    has_resume.short_description = 'Resume'

    def has_additional_document(self, obj):
        return bool(obj.additional_document)
    has_additional_document.boolean = True
    has_additional_document.short_description = 'Add. Doc'

    def resume_link(self, obj):
        if obj.resume:
            return format_html('<a href="{}" target="_blank">View Resume</a>', obj.resume.url)
        return "No resume uploaded"
    resume_link.short_description = 'Resume Preview'

    def additional_document_link(self, obj):
        if obj.additional_document:
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.additional_document.url)
        return "No additional document uploaded"
    additional_document_link.short_description = 'Additional Document Preview'

    def save_model(self, request, obj, form, change):
        # If status is changed, update the date_reviewed
        if change and 'status' in form.changed_data:
            obj.date_reviewed = timezone.now()

            # Send status update email if status is changed to something other than 'pending'
            if obj.status != 'pending':
                obj.send_status_update_email()

        super().save_model(request, obj, form, change)
