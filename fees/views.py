from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.conf import settings
from django.urls import reverse
from django.db import transaction
from decimal import Decimal

from users.models import CustomUser, Student, SchoolSettings
from courses.models import ClassRoom
from .models import Term, FeeCategory, ClassFee, StudentFee, Payment, Receipt

# Helper functions for role-based access
def is_admin_or_accountant(user):
    return user.is_authenticated and (user.role == CustomUser.Role.ADMIN or
                                     user.role == 'ACCOUNTANT')

# Admin/Accountant views
@login_required
@user_passes_test(is_admin_or_accountant)
def admin_fees_dashboard(request):
    """Dashboard for fee management."""
    # Get current term
    current_term = Term.objects.filter(is_current=True).first()

    # Summary statistics
    total_expected = StudentFee.objects.filter(
        class_fee__term=current_term
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_collected = StudentFee.objects.filter(
        class_fee__term=current_term
    ).aggregate(total=Sum('amount_paid'))['total'] or 0

    total_outstanding = total_expected - total_collected

    collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else 0

    # Recent payments
    recent_payments = Payment.objects.select_related(
        'student_fee', 'student_fee__student', 'student_fee__student__user',
        'student_fee__class_fee', 'student_fee__class_fee__fee_category'
    ).order_by('-created_at')[:10]

    # Students with outstanding fees
    students_with_balance = StudentFee.objects.filter(
        class_fee__term=current_term,
        balance__gt=0
    ).select_related(
        'student', 'student__user', 'class_fee', 'class_fee__classroom'
    ).order_by('-balance')[:10]

    # Fee collection by category
    fee_categories = FeeCategory.objects.filter(is_active=True)
    category_stats = []

    for category in fee_categories:
        category_fees = StudentFee.objects.filter(
            class_fee__term=current_term,
            class_fee__fee_category=category
        )

        expected = category_fees.aggregate(total=Sum('amount'))['total'] or 0
        collected = category_fees.aggregate(total=Sum('amount_paid'))['total'] or 0

        if expected > 0:
            category_stats.append({
                'category': category,
                'expected': expected,
                'collected': collected,
                'outstanding': expected - collected,
                'collection_rate': (collected / expected * 100) if expected > 0 else 0
            })

    context = {
        'current_term': current_term,
        'total_expected': total_expected,
        'total_collected': total_collected,
        'total_outstanding': total_outstanding,
        'collection_rate': collection_rate,
        'recent_payments': recent_payments,
        'students_with_balance': students_with_balance,
        'category_stats': category_stats,
    }

    return render(request, 'fees/admin/dashboard.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def fee_category_list(request):
    """List all fee categories."""
    categories = FeeCategory.objects.all().order_by('name')
    return render(request, 'fees/admin/category_list.html', {'categories': categories})

@login_required
@user_passes_test(is_admin_or_accountant)
def create_fee_category(request):
    """Create a new fee category."""
    if request.method == 'POST':
        # Process form data
        name = request.POST.get('name')
        category_type = request.POST.get('category_type')
        description = request.POST.get('description')
        is_required = request.POST.get('is_required') == 'on'
        is_recurring = request.POST.get('is_recurring') == 'on'

        try:
            FeeCategory.objects.create(
                name=name,
                category_type=category_type,
                description=description,
                is_required=is_required,
                is_recurring=is_recurring
            )
            messages.success(request, f'Fee category "{name}" created successfully.')
            return redirect('fees:category_list')
        except Exception as e:
            messages.error(request, f'Error creating fee category: {str(e)}')

    return render(request, 'fees/admin/create_category.html')

@login_required
@user_passes_test(is_admin_or_accountant)
def edit_fee_category(request, category_id):
    """Edit an existing fee category."""
    category = get_object_or_404(FeeCategory, id=category_id)

    if request.method == 'POST':
        # Process form data
        category.name = request.POST.get('name')
        category.category_type = request.POST.get('category_type')
        category.description = request.POST.get('description')
        category.is_required = request.POST.get('is_required') == 'on'
        category.is_recurring = request.POST.get('is_recurring') == 'on'
        category.is_active = request.POST.get('is_active') == 'on'

        try:
            category.save()
            messages.success(request, f'Fee category "{category.name}" updated successfully.')
            return redirect('fees:category_list')
        except Exception as e:
            messages.error(request, f'Error updating fee category: {str(e)}')

    return render(request, 'fees/admin/edit_category.html', {'category': category})

@login_required
@user_passes_test(is_admin_or_accountant)
def delete_fee_category(request, category_id):
    """Delete a fee category."""
    category = get_object_or_404(FeeCategory, id=category_id)

    if request.method == 'POST':
        try:
            category_name = category.name
            category.delete()
            messages.success(request, f'Fee category "{category_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting fee category: {str(e)}')

        return redirect('fees:category_list')

    return render(request, 'fees/admin/delete_category.html', {'category': category})

@login_required
@user_passes_test(is_admin_or_accountant)
def export_fee_categories(request):
    """Export fee categories as CSV."""
    import csv

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fee_categories.csv"'

    # Create the CSV writer
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Description', 'Required', 'Active', 'Created Date'])

    # Get all categories
    categories = FeeCategory.objects.all().order_by('name')

    # Add category data to the CSV
    for category in categories:
        writer.writerow([
            category.id,
            category.name,
            category.description or '',
            'Yes' if category.is_required else 'No',
            'Active' if category.is_active else 'Inactive',
            category.created_at.strftime('%Y-%m-%d')
        ])

    return response

@login_required
@user_passes_test(is_admin_or_accountant)
def term_list(request):
    """List all academic terms."""
    terms = Term.objects.all().order_by('-academic_year', 'start_date')
    return render(request, 'fees/admin/term_list.html', {'terms': terms})

@login_required
@user_passes_test(is_admin_or_accountant)
def create_term(request):
    """Create a new academic term."""
    if request.method == 'POST':
        # Process form data
        name = request.POST.get('name')
        academic_year = request.POST.get('academic_year')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        is_current = request.POST.get('is_current') == 'on'

        try:
            term = Term.objects.create(
                name=name,
                academic_year=academic_year,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current
            )
            messages.success(request, f'Term "{term}" created successfully.')
            return redirect('fees:term_list')
        except Exception as e:
            messages.error(request, f'Error creating term: {str(e)}')

    # Get available academic years from settings
    academic_years = getattr(settings, 'ACADEMIC_YEARS', [])
    if not academic_years:
        # Default to current year and next 5 years if not defined in settings
        current_year = timezone.now().year
        academic_years = [f"{year}-{year+1}" for year in range(current_year-1, current_year+5)]

    return render(request, 'fees/admin/create_term.html', {'academic_years': academic_years})

@login_required
@user_passes_test(is_admin_or_accountant)
def edit_term(request, term_id):
    """Edit an existing academic term."""
    term = get_object_or_404(Term, id=term_id)

    if request.method == 'POST':
        # Process form data
        term.name = request.POST.get('name')
        term.academic_year = request.POST.get('academic_year')
        term.start_date = request.POST.get('start_date')
        term.end_date = request.POST.get('end_date')
        term.is_current = request.POST.get('is_current') == 'on'

        try:
            term.save()
            messages.success(request, f'Term "{term}" updated successfully.')
            return redirect('fees:term_list')
        except Exception as e:
            messages.error(request, f'Error updating term: {str(e)}')

    # Get available academic years from settings
    academic_years = getattr(settings, 'ACADEMIC_YEARS', [])
    if not academic_years:
        # Default to current year and next 5 years if not defined in settings
        current_year = timezone.now().year
        academic_years = [f"{year}-{year+1}" for year in range(current_year-1, current_year+5)]

    return render(request, 'fees/admin/edit_term.html', {'term': term, 'academic_years': academic_years})

@login_required
@user_passes_test(is_admin_or_accountant)
def delete_term(request, term_id):
    """Delete an academic term."""
    term = get_object_or_404(Term, id=term_id)

    if request.method == 'POST':
        try:
            term_name = str(term)
            term.delete()
            messages.success(request, f'Term "{term_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting term: {str(e)}')

        return redirect('fees:term_list')

    return render(request, 'fees/admin/delete_term.html', {'term': term})

@login_required
@user_passes_test(is_admin_or_accountant)
def class_fee_list(request):
    """List all class fees."""
    # Filter options
    term_id = request.GET.get('term')
    classroom_id = request.GET.get('classroom')
    category_id = request.GET.get('category')

    class_fees = ClassFee.objects.select_related('classroom', 'fee_category', 'term')

    # Apply filters
    if term_id:
        class_fees = class_fees.filter(term_id=term_id)

    if classroom_id:
        class_fees = class_fees.filter(classroom_id=classroom_id)

    if category_id:
        class_fees = class_fees.filter(fee_category_id=category_id)

    # Order by term, classroom, and category
    class_fees = class_fees.order_by('-term__academic_year', 'term__name', 'classroom__name', 'fee_category__name')

    # Get filter options for dropdowns
    terms = Term.objects.all().order_by('-academic_year', 'name')
    classrooms = ClassRoom.objects.all().order_by('name')
    categories = FeeCategory.objects.filter(is_active=True).order_by('name')

    # Annotate class fees with student count
    for fee in class_fees:
        fee.student_count = StudentFee.objects.filter(class_fee=fee).count()

    context = {
        'class_fees': class_fees,
        'terms': terms,
        'classrooms': classrooms,
        'categories': categories,
        'selected_term': term_id,
        'selected_classroom': classroom_id,
        'selected_category': category_id,
    }

    return render(request, 'fees/admin/class_fee_list.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def create_class_fee(request):
    """Create a new class fee."""
    if request.method == 'POST':
        # Process form data
        classroom_id = request.POST.get('classroom')
        fee_category_id = request.POST.get('fee_category')
        term_id = request.POST.get('term')
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        due_date = request.POST.get('due_date')

        try:
            class_fee = ClassFee.objects.create(
                classroom_id=classroom_id,
                fee_category_id=fee_category_id,
                term_id=term_id,
                amount=amount,
                description=description,
                due_date=due_date,
                created_by=request.user
            )
            messages.success(request, f'Class fee created successfully.')

            # Ask if user wants to generate student fees
            return redirect('fees:generate_student_fees')
        except Exception as e:
            messages.error(request, f'Error creating class fee: {str(e)}')

    # Get data for dropdowns
    classrooms = ClassRoom.objects.all().order_by('name')
    fee_categories = FeeCategory.objects.filter(is_active=True).order_by('name')
    terms = Term.objects.all().order_by('-academic_year', 'name')

    context = {
        'classrooms': classrooms,
        'fee_categories': fee_categories,
        'terms': terms,
    }

    return render(request, 'fees/admin/create_class_fee.html', context)

# Placeholder for remaining views
@login_required
@user_passes_test(is_admin_or_accountant)
def edit_class_fee(request, fee_id):
    """Edit an existing class fee."""
    class_fee = get_object_or_404(ClassFee, id=fee_id)

    if request.method == 'POST':
        # Get form data
        term_id = request.POST.get('term')
        classroom_id = request.POST.get('classroom')
        fee_category_id = request.POST.get('fee_category')
        amount = request.POST.get('amount')
        due_date = request.POST.get('due_date')
        description = request.POST.get('description')

        try:
            # Update class fee
            class_fee.term_id = term_id
            class_fee.classroom_id = classroom_id
            class_fee.fee_category_id = fee_category_id
            class_fee.amount = amount
            class_fee.due_date = due_date
            class_fee.description = description
            class_fee.save()

            # Update all associated student fees
            student_fee_count = StudentFee.objects.filter(class_fee=class_fee).count()
            StudentFee.objects.filter(class_fee=class_fee).update(
                amount=amount,
                due_date=due_date
            )

            messages.success(
                request,
                f'Class fee updated successfully. {student_fee_count} student fees were also updated.'
            )
            return redirect('fees:class_fee_list')
        except Exception as e:
            messages.error(request, f'Error updating class fee: {str(e)}')
            return redirect('fees:class_fee_list')

    # If GET request, redirect to class fee list
    return redirect('fees:class_fee_list')

@login_required
@user_passes_test(is_admin_or_accountant)
def delete_class_fee(request, fee_id):
    """Delete a class fee."""
    class_fee = get_object_or_404(ClassFee, id=fee_id)

    if request.method == 'POST':
        try:
            # Get fee details for success message
            term_name = class_fee.term.name
            classroom_name = class_fee.classroom.name
            category_name = class_fee.fee_category.name

            # Count associated student fees for reporting
            student_fee_count = StudentFee.objects.filter(class_fee=class_fee).count()

            # Delete the class fee (will cascade delete student fees)
            class_fee.delete()

            messages.success(
                request,
                f'Successfully deleted {category_name} fee for {classroom_name} ({term_name}). '
                f'{student_fee_count} student fee records were also removed.'
            )
            return redirect('fees:class_fee_list')
        except Exception as e:
            messages.error(request, f'Error deleting class fee: {str(e)}')
            return redirect('fees:class_fee_list')

    # If GET request, redirect to class fee list
    return redirect('fees:class_fee_list')

@login_required
@user_passes_test(is_admin_or_accountant)
def bulk_create_class_fees(request):
    """Create fees for multiple classes at once."""
    # Placeholder - to be implemented
    return render(request, 'fees/admin/bulk_create_class_fees.html')

@login_required
@user_passes_test(is_admin_or_accountant)
def export_class_fees(request):
    """Export class fees as CSV."""
    import csv

    # Get filter parameters
    term_id = request.GET.get('term')
    classroom_id = request.GET.get('classroom')
    category_id = request.GET.get('fee_category')

    # Base query
    class_fees = ClassFee.objects.select_related('classroom', 'fee_category', 'term')

    # Apply filters
    if term_id:
        class_fees = class_fees.filter(term_id=term_id)

    if classroom_id:
        class_fees = class_fees.filter(classroom_id=classroom_id)

    if category_id:
        class_fees = class_fees.filter(fee_category_id=category_id)

    # Order by term, classroom, and category
    class_fees = class_fees.order_by('-term__academic_year', 'term__name', 'classroom__name', 'fee_category__name')

    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="class_fees.csv"'

    # Create the CSV writer
    writer = csv.writer(response)
    writer.writerow([
        'Term', 'Academic Year', 'Class', 'Fee Type', 'Amount', 'Due Date', 'Description'
    ])

    # Add class fee data to the CSV
    for fee in class_fees:
        writer.writerow([
            fee.term.name,
            fee.term.academic_year,
            fee.classroom.name,
            fee.fee_category.name,
            fee.amount,
            fee.due_date.strftime('%Y-%m-%d'),
            fee.description or ''
        ])

    return response

@login_required
@user_passes_test(is_admin_or_accountant)
def student_fee_list(request):
    """List all student fees."""
    # Get filter parameters
    term_id = request.GET.get('term')
    classroom_id = request.GET.get('classroom')
    category_id = request.GET.get('fee_category')
    status = request.GET.get('status')
    search_query = request.GET.get('search')

    # Base query
    student_fees = StudentFee.objects.select_related(
        'student', 'student__user', 'class_fee', 'class_fee__classroom',
        'class_fee__fee_category', 'class_fee__term'
    )

    # Apply filters
    if term_id:
        student_fees = student_fees.filter(class_fee__term_id=term_id)

    if classroom_id:
        student_fees = student_fees.filter(class_fee__classroom_id=classroom_id)

    if category_id:
        student_fees = student_fees.filter(class_fee__fee_category_id=category_id)

    if status:
        student_fees = student_fees.filter(status=status)

    if search_query:
        student_fees = student_fees.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)
        )

    # Calculate totals
    total_amount = student_fees.aggregate(total=Sum('amount'))['total'] or 0
    total_paid = student_fees.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_balance = total_amount - total_paid
    collection_rate = (total_paid / total_amount * 100) if total_amount > 0 else 0

    # Order by due date and status
    student_fees = student_fees.order_by('due_date', '-status')

    # Pagination
    paginator = Paginator(student_fees, 25)  # Show 25 fees per page
    page = request.GET.get('page')
    student_fees = paginator.get_page(page)

    # Get filter options for dropdowns
    terms = Term.objects.all().order_by('-academic_year', 'name')
    classrooms = ClassRoom.objects.all().order_by('name')
    fee_categories = FeeCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'student_fees': student_fees,
        'paginator': paginator,
        'terms': terms,
        'classrooms': classrooms,
        'fee_categories': fee_categories,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'collection_rate': collection_rate,
        'selected_term': term_id,
        'selected_classroom': classroom_id,
        'selected_category': category_id,
        'selected_status': status,
        'search_query': search_query,
        'today': timezone.now().date(),
    }

    return render(request, 'fees/admin/student_fee_list.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def generate_student_fees(request):
    """Generate student fees based on class fees."""
    if request.method == 'POST':
        # Check if we're generating fees for a specific class fee or bulk generating
        class_fee_id = request.POST.get('class_fee')

        # Validate class_fee_id is a number
        try:
            if class_fee_id:
                class_fee_id = int(class_fee_id)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid class fee ID.')
            return redirect('fees:generate_student_fees')

        if class_fee_id:
            # Single class fee mode
            class_fee = get_object_or_404(ClassFee, id=class_fee_id)

            # Debug: Print all POST data
            print("POST data:", dict(request.POST))

            # Get student IDs and ensure they are valid
            raw_student_ids = request.POST.getlist('students')

            # Debug: Print all student IDs
            print("Raw student IDs:", raw_student_ids)

            # Filter out any non-numeric values
            student_ids = []
            for sid in raw_student_ids:
                if sid == 'all':
                    # Skip 'all' value
                    print("Skipping 'all' value")
                    continue

                try:
                    # Try to convert to integer to validate
                    student_id = int(sid)
                    student_ids.append(str(student_id))
                except (ValueError, TypeError):
                    # Skip invalid IDs
                    print(f"Skipping invalid student ID: {sid}")

            if not student_ids:
                messages.error(request, 'Please select at least one student.')
                return redirect('fees:generate_student_fees')

            # Check for custom amount and due date
            override_amount = request.POST.get('override_amount') == 'on'
            override_due_date = request.POST.get('override_due_date') == 'on'

            custom_amount = None
            if override_amount:
                custom_amount = request.POST.get('custom_amount')
                if not custom_amount:
                    messages.error(request, 'Custom amount is required when overriding amount.')
                    return redirect('fees:generate_student_fees')

            custom_due_date = None
            if override_due_date:
                custom_due_date = request.POST.get('custom_due_date')
                if not custom_due_date:
                    messages.error(request, 'Custom due date is required when overriding due date.')
                    return redirect('fees:generate_student_fees')

            # Generate student fees
            created_count = 0
            skipped_count = 0

            for student_id in student_ids:
                try:
                    # Convert to integer for database query
                    int_student_id = int(student_id)

                    # Check if student fee already exists
                    existing_fee = StudentFee.objects.filter(
                        student_id=int_student_id,
                        class_fee=class_fee
                    ).exists()

                    if existing_fee:
                        skipped_count += 1
                        continue

                    # Create student fee
                    student_fee = StudentFee(
                        student_id=int_student_id,
                        class_fee=class_fee,
                        amount=custom_amount if override_amount else class_fee.amount,
                        due_date=custom_due_date if override_due_date else class_fee.due_date
                    )
                    student_fee.save()
                    created_count += 1
                except (ValueError, TypeError) as e:
                    print(f"Error processing student ID {student_id}: {e}")
                    continue

            if created_count > 0:
                messages.success(request, f'Successfully generated {created_count} student fees. {skipped_count} were skipped because they already exist.')
            else:
                messages.warning(request, f'No new student fees were generated. {skipped_count} were skipped because they already exist.')

            return redirect('fees:student_fee_list')
        else:
            # Bulk generation mode
            term_id = request.POST.get('term')
            classroom_id = request.POST.get('classroom')
            fee_category_ids = request.POST.getlist('fee_categories')

            # Filter out any non-numeric values
            fee_category_ids = [fcid for fcid in fee_category_ids if fcid.isdigit()]

            if not term_id or not classroom_id or not fee_category_ids:
                messages.error(request, 'Term, class, and at least one fee type are required.')
                return redirect('fees:generate_student_fees')

            # Validate term_id
            try:
                term_id = int(term_id)
            except (ValueError, TypeError):
                messages.error(request, 'Invalid term ID.')
                return redirect('fees:generate_student_fees')

            # Get class fees
            class_fees = ClassFee.objects.filter(
                term_id=term_id,
                classroom_id=classroom_id,
                fee_category_id__in=fee_category_ids
            )

            if not class_fees.exists():
                messages.error(request, 'No class fees found for the selected criteria.')
                return redirect('fees:generate_student_fees')

            # Get students in the class
            try:
                classroom = ClassRoom.objects.get(id=int(classroom_id))
                students = classroom.students.all()

                if not students.exists():
                    messages.error(request, 'No students found in the selected class.')
                    return redirect('fees:generate_student_fees')
            except (ValueError, TypeError, ClassRoom.DoesNotExist):
                messages.error(request, 'Invalid classroom ID or classroom not found.')
                return redirect('fees:generate_student_fees')

            # Generate student fees
            created_count = 0
            skipped_count = 0

            for class_fee in class_fees:
                for student in students:
                    try:
                        # Check if student fee already exists
                        existing_fee = StudentFee.objects.filter(
                            student=student,
                            class_fee=class_fee
                        ).exists()

                        if existing_fee:
                            skipped_count += 1
                            continue

                        # Create student fee
                        student_fee = StudentFee(
                            student=student,
                            class_fee=class_fee,
                            amount=class_fee.amount,
                            due_date=class_fee.due_date
                        )
                        student_fee.save()
                        created_count += 1
                    except Exception as e:
                        print(f"Error processing student {student.id} for class fee {class_fee.id}: {e}")
                        continue

            if created_count > 0:
                messages.success(request, f'Successfully generated {created_count} student fees. {skipped_count} were skipped because they already exist.')
            else:
                messages.warning(request, f'No new student fees were generated. {skipped_count} were skipped because they already exist.')

            return redirect('fees:student_fee_list')

    # GET request - show form
    class_fee_id = request.GET.get('class_fee')
    raw_selected_students = request.GET.getlist('students')

    # Filter out any non-numeric values from selected_students
    selected_students = []
    for sid in raw_selected_students:
        try:
            selected_students.append(int(sid))
        except (ValueError, TypeError):
            # Skip invalid IDs
            continue

    context = {}

    # Validate class_fee_id
    try:
        if class_fee_id:
            class_fee_id = int(class_fee_id)
    except (ValueError, TypeError):
        messages.error(request, 'Invalid class fee ID.')
        return redirect('fees:class_fee_list')

    if class_fee_id:
        # Single class fee mode
        class_fee = get_object_or_404(ClassFee, id=class_fee_id)
        students = class_fee.classroom.students.all().select_related('user').order_by('user__first_name', 'user__last_name')

        context = {
            'class_fee': class_fee,
            'students': students,
            'selected_students': [int(id) for id in selected_students] if selected_students else []
        }
    else:
        # Bulk generation mode
        classrooms = ClassRoom.objects.all().order_by('name')
        categories = FeeCategory.objects.filter(is_active=True).order_by('name')
        terms = Term.objects.all().order_by('-academic_year', 'name')

        context = {
            'classrooms': classrooms,
            'categories': categories,
            'terms': terms
        }

    return render(request, 'fees/admin/generate_student_fees.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def bulk_update_student_fees(request):
    """Bulk update student fees."""
    if request.method == 'POST':
        # Get form data
        term_id = request.POST.get('term')
        classroom_id = request.POST.get('classroom')
        fee_category_id = request.POST.get('fee_category')
        action = request.POST.get('action')

        # Validate required fields
        if not term_id or not action:
            messages.error(request, 'Term and action are required fields.')
            return redirect('fees:student_fee_list')

        # Base query for student fees
        student_fees = StudentFee.objects.filter(class_fee__term_id=term_id)

        # Apply additional filters if provided
        if classroom_id:
            student_fees = student_fees.filter(class_fee__classroom_id=classroom_id)

        if fee_category_id:
            student_fees = student_fees.filter(class_fee__fee_category_id=fee_category_id)

        # Count fees to be updated
        fee_count = student_fees.count()

        if fee_count == 0:
            messages.warning(request, 'No student fees match the selected criteria.')
            return redirect('fees:student_fee_list')

        # Perform the selected action
        if action == 'update_due_date':
            due_date = request.POST.get('due_date')
            if not due_date:
                messages.error(request, 'Due date is required for this action.')
                return redirect('fees:student_fee_list')

            try:
                # Update due date for all matching fees
                student_fees.update(due_date=due_date)
                messages.success(request, f'Due date updated for {fee_count} student fees.')
            except Exception as e:
                messages.error(request, f'Error updating due date: {str(e)}')

        elif action == 'mark_as_overdue':
            # Mark all matching fees as overdue
            student_fees.update(status='OVERDUE')
            messages.success(request, f'{fee_count} student fees marked as overdue.')

        elif action == 'waive_fees':
            waiver_reason = request.POST.get('waiver_reason')
            if not waiver_reason:
                messages.error(request, 'Waiver reason is required for this action.')
                return redirect('fees:student_fee_list')

            try:
                # Mark fees as waived and update notes
                for fee in student_fees:
                    fee.is_waived = True
                    fee.waiver_reason = waiver_reason
                    fee.save()

                messages.success(request, f'{fee_count} student fees have been waived.')
            except Exception as e:
                messages.error(request, f'Error waiving fees: {str(e)}')

        else:
            messages.error(request, 'Invalid action selected.')

    return redirect('fees:student_fee_list')

@login_required
@user_passes_test(is_admin_or_accountant)
def export_student_fees(request):
    """Export student fees as CSV."""
    import csv

    # Get filter parameters
    term_id = request.GET.get('term')
    classroom_id = request.GET.get('classroom')
    category_id = request.GET.get('fee_category')
    status = request.GET.get('status')
    search_query = request.GET.get('search')

    # Base query
    student_fees = StudentFee.objects.select_related(
        'student', 'student__user', 'class_fee', 'class_fee__classroom',
        'class_fee__fee_category', 'class_fee__term'
    )

    # Apply filters
    if term_id:
        student_fees = student_fees.filter(class_fee__term_id=term_id)

    if classroom_id:
        student_fees = student_fees.filter(class_fee__classroom_id=classroom_id)

    if category_id:
        student_fees = student_fees.filter(class_fee__fee_category_id=category_id)

    if status:
        student_fees = student_fees.filter(status=status)

    if search_query:
        student_fees = student_fees.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__student_id__icontains=search_query)
        )

    # Order by due date and status
    student_fees = student_fees.order_by('due_date', '-status')

    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_fees.csv"'

    # Create the CSV writer
    writer = csv.writer(response)
    writer.writerow([
        'Student ID', 'Student Name', 'Class', 'Fee Type', 'Term',
        'Amount', 'Paid', 'Balance', 'Due Date', 'Status', 'Waived'
    ])

    # Add student fee data to the CSV
    for fee in student_fees:
        writer.writerow([
            fee.student.student_id,
            fee.student.user.get_full_name(),
            fee.class_fee.classroom.name,
            fee.class_fee.fee_category.name,
            f"{fee.class_fee.term.name} ({fee.class_fee.term.academic_year})",
            fee.amount,
            fee.amount_paid,
            fee.balance,
            fee.due_date.strftime('%Y-%m-%d') if fee.due_date else '',
            fee.get_status_display(),
            'Yes' if fee.is_waived else 'No'
        ])

    return response

@login_required
@user_passes_test(is_admin_or_accountant)
def student_fee_detail(request, fee_id):
    """View details of a student fee."""
    # Placeholder - to be implemented
    return render(request, 'fees/admin/student_fee_detail.html')

@login_required
@user_passes_test(is_admin_or_accountant)
def edit_student_fee(request, fee_id):
    """Edit a student fee."""
    student_fee = get_object_or_404(StudentFee, id=fee_id)

    if request.method == 'POST':
        # Get form data
        amount = request.POST.get('amount')
        due_date = request.POST.get('due_date')
        status = request.POST.get('status')
        waiver_reason = request.POST.get('waiver_reason')

        try:
            # Update student fee
            student_fee.amount = amount
            student_fee.due_date = due_date
            student_fee.status = status

            # Handle waiver reason if status is WAIVED
            if status == 'WAIVED':
                student_fee.is_waived = True
                student_fee.waiver_reason = waiver_reason
            else:
                student_fee.is_waived = False

            student_fee.save()

            messages.success(request, f'Student fee updated successfully.')
        except Exception as e:
            messages.error(request, f'Error updating student fee: {str(e)}')

        return redirect('fees:student_fee_list')

    # For GET requests, redirect to the student fee list
    return redirect('fees:student_fee_list')

@login_required
@user_passes_test(is_admin_or_accountant)
def payment_list(request):
    """List all payments."""
    # Get filter parameters
    term_id = request.GET.get('term')
    category_id = request.GET.get('fee_category')
    payment_method = request.GET.get('payment_method')
    date_range = request.GET.get('date_range')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_query = request.GET.get('search')

    # Base query
    payments = Payment.objects.select_related(
        'student_fee', 'student_fee__student', 'student_fee__student__user',
        'student_fee__class_fee', 'student_fee__class_fee__fee_category',
        'student_fee__class_fee__term', 'receipt', 'received_by'
    )

    # Apply filters
    if term_id:
        payments = payments.filter(student_fee__class_fee__term_id=term_id)

    if category_id:
        payments = payments.filter(student_fee__class_fee__fee_category_id=category_id)

    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    # Date range filtering
    today = timezone.now().date()
    if date_range == 'today':
        payments = payments.filter(payment_date__date=today)
    elif date_range == 'yesterday':
        payments = payments.filter(payment_date__date=today - timezone.timedelta(days=1))
    elif date_range == 'this_week':
        start_of_week = today - timezone.timedelta(days=today.weekday())
        payments = payments.filter(payment_date__date__gte=start_of_week)
    elif date_range == 'last_week':
        start_of_last_week = today - timezone.timedelta(days=today.weekday() + 7)
        end_of_last_week = start_of_last_week + timezone.timedelta(days=6)
        payments = payments.filter(payment_date__date__gte=start_of_last_week, payment_date__date__lte=end_of_last_week)
    elif date_range == 'this_month':
        payments = payments.filter(payment_date__year=today.year, payment_date__month=today.month)
    elif date_range == 'last_month':
        last_month = today.month - 1 if today.month > 1 else 12
        last_month_year = today.year if today.month > 1 else today.year - 1
        payments = payments.filter(payment_date__year=last_month_year, payment_date__month=last_month)
    elif date_range == 'custom' and start_date and end_date:
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            payments = payments.filter(payment_date__date__gte=start_date, payment_date__date__lte=end_date)
        except ValueError:
            # Invalid date format, ignore filter
            pass

    if search_query:
        payments = payments.filter(
            Q(student_fee__student__user__first_name__icontains=search_query) |
            Q(student_fee__student__user__last_name__icontains=search_query) |
            Q(student_fee__student__student_id__icontains=search_query)
        )

    # Calculate statistics
    payment_count = payments.count()
    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    average_amount = total_amount / payment_count if payment_count > 0 else 0

    # Calculate period amount (for the selected date range)
    period_amount = total_amount

    # Order by payment date (most recent first)
    payments = payments.order_by('-payment_date')

    # Pagination
    paginator = Paginator(payments, 25)  # Show 25 payments per page
    page = request.GET.get('page')
    payments = paginator.get_page(page)

    # Get filter options for dropdowns
    terms = Term.objects.all().order_by('-academic_year', 'name')
    fee_categories = FeeCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'payments': payments,
        'paginator': paginator,
        'terms': terms,
        'fee_categories': fee_categories,
        'payment_count': payment_count,
        'total_amount': total_amount,
        'average_amount': average_amount,
        'period_amount': period_amount,
        'selected_term': term_id,
        'selected_category': category_id,
        'selected_method': payment_method,
        'selected_date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
    }

    return render(request, 'fees/admin/payment_list.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def create_payment(request):
    """Record a new payment."""
    if request.method == 'POST':
        # Process form data
        student_id = request.POST.get('student')
        fee_id = request.POST.get('fee')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id')

        # Handle payment date - extract just the date part from datetime-local input
        payment_date_str = request.POST.get('payment_date')
        if payment_date_str and 'T' in payment_date_str:
            # Extract just the date part from the datetime string
            payment_date = payment_date_str.split('T')[0]
        else:
            payment_date = payment_date_str

        received_by = request.POST.get('received_by')
        notes = request.POST.get('notes')

        try:
            # Get the student fee
            student_fee = StudentFee.objects.get(id=fee_id)

            # Create the payment
            payment = Payment.objects.create(
                student_fee=student_fee,
                amount=amount,
                payment_method=payment_method,
                transaction_id=transaction_id,
                payment_date=payment_date,
                received_by=request.user,  # Use the current user instead of the text input
                notes=notes
            )

            # Generate receipt number
            receipt_number = f"REC-{payment.id:06d}"
            payment.receipt_number = receipt_number
            payment.save()

            # Update student fee status
            # Convert amount to Decimal before adding to avoid type mismatch
            student_fee.amount_paid = student_fee.amount_paid + Decimal(amount)

            # Update status based on payment
            if student_fee.amount_paid >= student_fee.amount:
                student_fee.status = StudentFee.Status.PAID
            elif student_fee.amount_paid > 0:
                student_fee.status = StudentFee.Status.PARTIALLY_PAID

            student_fee.save()

            # Check if this is an AJAX request (from quick payment form)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'receipt_number': receipt_number,
                    'amount': amount,
                    'receipt_url': reverse('fees:payment_detail', args=[payment.id]),
                    'print_url': reverse('fees:print_receipt', args=[payment.id])
                })
            else:
                # Regular form submission
                messages.success(request, f'Payment of GHS {amount} recorded successfully. Receipt number: {receipt_number}')
                return redirect('fees:payment_detail', payment_id=payment.id)
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            else:
                messages.error(request, f'Error recording payment: {str(e)}')

    # Get all students
    students = Student.objects.select_related('user').order_by('user__first_name', 'user__last_name')

    return render(request, 'fees/admin/create_payment.html', {'students': students})

@login_required
@user_passes_test(is_admin_or_accountant)
def payment_detail(request, payment_id):
    """View details of a payment."""
    payment = get_object_or_404(Payment, id=payment_id)

    # Get payment history for this student fee
    payment_history = Payment.objects.filter(
        student_fee=payment.student_fee
    ).exclude(id=payment_id).order_by('-payment_date')

    context = {
        'payment': payment,
        'payment_history': payment_history
    }

    return render(request, 'fees/admin/payment_detail.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def adjust_payment(request, payment_id):
    """Adjust or cancel a payment."""
    payment = get_object_or_404(Payment, id=payment_id)
    student_fee = payment.student_fee

    if request.method == 'POST':
        adjustment_type = request.POST.get('adjustment_type')
        reason = request.POST.get('reason')
        confirm = request.POST.get('confirm')

        if not adjustment_type or not reason or not confirm:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('fees:adjust_payment', payment_id=payment_id)

        # Get the original amount for logging
        original_amount = payment.amount

        try:
            # Start a transaction to ensure data consistency
            with transaction.atomic():
                if adjustment_type == 'cancel':
                    # Cancel the payment entirely

                    # First, update the student fee
                    student_fee.amount_paid -= original_amount

                    # Update status based on new amount_paid
                    if student_fee.amount_paid <= 0:
                        student_fee.amount_paid = 0
                        student_fee.status = StudentFee.Status.PENDING
                    elif student_fee.amount_paid < student_fee.amount:
                        student_fee.status = StudentFee.Status.PARTIALLY_PAID

                    # Recalculate balance
                    student_fee.balance = student_fee.amount - student_fee.amount_paid
                    student_fee.save()

                    # Delete receipt if exists
                    if hasattr(payment, 'receipt'):
                        payment.receipt.delete()

                    # Create an audit log entry
                    from django.contrib.admin.models import LogEntry, DELETION
                    from django.contrib.contenttypes.models import ContentType
                    LogEntry.objects.log_action(
                        user_id=request.user.id,
                        content_type_id=ContentType.objects.get_for_model(Payment).pk,
                        object_id=payment.id,
                        object_repr=str(payment),
                        action_flag=DELETION,
                        change_message=f'Payment cancelled. Reason: {reason}'
                    )

                    # Delete the payment
                    payment.delete()

                    messages.success(request, f'Payment of GHS {original_amount} has been cancelled successfully.')
                    return redirect('fees:student_fees', student_id=student_fee.student.id)

                elif adjustment_type == 'adjust':
                    # Adjust the payment amount
                    new_amount = request.POST.get('new_amount')

                    if not new_amount:
                        messages.error(request, 'New amount is required for adjustment.')
                        return redirect('fees:adjust_payment', payment_id=payment_id)

                    try:
                        new_amount = Decimal(new_amount)
                    except:
                        messages.error(request, 'Invalid amount format.')
                        return redirect('fees:adjust_payment', payment_id=payment_id)

                    if new_amount <= 0 or new_amount > original_amount:
                        messages.error(request, 'New amount must be greater than 0 and less than or equal to the original amount.')
                        return redirect('fees:adjust_payment', payment_id=payment_id)

                    # Calculate the difference
                    difference = original_amount - new_amount

                    # Update the payment amount
                    payment.amount = new_amount
                    payment.notes = f"{payment.notes or ''}\n[ADJUSTED] Original amount: GHS {original_amount}. Adjusted on {timezone.now().strftime('%Y-%m-%d %H:%M')} by {request.user.get_full_name()}. Reason: {reason}"
                    payment.save()

                    # Update the student fee
                    student_fee.amount_paid -= difference

                    # Update status based on new amount_paid
                    if student_fee.amount_paid <= 0:
                        student_fee.amount_paid = 0
                        student_fee.status = StudentFee.Status.PENDING
                    elif student_fee.amount_paid < student_fee.amount:
                        student_fee.status = StudentFee.Status.PARTIALLY_PAID
                    elif student_fee.amount_paid >= student_fee.amount:
                        student_fee.status = StudentFee.Status.PAID

                    # Recalculate balance
                    student_fee.balance = student_fee.amount - student_fee.amount_paid
                    student_fee.save()

                    messages.success(request, f'Payment adjusted from GHS {original_amount} to GHS {new_amount} successfully.')
                    return redirect('fees:payment_detail', payment_id=payment.id)

        except Exception as e:
            messages.error(request, f'Error adjusting payment: {str(e)}')
            return redirect('fees:adjust_payment', payment_id=payment_id)

    context = {
        'payment': payment
    }

    return render(request, 'fees/admin/adjust_payment.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def export_payments(request):
    """Export payments as CSV."""
    import csv
    from datetime import datetime

    # Get filter parameters
    term_id = request.GET.get('term')
    category_id = request.GET.get('fee_category')
    payment_method = request.GET.get('payment_method')
    date_range = request.GET.get('date_range')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_query = request.GET.get('search')

    # Base query
    payments = Payment.objects.select_related(
        'student_fee', 'student_fee__student', 'student_fee__student__user',
        'student_fee__class_fee', 'student_fee__class_fee__classroom',
        'student_fee__class_fee__fee_category', 'student_fee__class_fee__term'
    )

    # Apply filters
    if term_id:
        payments = payments.filter(student_fee__class_fee__term_id=term_id)

    if category_id:
        payments = payments.filter(student_fee__class_fee__fee_category_id=category_id)

    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    # Date filters
    if date_range == 'today':
        today = timezone.now().date()
        payments = payments.filter(payment_date__date=today)
    elif date_range == 'this_week':
        start_of_week = timezone.now().date() - timezone.timedelta(days=timezone.now().weekday())
        payments = payments.filter(payment_date__date__gte=start_of_week)
    elif date_range == 'this_month':
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        payments = payments.filter(payment_date__date__gte=start_of_month)
    elif date_range == 'custom' and start_date and end_date:
        payments = payments.filter(payment_date__date__gte=start_date, payment_date__date__lte=end_date)

    if search_query:
        payments = payments.filter(
            Q(student_fee__student__user__first_name__icontains=search_query) |
            Q(student_fee__student__user__last_name__icontains=search_query) |
            Q(student_fee__student__student_id__icontains=search_query) |
            Q(receipt_number__icontains=search_query)
        )

    # Order by payment date (most recent first)
    payments = payments.order_by('-payment_date')

    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payments.csv"'

    # Create the CSV writer
    writer = csv.writer(response)
    writer.writerow([
        'Receipt Number', 'Student ID', 'Student Name', 'Class', 'Fee Type',
        'Term', 'Payment Date', 'Amount', 'Payment Method', 'Notes'
    ])

    # Add payment data to the CSV
    for payment in payments:
        student_fee = payment.student_fee
        student = student_fee.student
        class_fee = student_fee.class_fee

        writer.writerow([
            payment.receipt_number,
            student.student_id,
            f"{student.user.first_name} {student.user.last_name}",
            class_fee.classroom.name,
            class_fee.fee_category.name,
            f"{class_fee.term.name} ({class_fee.term.academic_year})",
            payment.payment_date.strftime('%Y-%m-%d %H:%M'),
            payment.amount,
            payment.get_payment_method_display(),
            payment.notes or ''
        ])

    return response

@login_required
@user_passes_test(is_admin_or_accountant)
def receipt_list(request):
    """List all receipts."""
    # Placeholder - to be implemented
    return render(request, 'fees/admin/receipt_list.html')

@login_required
@user_passes_test(is_admin_or_accountant)
def generate_receipt(request, payment_id):
    """Generate a receipt for a payment."""
    payment = get_object_or_404(Payment, id=payment_id)

    # Check if receipt already exists
    if hasattr(payment, 'receipt'):
        messages.warning(request, 'Receipt already exists for this payment.')
        return redirect('fees:payment_detail', payment_id=payment.id)

    try:
        # Generate receipt number
        receipt_number = Receipt.generate_receipt_number()

        # Create receipt
        receipt = Receipt.objects.create(
            payment=payment,
            receipt_number=receipt_number,
            generated_by=request.user
        )

        messages.success(request, f'Receipt #{receipt_number} generated successfully.')
        return redirect('fees:receipt_detail', receipt_id=receipt.id)
    except Exception as e:
        messages.error(request, f'Error generating receipt: {str(e)}')
        return redirect('fees:payment_detail', payment_id=payment.id)

@login_required
@user_passes_test(is_admin_or_accountant)
def receipt_detail(request, receipt_id):
    """View details of a receipt."""
    receipt = get_object_or_404(Receipt, id=receipt_id)

    # Get school settings
    try:
        school_settings = SchoolSettings.objects.first()
    except:
        school_settings = None

    # Convert amount to words
    def number_to_words(num):
        units = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
        teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

        if num < 10:
            return units[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            return tens[num // 10] + ('' if num % 10 == 0 else ' ' + units[num % 10])
        elif num < 1000:
            return units[num // 100] + ' Hundred' + ('' if num % 100 == 0 else ' and ' + number_to_words(num % 100))
        elif num < 1000000:
            return number_to_words(num // 1000) + ' Thousand' + ('' if num % 1000 == 0 else ' ' + number_to_words(num % 1000))
        return 'Number too large'

    # Convert the payment amount to words
    amount = float(receipt.payment.amount)
    cedis = int(amount)
    pesewas = int((amount - cedis) * 100)

    amount_in_words = number_to_words(cedis) + ' Ghana Cedis'
    if pesewas > 0:
        amount_in_words += ' and ' + number_to_words(pesewas) + ' Pesewas'

    context = {
        'receipt': receipt,
        'school_settings': school_settings,
        'amount_in_words': amount_in_words,
    }

    return render(request, 'fees/admin/receipt_detail.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def print_receipt(request, receipt_id):
    """Print a receipt."""
    receipt = get_object_or_404(Receipt, id=receipt_id)

    # Redirect to receipt detail with print parameter
    return redirect(f'/fees/admin/receipts/{receipt_id}/?print=true')

@login_required
@user_passes_test(is_admin_or_accountant)
def fee_reports(request):
    """View fee reports."""
    # Get current term
    current_term = Term.objects.filter(is_current=True).first()

    # Get basic statistics
    total_expected = StudentFee.objects.filter(
        class_fee__term=current_term
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_collected = StudentFee.objects.filter(
        class_fee__term=current_term
    ).aggregate(total=Sum('amount_paid'))['total'] or 0

    total_outstanding = total_expected - total_collected
    collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else 0

    context = {
        'current_term': current_term,
        'total_expected': total_expected,
        'total_collected': total_collected,
        'total_outstanding': total_outstanding,
        'collection_rate': collection_rate,
    }

    return render(request, 'fees/admin/fee_reports.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def class_fee_summary(request):
    """View fee summary by class."""
    # Get filter parameters
    term_id = request.GET.get('term')
    category_id = request.GET.get('fee_category')

    # Get current term if no term is specified
    if term_id:
        term = get_object_or_404(Term, id=term_id)
    else:
        term = Term.objects.filter(is_current=True).first()

    # Base query for class fees
    class_fees = ClassFee.objects.filter(term=term)

    # Apply category filter if specified
    if category_id:
        class_fees = class_fees.filter(fee_category_id=category_id)

    # Get all classrooms with fees
    classrooms = ClassRoom.objects.filter(id__in=class_fees.values_list('classroom_id', flat=True)).distinct()

    # Calculate summary for each class
    class_summaries = []
    total_expected = 0
    total_collected = 0

    for classroom in classrooms:
        # Get student fees for this class
        student_fees = StudentFee.objects.filter(
            class_fee__classroom=classroom,
            class_fee__term=term
        )

        if category_id:
            student_fees = student_fees.filter(class_fee__fee_category_id=category_id)

        # Calculate totals
        expected_amount = student_fees.aggregate(total=Sum('amount'))['total'] or 0
        collected_amount = student_fees.aggregate(total=Sum('amount_paid'))['total'] or 0
        outstanding_amount = expected_amount - collected_amount
        collection_rate = (collected_amount / expected_amount * 100) if expected_amount > 0 else 0
        student_count = student_fees.values('student').distinct().count()

        # Add to totals
        total_expected += expected_amount
        total_collected += collected_amount

        # Add to summary list
        class_summaries.append({
            'classroom': classroom,
            'student_count': student_count,
            'expected_amount': expected_amount,
            'collected_amount': collected_amount,
            'outstanding_amount': outstanding_amount,
            'collection_rate': collection_rate
        })

    # Sort by collection rate (descending)
    class_summaries.sort(key=lambda x: x['collection_rate'], reverse=True)

    # Calculate overall collection rate
    total_outstanding = total_expected - total_collected
    collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else 0

    # Get filter options
    terms = Term.objects.all().order_by('-academic_year', 'name')
    fee_categories = FeeCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'class_summaries': class_summaries,
        'terms': terms,
        'fee_categories': fee_categories,
        'selected_term': term_id,
        'selected_category': category_id,
        'current_term': term,
        'total_expected': total_expected,
        'total_collected': total_collected,
        'total_outstanding': total_outstanding,
        'collection_rate': collection_rate,
    }

    return render(request, 'fees/admin/class_fee_summary.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def outstanding_fees_report(request):
    """View report of outstanding fees."""
    # Get filter parameters
    term_id = request.GET.get('term')
    classroom_id = request.GET.get('classroom')
    overdue_only = request.GET.get('overdue') == 'overdue'

    # Get current term if no term is specified
    if term_id:
        term = get_object_or_404(Term, id=term_id)
    else:
        term = Term.objects.filter(is_current=True).first()

    # Base query for outstanding fees
    outstanding_fees = StudentFee.objects.filter(
        balance__gt=0,  # Only fees with balance
        class_fee__term=term
    ).select_related(
        'student', 'student__user', 'class_fee', 'class_fee__classroom',
        'class_fee__fee_category', 'class_fee__term'
    )

    # Apply classroom filter if specified
    if classroom_id:
        outstanding_fees = outstanding_fees.filter(class_fee__classroom_id=classroom_id)

    # Apply overdue filter if specified
    today = timezone.now().date()
    if overdue_only:
        outstanding_fees = outstanding_fees.filter(due_date__lt=today)

    # Calculate totals
    total_outstanding = outstanding_fees.aggregate(total=Sum('balance'))['total'] or 0
    overdue_amount = outstanding_fees.filter(due_date__lt=today).aggregate(total=Sum('balance'))['total'] or 0
    student_count = outstanding_fees.values('student').distinct().count()
    average_outstanding = total_outstanding / student_count if student_count > 0 else 0

    # Get filter options
    terms = Term.objects.all().order_by('-academic_year', 'name')
    classrooms = ClassRoom.objects.all().order_by('name')

    # Pagination
    paginator = Paginator(outstanding_fees.order_by('due_date'), 25)  # Show 25 fees per page
    page = request.GET.get('page')
    outstanding_fees = paginator.get_page(page)

    context = {
        'outstanding_fees': outstanding_fees,
        'paginator': paginator,
        'terms': terms,
        'classrooms': classrooms,
        'total_outstanding': total_outstanding,
        'overdue_amount': overdue_amount,
        'student_count': student_count,
        'average_outstanding': average_outstanding,
        'selected_term': term_id,
        'selected_classroom': classroom_id,
        'overdue_only': overdue_only,
        'today': today,
    }

    return render(request, 'fees/admin/outstanding_fees_report.html', context)

@login_required
@user_passes_test(is_admin_or_accountant)
def fee_collection_report(request):
    """View report of fee collection."""
    # Get filter parameters
    term_id = request.GET.get('term')
    period = request.GET.get('period', 'daily')
    date_range = request.GET.get('date_range', 'last_30_days')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Get current term if no term is specified
    if term_id:
        term = get_object_or_404(Term, id=term_id)
    else:
        term = Term.objects.filter(is_current=True).first()

    # Set date range
    today = timezone.now().date()

    if date_range == 'last_30_days':
        start_date = today - timezone.timedelta(days=30)
        end_date = today
    elif date_range == 'last_90_days':
        start_date = today - timezone.timedelta(days=90)
        end_date = today
    elif date_range == 'this_term' and term:
        start_date = term.start_date
        end_date = term.end_date if term.end_date else today
    elif date_range == 'custom' and start_date_str and end_date_str:
        try:
            start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timezone.timedelta(days=30)
            end_date = today
    else:
        start_date = today - timezone.timedelta(days=30)
        end_date = today

    # Base query for payments
    payments = Payment.objects.filter(
        payment_date__date__gte=start_date,
        payment_date__date__lte=end_date
    ).select_related(
        'student_fee', 'student_fee__student', 'student_fee__student__user',
        'student_fee__class_fee', 'student_fee__class_fee__fee_category'
    )

    # Apply term filter if specified
    if term_id:
        payments = payments.filter(student_fee__class_fee__term_id=term_id)

    # Calculate statistics
    payment_count = payments.count()
    total_collected = payments.aggregate(total=Sum('amount'))['total'] or 0
    average_payment = total_collected / payment_count if payment_count > 0 else 0

    # Calculate collection percentage against expected fees
    total_expected = StudentFee.objects.filter(
        class_fee__term=term
    ).aggregate(total=Sum('amount'))['total'] or 0

    collection_percentage = (total_collected / total_expected * 100) if total_expected > 0 else 0

    # Generate collection trend data based on period
    collection_trend = []

    if period == 'daily':
        # Daily trend for the selected date range
        current_date = start_date
        while current_date <= end_date:
            day_payments = payments.filter(payment_date__date=current_date)
            day_amount = day_payments.aggregate(total=Sum('amount'))['total'] or 0

            collection_trend.append({
                'date': current_date,
                'label': current_date.strftime('%b %d'),
                'amount': day_amount
            })

            current_date += timezone.timedelta(days=1)

    elif period == 'weekly':
        # Weekly trend
        # Start from the beginning of the week containing start_date
        week_start = start_date - timezone.timedelta(days=start_date.weekday())
        current_week_start = week_start

        while current_week_start <= end_date:
            week_end = current_week_start + timezone.timedelta(days=6)
            week_payments = payments.filter(
                payment_date__date__gte=current_week_start,
                payment_date__date__lte=min(week_end, end_date)
            )
            week_amount = week_payments.aggregate(total=Sum('amount'))['total'] or 0

            collection_trend.append({
                'date': current_week_start,
                'label': f'{current_week_start.strftime("%b %d")} - {min(week_end, end_date).strftime("%b %d")}',
                'amount': week_amount
            })

            current_week_start += timezone.timedelta(days=7)

    elif period == 'monthly':
        # Monthly trend
        # Start from the beginning of the month containing start_date
        month_start = start_date.replace(day=1)
        current_month = month_start

        while current_month <= end_date:
            # Calculate the last day of the current month
            if current_month.month == 12:
                next_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                next_month = current_month.replace(month=current_month.month + 1)

            month_end = next_month - timezone.timedelta(days=1)

            month_payments = payments.filter(
                payment_date__date__gte=current_month,
                payment_date__date__lte=min(month_end, end_date)
            )
            month_amount = month_payments.aggregate(total=Sum('amount'))['total'] or 0

            collection_trend.append({
                'date': current_month,
                'label': current_month.strftime('%b %Y'),
                'amount': month_amount
            })

            current_month = next_month

    # Get payment method distribution
    payment_methods = []
    for method_choice in Payment.PAYMENT_METHOD_CHOICES:
        method_code = method_choice[0]
        method_name = method_choice[1]

        method_payments = payments.filter(payment_method=method_code)
        method_amount = method_payments.aggregate(total=Sum('amount'))['total'] or 0

        if method_amount > 0:
            payment_methods.append({
                'code': method_code,
                'name': method_name,
                'amount': method_amount,
                'percentage': (method_amount / total_collected * 100) if total_collected > 0 else 0
            })

    # Get fee category distribution
    fee_categories_data = []
    categories = FeeCategory.objects.filter(is_active=True)

    for category in categories:
        category_payments = payments.filter(student_fee__class_fee__fee_category=category)
        category_amount = category_payments.aggregate(total=Sum('amount'))['total'] or 0

        if category_amount > 0:
            fee_categories_data.append({
                'id': category.id,
                'name': category.name,
                'amount': category_amount,
                'percentage': (category_amount / total_collected * 100) if total_collected > 0 else 0
            })

    # Get recent payments
    recent_payments = payments.order_by('-payment_date')[:10]

    # Get filter options
    terms = Term.objects.all().order_by('-academic_year', 'name')
    fee_categories = FeeCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'payment_count': payment_count,
        'total_collected': total_collected,
        'average_payment': average_payment,
        'collection_percentage': collection_percentage,
        'period_amount': total_collected,  # Same as total_collected for now
        'collection_trend': collection_trend,
        'payment_methods': payment_methods,
        'fee_categories': fee_categories_data,
        'recent_payments': recent_payments,
        'terms': terms,
        'fee_categories': fee_categories,
        'selected_term': term_id,
        'selected_period': period,
        'selected_date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'current_term': term,
    }

    return render(request, 'fees/admin/fee_collection_report.html', context)

# Student/Parent views
@login_required
def student_fees(request, student_id):
    """View fees for a student."""
    # Get the student
    student = get_object_or_404(Student, id=student_id)

    # Check if the user has permission to view this student's fees
    user = request.user
    if user.role == CustomUser.Role.STUDENT and user.student_profile.id != student_id:
        messages.error(request, "You don't have permission to view this student's fees.")
        return redirect('dashboard:index')
    elif user.role == CustomUser.Role.PARENT and student not in user.parent_profile.children.all():
        messages.error(request, "You don't have permission to view this student's fees.")
        return redirect('dashboard:index')

    # Get all terms
    terms = Term.objects.all().order_by('-academic_year', 'start_date')

    # Get the selected term (default to current term)
    term_id = request.GET.get('term')
    if term_id:
        term = get_object_or_404(Term, id=term_id)
    else:
        term = Term.objects.filter(is_current=True).first() or terms.first()

    # Get student fees for the selected term
    student_fees = StudentFee.objects.filter(
        student=student,
        class_fee__term=term
    ).select_related(
        'class_fee', 'class_fee__fee_category', 'class_fee__classroom'
    ).order_by('class_fee__fee_category__name')

    # Calculate totals
    total_amount = sum(fee.amount for fee in student_fees)
    total_paid = sum(fee.amount_paid for fee in student_fees)
    total_balance = total_amount - total_paid
    payment_percentage = (total_paid / total_amount * 100) if total_amount > 0 else 0

    # Get recent payments
    recent_payments = Payment.objects.filter(
        student_fee__student=student,
        student_fee__class_fee__term=term
    ).select_related(
        'student_fee', 'student_fee__class_fee', 'student_fee__class_fee__fee_category'
    ).order_by('-payment_date')[:5]

    context = {
        'student': student,
        'terms': terms,
        'term': term,
        'student_fees': student_fees,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'payment_percentage': payment_percentage,
        'recent_payments': recent_payments,
    }

    return render(request, 'fees/student/student_fees.html', context)

@login_required
def student_fee_invoice(request, student_id, fee_id):
    """View invoice for a student fee."""
    # Get the student and fee
    student = get_object_or_404(Student, id=student_id)
    student_fee = get_object_or_404(StudentFee, id=fee_id, student=student)

    # Check if the user has permission to view this student's fee invoice
    user = request.user
    if user.role == CustomUser.Role.STUDENT:
        messages.error(request, "Students cannot access invoice details. Please contact the school administration.")
        return redirect('fees:student_fees', student_id=student_id)
    elif user.role == CustomUser.Role.PARENT and student not in user.parent_profile.children.all():
        messages.error(request, "You don't have permission to view this invoice.")
        return redirect('dashboard:index')
    elif not (user.is_admin or user.is_accountant or user.role == CustomUser.Role.PARENT):
        messages.error(request, "You don't have permission to view this invoice.")
        return redirect('dashboard:index')

    # Get related fees for the same term and student
    related_fees = StudentFee.objects.filter(
        student=student,
        class_fee__term=student_fee.class_fee.term
    ).exclude(id=fee_id).select_related('class_fee', 'class_fee__fee_category')

    # Calculate totals
    total_amount = student_fee.amount + sum(fee.amount for fee in related_fees)
    total_paid = student_fee.amount_paid + sum(fee.amount_paid for fee in related_fees)
    total_balance = total_amount - total_paid

    # Get payment history for this fee
    payments = Payment.objects.filter(
        student_fee__in=[student_fee] + list(related_fees)
    ).select_related('receipt').order_by('-payment_date')

    # Get parent information
    parent = student.parents.first()

    # Generate invoice number if not exists
    invoice_number = f"INV-{student.student_id}-{student_fee.class_fee.term.academic_year.replace('-', '')}-{fee_id}"

    # Get school settings
    from users.models import SchoolSettings
    school_settings = SchoolSettings.objects.first()

    # Default values if school settings don't exist
    school_name = 'Ricas School'
    school_address = '123 Education Street, Accra, Ghana'
    school_contact = 'Tel: +233 123 456 789'
    school_logo_url = '/static/img/logo.png'
    school_email = ''

    # Use school settings if available
    if school_settings:
        school_name = school_settings.school_name
        school_address = school_settings.address or school_address
        school_contact = f"Tel: {school_settings.phone}" if school_settings.phone else school_contact
        school_logo_url = school_settings.logo.url if school_settings.logo else school_logo_url
        school_email = school_settings.email or ''

    context = {
        'student': student,
        'student_fee': student_fee,
        'related_fees': related_fees,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'payments': payments,
        'parent': parent,
        'invoice_number': invoice_number,
        'today': timezone.now().date(),
        'school_name': school_name,
        'school_address': school_address,
        'school_contact': school_contact,
        'school_logo_url': school_logo_url,
        'school_email': school_email,
        'school_settings': school_settings,
    }

    # Use different templates based on user role
    if request.user.role == CustomUser.Role.PARENT:
        return render(request, 'fees/student/parent_fee_invoice.html', context)
    else:  # Admin or accountant
        return render(request, 'fees/student/student_fee_invoice.html', context)


@login_required
@user_passes_test(is_admin_or_accountant)
def email_invoice(request, student_id, fee_id):
    """Email a fee invoice to a parent."""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('fees:student_fee_invoice', student_id=student_id, fee_id=fee_id)

    # Get student and fee
    student = get_object_or_404(Student, id=student_id)
    student_fee = get_object_or_404(StudentFee, id=fee_id)

    # Get email details from form
    recipient_email = request.POST.get('recipient_email')
    email_subject = request.POST.get('email_subject')
    email_message = request.POST.get('email_message')

    if not all([recipient_email, email_subject, email_message]):
        messages.error(request, 'Please fill in all email fields.')
        return redirect('fees:student_fee_invoice', student_id=student_id, fee_id=fee_id)

    try:
        # Generate PDF invoice
        from django.template.loader import render_to_string
        from weasyprint import HTML
        import tempfile
        from django.core.mail import EmailMessage

        # Get related fees (same category, term, and student)
        related_fees = StudentFee.objects.filter(
            student=student,
            class_fee__fee_category=student_fee.class_fee.fee_category,
            class_fee__term=student_fee.class_fee.term
        ).exclude(id=student_fee.id)

        # Calculate totals
        total_amount = student_fee.amount + sum(fee.amount for fee in related_fees)
        total_paid = student_fee.amount_paid + sum(fee.amount_paid for fee in related_fees)
        total_balance = total_amount - total_paid

        # Get payments
        payments = Payment.objects.filter(
            student_fee__in=[student_fee] + list(related_fees)
        ).select_related('receipt').order_by('-payment_date')

        # Get parent information
        parent = student.parents.first()

        # Generate invoice number if not exists
        invoice_number = f"INV-{student.student_id}-{student_fee.class_fee.term.academic_year.replace('-', '')}-{fee_id}"

        # Get school settings
        from users.models import SchoolSettings
        school_settings = SchoolSettings.objects.first()

        # Default values if school settings don't exist
        school_name = 'Ricas School'
        school_address = '123 Education Street, Accra, Ghana'
        school_contact = 'Tel: +233 123 456 789'
        school_logo_url = '/static/img/logo.png'
        school_email = ''

        # Use school settings if available
        if school_settings:
            school_name = school_settings.school_name
            school_address = school_settings.address or school_address
            school_contact = f"Tel: {school_settings.phone}" if school_settings.phone else school_contact
            school_logo_url = school_settings.logo.url if school_settings.logo else school_logo_url
            school_email = school_settings.email or ''

        # Prepare context for PDF template
        context = {
            'student': student,
            'student_fee': student_fee,
            'related_fees': related_fees,
            'total_amount': total_amount,
            'total_paid': total_paid,
            'total_balance': total_balance,
            'payments': payments,
            'parent': parent,
            'invoice_number': invoice_number,
            'today': timezone.now().date(),
            'school_name': school_name,
            'school_address': school_address,
            'school_contact': school_contact,
            'school_logo_url': request.build_absolute_uri(school_logo_url),
            'school_email': school_email,
            'school_settings': school_settings,
            'is_pdf': True,
        }

        # Render HTML content
        html_string = render_to_string('fees/student/student_fee_invoice_pdf.html', context)

        # Create a temporary file to store the PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output_file:
            # Generate PDF
            HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(output_file)
            output_file_path = output_file.name

        # Send email with PDF attachment
        email = EmailMessage(
            subject=email_subject,
            body=email_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )

        # Attach the PDF
        with open(output_file_path, 'rb') as pdf_file:
            email.attach(f'{invoice_number}.pdf', pdf_file.read(), 'application/pdf')

        # Send the email
        email.send()

        # Delete the temporary file
        import os
        os.unlink(output_file_path)

        messages.success(request, f'Invoice has been emailed to {recipient_email}.')
    except Exception as e:
        messages.error(request, f'Error sending email: {str(e)}')

    return redirect('fees:student_fee_invoice', student_id=student_id, fee_id=fee_id)

@login_required
def student_payment_history(request, student_id):
    """View payment history for a student."""
    # Get the student
    student = get_object_or_404(Student, id=student_id)

    # Check if the user has permission to view this student's payment history
    user = request.user
    if user.role == CustomUser.Role.STUDENT and user.student_profile.id != student_id:
        messages.error(request, "You don't have permission to view this student's payment history.")
        return redirect('dashboard:index')
    elif user.role == CustomUser.Role.PARENT and student not in user.parent_profile.children.all():
        messages.error(request, "You don't have permission to view this student's payment history.")
        return redirect('dashboard:index')

    # Get filter parameters
    selected_term = request.GET.get('term')
    selected_category = request.GET.get('fee_category')
    selected_method = request.GET.get('payment_method')

    # Base query
    payments = Payment.objects.filter(
        student_fee__student=student
    ).select_related(
        'student_fee', 'student_fee__class_fee', 'student_fee__class_fee__fee_category',
        'student_fee__class_fee__term', 'receipt'
    ).order_by('-payment_date')

    # Apply filters
    if selected_term:
        payments = payments.filter(student_fee__class_fee__term_id=selected_term)

    if selected_category:
        payments = payments.filter(student_fee__class_fee__fee_category_id=selected_category)

    if selected_method:
        payments = payments.filter(payment_method=selected_method)

    # Calculate total paid
    total_paid = sum(payment.amount for payment in payments)

    # Get the last payment date
    last_payment = payments.first()

    # Pagination
    paginator = Paginator(payments, 10)  # Show 10 payments per page
    page = request.GET.get('page')
    payments = paginator.get_page(page)

    # Get all terms and fee categories for filter dropdowns
    terms = Term.objects.all().order_by('-academic_year', 'start_date')
    fee_categories = FeeCategory.objects.filter(is_active=True).order_by('name')

    context = {
        'student': student,
        'payments': payments,
        'paginator': paginator,
        'total_paid': total_paid,
        'last_payment': last_payment,
        'terms': terms,
        'fee_categories': fee_categories,
        'selected_term': selected_term,
        'selected_category': selected_category,
        'selected_method': selected_method,
    }

    return render(request, 'fees/student/student_payment_history.html', context)

# API endpoints for AJAX
@login_required
@user_passes_test(is_admin_or_accountant)
def api_class_fees(request):
    """Get class fees for a classroom and term as JSON."""
    classroom_id = request.GET.get('classroom')
    term_id = request.GET.get('term')

    if not classroom_id or not term_id:
        return JsonResponse({'error': 'Classroom and term are required'}, status=400)

    class_fees = ClassFee.objects.filter(
        classroom_id=classroom_id,
        term_id=term_id
    ).select_related('fee_category')

    data = [{
        'id': fee.id,
        'category': fee.fee_category.name,
        'category_id': fee.fee_category.id,
        'amount': float(fee.amount),
        'due_date': fee.due_date.strftime('%Y-%m-%d')
    } for fee in class_fees]

    return JsonResponse({'fees': data})

@login_required
@user_passes_test(is_admin_or_accountant)
def api_students_by_class(request, class_id):
    """Get students in a class as JSON."""
    # Check if we're getting students for a specific class fee
    class_fee_id = request.GET.get('class_fee')

    classroom = get_object_or_404(ClassRoom, id=class_id)
    students = classroom.students.all().select_related('user')

    # Get students who already have this fee assigned
    students_with_fee = set()
    if class_fee_id:
        try:
            class_fee = ClassFee.objects.get(id=class_fee_id)
            # Get IDs of students who already have this fee
            students_with_fee = set(
                StudentFee.objects.filter(class_fee=class_fee)
                .values_list('student_id', flat=True)
            )
        except ClassFee.DoesNotExist:
            pass

    data = [{
        'id': student.id,
        'name': f"{student.user.first_name} {student.user.last_name}",
        'student_id': student.student_id,
        'has_fee': student.id in students_with_fee
    } for student in students]

    return JsonResponse({'students': data})

@login_required
@user_passes_test(is_admin_or_accountant)
def api_student_fees(request, student_id):
    """Get fees for a student as JSON."""
    student = get_object_or_404(Student, id=student_id)

    # Get all student fees that are not fully paid
    student_fees = StudentFee.objects.filter(
        student=student
    ).exclude(
        status=StudentFee.Status.PAID
    ).select_related(
        'class_fee', 'class_fee__fee_category', 'class_fee__classroom', 'class_fee__term'
    ).order_by('-class_fee__term__academic_year', 'class_fee__term__name')

    data = [{
        'id': fee.id,
        'category': fee.class_fee.fee_category.name,
        'term': f"{fee.class_fee.term.name} ({fee.class_fee.term.academic_year})",
        'classroom': fee.class_fee.classroom.name,
        'amount': float(fee.amount),
        'amount_paid': float(fee.amount_paid),
        'balance': float(fee.amount - fee.amount_paid),
        'status': fee.get_status_display(),
        'due_date': fee.due_date.strftime('%Y-%m-%d')
    } for fee in student_fees]

    return JsonResponse({
        'student_name': f"{student.user.first_name} {student.user.last_name}",
        'student_id': student.student_id,
        'fees': data
    })


@login_required
@user_passes_test(is_admin_or_accountant)
def api_search_students(request):
    """API endpoint for searching students."""
    search_query = request.GET.get('q', '')

    if not search_query or len(search_query) < 2:
        return JsonResponse({'students': []})

    # Search students by name or ID
    students = Student.objects.filter(
        Q(user__first_name__icontains=search_query) |
        Q(user__last_name__icontains=search_query) |
        Q(student_id__icontains=search_query)
    ).select_related('user')[:20]  # Limit to 20 results for performance

    data = [{
        'id': student.id,
        'name': f"{student.user.first_name} {student.user.last_name}",
        'student_id': student.student_id
    } for student in students]

    return JsonResponse({'students': data})


@login_required
@user_passes_test(is_admin_or_accountant)
def quick_payment(request):
    """Quick payment recording interface."""
    return render(request, 'fees/admin/quick_payment.html')