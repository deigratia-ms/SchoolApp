from django.contrib import admin
from .models import Message, Announcement, Event, Notification

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'recipient__username', 'subject', 'content')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'read_at')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_type', 'is_active', 'created_by', 'created_at')
    list_filter = ('target_type', 'is_active', 'created_at')
    search_fields = ('title', 'content', 'created_by__username')
    date_hierarchy = 'created_at'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'start_date', 'end_date', 'is_school_wide', 'show_on_website', 'created_by')
    list_filter = ('event_type', 'is_school_wide', 'show_on_website', 'start_date')
    search_fields = ('title', 'description', 'location', 'created_by__username')
    date_hierarchy = 'start_date'
    list_editable = ('show_on_website',)

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'event_type')
        }),
        ('Date & Time', {
            'fields': ('start_date', 'end_date', 'all_day', 'start_time', 'end_time')
        }),
        ('Target Audience', {
            'fields': ('is_school_wide', 'specific_class', 'specific_subject')
        }),
        ('Location', {
            'fields': ('location', 'is_virtual', 'virtual_link')
        }),
        ('Website Integration', {
            'fields': ('show_on_website', 'attachment'),
            'description': 'If checked, this event will also be displayed on the public website.'
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'read_at')