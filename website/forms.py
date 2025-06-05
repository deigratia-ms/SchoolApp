from django import forms
from .models import ContactMessage, AdmissionsInquiry

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Phone Number'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Your Message',
                'rows': 5
            }),
        }

class AdmissionsInquiryForm(forms.ModelForm):
    class Meta:
        model = AdmissionsInquiry
        fields = ['name', 'email', 'phone', 'child_name', 'child_age', 
                 'program_interest', 'start_date', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Parent/Guardian Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
            'child_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Child\'s Name'
            }),
            'child_age': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Child\'s Age'
            }),
            'program_interest': forms.Select(attrs={
                'class': 'form-control'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Additional Information or Questions',
                'rows': 4
            }),
        }
        
    def clean_child_age(self):
        age = self.cleaned_data.get('child_age')
        if age < 1 or age > 12:
            raise forms.ValidationError("Child's age must be between 1 and 12 years.")
        return age

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        if len(phone) < 10:
            raise forms.ValidationError("Please enter a valid phone number.")
        return phone
