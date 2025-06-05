from django import forms
from .models import Appointment, TimeSlot, AppointmentSettings

class AppointmentForm(forms.ModelForm):
    """
    Form for creating and updating appointments
    """
    class Meta:
        model = Appointment
        fields = ['purpose']
        widgets = {
            'purpose': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.parent = kwargs.pop('parent', None)
        self.time_slot = kwargs.pop('time_slot', None)
        super().__init__(*args, **kwargs)

        # Set default purpose from settings
        try:
            settings = AppointmentSettings.objects.first()
            if settings and not self.instance.pk:  # Only for new appointments
                self.fields['purpose'].initial = settings.default_appointment_purpose
        except:
            pass

class TimeSlotSelectionForm(forms.Form):
    """
    Form for selecting a time slot
    """
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.available_dates = kwargs.pop('available_dates', None)
        super().__init__(*args, **kwargs)

        if self.available_dates:
            self.fields['date'].widget.attrs['min'] = min(self.available_dates).isoformat()
            self.fields['date'].widget.attrs['max'] = max(self.available_dates).isoformat()

class AppointmentSettingsForm(forms.ModelForm):
    """
    Form for updating appointment settings
    """
    class Meta:
        model = AppointmentSettings
        fields = [
            'appointment_duration',
            'day_start_time',
            'day_end_time',
            'days_to_generate',
            'excluded_days',
            'slot_start_date',
            'slot_end_date',
            'excluded_hours',
            'auto_confirm_appointments',
            'default_appointment_purpose',
            'reminder_days',
            'system_active'
        ]
        widgets = {
            'appointment_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'day_start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'day_end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'days_to_generate': forms.NumberInput(attrs={'class': 'form-control'}),
            'slot_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'slot_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'excluded_hours': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '[{"start": "12:00", "end": "13:00"}]'}),
            'default_appointment_purpose': forms.TextInput(attrs={'class': 'form-control'}),
            'reminder_days': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_excluded_days(self):
        excluded_days = self.cleaned_data.get('excluded_days')
        if not excluded_days:
            return [5, 6]  # Default to weekends
        return excluded_days

    def clean_excluded_hours(self):
        excluded_hours = self.cleaned_data.get('excluded_hours')
        if not excluded_hours:
            return []

        import json
        try:
            # Try to parse as JSON
            hours = json.loads(excluded_hours)

            # Validate format
            for item in hours:
                if not isinstance(item, dict) or 'start' not in item or 'end' not in item:
                    raise forms.ValidationError("Each excluded hour must have 'start' and 'end' times.")

                # Validate time format
                try:
                    from datetime import datetime
                    datetime.strptime(item['start'], '%H:%M')
                    datetime.strptime(item['end'], '%H:%M')
                except ValueError:
                    raise forms.ValidationError("Time must be in 24-hour format (HH:MM).")

            return hours
        except json.JSONDecodeError:
            raise forms.ValidationError("Excluded hours must be valid JSON.")
