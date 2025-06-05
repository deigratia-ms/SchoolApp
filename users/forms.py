from django import forms
from .models import AdmissionLetterTemplate

class AdmissionLetterTemplateForm(forms.ModelForm):
    class Meta:
        model = AdmissionLetterTemplate
        fields = [
            'name', 'header_text', 'body_template', 'footer_text',
            'signatory_name', 'signatory_position', 'signature_image', 'is_active'
        ]
