from django.contrib import admin
from .models import AttendanceRecord, StudentAttendance, AttendanceReport, AttendanceNotification

class StudentAttendanceInline(admin.TabularInline):
    model = StudentAttendance
    extra = 0


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'date', 'taken_by', 'created_at')
    list_filter = ('date', 'classroom')
    search_fields = ('classroom__name', 'taken_by__user__username')
    date_hierarchy = 'date'
    inlines = [StudentAttendanceInline]


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'attendance_record', 'status', 'remarks')
    list_filter = ('status', 'attendance_record__date')
    search_fields = ('student__user__username', 'remarks', 'attendance_record__classroom__name')


@admin.register(AttendanceReport)
class AttendanceReportAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'student', 'period_type', 'start_date', 'end_date', 
                   'days_present', 'days_absent', 'days_late', 'attendance_percentage')
    list_filter = ('period_type', 'is_class_report', 'start_date')
    search_fields = ('classroom__name', 'student__user__username')
    date_hierarchy = 'generated_at'
    readonly_fields = ('attendance_percentage',)


@admin.register(AttendanceNotification)
class AttendanceNotificationAdmin(admin.ModelAdmin):
    list_display = ('student', 'sent_to_parent', 'is_read', 'created_at')
    list_filter = ('sent_to_parent', 'is_read', 'created_at')
    search_fields = ('student__user__username', 'message')
    date_hierarchy = 'created_at'