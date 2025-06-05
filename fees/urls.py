from django.urls import path
from . import views

app_name = 'fees'

urlpatterns = [
    # Admin/Accountant views
    path('admin/', views.admin_fees_dashboard, name='admin_dashboard'),
    path('admin/categories/', views.fee_category_list, name='category_list'),
    path('admin/categories/create/', views.create_fee_category, name='create_category'),
    path('admin/categories/<int:category_id>/edit/', views.edit_fee_category, name='edit_category'),
    path('admin/categories/<int:category_id>/delete/', views.delete_fee_category, name='delete_category'),
    path('admin/categories/export/', views.export_fee_categories, name='category_export'),

    path('admin/terms/', views.term_list, name='term_list'),
    path('admin/terms/create/', views.create_term, name='create_term'),
    path('admin/terms/<int:term_id>/edit/', views.edit_term, name='edit_term'),
    path('admin/terms/<int:term_id>/delete/', views.delete_term, name='delete_term'),

    path('admin/class-fees/', views.class_fee_list, name='class_fee_list'),
    path('admin/class-fees/create/', views.create_class_fee, name='create_class_fee'),
    path('admin/class-fees/<int:fee_id>/edit/', views.edit_class_fee, name='edit_class_fee'),
    path('admin/class-fees/<int:fee_id>/delete/', views.delete_class_fee, name='delete_class_fee'),
    path('admin/class-fees/bulk-create/', views.bulk_create_class_fees, name='bulk_create_class_fees'),
    path('admin/class-fees/export/', views.export_class_fees, name='class_fee_export'),

    path('admin/student-fees/', views.student_fee_list, name='student_fee_list'),
    path('admin/student-fees/generate/', views.generate_student_fees, name='generate_student_fees'),
    path('admin/student-fees/bulk-update/', views.bulk_update_student_fees, name='bulk_update_fees'),
    path('admin/student-fees/export/', views.export_student_fees, name='student_fee_export'),
    path('admin/student-fees/<int:fee_id>/', views.student_fee_detail, name='student_fee_detail'),
    path('admin/student-fees/<int:fee_id>/edit/', views.edit_student_fee, name='edit_student_fee'),

    path('admin/payments/', views.payment_list, name='payment_list'),
    path('admin/payments/create/', views.create_payment, name='create_payment'),
    path('admin/payments/<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('admin/payments/<int:payment_id>/adjust/', views.adjust_payment, name='adjust_payment'),
    path('admin/payments/export/', views.export_payments, name='payment_export'),

    path('admin/receipts/', views.receipt_list, name='receipt_list'),
    path('admin/receipts/<int:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path('admin/receipts/<int:receipt_id>/print/', views.print_receipt, name='print_receipt'),
    path('admin/payments/<int:payment_id>/generate-receipt/', views.generate_receipt, name='generate_receipt'),

    path('admin/reports/', views.fee_reports, name='fee_reports'),
    path('admin/reports/class-summary/', views.class_fee_summary, name='class_fee_summary'),
    path('admin/reports/outstanding/', views.outstanding_fees_report, name='outstanding_fees_report'),
    path('admin/reports/collection/', views.fee_collection_report, name='fee_collection_report'),

    # Student/Parent views
    path('student/<int:student_id>/', views.student_fees, name='student_fees'),
    path('student/<int:student_id>/invoice/<int:fee_id>/', views.student_fee_invoice, name='student_fee_invoice'),
    path('student/<int:student_id>/invoice/<int:fee_id>/email/', views.email_invoice, name='email_invoice'),
    path('student/<int:student_id>/payment-history/', views.student_payment_history, name='student_payment_history'),

    # API endpoints for AJAX
    path('api/class-fees/', views.api_class_fees, name='api_class_fees'),
    path('api/students-by-class/<int:class_id>/', views.api_students_by_class, name='api_students_by_class'),
    path('api/student-fees/<int:student_id>/', views.api_student_fees, name='api_student_fees'),
    path('api/search-students/', views.api_search_students, name='api_search_students'),
    path('quick-payment/', views.quick_payment, name='quick_payment'),
]

