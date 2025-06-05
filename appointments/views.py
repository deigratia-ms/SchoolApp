from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta, date
import json
import csv

from users.models import CustomUser, Parent
from .models import Appointment, TimeSlot, AppointmentSettings
from .forms import AppointmentForm, TimeSlotSelectionForm, AppointmentSettingsForm
from .notifications import send_appointment_confirmation, send_appointment_update, send_appointment_cancellation

# Helper functions for role-based access
def is_admin(user):
    return user.is_authenticated and user.role == CustomUser.Role.ADMIN

def is_parent(user):
    return user.is_authenticated and user.role == CustomUser.Role.PARENT

def check_system_active(view_func):
    """Decorator to check if the appointment system is active"""
    def _wrapped_view(request, *args, **kwargs):
        settings = AppointmentSettings.objects.first()
        if not settings or not settings.system_active:
            return redirect('appointments:system_inactive')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def system_inactive(request):
    """View for when the appointment system is inactive"""
    return render(request, 'appointments/system_inactive.html')

@login_required
def appointment_home(request):
    """
    Home page for the appointments app
    """
    # Check if the system is active
    settings = AppointmentSettings.objects.first()
    if not settings or not settings.system_active:
        return render(request, 'appointments/system_inactive.html')

    # Redirect based on user role
    if is_admin(request.user):
        return redirect('appointments:admin_dashboard')
    elif is_parent(request.user):
        return redirect('appointments:parent_dashboard')
    else:
        messages.warning(request, "You don't have access to the appointment system.")
        return redirect('dashboard:index')

@login_required
@user_passes_test(is_parent)
@check_system_active
def parent_dashboard(request):
    """
    Dashboard for parents to view and manage their appointments
    """
    # Get parent profile
    parent = get_object_or_404(Parent, user=request.user)

    # Get upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        parent=parent,
        time_slot__date__gte=timezone.now().date(),
        status__in=['pending', 'confirmed']
    ).order_by('time_slot__date', 'time_slot__start_time')

    # Get past appointments
    past_appointments = Appointment.objects.filter(
        parent=parent,
        time_slot__date__lt=timezone.now().date()
    ).order_by('-time_slot__date', '-time_slot__start_time')[:10]

    context = {
        'parent': parent,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
    }

    return render(request, 'appointments/parent_dashboard.html', context)

@login_required
@user_passes_test(is_parent)
@check_system_active
def book_appointment(request):
    """
    Allow parents to book a new appointment
    """
    # Get parent profile
    parent = get_object_or_404(Parent, user=request.user)

    # Get filter parameters
    selected_date = request.GET.get('date')
    time_range = request.GET.get('time_range', 'all')

    # Base queryset - get available time slots
    time_slots = TimeSlot.objects.filter(
        date__gte=timezone.now().date(),
        is_available=True,
        is_active=True
    )

    # Apply date filter if provided
    if selected_date:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            time_slots = time_slots.filter(date=date_obj)
        except ValueError:
            messages.warning(request, "Invalid date format.")

    # Apply time range filter if provided
    if time_range and time_range != 'all':
        if time_range == 'morning':
            # Morning: 9 AM - 12 PM
            morning_start = datetime.strptime('09:00', '%H:%M').time()
            morning_end = datetime.strptime('12:00', '%H:%M').time()
            time_slots = time_slots.filter(start_time__gte=morning_start, start_time__lt=morning_end)
        elif time_range == 'afternoon':
            # Afternoon: 12 PM - 3 PM
            afternoon_start = datetime.strptime('12:00', '%H:%M').time()
            afternoon_end = datetime.strptime('15:00', '%H:%M').time()
            time_slots = time_slots.filter(start_time__gte=afternoon_start, start_time__lt=afternoon_end)
        elif time_range == 'evening':
            # Evening: 3 PM - 6 PM
            evening_start = datetime.strptime('15:00', '%H:%M').time()
            evening_end = datetime.strptime('18:00', '%H:%M').time()
            time_slots = time_slots.filter(start_time__gte=evening_start, start_time__lt=evening_end)

    # Order by date and time
    time_slots = time_slots.order_by('date', 'start_time')

    # Get available dates for the filter dropdown
    available_dates = TimeSlot.objects.filter(
        date__gte=timezone.now().date(),
        is_available=True,
        is_active=True
    ).values_list('date', flat=True).distinct()
    available_dates = list(set(available_dates))

    if not time_slots.exists() and not available_dates:
        messages.warning(request, "There are no available appointment slots at this time.")
        return redirect('appointments:parent_dashboard')

    # Paginate results
    paginator = Paginator(time_slots, 15)  # 15 slots per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'parent': parent,
        'page_obj': page_obj,
        'available_dates': available_dates,
        'selected_date': selected_date,
        'time_range': time_range,
    }

    return render(request, 'appointments/book_appointment.html', context)

@login_required
@user_passes_test(is_parent)
def select_time_slot(request, date):
    """
    Allow parents to select a time slot for their appointment
    """
    # Get parent profile
    parent = get_object_or_404(Parent, user=request.user)

    # Convert date string to date object
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect('appointments:book_appointment')

    # Check if date is in the past
    if selected_date < timezone.now().date():
        messages.error(request, "Cannot book appointments for past dates.")
        return redirect('appointments:book_appointment')

    # Get available time slots for the selected date
    available_slots = TimeSlot.objects.filter(
        date=selected_date,
        is_available=True
    ).order_by('start_time')

    if not available_slots:
        messages.warning(request, f"There are no available time slots for {selected_date}.")
        return redirect('appointments:book_appointment')

    context = {
        'parent': parent,
        'selected_date': selected_date,
        'available_slots': available_slots,
    }

    return render(request, 'appointments/select_time_slot.html', context)

@login_required
@user_passes_test(is_parent)
def preview_appointment(request, slot_id):
    """
    Preview appointment details before confirming
    """
    # Get parent profile
    parent = get_object_or_404(Parent, user=request.user)

    # Get time slot
    time_slot = get_object_or_404(TimeSlot, id=slot_id, is_available=True)

    # Check if slot is in the past
    slot_datetime = datetime.combine(time_slot.date, time_slot.start_time)
    # Make the slot_datetime timezone-aware to compare with timezone.now()
    slot_datetime = timezone.make_aware(slot_datetime)
    if slot_datetime < timezone.now():
        messages.error(request, "This time slot is no longer available.")
        return redirect('appointments:book_appointment')

    # Create appointment form
    form = AppointmentForm(request.POST or None, parent=parent, time_slot=time_slot)

    if request.method == 'POST' and form.is_valid():
        # Create appointment
        appointment = form.save(commit=False)
        appointment.parent = parent
        appointment.time_slot = time_slot

        # Check if auto-confirm is enabled
        settings = AppointmentSettings.objects.first()
        if settings and settings.auto_confirm_appointments:
            appointment.status = 'confirmed'

        appointment.save()

        # Send confirmation email
        send_appointment_confirmation(appointment)

        messages.success(request, "Your appointment has been booked successfully.")
        return redirect('appointments:parent_dashboard')

    context = {
        'parent': parent,
        'time_slot': time_slot,
        'form': form,
        'children': parent.children.all(),
    }

    return render(request, 'appointments/preview_appointment.html', context)

@login_required
def appointment_detail(request, appointment_id):
    """
    View appointment details
    """
    # Get appointment
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Check if user has permission to view this appointment
    if not is_admin(request.user) and not (is_parent(request.user) and appointment.parent.user == request.user):
        messages.error(request, "You don't have permission to view this appointment.")
        return redirect('dashboard:index')

    context = {
        'appointment': appointment,
        'today': timezone.now().date(),
    }

    return render(request, 'appointments/appointment_detail.html', context)

@login_required
def cancel_appointment(request, appointment_id):
    """
    Cancel an appointment
    """
    # Get appointment
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Check if user has permission to cancel this appointment
    if not is_admin(request.user) and not (is_parent(request.user) and appointment.parent.user == request.user):
        messages.error(request, "You don't have permission to cancel this appointment.")
        return redirect('dashboard:index')

    # Check if appointment can be cancelled
    if appointment.status in ['cancelled', 'completed']:
        messages.error(request, "This appointment cannot be cancelled.")
        return redirect('appointments:appointment_detail', appointment_id=appointment.id)

    if request.method == 'POST':
        # Cancel appointment
        appointment.status = 'cancelled'
        appointment.save()

        # Make time slot available again
        time_slot = appointment.time_slot
        time_slot.is_available = True
        time_slot.save()

        # Send cancellation email
        send_appointment_cancellation(appointment)

        messages.success(request, "The appointment has been cancelled.")

        # Always redirect to the appropriate dashboard
        if is_admin(request.user):
            return redirect('appointments:admin_dashboard')
        else:
            return redirect('appointments:parent_dashboard')

    context = {
        'appointment': appointment,
    }

    return render(request, 'appointments/cancel_appointment.html', context)

@login_required
@user_passes_test(is_admin)
@check_system_active
def admin_dashboard(request):
    """
    Dashboard for admins to manage appointments
    """
    # Get all appointments
    upcoming_appointments = Appointment.objects.filter(
        time_slot__date__gte=timezone.now().date(),
        status__in=['pending', 'confirmed']
    ).order_by('time_slot__date', 'time_slot__start_time')

    # Get today's appointments
    today_appointments = Appointment.objects.filter(
        time_slot__date=timezone.now().date(),
        status__in=['pending', 'confirmed']
    ).order_by('time_slot__start_time')

    # Get pending appointments
    pending_appointments = Appointment.objects.filter(
        status='pending'
    ).order_by('time_slot__date', 'time_slot__start_time')

    # Get appointment settings
    settings = AppointmentSettings.objects.first()

    context = {
        'upcoming_appointments': upcoming_appointments,
        'today_appointments': today_appointments,
        'pending_appointments': pending_appointments,
        'settings': settings,
    }

    return render(request, 'appointments/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def manage_settings(request):
    """
    Manage appointment settings
    """
    # Get or create settings
    settings, created = AppointmentSettings.objects.get_or_create(
        defaults={'school_name': 'School Appointment System'}
    )

    # Create form
    form = AppointmentSettingsForm(request.POST or None, instance=settings)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Settings updated successfully.")
        return redirect('appointments:admin_dashboard')

    context = {
        'form': form,
        'settings': settings,
    }

    return render(request, 'appointments/manage_settings.html', context)

@login_required
@user_passes_test(is_admin)
def generate_time_slots(request):
    """
    Generate time slots based on settings
    """
    if request.method == 'POST':
        # Get settings
        settings = AppointmentSettings.objects.first()
        if not settings:
            messages.error(request, "Appointment settings not found.")
            return redirect('appointments:manage_settings')

        # Get date range
        start_date = settings.slot_start_date or timezone.now().date()
        if start_date < timezone.now().date():
            start_date = timezone.now().date()

        end_date = settings.slot_end_date
        if not end_date:
            end_date = start_date + timedelta(days=settings.days_to_generate)

        # Generate slots
        slots_created = 0
        current_date = start_date

        while current_date <= end_date:
            # Skip excluded days
            weekday = current_date.weekday()
            if weekday in settings.excluded_days:
                current_date += timedelta(days=1)
                continue

            # Generate slots for this day
            current_time = datetime.combine(current_date, settings.day_start_time).time()
            end_time = settings.day_end_time

            while current_time < end_time:
                # Check if this time is in excluded hours
                is_excluded = False
                for excluded in settings.excluded_hours:
                    excluded_start = datetime.strptime(excluded['start'], '%H:%M').time()
                    excluded_end = datetime.strptime(excluded['end'], '%H:%M').time()
                    if excluded_start <= current_time < excluded_end:
                        is_excluded = True
                        break

                if not is_excluded:
                    # Calculate slot end time
                    slot_end_time = (datetime.combine(date.today(), current_time) +
                                    timedelta(minutes=settings.appointment_duration)).time()

                    # Create slot if it doesn't exist
                    if not TimeSlot.objects.filter(date=current_date, start_time=current_time).exists():
                        TimeSlot.objects.create(
                            date=current_date,
                            start_time=current_time,
                            end_time=slot_end_time,
                            is_available=True
                        )
                        slots_created += 1

                # Move to next slot
                current_time = (datetime.combine(date.today(), current_time) +
                               timedelta(minutes=settings.appointment_duration)).time()

            # Move to next day
            current_date += timedelta(days=1)

        messages.success(request, f"{slots_created} time slots generated successfully.")
        return redirect('appointments:admin_dashboard')

    return redirect('appointments:manage_settings')

@login_required
@user_passes_test(is_admin)
@check_system_active
def manage_time_slots(request):
    """
    View and manage time slots
    """
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    time_filter = request.GET.get('time')

    # Base queryset - get future time slots
    time_slots = TimeSlot.objects.filter(
        date__gte=timezone.now().date()
    )

    # Apply filters
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            time_slots = time_slots.filter(date__gte=date_from)
        except ValueError:
            messages.warning(request, "Invalid date format for 'Date From'.")

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            time_slots = time_slots.filter(date__lte=date_to)
        except ValueError:
            messages.warning(request, "Invalid date format for 'Date To'.")

    if status:
        if status == 'available':
            time_slots = time_slots.filter(is_available=True, is_active=True)
        elif status == 'unavailable':
            time_slots = time_slots.filter(is_available=False)
        elif status == 'inactive':
            time_slots = time_slots.filter(is_active=False)

    if time_filter:
        try:
            time_obj = datetime.strptime(time_filter, '%H:%M').time()
            time_slots = time_slots.filter(start_time__lte=time_obj, end_time__gte=time_obj)
        except ValueError:
            messages.warning(request, "Invalid time format. Please use HH:MM format.")

    # Order by date and time
    time_slots = time_slots.order_by('date', 'start_time')

    context = {
        'time_slots': time_slots,
    }

    return render(request, 'appointments/manage_time_slots.html', context)

@login_required
@user_passes_test(is_admin)
def delete_time_slot(request, slot_id):
    """
    Delete a time slot
    """
    # Get time slot
    time_slot = get_object_or_404(TimeSlot, id=slot_id)

    # Check if slot has appointments
    if Appointment.objects.filter(time_slot=time_slot).exists():
        messages.error(request, "Cannot delete time slot with existing appointments.")
        return redirect('appointments:manage_time_slots')

    # Delete slot
    time_slot.delete()
    messages.success(request, "Time slot deleted successfully.")
    return redirect('appointments:manage_time_slots')

@login_required
@user_passes_test(is_admin)
def bulk_time_slot_action(request):
    """
    Perform bulk actions on time slots (delete, activate, deactivate)
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        slot_ids = request.POST.get('slot_ids', '')

        if not slot_ids:
            messages.error(request, "No time slots selected.")
            return redirect('appointments:manage_time_slots')

        # Convert comma-separated IDs to list
        slot_id_list = [int(id) for id in slot_ids.split(',')]
        slots = TimeSlot.objects.filter(id__in=slot_id_list)

        if action == 'delete':
            # Check if any slots have appointments
            slots_with_appointments = slots.filter(appointment__isnull=False).distinct()
            if slots_with_appointments.exists():
                messages.error(request, f"Cannot delete {slots_with_appointments.count()} time slots with existing appointments.")
                # Delete only slots without appointments
                slots_to_delete = slots.exclude(id__in=slots_with_appointments.values_list('id', flat=True))
                count = slots_to_delete.count()
                if count > 0:
                    slots_to_delete.delete()
                    messages.success(request, f"{count} time slots deleted successfully.")
            else:
                # Delete all selected slots
                count = slots.count()
                slots.delete()
                messages.success(request, f"{count} time slots deleted successfully.")

        elif action == 'deactivate':
            # Only deactivate available slots
            available_slots = slots.filter(is_available=True)
            count = available_slots.count()
            available_slots.update(is_active=False)
            messages.success(request, f"{count} time slots deactivated successfully.")

        elif action == 'activate':
            # Only activate available slots
            available_slots = slots.filter(is_available=True)
            count = available_slots.count()
            available_slots.update(is_active=True)
            messages.success(request, f"{count} time slots activated successfully.")

        else:
            messages.error(request, "Invalid action.")

    return redirect('appointments:manage_time_slots')

@login_required
@user_passes_test(is_admin)
@check_system_active
def appointment_list(request):
    """
    List all appointments with filtering and export options
    """
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    search = request.GET.get('search')

    # Base queryset
    appointments = Appointment.objects.all().select_related('parent__user', 'time_slot')

    # Apply filters
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            appointments = appointments.filter(time_slot__date__gte=date_from)
        except ValueError:
            messages.warning(request, "Invalid date format for 'Date From'.")

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            appointments = appointments.filter(time_slot__date__lte=date_to)
        except ValueError:
            messages.warning(request, "Invalid date format for 'Date To'.")

    if status:
        appointments = appointments.filter(status=status)

    if search:
        appointments = appointments.filter(
            Q(parent__user__first_name__icontains=search) |
            Q(parent__user__last_name__icontains=search) |
            Q(parent__user__email__icontains=search) |
            Q(purpose__icontains=search)
        )

    # Order by date and time
    appointments = appointments.order_by('time_slot__date', 'time_slot__start_time')

    # Paginate results
    paginator = Paginator(appointments, 20)  # 20 appointments per page
    page_number = request.GET.get('page')
    appointments = paginator.get_page(page_number)

    context = {
        'appointments': appointments,
    }

    return render(request, 'appointments/appointment_list.html', context)

@login_required
@user_passes_test(is_admin)
def export_appointments(request):
    """
    Export appointments to CSV
    """
    # Get filter parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    search = request.GET.get('search')
    ids = request.GET.get('ids')

    # Base queryset
    appointments = Appointment.objects.all().select_related('parent__user', 'time_slot')

    # Filter by IDs if provided
    if ids:
        id_list = [int(id) for id in ids.split(',')]
        appointments = appointments.filter(id__in=id_list)
    else:
        # Apply other filters
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                appointments = appointments.filter(time_slot__date__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                appointments = appointments.filter(time_slot__date__lte=date_to)
            except ValueError:
                pass

        if status:
            appointments = appointments.filter(status=status)

        if search:
            appointments = appointments.filter(
                Q(parent__user__first_name__icontains=search) |
                Q(parent__user__last_name__icontains=search) |
                Q(parent__user__email__icontains=search) |
                Q(purpose__icontains=search)
            )

    # Order by date and time
    appointments = appointments.order_by('time_slot__date', 'time_slot__start_time')

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="appointments.csv"'

    # Create CSV writer
    writer = csv.writer(response)

    # Write header row
    writer.writerow([
        'Date', 'Time', 'Parent Name', 'Email', 'Phone', 'Children', 'Classes',
        'Purpose', 'Status', 'Created At'
    ])

    # Write data rows
    for appointment in appointments:
        # Get children and their classes
        children = []
        classes = []
        for child in appointment.parent.children.all():
            children.append(child.user.get_full_name())
            if child.grade:
                section = f" {child.section}" if child.section and child.section != 'None' else ""
                classes.append(f"{child.grade.name}{section}")
            else:
                classes.append("No class")

        writer.writerow([
            appointment.time_slot.date.strftime('%Y-%m-%d'),
            f"{appointment.time_slot.start_time.strftime('%H:%M')} - {appointment.time_slot.end_time.strftime('%H:%M')}",
            appointment.parent.user.get_full_name(),
            appointment.parent.user.email,
            appointment.parent.user.phone_number or 'Not provided',
            ', '.join(children),
            ', '.join(classes),
            appointment.purpose.replace('\n', ' ').replace('\r', ''),
            appointment.get_status_display(),
            appointment.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response

@login_required
@user_passes_test(is_admin)
def update_appointment_status(request, appointment_id):
    """
    Update the status of an appointment
    """
    # Get appointment
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [status[0] for status in Appointment.STATUS_CHOICES]:
            old_status = appointment.status
            appointment.status = new_status

            # If marking as completed, set completed_at
            if new_status == 'completed' and not appointment.completed_at:
                appointment.completed_at = timezone.now()

            appointment.save()

            # Send notification if status changed
            if old_status != new_status:
                send_appointment_update(appointment, [f"Status changed from {old_status} to {new_status}"])

            messages.success(request, "Appointment status updated successfully.")
        else:
            messages.error(request, "Invalid status.")

    return redirect('appointments:appointment_detail', appointment_id=appointment.id)

@login_required
@user_passes_test(is_admin)
def create_appointment(request):
    """
    Admin can create an appointment for a parent
    """
    # Get all parents
    parents = Parent.objects.all()

    # Get available time slots
    available_slots = TimeSlot.objects.filter(
        date__gte=timezone.now().date(),
        is_available=True
    ).order_by('date', 'start_time')

    if request.method == 'POST':
        parent_id = request.POST.get('parent_id')
        slot_id = request.POST.get('slot_id')
        purpose = request.POST.get('purpose')

        if not parent_id or not slot_id or not purpose:
            messages.error(request, "All fields are required.")
        else:
            try:
                parent = Parent.objects.get(id=parent_id)
                time_slot = TimeSlot.objects.get(id=slot_id, is_available=True)

                # Create appointment
                appointment = Appointment.objects.create(
                    parent=parent,
                    time_slot=time_slot,
                    purpose=purpose,
                    status='confirmed'  # Admin-created appointments are automatically confirmed
                )

                # Mark slot as unavailable
                time_slot.is_available = False
                time_slot.save()

                # Send confirmation email
                send_appointment_confirmation(appointment)

                messages.success(request, "Appointment created successfully.")
                return redirect('appointments:appointment_detail', appointment_id=appointment.id)
            except (Parent.DoesNotExist, TimeSlot.DoesNotExist):
                messages.error(request, "Invalid parent or time slot.")

    context = {
        'parents': parents,
        'available_slots': available_slots,
    }

    return render(request, 'appointments/create_appointment.html', context)
