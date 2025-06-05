from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.template.loader import render_to_string, get_template
from django.core.paginator import Paginator
from django.conf import settings
from django.core.files.base import ContentFile
import tempfile
import os
import io
import calendar
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
import urllib.request
from PIL import Image as PILImage
import io as pil_io

from users.models import CustomUser, Teacher, SchoolSettings
from .models import (
    StaffRole, StaffSalary, PayrollPeriod, Deduction,
    Payroll, PayrollPayment, Payslip
)

# Helper function to convert numbers to words
def num_to_words(num):
    """Convert a number to words for payslip display."""
    units = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def convert_below_thousand(num):
        if num < 10:
            return units[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            return tens[num // 10] + ('' if num % 10 == 0 else ' ' + units[num % 10])
        else:
            return units[num // 100] + ' Hundred' + ('' if num % 100 == 0 else ' and ' + convert_below_thousand(num % 100))

    if num == 0:
        return 'Zero Ghana Cedis'

    # Handle decimal part
    num_str = f"{num:.2f}"
    whole, decimal = num_str.split('.')
    whole = int(whole)
    decimal = int(decimal)

    result = ''

    if whole > 0:
        if whole >= 1000000:
            result += convert_below_thousand(whole // 1000000) + ' Million '
            whole %= 1000000

        if whole >= 1000:
            result += convert_below_thousand(whole // 1000) + ' Thousand '
            whole %= 1000

        if whole > 0:
            result += convert_below_thousand(whole)

        result += ' Ghana Cedis'

    if decimal > 0:
        result += ' and ' + convert_below_thousand(decimal) + ' Pesewas'

    return result.strip()

# Helper functions for role-based access
def is_admin_or_accountant(user):
    return user.is_authenticated and (user.role == CustomUser.Role.ADMIN or
                                     user.role == 'ACCOUNTANT')

# Admin Dashboard Views
@login_required
@user_passes_test(is_admin_or_accountant)
def admin_payroll_dashboard(request):
    """Dashboard for payroll management."""
    # Get current payroll period
    current_period = PayrollPeriod.objects.filter(is_active=True).first()

    # Summary statistics
    total_staff = StaffSalary.objects.count()

    # Get payroll statistics for current period
    if current_period:
        total_payroll = Payroll.objects.filter(period=current_period)
        total_salary = total_payroll.aggregate(total=Sum('gross_salary'))['total'] or 0
        total_paid = PayrollPayment.objects.filter(payroll__period=current_period).aggregate(total=Sum('amount'))['total'] or 0
        total_pending = total_salary - total_paid
        payment_rate = (total_paid / total_salary * 100) if total_salary > 0 else 0

        # Staff payment status
        paid_staff = total_payroll.filter(status=Payroll.Status.PAID).count()
        pending_staff = total_payroll.filter(status=Payroll.Status.PENDING).count()
        approved_staff = total_payroll.filter(status=Payroll.Status.APPROVED).count()
    else:
        total_salary = 0
        total_paid = 0
        total_pending = 0
        payment_rate = 0
        paid_staff = 0
        pending_staff = 0
        approved_staff = 0

    # Recent payments
    recent_payments = PayrollPayment.objects.select_related(
        'payroll', 'payroll__staff_salary', 'payroll__staff_salary__user'
    ).order_by('-payment_date')[:10]

    # Staff with pending payments
    staff_pending_payment = Payroll.objects.filter(
        status__in=[Payroll.Status.PENDING, Payroll.Status.APPROVED]
    ).select_related('staff_salary', 'staff_salary__user', 'period').order_by('staff_salary__user__first_name')[:10]

    # Role-based statistics
    role_stats = []
    roles = StaffRole.objects.filter(is_active=True)

    for role in roles:
        role_salaries = StaffSalary.objects.filter(role=role)
        role_staff_count = role_salaries.count()

        if role_staff_count > 0:
            role_total_salary = role_salaries.aggregate(total=Sum('base_salary'))['total'] or 0
            role_stats.append({
                'id': role.id,
                'name': role.name,
                'staff_count': role_staff_count,
                'total_salary': role_total_salary,
                'average_salary': role_total_salary / role_staff_count
            })

    context = {
        'current_period': current_period,
        'total_staff': total_staff,
        'total_salary': total_salary,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'payment_rate': payment_rate,
        'paid_staff': paid_staff,
        'pending_staff': pending_staff,
        'approved_staff': approved_staff,
        'recent_payments': recent_payments,
        'staff_pending_payment': staff_pending_payment,
        'role_stats': role_stats,
    }

    return render(request, 'payroll/admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def staff_salary_list(request):
    """List all staff salaries."""
    # Get filter parameters
    role_id = request.GET.get('role')
    search_query = request.GET.get('search')

    # Base query
    staff_salaries = StaffSalary.objects.select_related('user', 'role')

    # Apply filters
    if role_id:
        staff_salaries = staff_salaries.filter(role_id=role_id)

    if search_query:
        staff_salaries = staff_salaries.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Order by name
    staff_salaries = staff_salaries.order_by('user__first_name', 'user__last_name')

    # Calculate totals
    total_base_salary = staff_salaries.aggregate(total=Sum('base_salary'))['total'] or 0
    total_gross_salary = sum(salary.gross_salary for salary in staff_salaries)
    total_net_salary = sum(salary.net_salary for salary in staff_salaries)

    # Pagination
    paginator = Paginator(staff_salaries, 25)  # Show 25 salaries per page
    page = request.GET.get('page')
    staff_salaries = paginator.get_page(page)

    # Get filter options for dropdowns
    roles = StaffRole.objects.filter(is_active=True).order_by('name')

    context = {
        'staff_salaries': staff_salaries,
        'roles': roles,
        'total_base_salary': total_base_salary,
        'total_gross_salary': total_gross_salary,
        'total_net_salary': total_net_salary,
        'selected_role': role_id,
        'search_query': search_query,
    }

    return render(request, 'payroll/admin/staff_salary_list.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def staff_salary_detail(request, salary_id):
    """View details of a staff salary."""
    staff_salary = get_object_or_404(StaffSalary, id=salary_id)

    # Get deductions for this staff
    deductions = Deduction.objects.filter(staff_salary=staff_salary).order_by('-created_at')

    # Get payroll history for this staff
    payrolls = Payroll.objects.filter(staff_salary=staff_salary).select_related('period').order_by('-period__start_date')

    # Calculate tax amount
    tax_amount = (staff_salary.base_salary * staff_salary.tax_rate) / 100

    context = {
        'staff_salary': staff_salary,
        'deductions': deductions,
        'payrolls': payrolls,
        'tax_amount': tax_amount,
    }

    return render(request, 'payroll/admin/staff_salary_detail.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def create_staff_salary(request):
    """Create a new staff salary."""
    if request.method == 'POST':
        # Get form data
        user_id = request.POST.get('user')
        role_id = request.POST.get('role')
        base_salary = request.POST.get('base_salary')
        transport_allowance = request.POST.get('transport_allowance', 0)
        housing_allowance = request.POST.get('housing_allowance', 0)
        other_allowances = request.POST.get('other_allowances', 0)
        ssnit_contribution = request.POST.get('ssnit_contribution', 0)
        tax_rate = request.POST.get('tax_rate', 0)
        effective_date = request.POST.get('effective_date')
        notes = request.POST.get('notes', '')

        # Validate required fields
        if not all([user_id, role_id, base_salary, effective_date]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('payroll:create_staff_salary')

        # Check if user already has a salary
        if StaffSalary.objects.filter(user_id=user_id).exists():
            messages.error(request, 'This staff member already has a salary defined.')
            return redirect('payroll:staff_salary_list')

        # Create the staff salary
        try:
            staff_salary = StaffSalary.objects.create(
                user_id=user_id,
                role_id=role_id,
                base_salary=base_salary,
                transport_allowance=transport_allowance,
                housing_allowance=housing_allowance,
                other_allowances=other_allowances,
                ssnit_contribution=ssnit_contribution,
                tax_rate=tax_rate,
                effective_date=effective_date,
                notes=notes,
                created_by=request.user
            )
            messages.success(request, f'Salary for {staff_salary.user.get_full_name()} created successfully.')
            return redirect('payroll:staff_salary_detail', salary_id=staff_salary.id)
        except Exception as e:
            messages.error(request, f'Error creating staff salary: {str(e)}')
            return redirect('payroll:create_staff_salary')

    # GET request - show form
    # Get staff without salary
    staff_without_salary = CustomUser.objects.filter(
        Q(role=CustomUser.Role.ADMIN) | Q(role=CustomUser.Role.TEACHER) | Q(role='ACCOUNTANT')
    ).exclude(
        id__in=StaffSalary.objects.values_list('user_id', flat=True)
    ).order_by('first_name', 'last_name')

    # Get roles
    roles = StaffRole.objects.filter(is_active=True).order_by('name')

    context = {
        'staff_without_salary': staff_without_salary,
        'roles': roles,
        'today': timezone.now().date(),
    }

    return render(request, 'payroll/admin/create_staff_salary.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def edit_staff_salary(request, salary_id):
    """Edit an existing staff salary."""
    staff_salary = get_object_or_404(StaffSalary, id=salary_id)

    if request.method == 'POST':
        # Get form data
        role_id = request.POST.get('role')
        base_salary = request.POST.get('base_salary')
        transport_allowance = request.POST.get('transport_allowance', 0)
        housing_allowance = request.POST.get('housing_allowance', 0)
        other_allowances = request.POST.get('other_allowances', 0)
        ssnit_contribution = request.POST.get('ssnit_contribution', 0)
        tax_rate = request.POST.get('tax_rate', 0)
        effective_date = request.POST.get('effective_date')
        notes = request.POST.get('notes', '')

        # Validate required fields
        if not all([role_id, base_salary, effective_date]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('payroll:edit_staff_salary', salary_id=salary_id)

        # Update the staff salary
        try:
            staff_salary.role_id = role_id
            staff_salary.base_salary = base_salary
            staff_salary.transport_allowance = transport_allowance
            staff_salary.housing_allowance = housing_allowance
            staff_salary.other_allowances = other_allowances
            staff_salary.ssnit_contribution = ssnit_contribution
            staff_salary.tax_rate = tax_rate
            staff_salary.effective_date = effective_date
            staff_salary.notes = notes
            staff_salary.save()

            messages.success(request, f'Salary for {staff_salary.user.get_full_name()} updated successfully.')
            return redirect('payroll:staff_salary_detail', salary_id=staff_salary.id)
        except Exception as e:
            messages.error(request, f'Error updating staff salary: {str(e)}')
            return redirect('payroll:edit_staff_salary', salary_id=salary_id)

    # GET request - show form
    # Get roles
    roles = StaffRole.objects.filter(is_active=True).order_by('name')

    context = {
        'staff_salary': staff_salary,
        'roles': roles,
    }

    return render(request, 'payroll/admin/edit_staff_salary.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def staff_role_list(request):
    """List all staff roles."""
    roles = StaffRole.objects.all().order_by('name')
    return render(request, 'payroll/admin/staff_role_list.html', {'roles': roles})

@login_required
@user_passes_test(is_admin_or_accountant)
def create_staff_role(request):
    """Create a new staff role."""
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_teaching_staff = request.POST.get('is_teaching_staff') == 'on'

        # Validate required fields
        if not name:
            messages.error(request, 'Please provide a role name.')
            return redirect('payroll:create_staff_role')

        # Check if role already exists
        if StaffRole.objects.filter(name=name).exists():
            messages.error(request, 'A role with this name already exists.')
            return redirect('payroll:create_staff_role')

        # Create the role
        try:
            role = StaffRole.objects.create(
                name=name,
                description=description,
                is_teaching_staff=is_teaching_staff
            )
            messages.success(request, f'Role "{role.name}" created successfully.')
            return redirect('payroll:staff_role_list')
        except Exception as e:
            messages.error(request, f'Error creating role: {str(e)}')
            return redirect('payroll:create_staff_role')

    # GET request - show form
    return render(request, 'payroll/admin/create_staff_role.html')

@login_required
@user_passes_test(is_admin_or_accountant)
def edit_staff_role(request, role_id):
    """Edit an existing staff role."""
    role = get_object_or_404(StaffRole, id=role_id)

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_teaching_staff = request.POST.get('is_teaching_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        # Validate required fields
        if not name:
            messages.error(request, 'Please provide a role name.')
            return redirect('payroll:edit_staff_role', role_id=role_id)

        # Check if role already exists with this name (excluding current role)
        if StaffRole.objects.filter(name=name).exclude(id=role_id).exists():
            messages.error(request, 'A role with this name already exists.')
            return redirect('payroll:edit_staff_role', role_id=role_id)

        # Update the role
        try:
            role.name = name
            role.description = description
            role.is_teaching_staff = is_teaching_staff
            role.is_active = is_active
            role.save()

            messages.success(request, f'Role "{role.name}" updated successfully.')
            return redirect('payroll:staff_role_list')
        except Exception as e:
            messages.error(request, f'Error updating role: {str(e)}')
            return redirect('payroll:edit_staff_role', role_id=role_id)

    # GET request - show form
    context = {
        'role': role,
    }

    return render(request, 'payroll/admin/edit_staff_role.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def payroll_period_list(request):
    """List all payroll periods."""
    periods = PayrollPeriod.objects.all().order_by('-start_date')
    return render(request, 'payroll/admin/payroll_period_list.html', {'periods': periods})

@login_required
@user_passes_test(is_admin_or_accountant)
def create_payroll_period(request):
    """Create a new payroll period."""
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_active = request.POST.get('is_active') == 'on'

        # Validate required fields
        if not all([name, start_date, end_date]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('payroll:create_payroll_period')

        # Check if period already exists with this name
        if PayrollPeriod.objects.filter(name=name).exists():
            messages.error(request, 'A payroll period with this name already exists.')
            return redirect('payroll:create_payroll_period')

        # Create the period
        try:
            period = PayrollPeriod.objects.create(
                name=name,
                start_date=start_date,
                end_date=end_date,
                is_active=is_active,
                created_by=request.user
            )
            messages.success(request, f'Payroll period "{period.name}" created successfully.')
            return redirect('payroll:payroll_period_list')
        except Exception as e:
            messages.error(request, f'Error creating payroll period: {str(e)}')
            return redirect('payroll:create_payroll_period')

    # GET request - show form
    context = {
        'today': timezone.now().date(),
    }

    return render(request, 'payroll/admin/create_payroll_period.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def edit_payroll_period(request, period_id):
    """Edit an existing payroll period."""
    period = get_object_or_404(PayrollPeriod, id=period_id)

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_active = request.POST.get('is_active') == 'on'
        is_locked = request.POST.get('is_locked') == 'on'

        # Validate required fields
        if not all([name, start_date, end_date]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('payroll:edit_payroll_period', period_id=period_id)

        # Check if period already exists with this name (excluding current period)
        if PayrollPeriod.objects.filter(name=name).exclude(id=period_id).exists():
            messages.error(request, 'A payroll period with this name already exists.')
            return redirect('payroll:edit_payroll_period', period_id=period_id)

        # Update the period
        try:
            period.name = name
            period.start_date = start_date
            period.end_date = end_date
            period.is_active = is_active
            period.is_locked = is_locked
            period.save()

            messages.success(request, f'Payroll period "{period.name}" updated successfully.')
            return redirect('payroll:payroll_period_list')
        except Exception as e:
            messages.error(request, f'Error updating payroll period: {str(e)}')
            return redirect('payroll:edit_payroll_period', period_id=period_id)

    # GET request - show form
    context = {
        'period': period,
    }

    return render(request, 'payroll/admin/edit_payroll_period.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def deduction_list(request):
    """List all deductions."""
    # Get filter parameters
    staff_id = request.GET.get('staff')
    deduction_type = request.GET.get('type')
    is_recurring = request.GET.get('recurring')

    # Base query
    deductions = Deduction.objects.select_related('staff_salary', 'staff_salary__user', 'staff_salary__role')

    # Apply filters
    if staff_id:
        deductions = deductions.filter(staff_salary__user_id=staff_id)

    if deduction_type:
        deductions = deductions.filter(deduction_type=deduction_type)

    if is_recurring is not None:
        is_recurring_bool = is_recurring.lower() == 'true'
        deductions = deductions.filter(is_recurring=is_recurring_bool)

    # Order by staff name and creation date
    deductions = deductions.order_by('staff_salary__user__first_name', 'staff_salary__user__last_name', '-created_at')

    # Pagination
    paginator = Paginator(deductions, 25)  # Show 25 deductions per page
    page = request.GET.get('page')
    deductions = paginator.get_page(page)

    # Get filter options for dropdowns
    staff_with_salary = StaffSalary.objects.select_related('user').order_by('user__first_name', 'user__last_name')
    deduction_types = Deduction.DeductionType.choices

    context = {
        'deductions': deductions,
        'staff_with_salary': staff_with_salary,
        'deduction_types': deduction_types,
        'selected_staff': staff_id,
        'selected_type': deduction_type,
        'selected_recurring': is_recurring,
    }

    return render(request, 'payroll/admin/deduction_list.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def create_deduction(request):
    """Create a new deduction."""
    if request.method == 'POST':
        # Get form data
        staff_salary_id = request.POST.get('staff_salary')
        deduction_type = request.POST.get('deduction_type')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date', None)
        is_recurring = request.POST.get('is_recurring') == 'on'

        # Validate required fields
        if not all([staff_salary_id, deduction_type, amount, start_date]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('payroll:create_deduction')

        # Create the deduction
        try:
            deduction = Deduction.objects.create(
                staff_salary_id=staff_salary_id,
                deduction_type=deduction_type,
                amount=amount,
                description=description,
                start_date=start_date,
                end_date=end_date if end_date else None,
                is_recurring=is_recurring,
                created_by=request.user
            )

            staff_name = deduction.staff_salary.user.get_full_name()
            messages.success(request, f'Deduction for {staff_name} created successfully.')
            return redirect('payroll:deduction_list')
        except Exception as e:
            messages.error(request, f'Error creating deduction: {str(e)}')
            return redirect('payroll:create_deduction')

    # GET request - show form
    # Get staff with salary
    staff_with_salary = StaffSalary.objects.select_related('user').order_by('user__first_name', 'user__last_name')

    # Get deduction types
    deduction_types = Deduction.DeductionType.choices

    context = {
        'staff_with_salary': staff_with_salary,
        'deduction_types': deduction_types,
        'today': timezone.now().date(),
    }

    return render(request, 'payroll/admin/create_deduction.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def edit_deduction(request, deduction_id):
    """Edit an existing deduction."""
    deduction = get_object_or_404(Deduction, id=deduction_id)

    if request.method == 'POST':
        # Get form data
        deduction_type = request.POST.get('deduction_type')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date', None)
        is_recurring = request.POST.get('is_recurring') == 'on'

        # Validate required fields
        if not all([deduction_type, amount, start_date]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('payroll:edit_deduction', deduction_id=deduction_id)

        # Update the deduction
        try:
            deduction.deduction_type = deduction_type
            deduction.amount = amount
            deduction.description = description
            deduction.start_date = start_date
            deduction.end_date = end_date if end_date else None
            deduction.is_recurring = is_recurring
            deduction.save()

            staff_name = deduction.staff_salary.user.get_full_name()
            messages.success(request, f'Deduction for {staff_name} updated successfully.')
            return redirect('payroll:deduction_list')
        except Exception as e:
            messages.error(request, f'Error updating deduction: {str(e)}')
            return redirect('payroll:edit_deduction', deduction_id=deduction_id)

    # GET request - show form
    # Get deduction types
    deduction_types = Deduction.DeductionType.choices

    context = {
        'deduction': deduction,
        'deduction_types': deduction_types,
    }

    return render(request, 'payroll/admin/edit_deduction.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def payroll_list(request):
    """List all payrolls."""
    # Get filter parameters
    period_id = request.GET.get('period')
    status = request.GET.get('status')
    search_query = request.GET.get('search')

    # Base query
    payrolls = Payroll.objects.select_related(
        'staff_salary', 'staff_salary__user', 'staff_salary__role', 'period'
    )

    # Apply filters
    if period_id:
        payrolls = payrolls.filter(period_id=period_id)

    if status:
        payrolls = payrolls.filter(status=status)

    if search_query:
        payrolls = payrolls.filter(
            Q(staff_salary__user__first_name__icontains=search_query) |
            Q(staff_salary__user__last_name__icontains=search_query) |
            Q(staff_salary__user__email__icontains=search_query)
        )

    # Order by period and staff name
    payrolls = payrolls.order_by('-period__start_date', 'staff_salary__user__first_name', 'staff_salary__user__last_name')

    # Calculate totals
    total_gross = payrolls.aggregate(total=Sum('gross_salary'))['total'] or 0
    total_deductions = payrolls.aggregate(total=Sum('total_deductions'))['total'] or 0
    total_net = payrolls.aggregate(total=Sum('net_salary'))['total'] or 0

    # Pagination
    paginator = Paginator(payrolls, 25)  # Show 25 payrolls per page
    page = request.GET.get('page')
    payrolls = paginator.get_page(page)

    # Get filter options for dropdowns
    periods = PayrollPeriod.objects.all().order_by('-start_date')
    status_choices = Payroll.Status.choices

    context = {
        'payrolls': payrolls,
        'periods': periods,
        'status_choices': status_choices,
        'total_gross': total_gross,
        'total_deductions': total_deductions,
        'total_net': total_net,
        'selected_period': period_id,
        'selected_status': status,
        'search_query': search_query,
    }

    return render(request, 'payroll/admin/payroll_list.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def generate_payroll(request):
    """Generate payroll for a period."""
    if request.method == 'POST':
        # Get form data
        period_id = request.POST.get('period')
        staff_ids = request.POST.getlist('staff_ids')

        # Validate required fields
        if not period_id:
            messages.error(request, 'Please select a payroll period.')
            return redirect('payroll:generate_payroll')

        if not staff_ids:
            messages.error(request, 'Please select at least one staff member.')
            return redirect('payroll:generate_payroll')

        # Get the period
        period = get_object_or_404(PayrollPeriod, id=period_id)

        # Check if period is locked
        if period.is_locked:
            messages.error(request, f'Payroll period "{period.name}" is locked. Cannot generate payroll.')
            return redirect('payroll:generate_payroll')

        # Generate payroll for each selected staff
        success_count = 0
        error_count = 0

        for staff_id in staff_ids:
            try:
                # Get staff salary
                staff_salary = StaffSalary.objects.get(id=staff_id)

                # Check if payroll already exists for this staff and period
                if Payroll.objects.filter(staff_salary=staff_salary, period=period).exists():
                    error_count += 1
                    continue

                # Calculate deductions
                # Get recurring deductions that are active during this period
                deductions = Deduction.objects.filter(
                    staff_salary=staff_salary,
                    is_recurring=True,
                    start_date__lte=period.end_date
                ).filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=period.start_date)
                )

                # Calculate total deductions
                other_deductions_total = sum(d.amount for d in deductions)

                # Create the payroll record
                payroll = Payroll.objects.create(
                    staff_salary=staff_salary,
                    period=period,
                    base_salary=staff_salary.base_salary,
                    transport_allowance=staff_salary.transport_allowance,
                    housing_allowance=staff_salary.housing_allowance,
                    other_allowances=staff_salary.other_allowances,
                    gross_salary=staff_salary.gross_salary,
                    ssnit_deduction=staff_salary.ssnit_contribution,
                    tax_deduction=staff_salary.base_salary * (staff_salary.tax_rate / 100) if staff_salary.tax_rate > 0 else 0,
                    other_deductions=other_deductions_total,
                    total_deductions=staff_salary.ssnit_contribution +
                                    (staff_salary.base_salary * (staff_salary.tax_rate / 100) if staff_salary.tax_rate > 0 else 0) +
                                    other_deductions_total,
                    net_salary=staff_salary.gross_salary -
                              (staff_salary.ssnit_contribution +
                               (staff_salary.base_salary * (staff_salary.tax_rate / 100) if staff_salary.tax_rate > 0 else 0) +
                               other_deductions_total),
                    status=Payroll.Status.PENDING,
                    created_by=request.user
                )

                success_count += 1
            except Exception as e:
                error_count += 1
                continue

        if success_count > 0:
            messages.success(request, f'Successfully generated payroll for {success_count} staff members.')

        if error_count > 0:
            messages.warning(request, f'Failed to generate payroll for {error_count} staff members. They may already have payroll for this period.')

        return redirect('payroll:payroll_list')

    # GET request - show form
    # Get active periods
    periods = PayrollPeriod.objects.filter(is_active=True, is_locked=False).order_by('-start_date')

    # Get staff with salary
    staff_with_salary = StaffSalary.objects.select_related('user', 'role').order_by('user__first_name', 'user__last_name')

    context = {
        'periods': periods,
        'staff_with_salary': staff_with_salary,
    }

    return render(request, 'payroll/admin/generate_payroll.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def payroll_detail(request, payroll_id):
    """View details of a payroll."""
    payroll = get_object_or_404(Payroll, id=payroll_id)

    # Get deductions for this staff
    deductions = Deduction.objects.filter(
        staff_salary=payroll.staff_salary,
        is_recurring=True,
        start_date__lte=payroll.period.end_date
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=payroll.period.start_date)
    )

    # Check if payslip exists
    has_payslip = hasattr(payroll, 'payslip')

    # Check if payment exists
    has_payment = hasattr(payroll, 'payment')

    context = {
        'payroll': payroll,
        'deductions': deductions,
        'has_payslip': has_payslip,
        'has_payment': has_payment,
    }

    return render(request, 'payroll/admin/payroll_detail.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def approve_payroll(request, payroll_id):
    """Approve a payroll."""
    payroll = get_object_or_404(Payroll, id=payroll_id)

    # Check if payroll can be approved
    if payroll.status != Payroll.Status.PENDING:
        messages.error(request, 'Only pending payrolls can be approved.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    # Check if period is locked
    if payroll.period.is_locked:
        messages.error(request, f'Payroll period "{payroll.period.name}" is locked. Cannot approve payroll.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    # Update payroll status
    try:
        payroll.status = Payroll.Status.APPROVED
        payroll.approved_by = request.user
        payroll.approved_at = timezone.now()
        payroll.save()

        messages.success(request, f'Payroll for {payroll.staff_salary.user.get_full_name()} approved successfully.')
    except Exception as e:
        messages.error(request, f'Error approving payroll: {str(e)}')

    return redirect('payroll:payroll_detail', payroll_id=payroll_id)

@login_required
@user_passes_test(is_admin_or_accountant)
def cancel_payroll(request, payroll_id):
    """Cancel a payroll."""
    payroll = get_object_or_404(Payroll, id=payroll_id)

    # Check if payroll can be cancelled
    if payroll.status == Payroll.Status.PAID:
        messages.error(request, 'Paid payrolls cannot be cancelled.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    # Check if period is locked
    if payroll.period.is_locked:
        messages.error(request, f'Payroll period "{payroll.period.name}" is locked. Cannot cancel payroll.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    # Update payroll status
    try:
        payroll.status = Payroll.Status.CANCELLED
        payroll.save()

        messages.success(request, f'Payroll for {payroll.staff_salary.user.get_full_name()} cancelled successfully.')
    except Exception as e:
        messages.error(request, f'Error cancelling payroll: {str(e)}')

    return redirect('payroll:payroll_detail', payroll_id=payroll_id)

@login_required
@user_passes_test(is_admin_or_accountant)
def payment_list(request):
    """List all payments."""
    # Get filter parameters
    period_id = request.GET.get('period')
    payment_method = request.GET.get('method')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Base query
    payments = PayrollPayment.objects.select_related(
        'payroll', 'payroll__staff_salary', 'payroll__staff_salary__user', 'payroll__period'
    )

    # Apply filters
    if period_id:
        payments = payments.filter(payroll__period_id=period_id)

    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    if start_date:
        payments = payments.filter(payment_date__gte=start_date)

    if end_date:
        payments = payments.filter(payment_date__lte=end_date)

    # Order by payment date (newest first)
    payments = payments.order_by('-payment_date')

    # Calculate total
    total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0

    # Pagination
    paginator = Paginator(payments, 25)  # Show 25 payments per page
    page = request.GET.get('page')
    payments = paginator.get_page(page)

    # Get filter options for dropdowns
    periods = PayrollPeriod.objects.all().order_by('-start_date')
    payment_methods = PayrollPayment.PaymentMethod.choices

    context = {
        'payments': payments,
        'periods': periods,
        'payment_methods': payment_methods,
        'total_paid': total_paid,
        'selected_period': period_id,
        'selected_method': payment_method,
        'selected_start_date': start_date,
        'selected_end_date': end_date,
    }

    return render(request, 'payroll/admin/payment_list.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def bulk_actions(request):
    """Handle bulk actions for payrolls."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('payroll:payroll_list')

    # Get selected action and payroll IDs
    action = request.POST.get('bulk_action')
    payroll_ids = request.POST.getlist('payroll_ids[]')

    if not action:
        messages.error(request, 'No action selected.')
        return redirect('payroll:payroll_list')

    if not payroll_ids:
        messages.error(request, 'No payrolls selected.')
        return redirect('payroll:payroll_list')

    # Get payrolls
    payrolls = Payroll.objects.filter(id__in=payroll_ids)

    # Process based on action
    if action == 'approve':
        return bulk_approve_payrolls(request, payrolls)
    elif action == 'pay':
        return bulk_create_payments(request, payrolls)
    elif action == 'generate_payslip':
        return bulk_generate_payslips(request, payrolls)
    else:
        messages.error(request, f'Invalid action: {action}')
        return redirect('payroll:payroll_list')

@login_required
@user_passes_test(is_admin_or_accountant)
def bulk_approve_payrolls(request, payrolls):
    """Approve multiple payrolls at once."""
    success_count = 0
    error_count = 0
    skipped_count = 0

    for payroll in payrolls:
        # Check if payroll can be approved
        if payroll.status != Payroll.Status.PENDING:
            skipped_count += 1
            continue

        # Check if period is locked
        if payroll.period.is_locked:
            skipped_count += 1
            continue

        # Update payroll status
        try:
            payroll.status = Payroll.Status.APPROVED
            payroll.approved_by = request.user
            payroll.approved_at = timezone.now()
            payroll.save()
            success_count += 1
        except Exception:
            error_count += 1

    # Show appropriate messages
    if success_count > 0:
        messages.success(request, f'{success_count} payrolls approved successfully.')
    if error_count > 0:
        messages.error(request, f'Failed to approve {error_count} payrolls.')
    if skipped_count > 0:
        messages.warning(request, f'{skipped_count} payrolls were skipped (already approved or period locked).')

    return redirect('payroll:payroll_list')

@login_required
@user_passes_test(is_admin_or_accountant)
def bulk_create_payments(request, payrolls):
    """Create payments for multiple payrolls at once."""
    # Check if we need to show the form
    if 'confirm' not in request.POST:
        # Prepare context for the form
        context = {
            'payrolls': payrolls,
            'payment_methods': PayrollPayment.PaymentMethod.choices,
            'today': timezone.now().date(),
            'total_amount': sum(p.net_salary for p in payrolls),
            'payroll_ids': [p.id for p in payrolls],
        }
        return render(request, 'payroll/admin/bulk_create_payment.html', context)

    # Process the form submission
    payment_date = request.POST.get('payment_date')
    payment_method = request.POST.get('payment_method')
    transaction_id = request.POST.get('transaction_id', '')
    remarks = request.POST.get('remarks', '')
    payroll_ids = request.POST.getlist('payroll_ids')

    # Validate required fields
    if not all([payment_date, payment_method]):
        messages.error(request, 'Please fill in all required fields.')
        return redirect('payroll:payroll_list')

    # Get payrolls again to ensure they exist
    payrolls = Payroll.objects.filter(id__in=payroll_ids)

    success_count = 0
    error_count = 0
    skipped_count = 0

    for payroll in payrolls:
        # Check if payroll can be paid
        if payroll.status not in [Payroll.Status.APPROVED, Payroll.Status.PENDING]:
            skipped_count += 1
            continue

        # Check if payment already exists
        if hasattr(payroll, 'payment'):
            skipped_count += 1
            continue

        # Check if period is locked
        if payroll.period.is_locked:
            skipped_count += 1
            continue

        # Create the payment
        try:
            PayrollPayment.objects.create(
                payroll=payroll,
                amount=payroll.net_salary,
                payment_date=payment_date,
                payment_method=payment_method,
                transaction_id=transaction_id,
                remarks=remarks,
                paid_by=request.user
            )
            success_count += 1
        except Exception:
            error_count += 1

    # Show appropriate messages
    if success_count > 0:
        messages.success(request, f'{success_count} payments created successfully.')
    if error_count > 0:
        messages.error(request, f'Failed to create {error_count} payments.')
    if skipped_count > 0:
        messages.warning(request, f'{skipped_count} payments were skipped (already paid, not approved, or period locked).')

    return redirect('payroll:payroll_list')

@login_required
@user_passes_test(is_admin_or_accountant)
def bulk_generate_payslips(request, payrolls):
    """Generate payslips for multiple payrolls at once."""
    success_count = 0
    error_count = 0
    skipped_count = 0

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    for payroll in payrolls:
        # Check if payslip already exists
        if hasattr(payroll, 'payslip'):
            skipped_count += 1
            continue

        # Check if period is locked
        if payroll.period.is_locked:
            skipped_count += 1
            continue

        # Generate payslip number
        payslip_count = Payslip.objects.count() + 1
        payslip_number = f'PS-{timezone.now().strftime("%Y%m")}-{payslip_count:04d}'

        try:
            # Create payslip
            payslip = Payslip.objects.create(
                payroll=payroll,
                payslip_number=payslip_number,
                generated_by=request.user,
                generated_at=timezone.now()
            )

            # Calculate amount in words
            amount_in_words = num_to_words(payroll.net_salary)

            # Create PDF buffer
            buffer = io.BytesIO()

            # Create the PDF document
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

            # Container for the 'Flowable' objects
            elements = []

            # Styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Center', alignment=1))
            styles.add(ParagraphStyle(name='Right', alignment=2))

            # School logo and header
            if school_settings:
                # Add school logo if available
                if school_settings.logo and hasattr(school_settings.logo, 'url'):
                    try:
                        logo_path = school_settings.logo.path
                        img = Image(logo_path, width=2*inch, height=1*inch)
                        img.hAlign = 'CENTER'
                        elements.append(img)
                        elements.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        # If there's an error with the logo, just continue without it
                        print(f"Error adding logo: {str(e)}")

                # Add school name and details
                if school_settings.school_name:
                    elements.append(Paragraph(f'<b>{school_settings.school_name}</b>', styles['Center']))
                    if school_settings.address:
                        elements.append(Paragraph(school_settings.address, styles['Center']))
                    if school_settings.phone or school_settings.email:
                        elements.append(Paragraph(f'Tel: {school_settings.phone} | Email: {school_settings.email}', styles['Center']))
            else:
                elements.append(Paragraph('<b>Ricas School Management System</b>', styles['Center']))

            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph('<b>PAYSLIP</b>', styles['Center']))
            elements.append(Spacer(1, 0.25*inch))

            # Employee information
            data = [
                ['Employee Name:', payslip.payroll.staff_salary.user.get_full_name()],
                ['Employee ID:', str(payslip.payroll.staff_salary.user.id)],
                ['Designation:', payslip.payroll.staff_salary.role.name if payslip.payroll.staff_salary.role else 'Not Assigned']
            ]
            employee_table = Table(data, colWidths=[2*inch, 3*inch])
            employee_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(employee_table)

            elements.append(Spacer(1, 0.25*inch))

            # Payslip details
            data = [
                ['Payslip No:', payslip.payslip_number],
                ['Pay Period:', payslip.payroll.period.name],
                ['Payment Date:', payslip.payroll.payment.payment_date.strftime('%b %d, %Y') if hasattr(payslip.payroll, 'payment') and payslip.payroll.payment and payslip.payroll.payment.payment_date else '-']
            ]
            details_table = Table(data, colWidths=[2*inch, 3*inch])
            details_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(details_table)

            elements.append(Spacer(1, 0.5*inch))

            # Earnings
            elements.append(Paragraph('<b>Earnings</b>', styles['Normal']))
            data = [
                ['Description', 'Amount (GH₵)'],
                ['Basic Salary', f"{payslip.payroll.base_salary:.2f}"],
                ['Transport Allowance', f"{payslip.payroll.transport_allowance:.2f}"],
                ['Housing Allowance', f"{payslip.payroll.housing_allowance:.2f}"],
                ['Other Allowances', f"{payslip.payroll.other_allowances:.2f}"],
                ['Gross Earnings', f"{payslip.payroll.gross_salary:.2f}"]
            ]
            earnings_table = Table(data, colWidths=[3*inch, 2*inch])
            earnings_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(earnings_table)

            elements.append(Spacer(1, 0.25*inch))

            # Deductions
            elements.append(Paragraph('<b>Deductions</b>', styles['Normal']))
            data = [
                ['Description', 'Amount (GH₵)'],
                ['SSNIT Contribution', f"{payslip.payroll.ssnit_deduction:.2f}"],
                ['Income Tax', f"{payslip.payroll.tax_deduction:.2f}"]
            ]

            # Add other deductions if any
            if payslip.payroll.other_deductions > 0:
                data.append(['Other Deductions', f"{payslip.payroll.other_deductions:.2f}"])

            # Add total deductions
            data.append(['Total Deductions', f"{payslip.payroll.total_deductions:.2f}"])

            deductions_table = Table(data, colWidths=[3*inch, 2*inch])
            deductions_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(deductions_table)

            elements.append(Spacer(1, 0.5*inch))

            # Net Pay
            data = [
                [f"Net Pay: GH₵ {payslip.payroll.net_salary:.2f}", f"Amount in Words: {amount_in_words}"]
            ]
            net_pay_table = Table(data, colWidths=[2.5*inch, 3.5*inch])
            net_pay_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(net_pay_table)

            elements.append(Spacer(1, inch))

            # Signature
            data = [
                ['_______________________', ''],
                [school_settings.principal_name if school_settings and school_settings.principal_name else 'Principal', f"Generated on: {payslip.generated_at.strftime('%b %d, %Y %H:%M')}"],
                ['Principal', 'This is a computer-generated payslip.']
            ]
            signature_table = Table(data, colWidths=[3*inch, 3*inch])
            signature_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(signature_table)

            # Build the PDF
            doc.build(elements)

            # Get the value of the BytesIO buffer and save it to the payslip model
            pdf_value = buffer.getvalue()
            buffer.close()

            # Save the PDF to the payslip model
            payslip.pdf_file.save(
                f'{payslip.payslip_number}.pdf',
                ContentFile(pdf_value),
                save=True
            )

            success_count += 1
        except Exception:
            error_count += 1

    # Show appropriate messages
    if success_count > 0:
        messages.success(request, f'{success_count} payslips generated successfully.')
    if error_count > 0:
        messages.error(request, f'Failed to generate {error_count} payslips.')
    if skipped_count > 0:
        messages.warning(request, f'{skipped_count} payslips were skipped (already generated or period locked).')

    return redirect('payroll:payroll_list')

@login_required
@user_passes_test(is_admin_or_accountant)
def create_payment(request, payroll_id):
    """Create a payment for a payroll."""
    payroll = get_object_or_404(Payroll, id=payroll_id)

    # Check if payroll can be paid
    if payroll.status not in [Payroll.Status.APPROVED, Payroll.Status.PENDING]:
        messages.error(request, 'Only approved or pending payrolls can be paid.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    # Check if payment already exists
    if hasattr(payroll, 'payment'):
        messages.error(request, 'Payment already exists for this payroll.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    # Check if period is locked
    if payroll.period.is_locked:
        messages.error(request, f'Payroll period "{payroll.period.name}" is locked. Cannot create payment.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    if request.method == 'POST':
        # Get form data
        payment_date = request.POST.get('payment_date')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '')
        remarks = request.POST.get('remarks', '')

        # Validate required fields
        if not all([payment_date, payment_method]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('payroll:create_payment', payroll_id=payroll_id)

        # Create the payment
        try:
            payment = PayrollPayment.objects.create(
                payroll=payroll,
                amount=payroll.net_salary,
                payment_date=payment_date,
                payment_method=payment_method,
                transaction_id=transaction_id,
                remarks=remarks,
                paid_by=request.user
            )

            # Payment status is updated in the PayrollPayment.save() method

            messages.success(request, f'Payment for {payroll.staff_salary.user.get_full_name()} created successfully.')
            return redirect('payroll:payroll_detail', payroll_id=payroll_id)
        except Exception as e:
            messages.error(request, f'Error creating payment: {str(e)}')
            return redirect('payroll:create_payment', payroll_id=payroll_id)

    # GET request - show form
    context = {
        'payroll': payroll,
        'payment_methods': PayrollPayment.PaymentMethod.choices,
        'today': timezone.now().date(),
    }

    return render(request, 'payroll/admin/create_payment.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def payment_detail(request, payment_id):
    """View details of a payment."""
    payment = get_object_or_404(PayrollPayment, id=payment_id)

    context = {
        'payment': payment,
    }

    return render(request, 'payroll/admin/payment_detail.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def payslip_list(request):
    """List all payslips."""
    # Get filter parameters
    period_id = request.GET.get('period')
    is_emailed = request.GET.get('emailed')

    # Base query
    payslips = Payslip.objects.select_related(
        'payroll', 'payroll__staff_salary', 'payroll__staff_salary__user', 'payroll__period'
    )

    # Apply filters
    if period_id:
        payslips = payslips.filter(payroll__period_id=period_id)

    if is_emailed is not None:
        is_emailed_bool = is_emailed.lower() == 'true'
        payslips = payslips.filter(is_emailed=is_emailed_bool)

    # Order by generation date (newest first)
    payslips = payslips.order_by('-generated_at')

    # Pagination
    paginator = Paginator(payslips, 25)  # Show 25 payslips per page
    page = request.GET.get('page')
    payslips = paginator.get_page(page)

    # Get filter options for dropdowns
    periods = PayrollPeriod.objects.all().order_by('-start_date')

    context = {
        'payslips': payslips,
        'periods': periods,
        'selected_period': period_id,
        'selected_emailed': is_emailed,
    }

    return render(request, 'payroll/admin/payslip_list.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def generate_payslip(request, payroll_id):
    """Generate a payslip for a payroll."""
    payroll = get_object_or_404(Payroll, id=payroll_id)

    # Check if payroll is paid
    if payroll.status != Payroll.Status.PAID:
        messages.error(request, 'Only paid payrolls can have payslips generated.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    # Check if payslip already exists
    if hasattr(payroll, 'payslip'):
        messages.error(request, 'Payslip already exists for this payroll.')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

    # Generate the payslip
    try:
        # Generate a unique payslip number
        payslip_number = Payslip.generate_payslip_number(payroll)

        # Create the payslip record
        payslip = Payslip.objects.create(
            payroll=payroll,
            payslip_number=payslip_number,
            generated_by=request.user
        )

        # Generate PDF file using WeasyPrint
        try:
            # Get school settings
            school_settings = SchoolSettings.objects.first()

            # Calculate amount in words for the payslip
            amount_in_words = num_to_words(payroll.net_salary)

            # Prepare context for the PDF template
            context = {
                'payslip': payslip,
                'school_settings': school_settings,
                'amount_in_words': amount_in_words,
            }

            # Create a PDF buffer
            buffer = io.BytesIO()

            # Create the PDF document
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

            # Container for the 'Flowable' objects
            elements = []

            # Styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Center', alignment=1))
            styles.add(ParagraphStyle(name='Right', alignment=2))

            # School logo and header
            if school_settings:
                # Add school logo if available
                if school_settings.logo and hasattr(school_settings.logo, 'url'):
                    try:
                        logo_path = school_settings.logo.path
                        img = Image(logo_path, width=2*inch, height=1*inch)
                        img.hAlign = 'CENTER'
                        elements.append(img)
                        elements.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        # If there's an error with the logo, just continue without it
                        print(f"Error adding logo: {str(e)}")

                # Add school name and details
                if school_settings.school_name:
                    elements.append(Paragraph(f'<b>{school_settings.school_name}</b>', styles['Center']))
                    if school_settings.address:
                        elements.append(Paragraph(school_settings.address, styles['Center']))
                    if school_settings.phone or school_settings.email:
                        elements.append(Paragraph(f'Tel: {school_settings.phone} | Email: {school_settings.email}', styles['Center']))
            else:
                elements.append(Paragraph('<b>Ricas School Management System</b>', styles['Center']))

            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph('<b>PAYSLIP</b>', styles['Center']))
            elements.append(Spacer(1, 0.25*inch))

            # Employee information
            data = [
                ['Employee Name:', payslip.payroll.staff_salary.user.get_full_name()],
                ['Employee ID:', str(payslip.payroll.staff_salary.user.id)],
                ['Designation:', payslip.payroll.staff_salary.role.name if payslip.payroll.staff_salary.role else 'Not Assigned']
            ]
            employee_table = Table(data, colWidths=[2*inch, 3*inch])
            employee_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(employee_table)

            elements.append(Spacer(1, 0.25*inch))

            # Payslip details
            data = [
                ['Payslip No:', payslip.payslip_number],
                ['Pay Period:', payslip.payroll.period.name],
                ['Payment Date:', payslip.payroll.payment.payment_date.strftime('%b %d, %Y') if hasattr(payslip.payroll, 'payment') and payslip.payroll.payment and payslip.payroll.payment.payment_date else '-']
            ]
            details_table = Table(data, colWidths=[2*inch, 3*inch])
            details_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(details_table)

            elements.append(Spacer(1, 0.5*inch))

            # Earnings
            elements.append(Paragraph('<b>Earnings</b>', styles['Normal']))
            data = [
                ['Description', 'Amount (GH₵)'],
                ['Basic Salary', f"{payslip.payroll.base_salary:.2f}"],
                ['Transport Allowance', f"{payslip.payroll.transport_allowance:.2f}"],
                ['Housing Allowance', f"{payslip.payroll.housing_allowance:.2f}"],
                ['Other Allowances', f"{payslip.payroll.other_allowances:.2f}"],
                ['Gross Earnings', f"{payslip.payroll.gross_salary:.2f}"]
            ]
            earnings_table = Table(data, colWidths=[3*inch, 2*inch])
            earnings_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(earnings_table)

            elements.append(Spacer(1, 0.25*inch))

            # Deductions
            elements.append(Paragraph('<b>Deductions</b>', styles['Normal']))
            data = [
                ['Description', 'Amount (GH₵)'],
                ['SSNIT Contribution', f"{payslip.payroll.ssnit_deduction:.2f}"],
                ['Income Tax', f"{payslip.payroll.tax_deduction:.2f}"]
            ]

            # Add other deductions if any
            if payslip.payroll.other_deductions > 0:
                data.append(['Other Deductions', f"{payslip.payroll.other_deductions:.2f}"])

            # Add total deductions
            data.append(['Total Deductions', f"{payslip.payroll.total_deductions:.2f}"])

            deductions_table = Table(data, colWidths=[3*inch, 2*inch])
            deductions_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(deductions_table)

            elements.append(Spacer(1, 0.5*inch))

            # Net Pay
            data = [
                [f"Net Pay: GH₵ {payslip.payroll.net_salary:.2f}", f"Amount in Words: {amount_in_words}"]
            ]
            net_pay_table = Table(data, colWidths=[2.5*inch, 3.5*inch])
            net_pay_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(net_pay_table)

            elements.append(Spacer(1, inch))

            # Signature
            data = [
                ['_______________________', ''],
                [school_settings.principal_name if school_settings and school_settings.principal_name else 'Principal', f"Generated on: {payslip.generated_at.strftime('%b %d, %Y %H:%M')}"],
                ['Principal', 'This is a computer-generated payslip.']
            ]
            signature_table = Table(data, colWidths=[3*inch, 3*inch])
            signature_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(signature_table)

            # Build the PDF
            doc.build(elements)

            # Get the value of the BytesIO buffer and save it to the payslip model
            pdf_value = buffer.getvalue()
            buffer.close()

            # Save the PDF to the payslip model
            payslip.pdf_file.save(
                f'{payslip.payslip_number}.pdf',
                ContentFile(pdf_value),
                save=True
            )

            messages.success(request, f'Payslip for {payroll.staff_salary.user.get_full_name()} generated successfully.')
            return redirect('payroll:payslip_detail', payslip_id=payslip.id)
        except Exception as e:
            messages.error(request, f'Error generating PDF: {str(e)}')
            return redirect('payroll:payslip_detail', payslip_id=payslip.id)
    except Exception as e:
        messages.error(request, f'Error generating payslip: {str(e)}')
        return redirect('payroll:payroll_detail', payroll_id=payroll_id)

@login_required
@user_passes_test(is_admin_or_accountant)
def payslip_detail(request, payslip_id):
    """View details of a payslip."""
    payslip = get_object_or_404(Payslip, id=payslip_id)

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    # Calculate amount in words for the payslip
    amount_in_words = num_to_words(payslip.payroll.net_salary)

    context = {
        'payslip': payslip,
        'school_settings': school_settings,
        'amount_in_words': amount_in_words,
    }

    return render(request, 'payroll/admin/payslip_detail.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def download_payslip(request, payslip_id):
    """Download a payslip as PDF."""
    payslip = get_object_or_404(Payslip, id=payslip_id)

    # Check if PDF exists
    if not payslip.pdf_file:
        # Generate PDF on-the-fly if it doesn't exist
        try:
            # Get school settings
            school_settings = SchoolSettings.objects.first()

            # Calculate amount in words for the payslip
            amount_in_words = num_to_words(payslip.payroll.net_salary)

            # Prepare context for the PDF template
            context = {
                'payslip': payslip,
                'school_settings': school_settings,
                'amount_in_words': amount_in_words,
            }

            # Create a PDF buffer
            buffer = io.BytesIO()

            # Create the PDF document
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

            # Container for the 'Flowable' objects
            elements = []

            # Styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Center', alignment=1))
            styles.add(ParagraphStyle(name='Right', alignment=2))

            # School logo and header
            if school_settings:
                # Add school logo if available
                if school_settings.logo and hasattr(school_settings.logo, 'url'):
                    try:
                        logo_path = school_settings.logo.path
                        img = Image(logo_path, width=2*inch, height=1*inch)
                        img.hAlign = 'CENTER'
                        elements.append(img)
                        elements.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        # If there's an error with the logo, just continue without it
                        print(f"Error adding logo: {str(e)}")

                # Add school name and details
                if school_settings.school_name:
                    elements.append(Paragraph(f'<b>{school_settings.school_name}</b>', styles['Center']))
                    if school_settings.address:
                        elements.append(Paragraph(school_settings.address, styles['Center']))
                    if school_settings.phone or school_settings.email:
                        elements.append(Paragraph(f'Tel: {school_settings.phone} | Email: {school_settings.email}', styles['Center']))
            else:
                elements.append(Paragraph('<b>Ricas School Management System</b>', styles['Center']))

            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph('<b>PAYSLIP</b>', styles['Center']))
            elements.append(Spacer(1, 0.25*inch))

            # Employee information
            data = [
                ['Employee Name:', payslip.payroll.staff_salary.user.get_full_name()],
                ['Employee ID:', str(payslip.payroll.staff_salary.user.id)],
                ['Designation:', payslip.payroll.staff_salary.role.name if payslip.payroll.staff_salary.role else 'Not Assigned']
            ]
            employee_table = Table(data, colWidths=[2*inch, 3*inch])
            employee_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(employee_table)

            elements.append(Spacer(1, 0.25*inch))

            # Payslip details
            data = [
                ['Payslip No:', payslip.payslip_number],
                ['Pay Period:', payslip.payroll.period.name],
                ['Payment Date:', payslip.payroll.payment.payment_date.strftime('%b %d, %Y') if hasattr(payslip.payroll, 'payment') and payslip.payroll.payment and payslip.payroll.payment.payment_date else '-']
            ]
            details_table = Table(data, colWidths=[2*inch, 3*inch])
            details_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(details_table)

            elements.append(Spacer(1, 0.5*inch))

            # Earnings
            elements.append(Paragraph('<b>Earnings</b>', styles['Normal']))
            data = [
                ['Description', 'Amount (GH₵)'],
                ['Basic Salary', f"{payslip.payroll.base_salary:.2f}"],
                ['Transport Allowance', f"{payslip.payroll.transport_allowance:.2f}"],
                ['Housing Allowance', f"{payslip.payroll.housing_allowance:.2f}"],
                ['Other Allowances', f"{payslip.payroll.other_allowances:.2f}"],
                ['Gross Earnings', f"{payslip.payroll.gross_salary:.2f}"]
            ]
            earnings_table = Table(data, colWidths=[3*inch, 2*inch])
            earnings_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(earnings_table)

            elements.append(Spacer(1, 0.25*inch))

            # Deductions
            elements.append(Paragraph('<b>Deductions</b>', styles['Normal']))
            data = [
                ['Description', 'Amount (GH₵)'],
                ['SSNIT Contribution', f"{payslip.payroll.ssnit_deduction:.2f}"],
                ['Income Tax', f"{payslip.payroll.tax_deduction:.2f}"]
            ]

            # Add other deductions if any
            if payslip.payroll.other_deductions > 0:
                data.append(['Other Deductions', f"{payslip.payroll.other_deductions:.2f}"])

            # Add total deductions
            data.append(['Total Deductions', f"{payslip.payroll.total_deductions:.2f}"])

            deductions_table = Table(data, colWidths=[3*inch, 2*inch])
            deductions_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(deductions_table)

            elements.append(Spacer(1, 0.5*inch))

            # Net Pay
            data = [
                [f"Net Pay: GH₵ {payslip.payroll.net_salary:.2f}", f"Amount in Words: {amount_in_words}"]
            ]
            net_pay_table = Table(data, colWidths=[2.5*inch, 3.5*inch])
            net_pay_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(net_pay_table)

            elements.append(Spacer(1, inch))

            # Signature
            data = [
                ['_______________________', ''],
                [school_settings.principal_name if school_settings and school_settings.principal_name else 'Principal', f"Generated on: {payslip.generated_at.strftime('%b %d, %Y %H:%M')}"],
                ['Principal', 'This is a computer-generated payslip.']
            ]
            signature_table = Table(data, colWidths=[3*inch, 3*inch])
            signature_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(signature_table)

            # Build the PDF
            doc.build(elements)

            # Get the value of the BytesIO buffer and save it to the payslip model
            pdf_value = buffer.getvalue()
            buffer.close()

            # Save the PDF to the payslip model
            payslip.pdf_file.save(
                f'{payslip.payslip_number}.pdf',
                ContentFile(pdf_value),
                save=True
            )
        except Exception as e:
            messages.error(request, f'Error generating PDF: {str(e)}')
            return redirect('payroll:payslip_detail', payslip_id=payslip_id)

    # Return the PDF file
    response = HttpResponse(payslip.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{payslip.payslip_number}.pdf"'
    return response

@login_required
@user_passes_test(is_admin_or_accountant)
def email_payslip(request, payslip_id):
    """Email a payslip to the staff member."""
    payslip = get_object_or_404(Payslip, id=payslip_id)

    # Check if PDF exists
    if not payslip.pdf_file:
        # Generate PDF on-the-fly if it doesn't exist
        try:
            # Get school settings
            school_settings = SchoolSettings.objects.first()

            # Calculate amount in words for the payslip
            amount_in_words = num_to_words(payslip.payroll.net_salary)

            # Prepare context for the PDF template
            context = {
                'payslip': payslip,
                'school_settings': school_settings,
                'amount_in_words': amount_in_words,
            }

            # Create a PDF buffer
            buffer = io.BytesIO()

            # Create the PDF document
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

            # Container for the 'Flowable' objects
            elements = []

            # Styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Center', alignment=1))
            styles.add(ParagraphStyle(name='Right', alignment=2))

            # School logo and header
            if school_settings:
                # Add school logo if available
                if school_settings.logo and hasattr(school_settings.logo, 'url'):
                    try:
                        logo_path = school_settings.logo.path
                        img = Image(logo_path, width=2*inch, height=1*inch)
                        img.hAlign = 'CENTER'
                        elements.append(img)
                        elements.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        # If there's an error with the logo, just continue without it
                        print(f"Error adding logo: {str(e)}")

                # Add school name and details
                if school_settings.school_name:
                    elements.append(Paragraph(f'<b>{school_settings.school_name}</b>', styles['Center']))
                    if school_settings.address:
                        elements.append(Paragraph(school_settings.address, styles['Center']))
                    if school_settings.phone or school_settings.email:
                        elements.append(Paragraph(f'Tel: {school_settings.phone} | Email: {school_settings.email}', styles['Center']))
            else:
                elements.append(Paragraph('<b>Ricas School Management System</b>', styles['Center']))

            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph('<b>PAYSLIP</b>', styles['Center']))
            elements.append(Spacer(1, 0.25*inch))

            # Employee information
            data = [
                ['Employee Name:', payslip.payroll.staff_salary.user.get_full_name()],
                ['Employee ID:', str(payslip.payroll.staff_salary.user.id)],
                ['Designation:', payslip.payroll.staff_salary.role.name if payslip.payroll.staff_salary.role else 'Not Assigned']
            ]
            employee_table = Table(data, colWidths=[2*inch, 3*inch])
            employee_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(employee_table)

            elements.append(Spacer(1, 0.25*inch))

            # Payslip details
            data = [
                ['Payslip No:', payslip.payslip_number],
                ['Pay Period:', payslip.payroll.period.name],
                ['Payment Date:', payslip.payroll.payment.payment_date.strftime('%b %d, %Y') if hasattr(payslip.payroll, 'payment') and payslip.payroll.payment and payslip.payroll.payment.payment_date else '-']
            ]
            details_table = Table(data, colWidths=[2*inch, 3*inch])
            details_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(details_table)

            elements.append(Spacer(1, 0.5*inch))

            # Earnings
            elements.append(Paragraph('<b>Earnings</b>', styles['Normal']))
            data = [
                ['Description', 'Amount (GH₵)'],
                ['Basic Salary', f"{payslip.payroll.base_salary:.2f}"],
                ['Transport Allowance', f"{payslip.payroll.transport_allowance:.2f}"],
                ['Housing Allowance', f"{payslip.payroll.housing_allowance:.2f}"],
                ['Other Allowances', f"{payslip.payroll.other_allowances:.2f}"],
                ['Gross Earnings', f"{payslip.payroll.gross_salary:.2f}"]
            ]
            earnings_table = Table(data, colWidths=[3*inch, 2*inch])
            earnings_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(earnings_table)

            elements.append(Spacer(1, 0.25*inch))

            # Deductions
            elements.append(Paragraph('<b>Deductions</b>', styles['Normal']))
            data = [
                ['Description', 'Amount (GH₵)'],
                ['SSNIT Contribution', f"{payslip.payroll.ssnit_deduction:.2f}"],
                ['Income Tax', f"{payslip.payroll.tax_deduction:.2f}"]
            ]

            # Add other deductions if any
            if payslip.payroll.other_deductions > 0:
                data.append(['Other Deductions', f"{payslip.payroll.other_deductions:.2f}"])

            # Add total deductions
            data.append(['Total Deductions', f"{payslip.payroll.total_deductions:.2f}"])

            deductions_table = Table(data, colWidths=[3*inch, 2*inch])
            deductions_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(deductions_table)

            elements.append(Spacer(1, 0.5*inch))

            # Net Pay
            data = [
                [f"Net Pay: GH₵ {payslip.payroll.net_salary:.2f}", f"Amount in Words: {amount_in_words}"]
            ]
            net_pay_table = Table(data, colWidths=[2.5*inch, 3.5*inch])
            net_pay_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(net_pay_table)

            elements.append(Spacer(1, inch))

            # Signature
            data = [
                ['_______________________', ''],
                [school_settings.principal_name if school_settings and school_settings.principal_name else 'Principal', f"Generated on: {payslip.generated_at.strftime('%b %d, %Y %H:%M')}"],
                ['Principal', 'This is a computer-generated payslip.']
            ]
            signature_table = Table(data, colWidths=[3*inch, 3*inch])
            signature_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(signature_table)

            # Build the PDF
            doc.build(elements)

            # Get the value of the BytesIO buffer and save it to the payslip model
            pdf_value = buffer.getvalue()
            buffer.close()

            # Save the PDF to the payslip model
            payslip.pdf_file.save(
                f'{payslip.payslip_number}.pdf',
                ContentFile(pdf_value),
                save=True
            )
        except Exception as e:
            messages.error(request, f'Error generating PDF: {str(e)}')
            return redirect('payroll:payslip_detail', payslip_id=payslip_id)

    # Get staff email
    staff_email = payslip.payroll.staff_salary.user.email

    if not staff_email:
        messages.error(request, 'Staff member does not have an email address.')
        return redirect('payroll:payslip_detail', payslip_id=payslip_id)

    # TODO: Send email with payslip attachment
    # This would be implemented with Django's email functionality

    # Update payslip record
    payslip.is_emailed = True
    payslip.emailed_at = timezone.now()
    payslip.save()

    messages.success(request, f'Payslip emailed to {staff_email} successfully.')
    return redirect('payroll:payslip_detail', payslip_id=payslip_id)

@login_required
@user_passes_test(is_admin_or_accountant)
def monthly_salary_report(request):
    """Generate monthly salary report."""
    # Get filter parameters
    period_id = request.GET.get('period')
    role_id = request.GET.get('role')

    # Get periods for filter
    periods = PayrollPeriod.objects.all().order_by('-start_date')
    roles = StaffRole.objects.filter(is_active=True).order_by('name')

    # If no period selected, use the most recent one
    if not period_id and periods.exists():
        period_id = periods.first().id

    # Base query
    payrolls = Payroll.objects.select_related(
        'staff_salary', 'staff_salary__user', 'staff_salary__role', 'period'
    )

    # Apply filters
    if period_id:
        payrolls = payrolls.filter(period_id=period_id)

    if role_id:
        payrolls = payrolls.filter(staff_salary__role_id=role_id)

    # Order by staff name
    payrolls = payrolls.order_by('staff_salary__user__first_name', 'staff_salary__user__last_name')

    # Calculate totals
    total_gross = payrolls.aggregate(total=Sum('gross_salary'))['total'] or 0
    total_deductions = payrolls.aggregate(total=Sum('total_deductions'))['total'] or 0
    total_net = payrolls.aggregate(total=Sum('net_salary'))['total'] or 0

    # Get payment status
    paid_count = payrolls.filter(status=Payroll.Status.PAID).count()
    pending_count = payrolls.filter(status__in=[Payroll.Status.PENDING, Payroll.Status.APPROVED]).count()
    total_count = payrolls.count()
    payment_rate = (paid_count / total_count * 100) if total_count > 0 else 0

    # Role-based breakdown
    role_breakdown = []
    for role in roles:
        role_payrolls = payrolls.filter(staff_salary__role=role)
        role_count = role_payrolls.count()

        if role_count > 0:
            role_total = role_payrolls.aggregate(total=Sum('net_salary'))['total'] or 0
            role_breakdown.append({
                'role': role,
                'count': role_count,
                'total': role_total,
                'average': role_total / role_count
            })

    context = {
        'payrolls': payrolls,
        'periods': periods,
        'roles': roles,
        'selected_period': period_id,
        'selected_role': role_id,
        'total_gross': total_gross,
        'total_deductions': total_deductions,
        'total_net': total_net,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'total_count': total_count,
        'payment_rate': payment_rate,
        'role_breakdown': role_breakdown,
    }

    return render(request, 'payroll/admin/monthly_salary_report.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def staff_payment_history(request):
    """View payment history for a staff member."""
    # Get filter parameters
    staff_id = request.GET.get('staff')
    year = request.GET.get('year')

    # Get staff with salary for filter
    staff_with_salary = StaffSalary.objects.select_related('user').order_by('user__first_name', 'user__last_name')

    # Get years for filter
    current_year = timezone.now().year
    years = list(range(current_year - 5, current_year + 1))

    if not year:
        year = current_year

    # Base query
    if staff_id:
        # Get the staff salary
        staff_salary = get_object_or_404(StaffSalary, id=staff_id)

        # Get payrolls for this staff
        payrolls = Payroll.objects.filter(
            staff_salary=staff_salary,
            period__start_date__year=year
        ).select_related('period', 'staff_salary', 'staff_salary__user').order_by('-period__start_date')

        # Get payments for this staff
        payments = PayrollPayment.objects.filter(
            payroll__staff_salary=staff_salary,
            payment_date__year=year
        ).select_related('payroll', 'payroll__period').order_by('-payment_date')

        # Calculate totals
        total_gross = payrolls.aggregate(total=Sum('gross_salary'))['total'] or 0
        total_deductions = payrolls.aggregate(total=Sum('total_deductions'))['total'] or 0
        total_net = payrolls.aggregate(total=Sum('net_salary'))['total'] or 0
        total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0

        # Monthly breakdown
        monthly_breakdown = []
        for month in range(1, 13):
            month_payrolls = payrolls.filter(period__start_date__month=month)
            month_payments = payments.filter(payment_date__month=month)

            if month_payrolls.exists() or month_payments.exists():
                month_name = timezone.datetime(year=2000, month=month, day=1).strftime('%B')
                month_gross = month_payrolls.aggregate(total=Sum('gross_salary'))['total'] or 0
                month_deductions = month_payrolls.aggregate(total=Sum('total_deductions'))['total'] or 0
                month_net = month_payrolls.aggregate(total=Sum('net_salary'))['total'] or 0
                month_paid = month_payments.aggregate(total=Sum('amount'))['total'] or 0

                monthly_breakdown.append({
                    'month': month_name,
                    'gross': month_gross,
                    'deductions': month_deductions,
                    'net': month_net,
                    'paid': month_paid,
                })

        context = {
            'staff_salary': staff_salary,
            'payrolls': payrolls,
            'payments': payments,
            'staff_with_salary': staff_with_salary,
            'years': years,
            'selected_staff': staff_id,
            'selected_year': year,
            'total_gross': total_gross,
            'total_deductions': total_deductions,
            'total_net': total_net,
            'total_paid': total_paid,
            'monthly_breakdown': monthly_breakdown,
        }
    else:
        # No staff selected
        context = {
            'staff_with_salary': staff_with_salary,
            'years': years,
            'selected_year': year,
        }

    return render(request, 'payroll/admin/staff_payment_history.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def unpaid_staff_report(request):
    """Report of staff with unpaid salaries."""
    # Get filter parameters
    period_id = request.GET.get('period')
    role_id = request.GET.get('role')

    # Get periods for filter
    periods = PayrollPeriod.objects.all().order_by('-start_date')
    roles = StaffRole.objects.filter(is_active=True).order_by('name')

    # If no period selected, use the most recent one
    if not period_id and periods.exists():
        period_id = periods.first().id

    # Base query - get payrolls that are not paid
    payrolls = Payroll.objects.filter(
        status__in=[Payroll.Status.PENDING, Payroll.Status.APPROVED]
    ).select_related(
        'staff_salary', 'staff_salary__user', 'staff_salary__role', 'period'
    )

    # Apply filters
    if period_id:
        payrolls = payrolls.filter(period_id=period_id)

    if role_id:
        payrolls = payrolls.filter(staff_salary__role_id=role_id)

    # Order by staff name
    payrolls = payrolls.order_by('staff_salary__user__first_name', 'staff_salary__user__last_name')

    # Calculate total unpaid amount
    total_unpaid = payrolls.aggregate(total=Sum('net_salary'))['total'] or 0

    context = {
        'payrolls': payrolls,
        'periods': periods,
        'roles': roles,
        'selected_period': period_id,
        'selected_role': role_id,
        'total_unpaid': total_unpaid,
    }

    return render(request, 'payroll/admin/unpaid_staff_report.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def export_payroll_data(request):
    """Export payroll data to CSV."""
    # Get filter parameters
    period_id = request.GET.get('period')
    role_id = request.GET.get('role')
    export_type = request.GET.get('type', 'payroll')  # payroll, payments, or staff

    # Validate export type
    if export_type not in ['payroll', 'payments', 'staff']:
        messages.error(request, 'Invalid export type.')
        return redirect('payroll:monthly_salary_report')

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{export_type}_export.csv"'

    # Create CSV writer
    import csv
    writer = csv.writer(response)

    if export_type == 'payroll':
        # Export payroll data
        # Base query
        payrolls = Payroll.objects.select_related(
            'staff_salary', 'staff_salary__user', 'staff_salary__role', 'period'
        )

        # Apply filters
        if period_id:
            payrolls = payrolls.filter(period_id=period_id)

        if role_id:
            payrolls = payrolls.filter(staff_salary__role_id=role_id)

        # Order by staff name
        payrolls = payrolls.order_by('staff_salary__user__first_name', 'staff_salary__user__last_name')

        # Write header
        writer.writerow([
            'Staff ID', 'Name', 'Role', 'Period', 'Base Salary', 'Allowances',
            'Gross Salary', 'Deductions', 'Net Salary', 'Status'
        ])

        # Write data
        for payroll in payrolls:
            writer.writerow([
                payroll.staff_salary.user.id,
                payroll.staff_salary.user.get_full_name(),
                payroll.staff_salary.role.name if payroll.staff_salary.role else '',
                payroll.period.name,
                payroll.base_salary,
                payroll.transport_allowance + payroll.housing_allowance + payroll.other_allowances,
                payroll.gross_salary,
                payroll.total_deductions,
                payroll.net_salary,
                payroll.get_status_display()
            ])

    elif export_type == 'payments':
        # Export payment data
        # Base query
        payments = PayrollPayment.objects.select_related(
            'payroll', 'payroll__staff_salary', 'payroll__staff_salary__user', 'payroll__period'
        )

        # Apply filters
        if period_id:
            payments = payments.filter(payroll__period_id=period_id)

        if role_id:
            payments = payments.filter(payroll__staff_salary__role_id=role_id)

        # Order by payment date
        payments = payments.order_by('-payment_date')

        # Write header
        writer.writerow([
            'Staff ID', 'Name', 'Period', 'Amount', 'Payment Date',
            'Payment Method', 'Transaction ID', 'Remarks'
        ])

        # Write data
        for payment in payments:
            writer.writerow([
                payment.payroll.staff_salary.user.id,
                payment.payroll.staff_salary.user.get_full_name(),
                payment.payroll.period.name,
                payment.amount,
                payment.payment_date,
                payment.get_payment_method_display(),
                payment.transaction_id or '',
                payment.remarks or ''
            ])

    elif export_type == 'staff':
        # Export staff salary data
        # Base query
        staff_salaries = StaffSalary.objects.select_related('user', 'role')

        # Apply filters
        if role_id:
            staff_salaries = staff_salaries.filter(role_id=role_id)

        # Order by staff name
        staff_salaries = staff_salaries.order_by('user__first_name', 'user__last_name')

        # Write header
        writer.writerow([
            'Staff ID', 'Name', 'Role', 'Base Salary', 'Transport Allowance',
            'Housing Allowance', 'Other Allowances', 'SSNIT Contribution',
            'Tax Rate', 'Gross Salary', 'Net Salary', 'Effective Date'
        ])

        # Write data
        for salary in staff_salaries:
            writer.writerow([
                salary.user.id,
                salary.user.get_full_name(),
                salary.role.name if salary.role else '',
                salary.base_salary,
                salary.transport_allowance,
                salary.housing_allowance,
                salary.other_allowances,
                salary.ssnit_contribution,
                f"{salary.tax_rate}%",
                salary.gross_salary,
                salary.net_salary,
                salary.effective_date
            ])

    return response

# Staff Portal Views
@login_required
def staff_dashboard(request):
    """Staff payroll dashboard."""
    user = request.user

    # Check if user has a salary
    try:
        staff_salary = StaffSalary.objects.get(user=user)
    except StaffSalary.DoesNotExist:
        messages.error(request, 'You do not have a salary record in the system.')
        return redirect('dashboard:index')

    # Get payrolls for this staff
    payrolls = Payroll.objects.filter(
        staff_salary=staff_salary
    ).select_related('period').order_by('-period__start_date')[:5]

    # Get recent payments for this staff
    payments = PayrollPayment.objects.filter(
        payroll__staff_salary=staff_salary
    ).select_related('payroll', 'payroll__period').order_by('-payment_date')[:5]

    # Calculate totals
    total_gross = payrolls.aggregate(total=Sum('gross_salary'))['total'] or 0
    total_deductions = payrolls.aggregate(total=Sum('total_deductions'))['total'] or 0
    total_net = payrolls.aggregate(total=Sum('net_salary'))['total'] or 0
    total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'staff_salary': staff_salary,
        'payrolls': payrolls,
        'payments': payments,
        'total_gross': total_gross,
        'total_deductions': total_deductions,
        'total_net': total_net,
        'total_paid': total_paid,
    }

    return render(request, 'payroll/staff/dashboard.html', context)

@login_required
def staff_payslips(request):
    """View own payslips (for staff members)."""
    user = request.user

    # Check if user has a salary
    try:
        staff_salary = StaffSalary.objects.get(user=user)
    except StaffSalary.DoesNotExist:
        messages.error(request, 'You do not have a salary record in the system.')
        return redirect('dashboard:index')

    # Get payrolls for this staff
    payrolls = Payroll.objects.filter(
        staff_salary=staff_salary,
        status=Payroll.Status.PAID  # Only show paid payrolls
    ).select_related('period').order_by('-period__start_date')

    # Get payslips for this staff
    payslips = Payslip.objects.filter(
        payroll__staff_salary=staff_salary
    ).select_related('payroll', 'payroll__period').order_by('-generated_at')

    context = {
        'staff_salary': staff_salary,
        'payrolls': payrolls,
        'payslips': payslips,
    }

    return render(request, 'payroll/staff/staff_payslips.html', context)

@login_required
def staff_payment_history(request):
    """View own payment history (for staff members)."""
    user = request.user

    # Get filter parameters
    year = request.GET.get('year')

    # Get years for filter
    current_year = timezone.now().year
    years = list(range(current_year - 5, current_year + 1))

    if not year:
        year = current_year

    # Check if user has a salary
    try:
        staff_salary = StaffSalary.objects.get(user=user)
    except StaffSalary.DoesNotExist:
        messages.error(request, 'You do not have a salary record in the system.')
        return redirect('dashboard:index')

    # Get payrolls for this staff for the selected year
    payrolls = Payroll.objects.filter(
        staff_salary=staff_salary,
        period__start_date__year=year
    ).select_related('period').order_by('-period__start_date')

    # Get payments for this staff for the selected year
    payments = PayrollPayment.objects.filter(
        payroll__staff_salary=staff_salary,
        payment_date__year=year
    ).select_related('payroll', 'payroll__period').order_by('-payment_date')

    # Calculate totals
    total_gross = payrolls.aggregate(total=Sum('gross_salary'))['total'] or 0
    total_deductions = payrolls.aggregate(total=Sum('total_deductions'))['total'] or 0
    total_net = payrolls.aggregate(total=Sum('net_salary'))['total'] or 0
    total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0

    # Generate monthly breakdown
    monthly_breakdown = []
    for month in range(1, 13):
        month_name = calendar.month_name[month]

        # Get payrolls for this month
        month_payrolls = payrolls.filter(period__start_date__month=month)

        # Get payments for this month
        month_payments = payments.filter(payment_date__month=month)

        # Calculate totals for this month
        month_gross = month_payrolls.aggregate(total=Sum('gross_salary'))['total'] or 0
        month_deductions = month_payrolls.aggregate(total=Sum('total_deductions'))['total'] or 0
        month_net = month_payrolls.aggregate(total=Sum('net_salary'))['total'] or 0
        month_paid = month_payments.aggregate(total=Sum('amount'))['total'] or 0

        # Only add months with data
        if month_gross > 0 or month_paid > 0:
            monthly_breakdown.append({
                'month': month_name,
                'gross': month_gross,
                'deductions': month_deductions,
                'net': month_net,
                'paid': month_paid
            })

    context = {
        'staff_salary': staff_salary,
        'payrolls': payrolls,
        'payments': payments,
        'years': years,
        'selected_year': year,
        'total_gross': total_gross,
        'total_deductions': total_deductions,
        'total_net': total_net,
        'total_paid': total_paid,
        'monthly_breakdown': monthly_breakdown,
    }

    return render(request, 'payroll/staff/staff_payment_history.html', context)

@login_required
def staff_payslip_detail(request, payslip_id):
    """View details of own payslip (for staff members)."""
    user = request.user

    # Get the payslip
    payslip = get_object_or_404(Payslip, id=payslip_id)

    # Check if this payslip belongs to the user
    if payslip.payroll.staff_salary.user != user:
        messages.error(request, 'You do not have permission to view this payslip.')
        return redirect('payroll:staff_payslips')

    # Get school settings
    school_settings = SchoolSettings.objects.first()

    # Calculate amount in words for the payslip
    amount_in_words = num_to_words(payslip.payroll.net_salary)

    context = {
        'payslip': payslip,
        'school_settings': school_settings,
        'amount_in_words': amount_in_words,
    }

    return render(request, 'payroll/staff/staff_payslip_detail.html', context)

@login_required
def staff_download_payslip(request, payslip_id):
    """Download own payslip as PDF (for staff members)."""
    user = request.user

    # Get the payslip
    payslip = get_object_or_404(Payslip, id=payslip_id)

    # Check if this payslip belongs to the user
    if payslip.payroll.staff_salary.user != user:
        messages.error(request, 'You do not have permission to download this payslip.')
        return redirect('payroll:staff_payslips')

    # Check if PDF exists
    if not payslip.pdf_file:
        # Generate PDF on-the-fly if it doesn't exist
        try:
            # Get school settings
            school_settings = SchoolSettings.objects.first()

            # Calculate amount in words for the payslip
            amount_in_words = num_to_words(payslip.payroll.net_salary)

            # Prepare context for the PDF template
            context = {
                'payslip': payslip,
                'school_settings': school_settings,
                'amount_in_words': amount_in_words,
            }

            # Render the HTML template
            template = get_template('payroll/admin/payslip_pdf.html')
            html_string = template.render(context)

            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                # Generate PDF using WeasyPrint
                HTML(string=html_string).write_pdf(
                    tmp_file.name,
                    stylesheets=[CSS(string='@page { size: A4; margin: 1cm; }')]
                )

                # Save the PDF to the payslip model
                with open(tmp_file.name, 'rb') as pdf_file:
                    payslip.pdf_file.save(
                        f'{payslip.payslip_number}.pdf',
                        ContentFile(pdf_file.read()),
                        save=True
                    )

                # Clean up the temporary file
                os.unlink(tmp_file.name)
        except Exception as e:
            messages.error(request, f'Error generating PDF: {str(e)}')
            return redirect('payroll:staff_payslip_detail', payslip_id=payslip_id)

    # Return the PDF file
    response = HttpResponse(payslip.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{payslip.payslip_number}.pdf"'
    return response