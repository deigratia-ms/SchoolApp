from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    StaffRole, StaffSalary, PayrollPeriod, Deduction,
    Payroll, PayrollPayment, Payslip
)


@admin.register(StaffRole)
class StaffRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_teaching_staff', 'is_active')
    list_filter = ('is_teaching_staff', 'is_active')
    search_fields = ('name', 'description')


@admin.register(StaffSalary)
class StaffSalaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'base_salary', 'gross_salary', 'net_salary', 'effective_date')
    list_filter = ('role', 'effective_date')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('gross_salary', 'total_deductions', 'net_salary')
    fieldsets = (
        ('Staff Information', {
            'fields': ('user', 'role', 'effective_date')
        }),
        ('Salary Structure', {
            'fields': ('base_salary', 'transport_allowance', 'housing_allowance', 'other_allowances')
        }),
        ('Deductions', {
            'fields': ('ssnit_contribution', 'tax_rate')
        }),
        ('Calculated Amounts', {
            'fields': ('gross_salary', 'total_deductions', 'net_salary')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by')
        }),
    )

    def gross_salary(self, obj):
        return obj.gross_salary
    gross_salary.short_description = 'Gross Salary'

    def total_deductions(self, obj):
        return obj.total_deductions
    total_deductions.short_description = 'Total Deductions'

    def net_salary(self, obj):
        return obj.net_salary
    net_salary.short_description = 'Net Salary'


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active', 'is_locked')
    list_filter = ('is_active', 'is_locked')
    search_fields = ('name',)


@admin.register(Deduction)
class DeductionAdmin(admin.ModelAdmin):
    list_display = ('staff_salary', 'deduction_type', 'amount', 'start_date', 'end_date', 'is_recurring')
    list_filter = ('deduction_type', 'is_recurring')
    search_fields = ('staff_salary__user__first_name', 'staff_salary__user__last_name', 'description')


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('staff_name', 'period', 'gross_salary', 'total_deductions', 'net_salary', 'status', 'payment_status')
    list_filter = ('status', 'period')
    search_fields = ('staff_salary__user__first_name', 'staff_salary__user__last_name')
    readonly_fields = ('base_salary', 'transport_allowance', 'housing_allowance', 'other_allowances',
                      'gross_salary', 'ssnit_deduction', 'tax_deduction', 'other_deductions',
                      'total_deductions', 'net_salary')

    def staff_name(self, obj):
        return obj.staff_salary.user.get_full_name()
    staff_name.short_description = 'Staff'

    def payment_status(self, obj):
        if hasattr(obj, 'payment'):
            return format_html('<span style="color: green;">Paid</span>')
        return format_html('<span style="color: red;">Unpaid</span>')
    payment_status.short_description = 'Payment'


@admin.register(PayrollPayment)
class PayrollPaymentAdmin(admin.ModelAdmin):
    list_display = ('payroll', 'amount', 'payment_date', 'payment_method', 'transaction_id')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('payroll__staff_salary__user__first_name', 'payroll__staff_salary__user__last_name', 'transaction_id')


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('payslip_number', 'payroll', 'generated_at', 'is_emailed', 'pdf_link')
    list_filter = ('is_emailed', 'generated_at')
    search_fields = ('payslip_number', 'payroll__staff_salary__user__first_name', 'payroll__staff_salary__user__last_name')

    def pdf_link(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.pdf_file.url)
        return 'No PDF'
    pdf_link.short_description = 'PDF'
