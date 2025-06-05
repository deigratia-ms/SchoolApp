from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from courses.models import ClassRoom
from users.models import Student

class Term(models.Model):
    """
    Model to represent academic terms in a school year.
    """
    name = models.CharField(max_length=50)  # e.g., "First Term", "Second Term", "Third Term"
    start_date = models.DateField()
    end_date = models.DateField()
    academic_year = models.CharField(max_length=20)  # e.g., "2024-2025"
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-academic_year', 'start_date']
        unique_together = ['name', 'academic_year']

    def __str__(self):
        return f"{self.name} ({self.academic_year})"

    def save(self, *args, **kwargs):
        # If this term is being set as current, unset any other current terms
        if self.is_current:
            Term.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


class FeeCategory(models.Model):
    """
    Model to represent different types of fees (tuition, uniform, books, etc.)
    """
    class CategoryType(models.TextChoices):
        TUITION = 'TUITION', _('Tuition')
        UNIFORM = 'UNIFORM', _('Uniform')
        BOOKS = 'BOOKS', _('Books')
        PTA = 'PTA', _('PTA Dues')
        SPORTS = 'SPORTS', _('Sports')
        TECHNOLOGY = 'TECHNOLOGY', _('Technology')
        TRANSPORTATION = 'TRANSPORTATION', _('Transportation')
        FEEDING = 'FEEDING', _('Feeding')
        EXAMINATION = 'EXAMINATION', _('Examination')
        OTHER = 'OTHER', _('Other')

    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CategoryType.choices, default=CategoryType.TUITION)
    description = models.TextField(blank=True, null=True)
    is_required = models.BooleanField(default=True, help_text="Whether this fee is mandatory for all students")
    is_recurring = models.BooleanField(default=True, help_text="Whether this fee recurs every term")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Fee Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class ClassFee(models.Model):
    """
    Model to set fees for each class and term.
    """
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='fees')
    fee_category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name='class_fees')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='class_fees')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_fees')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['classroom', 'fee_category', 'term']
        ordering = ['term', 'classroom', 'fee_category']

    def __str__(self):
        return f"{self.classroom.name} - {self.fee_category.name} - {self.term.name} - {self.amount}"


class StudentFee(models.Model):
    """
    Model to track individual student fee assignments.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PARTIALLY_PAID = 'PARTIALLY_PAID', _('Partially Paid')
        PAID = 'PAID', _('Paid')
        WAIVED = 'WAIVED', _('Waived')
        OVERDUE = 'OVERDUE', _('Overdue')

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fees')
    class_fee = models.ForeignKey(ClassFee, on_delete=models.CASCADE, related_name='student_fees')
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="May differ from class fee if there are individual adjustments")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    due_date = models.DateField()
    last_payment_date = models.DateField(null=True, blank=True)
    waiver_reason = models.TextField(blank=True, null=True, help_text="Reason if fee is waived")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'class_fee']
        ordering = ['due_date', 'student']

    def __str__(self):
        return f"{self.student} - {self.class_fee.fee_category.name} - {self.amount}"

    def save(self, *args, **kwargs):
        # Calculate balance
        self.balance = self.amount - self.amount_paid

        # Update status based on payment
        if self.balance <= 0:
            self.status = self.Status.PAID
        elif self.amount_paid > 0:
            self.status = self.Status.PARTIALLY_PAID
        elif self.due_date < timezone.now().date() and self.status not in [self.Status.PAID, self.Status.WAIVED]:
            self.status = self.Status.OVERDUE

        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Model to record payments made by students/parents.
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', _('Cash')
        MOBILE_MONEY = 'MOBILE_MONEY', _('Mobile Money')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        CHEQUE = 'CHEQUE', _('Cheque')
        CARD = 'CARD', _('Card Payment')
        OTHER = 'OTHER', _('Other')

    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="Reference number for the transaction")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='received_payments')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"{self.student_fee.student} - {self.amount} - {self.payment_date}"

    def save(self, *args, **kwargs):
        # Create the payment record
        super().save(*args, **kwargs)

        # Update the student fee record
        student_fee = self.student_fee
        student_fee.amount_paid = sum(payment.amount for payment in student_fee.payments.all())
        student_fee.last_payment_date = self.payment_date
        student_fee.save()


class Receipt(models.Model):
    """
    Model to generate and store payment receipts.
    """
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=50, unique=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='generated_receipts')
    generated_at = models.DateTimeField(auto_now_add=True)
    printed = models.BooleanField(default=False)
    last_printed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Receipt #{self.receipt_number} - {self.payment.student_fee.student}"

    @classmethod
    def generate_receipt_number(cls):
        """Generate a unique receipt number."""
        # Format: RCT-YYYYMMDD-XXXX where XXXX is a sequential number
        today = timezone.now().strftime('%Y%m%d')
        prefix = f"RCT-{today}-"

        # Find the last receipt with this prefix
        last_receipt = cls.objects.filter(receipt_number__startswith=prefix).order_by('-receipt_number').first()

        if last_receipt:
            # Extract the sequential number and increment
            try:
                seq_num = int(last_receipt.receipt_number.split('-')[-1])
                new_seq_num = seq_num + 1
            except (ValueError, IndexError):
                new_seq_num = 1
        else:
            new_seq_num = 1

        # Format with leading zeros
        return f"{prefix}{new_seq_num:04d}"
