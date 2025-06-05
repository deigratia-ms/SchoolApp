from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Teacher, Student, Parent, StaffMember, SchoolSettings,
    IDCardTemplate, IDCard, AdmissionLetterTemplate, AdmissionLetter
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_verified', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'profile_picture')}),
        ('Permissions', {'fields': ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'department', 'qualification')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'employee_id', 'department')
    list_filter = ('department',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'status', 'grade', 'section', 'is_repeating', 'years_in_current_grade', 'last_promoted_date')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'student_id')
    list_filter = ('status', 'is_repeating', 'grade', 'section')
    fieldsets = (
        ('Student Information', {
            'fields': ('user', 'student_id', 'date_of_birth', 'guardian_name', 'emergency_contact')
        }),
        ('Academic Information', {
            'fields': ('grade', 'section')
        }),
        ('Academic Progression', {
            'fields': ('status', 'is_repeating', 'years_in_current_grade', 'last_promoted_date')
        }),
        ('Additional Information', {
            'fields': ('additional_info',)
        }),
    )



@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('user', 'occupation', 'relationship')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'occupation')
    filter_horizontal = ('children',)


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'staff_type', 'department', 'position', 'date_joined')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'employee_id', 'department', 'position')
    list_filter = ('staff_type', 'department', 'date_joined')
    fieldsets = (
        ('Staff Information', {
            'fields': ('user', 'employee_id', 'staff_type', 'date_joined')
        }),
        ('Position Details', {
            'fields': ('department', 'position', 'supervisor')
        }),
        ('Additional Information', {
            'fields': ('responsibilities',)
        }),
    )


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'email', 'phone')
    fieldsets = (
        ('School Information', {
            'fields': ('school_name', 'logo', 'address', 'phone', 'email', 'website')
        }),
        ('Email Configuration', {
            'fields': ('smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_tls')
        }),
    )


@admin.register(IDCardTemplate)
class IDCardTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'is_active', 'created_at', 'updated_at')
    list_filter = ('role', 'is_active')
    search_fields = ('name',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'role', 'is_active')
        }),
        ('Design', {
            'fields': ('header_text', 'background_image', 'card_width', 'card_height',
                       'text_color', 'background_color')
        }),
    )


@admin.register(IDCard)
class IDCardAdmin(admin.ModelAdmin):
    list_display = ('user', 'card_number', 'template', 'issue_date', 'expiry_date', 'is_active')
    list_filter = ('is_active', 'issue_date', 'expiry_date', 'template')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'card_number')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Card Information', {
            'fields': ('user', 'template', 'card_number', 'issue_date', 'expiry_date', 'is_active')
        }),
        ('Additional Information', {
            'fields': ('barcode_data', 'additional_info', 'created_at')
        }),
    )


@admin.register(AdmissionLetterTemplate)
class AdmissionLetterTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'header_text')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Content', {
            'fields': ('header_text', 'body_template', 'footer_text')
        }),
        ('Signature', {
            'fields': ('signature_image', 'signatory_name', 'signatory_position')
        }),
    )


@admin.register(AdmissionLetter)
class AdmissionLetterAdmin(admin.ModelAdmin):
    list_display = ('student', 'reference_number', 'admission_date', 'academic_year',
                    'grade_admitted', 'is_printed', 'created_at')
    list_filter = ('is_printed', 'admission_date', 'academic_year', 'grade_admitted')
    search_fields = ('student__user__email', 'student__user__first_name', 'student__user__last_name',
                     'reference_number', 'academic_year', 'grade_admitted')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Letter Information', {
            'fields': ('student', 'template', 'reference_number', 'admission_date',
                       'academic_year', 'grade_admitted', 'section_admitted')
        }),
        ('Fee Information', {
            'fields': ('fee_details',)
        }),
        ('Additional Information', {
            'fields': ('additional_info', 'is_printed', 'created_at')
        }),
    )
