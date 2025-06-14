from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard index - redirects to role-specific dashboard
    path('', views.index, name='index'),

    # Role-specific dashboards
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('parent/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/child/<int:child_id>/', views.parent_child_detail, name='parent_child_detail'),

    # Parent appointment and document management
    path('parent/request-appointment/', views.parent_request_appointment, name='parent_request_appointment'),
    path('parent/appointment-requests/', views.parent_appointment_requests, name='parent_appointment_requests'),
    path('parent/appointments/', views.parent_appointments, name='parent_appointments'),
    path('parent/upload-document/', views.parent_upload_document, name='parent_upload_document'),
    path('parent/documents/', views.parent_documents, name='parent_documents'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('receptionist/', views.receptionist_dashboard, name='receptionist_dashboard'),

    # Dashboard widgets
    path('widgets/', views.manage_widgets, name='manage_widgets'),
    path('widgets/toggle/<int:widget_id>/', views.toggle_widget, name='toggle_widget'),
    path('widgets/reorder/', views.reorder_widgets, name='reorder_widgets'),
    path('widgets/reset/', views.reset_widgets, name='reset_widgets'),
    path('widgets/size/', views.update_widget_size, name='update_widget_size'),
    path('widgets/remove/', views.remove_widget, name='remove_widget'),

    # Dashboard preferences
    path('preferences/', views.dashboard_preferences, name='preferences'),

    # Activity logs
    path('activity-log/', views.activity_log, name='activity_log'),

    # Admin-specific attendance tracking
    path('admin/attendance/', views.admin_attendance_overview, name='admin_attendance_overview'),
    path('admin/attendance/class/<int:class_id>/', views.admin_class_attendance, name='admin_class_attendance'),
    path('admin/attendance/student/<int:student_id>/', views.admin_student_attendance, name='admin_student_attendance'),
    path('admin/attendance/reports/', views.admin_attendance_reports, name='admin_attendance_reports'),

    # Admin-specific academic performance tracking
    path('admin/performance/', views.admin_performance_overview, name='admin_performance_overview'),
    path('admin/performance/class/<int:class_id>/', views.admin_class_performance, name='admin_class_performance'),
    path('admin/performance/student/<int:student_id>/', views.admin_student_performance, name='admin_student_performance'),
    path('admin/performance/comparison/', views.admin_performance_comparison, name='admin_performance_comparison'),
    path('admin/performance/trends/', views.admin_performance_trends, name='admin_performance_trends'),
    path('admin/reports/insights/', views.admin_report_insights, name='admin_report_insights'),

    # Parent-specific controls
    path('parent/child/<int:child_id>/toggle-chat/', views.toggle_child_chat, name='toggle_child_chat'),

    # Grading scales administration
    path('admin/grading/', views.admin_grading_scales, name='admin_grading_scales'),
    path('admin/grading/create/', views.admin_create_grading_scale, name='admin_create_grading_scale'),
    path('admin/grading/<int:scale_id>/', views.admin_edit_grading_scale, name='admin_edit_grading_scale'),
    path('admin/grading/<int:scale_id>/delete/', views.admin_delete_grading_scale, name='admin_delete_grading_scale'),
    path('admin/grading/<int:scale_id>/default/', views.admin_set_default_grading_scale, name='admin_set_default_grading_scale'),
    path('admin/grading/standard/', views.admin_create_standard_scale, name='admin_create_standard_scale'),

    # Assessment Weight Configuration
    path('admin/assessment-weights/', views.admin_assessment_weights, name='admin_assessment_weights'),
    path('admin/assessment-weights/create/', views.admin_create_assessment_weight, name='admin_create_assessment_weight'),
    path('admin/assessment-weights/<int:config_id>/', views.admin_edit_assessment_weight, name='admin_edit_assessment_weight'),
    path('admin/assessment-weights/<int:config_id>/delete/', views.admin_delete_assessment_weight, name='admin_delete_assessment_weight'),
    path('admin/assessment-weights/<int:config_id>/default/', views.admin_set_default_assessment_weight, name='admin_set_default_assessment_weight'),

    # Student promotion management
    path('admin/students/promotion/', views.admin_student_promotion, name='admin_student_promotion'),
    path('admin/activities/', views.admin_activities, name='admin_activities'),

    # Backup and Restore
    path('admin/backup/', views.backup_management, name='backup_management'),
    path('admin/backup/create/', views.backup_system, name='backup_system'),
    path('admin/backup/download/<str:filename>/', views.download_backup, name='download_backup'),
    path('admin/backup/delete/<str:filename>/', views.delete_backup, name='delete_backup'),
    path('admin/backup/upload-restore/', views.upload_restore_backup, name='upload_restore_backup'),
    path('admin/backup/progress/', views.backup_progress, name='backup_progress'),
]