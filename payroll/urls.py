from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    # Admin dashboard
    path('admin/', views.admin_payroll_dashboard, name='admin_dashboard'),

    # Staff salary management
    path('admin/staff-salaries/', views.staff_salary_list, name='staff_salary_list'),
    path('admin/staff-salaries/create/', views.create_staff_salary, name='create_staff_salary'),
    path('admin/staff-salaries/<int:salary_id>/', views.staff_salary_detail, name='staff_salary_detail'),
    path('admin/staff-salaries/<int:salary_id>/edit/', views.edit_staff_salary, name='edit_staff_salary'),

    # Staff roles
    path('admin/staff-roles/', views.staff_role_list, name='staff_role_list'),
    path('admin/staff-roles/create/', views.create_staff_role, name='create_staff_role'),
    path('admin/staff-roles/<int:role_id>/edit/', views.edit_staff_role, name='edit_staff_role'),

    # Deductions
    path('admin/deductions/', views.deduction_list, name='deduction_list'),
    path('admin/deductions/create/', views.create_deduction, name='create_deduction'),
    path('admin/deductions/<int:deduction_id>/edit/', views.edit_deduction, name='edit_deduction'),

    # Payroll periods
    path('admin/periods/', views.payroll_period_list, name='payroll_period_list'),
    path('admin/periods/create/', views.create_payroll_period, name='create_payroll_period'),
    path('admin/periods/<int:period_id>/edit/', views.edit_payroll_period, name='edit_payroll_period'),

    # Payroll generation and management
    path('admin/payrolls/', views.payroll_list, name='payroll_list'),
    path('admin/payrolls/generate/', views.generate_payroll, name='generate_payroll'),
    path('admin/payrolls/<int:payroll_id>/', views.payroll_detail, name='payroll_detail'),
    path('admin/payrolls/<int:payroll_id>/approve/', views.approve_payroll, name='approve_payroll'),
    path('admin/payrolls/<int:payroll_id>/cancel/', views.cancel_payroll, name='cancel_payroll'),
    path('admin/payrolls/bulk-actions/', views.bulk_actions, name='bulk_actions'),

    # Payments
    path('admin/payments/', views.payment_list, name='payment_list'),
    path('admin/payments/create/<int:payroll_id>/', views.create_payment, name='create_payment'),
    path('admin/payments/<int:payment_id>/', views.payment_detail, name='payment_detail'),

    # Payslips
    path('admin/payslips/', views.payslip_list, name='payslip_list'),
    path('admin/payslips/generate/<int:payroll_id>/', views.generate_payslip, name='generate_payslip'),
    path('admin/payslips/<int:payslip_id>/', views.payslip_detail, name='payslip_detail'),
    path('admin/payslips/<int:payslip_id>/download/', views.download_payslip, name='download_payslip'),
    path('admin/payslips/<int:payslip_id>/email/', views.email_payslip, name='email_payslip'),

    # Reports
    path('admin/reports/monthly/', views.monthly_salary_report, name='monthly_salary_report'),
    path('admin/reports/staff/', views.staff_payment_history, name='staff_payment_history'),
    path('admin/reports/unpaid/', views.unpaid_staff_report, name='unpaid_staff_report'),
    path('admin/reports/export/', views.export_payroll_data, name='export_payroll_data'),

    # Staff portal (for viewing own payslips and payment history)
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/payslips/', views.staff_payslips, name='staff_payslips'),
    path('staff/payslips/<int:payslip_id>/', views.staff_payslip_detail, name='staff_payslip_detail'),
    path('staff/payslips/<int:payslip_id>/download/', views.staff_download_payslip, name='staff_download_payslip'),
    path('staff/payment-history/', views.staff_payment_history, name='staff_payment_history'),
]
