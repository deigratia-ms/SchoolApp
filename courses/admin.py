from django.contrib import admin
from .models import Subject, ClassRoom, ClassSubject, CourseMaterial, YouTubeVideo, Schedule

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


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
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