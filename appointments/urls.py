from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # Main URLs
    path('', views.parent_dashboard, name='parent_dashboard'),  # Changed to redirect to parent dashboard
    path('book/', views.book_appointment, name='book_appointment'),
    path('select-time/<str:date>/', views.select_time_slot, name='select_time_slot'),
    path('preview/<int:slot_id>/', views.preview_appointment, name='preview_appointment'),
    path('appointment/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('appointment/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),

    # Admin URLs
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/settings/', views.manage_settings, name='manage_settings'),
    path('admin/generate-slots/', views.generate_time_slots, name='generate_time_slots'),
    path('admin/time-slots/', views.manage_time_slots, name='manage_time_slots'),
    path('admin/time-slots/<int:slot_id>/delete/', views.delete_time_slot, name='delete_time_slot'),
    path('admin/time-slots/bulk-action/', views.bulk_time_slot_action, name='bulk_time_slot_action'),
    path('admin/appointment/<int:appointment_id>/status/', views.update_appointment_status, name='update_appointment_status'),
    path('admin/create-appointment/', views.create_appointment, name='create_appointment'),
    path('admin/appointments/', views.appointment_list, name='appointment_list'),
    path('admin/appointments/export/', views.export_appointments, name='export_appointments'),

    # System inactive view
    path('inactive/', views.system_inactive, name='system_inactive'),
]
