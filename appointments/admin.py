from django.contrib import admin
from .models import AppointmentSettings, TimeSlot, Appointment

# Register your models here.

@admin.register(AppointmentSettings)
class AppointmentSettingsAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'appointment_duration', 'day_start_time', 'day_end_time', 'system_active')
    fieldsets = (
        ('General', {
            'fields': ('school_name', 'system_active', 'default_appointment_purpose')
        }),
        ('Time Slot Settings', {
            'fields': ('appointment_duration', 'day_start_time', 'day_end_time', 'days_to_generate',
                      'slot_start_date', 'slot_end_date', 'excluded_days', 'excluded_hours')
        }),
        ('Email Settings', {
            'fields': ('reminder_days', 'auto_confirm_appointments')
        }),
    )

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('generate-slots/', self.admin_site.admin_view(self.generate_slots_view), name='generate_slots'),
        ]
        return custom_urls + urls

    def generate_slots_view(self, request):
        from django.shortcuts import redirect
        from django.contrib import messages
        from django.urls import reverse
        from datetime import datetime, timedelta, date

        # Get settings
        settings = AppointmentSettings.objects.first()
        if not settings:
            messages.error(request, "Appointment settings not found.")
            return redirect('admin:appointments_appointmentsettings_changelist')

        # Get date range
        start_date = settings.slot_start_date or datetime.now().date()
        if start_date < datetime.now().date():
            start_date = datetime.now().date()

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
        return redirect('admin:appointments_appointmentsettings_changelist')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_generate_slots_button'] = True
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'start_time', 'end_time', 'is_available')
    list_filter = ('date', 'is_available')
    search_fields = ('date',)
    date_hierarchy = 'date'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('parent', 'time_slot', 'status', 'created_at')
    list_filter = ('status', 'time_slot__date')
    search_fields = ('parent__user__first_name', 'parent__user__last_name', 'purpose')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        ('Appointment Details', {
            'fields': ('parent', 'time_slot', 'purpose', 'status')
        }),
        ('Reminders', {
            'fields': ('reminder_sent', 'reminder_3days_sent', 'reminder_1day_sent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
