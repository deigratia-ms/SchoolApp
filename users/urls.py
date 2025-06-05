from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Admin specific URLs
    path('', views.admin_login, name='admin_login'),  # /my-admin/
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),  # /my-admin/dashboard/
    
    # Authentication
    path('login/', views.custom_login, name='login'),
    path('student-login/', views.student_login, name='student_login'),
    path('teacher-login/', views.teacher_login, name='teacher_login'),
    path('parent-login/', views.parent_login, name='parent_login'),
    path('logout/', views.custom_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Admin views
    path('school-settings/', views.school_settings, name='school_settings'),
    path('school-settings/backup/', views.backup_settings, name='backup_settings'),
    path('school-settings/restore/', views.restore_settings, name='restore_settings'),
    path('school-settings/test-email/', views.test_email, name='test_email'),
    path('user-management/', views.user_management, name='user_management'),
    path('teacher-management/', views.teacher_management, name='teacher_management'),
    path('student-management/', views.student_management, name='student_management'),
    path('parent-management/', views.parent_management, name='parent_management'),
    path('create-user/', views.create_user, name='create_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    
    path('reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    
    # Password Reset - Using Django's built-in views with custom templates
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # PIN Reset for students
    path('request-pin-reset/', views.request_pin_reset, name='request_pin_reset'),
   
    
    # Admin
    path('my-admin/', views.admin_login, name='admin_login'),
    path('my-admin/dashboard/', views.admin_dashboard, name='admin_dashboard_home'),

    # Teacher registration
    path('register-teacher/', views.register_teacher, name='register_teacher'),
    
    # Student registration
    path('register-student/', views.register_student, name='register_student'),
    
    # Parent registration
    path('register-parent/', views.register_parent, name='register_parent'),
    path('link-parent-to-child/', views.link_parent_to_child, name='link_parent_to_child'),
    path('search-parent/', views.search_parent, name='search_parent'),
    path('unlink-parent-child/', views.unlink_parent_child, name='unlink_parent_child'),
    
    # ID Cards and Admission Letters - Original basic functions
    path('generate-id-card/<int:user_id>/', views.generate_id_card, name='generate_id_card'),
    path('generate-admission-letter/<int:student_id>/', views.generate_admission_letter, name='generate_admission_letter'),
    
    # ID Card Template Management
    path('id-card-templates/', views.id_card_template_list, name='id_card_template_list'),
    path('id-card-templates/create/', views.id_card_template_create, name='id_card_template_create'),
    path('id-card-templates/<int:template_id>/', views.id_card_template_detail, name='id_card_template_detail'),
    path('id-card-templates/<int:template_id>/update/', views.id_card_template_update, name='id_card_template_update'),
    path('id-card-templates/<int:template_id>/delete/', views.id_card_template_delete, name='id_card_template_delete'),
    
    # ID Card Management
    path('id-cards/', views.id_card_list, name='id_card_list'),
    path('id-cards/generate/', views.id_card_generate, name='id_card_generate'),
    path('id-cards/batch-generate/', views.id_card_batch_generate, name='id_card_batch_generate'),
    path('id-cards/<int:card_id>/', views.id_card_detail, name='id_card_detail'),
    path('id-cards/<int:card_id>/print/', views.id_card_print, name='id_card_print'),
    path('id-cards/<int:card_id>/deactivate/', views.id_card_deactivate, name='id_card_deactivate'),
    path('id-cards/<int:card_id>/activate/', views.id_card_activate, name='id_card_activate'),
    path('id-cards/<int:card_id>/regenerate/', views.id_card_regenerate, name='id_card_regenerate'),
    path('id-cards/<int:card_id>/delete/', views.id_card_delete, name='id_card_delete'),
    
    # Admission Letter Template Management
    path('admission-letter-templates/', views.admission_letter_template_list, name='admission_letter_template_list'),
    path('admission-letter-templates/create/', views.admission_letter_template_create, name='admission_letter_template_create'),
    path('admission-letter-templates/<int:template_id>/', views.admission_letter_template_detail, name='admission_letter_template_detail'),
    path('admission-letter-templates/<int:template_id>/update/', views.admission_letter_template_update, name='admission_letter_template_update'),
    path('admission-letter-templates/<int:template_id>/delete/', views.admission_letter_template_delete, name='admission_letter_template_delete'),
    path('admission-letter-templates/duplicate/', views.admission_letter_template_duplicate, name='admission_letter_template_duplicate'),
    path('admission-letter-templates/import/', views.admission_letter_template_import, name='admission_letter_template_import'),
    path('admission-letter-templates/export/', views.admission_letter_template_export, name='admission_letter_template_export'),
    
    # Admission Letter Management
    path('admission-letters/', views.admission_letter_list, name='admission_letter_list'),
    path('admission-letters/generate/', views.admission_letter_generate, name='admission_letter_generate'),
    path('admission-letters/batch-generate/', views.admission_letter_batch_generate, name='admission_letter_batch_generate'),
    path('admission-letters/<int:letter_id>/', views.admission_letter_detail, name='admission_letter_detail'),
    path('admission-letters/<int:letter_id>/print/', views.admission_letter_print, name='admission_letter_print'),
    path('admission-letters/<int:letter_id>/email/', views.email_admission_letter, name='email_admission_letter'),
    path('admission-letters/<int:letter_id>/delete/', views.admission_letter_delete, name='admission_letter_delete'),
]
