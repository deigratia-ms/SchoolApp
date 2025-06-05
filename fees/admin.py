from django.contrib import admin
from django.utils.html import format_html
from .models import Term, FeeCategory, ClassFee, StudentFee, Payment, Receipt

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'start_date', 'end_date', 'is_current')
    list_filter = ('academic_year', 'is_current')
    search_fields = ('name', 'academic_year')
    ordering = ('-academic_year', 'start_date')
    actions = ['set_as_current_term']

    def set_as_current_term(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "Please select only one term to set as current", level='error')
            return

        term = queryset.first()
        term.is_current = True
        term.save()
        self.message_user(request, f"{term} has been set as the current term")

    set_as_current_term.short_description = "Set as current term"


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'is_required', 'is_recurring', 'is_active')
    list_filter = ('category_type', 'is_required', 'is_recurring', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(ClassFee)
class ClassFeeAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'fee_category', 'term', 'amount', 'due_date')
    list_filter = ('term', 'classroom', 'fee_category')
    search_fields = ('classroom__name', 'fee_category__name', 'term__name')
    ordering = ('-term__academic_year', 'term__name', 'classroom__name')
    date_hierarchy = 'due_date'


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'fee_category_display', 'amount', 'amount_paid', 'balance', 'status', 'due_date')
    list_filter = ('status', 'class_fee__term', 'class_fee__classroom', 'class_fee__fee_category')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'student__student_id', 'class_fee__fee_category__name')
    ordering = ('-class_fee__term__academic_year', 'class_fee__term__name', 'student__user__last_name')
    date_hierarchy = 'due_date'

    def fee_category_display(self, obj):
        return obj.class_fee.fee_category.name
    fee_category_display.short_description = 'Fee Category'
    fee_category_display.admin_order_field = 'class_fee__fee_category__name'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student_display', 'fee_category_display', 'amount', 'payment_date', 'payment_method', 'received_by')
    list_filter = ('payment_method', 'payment_date', 'student_fee__class_fee__fee_category')
    search_fields = ('student_fee__student__user__first_name', 'student_fee__student__user__last_name', 'student_fee__student__student_id')
    ordering = ('-payment_date', '-created_at')
    date_hierarchy = 'payment_date'

    def student_display(self, obj):
        return obj.student_fee.student
    student_display.short_description = 'Student'
    student_display.admin_order_field = 'student_fee__student__user__last_name'

    def fee_category_display(self, obj):
        return obj.student_fee.class_fee.fee_category.name
    fee_category_display.short_description = 'Fee Category'
    fee_category_display.admin_order_field = 'student_fee__class_fee__fee_category__name'


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'student_display', 'amount_display', 'payment_date_display', 'generated_at', 'printed')
    list_filter = ('printed', 'generated_at', 'payment__payment_method')
    search_fields = ('receipt_number', 'payment__student_fee__student__user__first_name', 'payment__student_fee__student__user__last_name')
    ordering = ('-generated_at',)
    date_hierarchy = 'generated_at'
    readonly_fields = ('receipt_number', 'generated_at')

    def student_display(self, obj):
        return obj.payment.student_fee.student
    student_display.short_description = 'Student'

    def amount_display(self, obj):
        return obj.payment.amount
    amount_display.short_description = 'Amount'

    def payment_date_display(self, obj):
        return obj.payment.payment_date
    payment_date_display.short_description = 'Payment Date'
