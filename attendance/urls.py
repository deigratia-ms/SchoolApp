from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Attendance Records
    path('', views.attendance_home, name='home'),
    path('take/', views.take_attendance, name='take_attendance'),
    path('take/<int:classroom_id>/', views.take_class_attendance, name='take_class_attendance'),
    path('records/', views.attendance_records, name='records'),
    path('records/<int:record_id>/', views.record_detail, name='record_detail'),
    path('records/<int:record_id>/edit/', views.edit_record, name='edit_record'),
    path('records/<int:record_id>/delete/', views.delete_record, name='delete_record'),
    
    # Student Attendance
    path('student/<int:student_id>/', views.student_attendance, name='student_attendance'),
    path('attendance-status/<int:student_attendance_id>/edit/', views.edit_attendance_status, name='edit_attendance_status'),
    
    # Attendance Reports
    path('reports/', views.attendance_reports, name='reports'),
    path('reports/generate/<int:student_id>/', views.generate_report, name='generate_report'),
    path('reports/export/', views.export_report, name='export_report'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('reports/<int:report_id>/print/', views.print_report, name='print_report'),
    
    # Class Reports
    path('reports/class/<int:classroom_id>/', views.class_report, name='class_report'),
    
    # Notifications
    path('notifications/', views.attendance_notifications, name='notifications'),
    path('notifications/create/', views.create_notification, name='create_notification'),
    path('notifications/<int:notification_id>/send/', views.send_notification, name='send_notification'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    
    # Teacher Views
    path('teacher/', views.teacher_attendance_dashboard, name='teacher_dashboard'),
    path('teacher/classes/', views.teacher_classes, name='teacher_classes'),
    
    # Student Views
    path('my-attendance/', views.my_attendance, name='my_attendance'),
    
    # Parent Views
    path('parent/', views.parent_children_attendance, name='parent_children_attendance'),
    path('parent/child/<int:student_id>/', views.parent_child_attendance, name='parent_child_attendance'),
]