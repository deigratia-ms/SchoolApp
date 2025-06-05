from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Classes
    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.create_class, name='create_class'),
    path('classes/<int:class_id>/', views.class_detail, name='class_detail'),
    path('classes/<int:class_id>/edit/', views.edit_class, name='edit_class'),
    path('classes/<int:class_id>/delete/', views.delete_class, name='delete_class'),
    path('classes/<int:class_id>/assign-teacher/', views.assign_class_teacher, name='assign_class_teacher'),
    
    # Subjects
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.create_subject, name='create_subject'),
    path('subjects/<int:subject_id>/', views.subject_detail, name='subject_detail'),
    path('subjects/<int:subject_id>/edit/', views.edit_subject, name='edit_subject'),
    path('subjects/<int:subject_id>/delete/', views.delete_subject, name='delete_subject'),
    
    # Class Subjects (linking classes, subjects, and teachers)
    path('class-subjects/', views.class_subject_list, name='class_subject_list'),
    path('class-subjects/create/', views.create_class_subject, name='create_class_subject'),
    path('class-subjects/<int:class_subject_id>/', views.class_subject_detail, name='class_subject_detail'),
    path('class-subjects/<int:class_subject_id>/edit/', views.edit_class_subject, name='edit_class_subject'),
    path('class-subjects/<int:class_subject_id>/delete/', views.delete_class_subject, name='delete_class_subject'),
    path('class-subjects/<int:class_subject_id>/students/', views.manage_class_students, name='manage_class_students'),
    
    # Course Materials
    path('materials/', views.material_list, name='material_list'),
    path('materials/create/', views.create_material, name='create_material'),
    path('materials/<int:material_id>/', views.material_detail, name='material_detail'),
    path('materials/<int:material_id>/edit/', views.edit_material, name='edit_material'),
    path('materials/<int:material_id>/delete/', views.delete_material, name='delete_material'),
    path('materials/manage/', views.manage_materials, name='manage_materials'),
    
    # YouTube Videos
    path('videos/', views.video_list, name='video_list'),
    path('videos/create/', views.create_video, name='create_video'),
    path('videos/<int:video_id>/', views.video_detail, name='video_detail'),
    path('videos/<int:video_id>/edit/', views.edit_video, name='edit_video'),
    path('videos/<int:video_id>/delete/', views.delete_video, name='delete_video'),
    
    # Schedule
    path('schedule/', views.schedule_list, name='schedule_list'),
    path('schedule/create/', views.create_schedule, name='create_schedule'),
    path('schedule/<int:schedule_id>/edit/', views.edit_schedule, name='edit_schedule'),
    path('schedule/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),
    
    # Advanced Admin Operations
    path('subjects/apply-to-all/', views.apply_subject_to_all, name='apply_subject_to_all'),
    path('subjects/bulk-apply-to-all/', views.bulk_apply_subjects_to_all, name='bulk_apply_subjects_to_all'),
    path('classes/bulk-assign-teacher/', views.bulk_assign_teacher, name='bulk_assign_teacher'),
    path('classes/bulk-add-subject/', views.bulk_add_subject, name='bulk_add_subject'),
    # Original URL pattern
    path('subjects/<int:subject_id>/assigned-classes/', 
         views.get_subject_assigned_classes, 
         name='get_subject_assigned_classes'),
    
    # Add alternative URL pattern to match the JavaScript fetch call with a more specific path
    # to avoid conflict with the class_subject_list pattern
    path('api/class-subjects/', views.get_class_subjects_by_query, name='get_class_subjects_by_query'),
    # API endpoint to get subjects for a specific class
    path('api/classes/<int:class_id>/subjects/', views.get_class_subjects, name='get_class_subjects'),
    
    # Student Details
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
]
