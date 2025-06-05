from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from users.models import CustomUser, Teacher


class StaffRole(models.Model):
    """
    Model to define different staff roles and their salary structures.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_teaching_staff = models.BooleanField(default=True, help_text="Whether this role is for teaching staff")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Staff Role"
        verbose_name_plural = "Staff Roles"
        ordering = ['name']


class StaffSalary(models.Model):
    """
    Model to define the salary structure for each staff member.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='salary')
    role = models.ForeignKey(StaffRole, on_delete=models.SET_NULL, null=True, related_name='staff_salaries')
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ssnit_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           help_text="Standard SSNIT deduction amount")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                 help_text="Tax rate as a percentage")
    effective_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, related_name='created_salaries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.base_salary}"

    @property
    def gross_salary(self):
        """Calculate gross salary including all allowances"""
        return self.base_salary + self.transport_allowance + self.housing_allowance + self.other_allowances

    @property
    def total_deductions(self):
        """Calculate standard deductions (SSNIT)"""
        return self.ssnit_contribution

    @property
    def net_salary(self):
        """Calculate net salary after standard deductions"""
        return self.gross_salary - self.total_deductions

    class Meta:
        verbose_name = "Staff Salary"
        verbose_name_plural = "Staff Salaries"
        ordering = ['-updated_at']


class PayrollPeriod(models.Model):
    """
    Model to define payroll periods (typically monthly).
    """
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False, help_text="If locked, no changes can be made to payrolls in this period")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, related_name='created_periods')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.start_date.strftime('%b %Y')} - {self.end_date.strftime('%b %Y')})"

    class Meta:
        verbose_name = "Payroll Period"
        verbose_name_plural = "Payroll Periods"
        ordering = ['-start_date']


class Deduction(models.Model):
    """
    Model to track additional deductions beyond standard ones.
    """
    class DeductionType(models.TextChoices):
        LOAN = 'LOAN', _('Loan Repayment')
        ADVANCE = 'ADVANCE', _('Salary Advance')
        LATENESS = 'LATENESS', _('Lateness')
        ABSENCE = 'ABSENCE', _('Absence')
        TAX = 'TAX', _('Additional Tax')
        OTHER = 'OTHER', _('Other')

    staff_salary = models.ForeignKey(StaffSalary, on_delete=models.CASCADE, related_name='deductions')
    deduction_type = models.CharField(max_length=20, choices=DeductionType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank for one-time deductions")
    is_recurring = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, related_name='created_deductions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff_salary.user.get_full_name()} - {self.get_deduction_type_display()} - {self.amount}"

    class Meta:
        verbose_name = "Deduction"
        verbose_name_plural = "Deductions"
        ordering = ['-created_at']


class Payroll(models.Model):
    """
    Model to generate and track monthly payroll for each staff member.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        PAID = 'PAID', _('Paid')
        CANCELLED = 'CANCELLED', _('Cancelled')

    staff_salary = models.ForeignKey(StaffSalary, on_delete=models.CASCADE, related_name='payrolls')
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name='payrolls')
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    housing_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    ssnit_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    remarks = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='approved_payrolls')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, related_name='created_payrolls')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff_salary.user.get_full_name()} - {self.period.name} - {self.net_salary}"

    class Meta:
        verbose_name = "Payroll"
        verbose_name_plural = "Payrolls"
        unique_together = ['staff_salary', 'period']
        ordering = ['-period__start_date', 'staff_salary__user__first_name']


class PayrollPayment(models.Model):
    """
    Model to track payments made for payroll.
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', _('Cash')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        MOBILE_MONEY = 'MOBILE_MONEY', _('Mobile Money')
        CHECK = 'CHECK', _('Check')
        OTHER = 'OTHER', _('Other')

    payroll = models.OneToOneField(Payroll, on_delete=models.CASCADE, related_name='payment')
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                               null=True, related_name='processed_payments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.payroll.staff_salary.user.get_full_name()} - {self.payment_date} - {self.amount}"

    def save(self, *args, **kwargs):
        # Update payroll status when payment is made
        super().save(*args, **kwargs)
        self.payroll.status = Payroll.Status.PAID
        self.payroll.save()

    class Meta:
        verbose_name = "Payroll Payment"
        verbose_name_plural = "Payroll Payments"
        ordering = ['-payment_date']


class Payslip(models.Model):
    """
    Model to generate and store payslips.
    """
    payroll = models.OneToOneField(Payroll, on_delete=models.CASCADE, related_name='payslip')
    payslip_number = models.CharField(max_length=50, unique=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='generated_payslips')
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='payslips/', null=True, blank=True)
    is_emailed = models.BooleanField(default=False)
    emailed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payslip #{self.payslip_number} - {self.payroll.staff_salary.user.get_full_name()}"

    @classmethod
    def generate_payslip_number(cls, payroll):
        """Generate a unique payslip number."""
        # Format: PSL-YYYYMM-XXXX where XXXX is a sequential number
        period_date = payroll.period.start_date
        period_str = period_date.strftime('%Y%m')
        prefix = f"PSL-{period_str}-"

        # Find the last payslip with this prefix
        last_payslip = cls.objects.filter(payslip_number__startswith=prefix).order_by('-payslip_number').first()

        if last_payslip:
            # Extract the sequential number and increment
            try:
                seq_num = int(last_payslip.payslip_number.split('-')[-1])
                new_seq_num = seq_num + 1
            except (ValueError, IndexError):
                new_seq_num = 1
        else:
            new_seq_num = 1

        # Format with leading zeros
        return f"{prefix}{new_seq_num:04d}"

    class Meta:
        verbose_name = "Payslip"
        verbose_name_plural = "Payslips"
        ordering = ['-generated_at']
