from django.core.management.base import BaseCommand
from users.models import AdmissionLetterTemplate
from django.utils import timezone

class Command(BaseCommand):
    help = 'Fixes the admission letter templates to use proper placeholder format'

    def handle(self, *args, **kwargs):
        # Default template content - clean version without Django template variables
        default_template_body = """Dear {student_name},

CONFIRMATION OF ADMISSION
We are pleased to inform you that you have been offered admission to Deigratia Montessory School for the academic year {academic_year}. Congratulations!

Please find below the details of your admission:

Student Name:	{student_name}
Student ID:	{student_id}
Grade/Class:	{grade}
Section:	{section}
Academic Year:	{academic_year}
Admission Date:	{admission_date}
School Start Date:	{start_date}

The school session will commence on {start_date}. Please report to the school office by 8:00 AM on the first day with the following documents:

1. Original copy of previous academic records
2. Birth certificate
3. Two recent passport-sized photographs
4. Transfer certificate (if applicable)
5. Medical certificate

Your School Management System Login Credentials:
Username: {student_id}
PIN: {pin}

These credentials will give you access to your academic records, assignments, grades, and other important school resources. Please keep them confidential and secure.

We look forward to welcoming you to our school community and are confident that you will have a rewarding educational experience at Deigratia Montessory School.

Sincerely,

Mrs. Elizabeth Okafor
Principal
Deigratia Montessory School"""

        # Find existing templates or create a new one
        templates = AdmissionLetterTemplate.objects.all()
        
        if templates.exists():
            # Update all existing templates
            template_count = 0
            for template in templates:
                template.body_template = default_template_body
                template.header_text = "DEIGRATIA MONTESSORY SCHOOL\nExcellence in Education"
                template.signatory_name = "Mrs. Elizabeth Okafor"
                template.signatory_position = "Principal"
                template.save()
                template_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {template_count} existing template(s)'))
        else:
            # Create a new template if none exist
            AdmissionLetterTemplate.objects.create(
                name="Default Admission Letter",
                header_text="DEIGRATIA MONTESSORY SCHOOL\nExcellence in Education",
                body_template=default_template_body,
                footer_text="This is an official document from Deigratia Montessory School. Please keep this letter for your records.",
                signatory_name="Mrs. Elizabeth Okafor",
                signatory_position="Principal",
                is_active=True,
                created_at=timezone.now()
            )
            self.stdout.write(self.style.SUCCESS('Successfully created a new default template'))