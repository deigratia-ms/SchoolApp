from django.core.management.base import BaseCommand
from users.models import IDCardTemplate, AdmissionLetterTemplate, SchoolSettings
from django.db.models import Q


class Command(BaseCommand):
    help = 'Creates default ID card templates and admission letter templates'

    def handle(self, *args, **kwargs):
        # Set school name to Deigratia Montessory School
        school_settings = SchoolSettings.objects.first()
        if school_settings:
            if school_settings.school_name != "Deigratia Montessory School":
                school_settings.school_name = "Deigratia Montessory School"
                school_settings.save()
                self.stdout.write(self.style.SUCCESS(
                    'School name set to "Deigratia Montessory School"'
                ))
        else:
            SchoolSettings.objects.create(school_name="Deigratia Montessory School")
            self.stdout.write(self.style.SUCCESS(
                'Created new school settings with name "Deigratia Montessory School"'
            ))

        # Part 1: Create ID Card Templates
        self.create_id_card_templates()
        
        # Part 2: Create Admission Letter Templates
        self.create_admission_letter_templates()

    def create_id_card_templates(self):
        # First, delete any existing templates
        existing_count = IDCardTemplate.objects.count()
        if existing_count > 0:
            self.stdout.write(self.style.WARNING(
                f'Removing {existing_count} existing ID card templates to create new ones.'
            ))
            IDCardTemplate.objects.all().delete()

        # CR80 standard card dimensions in landscape mode (300 DPI)
        # 2.125" x 3.375" (54.02mm x 85.77mm) with landscape orientation
        card_width = 1013  # 3.375" * 300 DPI
        card_height = 638  # 2.125" * 300 DPI

        # Default templates to create with new fields
        templates = [
            # University Style (Red with curves) - Based on first sample
            {
                'name': 'University Style - Student ID Card',
                'role': 'STUDENT',
                'header_text': 'STUDENT ID CARD',
                'card_width': card_width,
                'card_height': card_height,
                'text_color': '#FFFFFF',  # White text
                'background_color': '#c0392b',  # Deep red
                'header_color': '#a93226',  # Darker red for header
                'footer_color': '#a93226',  # Darker red for footer
                'use_curved_design': True,  # Enable curved design elements
                'footer_text': '<div>Deigratia Montessory School | 123 Education Avenue, Lagos, Nigeria</div><div>Tel: +234-123-456-7890 | Email: info@deigratia.edu.ng</div>',
                'is_active': True
            },
            
            # Fauget Highschool Style (Blue and Orange) - Based on second sample
            {
                'name': 'Fauget Highschool Style - Student ID Card',
                'role': 'STUDENT',
                'header_text': 'STUDENT ID CARD',
                'card_width': card_width,
                'card_height': card_height,
                'text_color': '#000000',  # Black text 
                'background_color': '#f39c12',  # Orange
                'header_color': '#3498db',  # Blue header
                'footer_color': '#3498db',  # Blue footer
                'use_curved_design': False, 
                'footer_text': '<div>Fauget Highschool | A Premier Educational Institution</div><div>123 Learning Drive | Tel: +234-123-456-7890 | www.fauget.edu</div>',
                'is_active': True
            },
            
            # Mount Convent Style (Blue) - Based on third sample
            {
                'name': 'Mount Convent Style - Student ID Card',
                'role': 'STUDENT',
                'header_text': 'IDENTITY CARD',
                'card_width': card_width,
                'card_height': card_height,
                'text_color': '#FFFFFF',  # White text
                'background_color': '#2980b9',  # Blue background
                'header_color': '#1a5276',  # Darker blue header
                'footer_color': '#1a5276',  # Darker blue footer
                'use_curved_design': False,
                'footer_text': '<div>Mount Convent Matriculation School | Affiliated to CBSE, New Delhi</div><div>School Code: 654321 | Contact: +234-123-456-7890</div>',
                'is_active': True
            },
            
            # Professional Teacher Template - Green design
            {
                'name': 'Professional Teacher ID Card',
                'role': 'TEACHER',
                'header_text': 'STAFF IDENTIFICATION CARD',
                'card_width': card_width,
                'card_height': card_height,
                'text_color': '#FFFFFF',  # White text
                'background_color': '#27ae60',  # Green
                'header_color': '#1e8449',  # Darker green header
                'footer_color': '#1e8449',  # Darker green footer
                'use_curved_design': True,  # Enable curved design for staff cards
                'footer_text': '<div>Deigratia Montessory School | Faculty Identification</div><div>Valid only with official school stamp | Contact: +234-123-456-7890</div>',
                'is_active': True
            },
            
            # Parent Template - Purple design
            {
                'name': 'Standard Parent ID Card',
                'role': 'PARENT',
                'header_text': 'PARENT/GUARDIAN ID CARD',
                'card_width': card_width,
                'card_height': card_height,
                'text_color': '#FFFFFF',  # White text
                'background_color': '#8e44ad',  # Purple
                'header_color': '#7d3c98',  # Darker purple header
                'footer_color': '#7d3c98',  # Darker purple footer
                'use_curved_design': True,  # Enable curved design for parent cards
                'footer_text': '<div>Deigratia Montessory School | Parent/Guardian Access</div><div>This card must be presented for campus access | Contact: +234-123-456-7890</div>',
                'is_active': True
            }
        ]

        # Create each template
        created_count = 0
        for template_data in templates:
            role = template_data['role']
            name = template_data['name']
            
            # Create the template
            IDCardTemplate.objects.create(**template_data)
            created_count += 1
            self.stdout.write(self.style.SUCCESS(
                f'Created template: {name} for {role}'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {created_count} professional ID card templates with CR80 standard dimensions '
            f'({card_width} x {card_height} pixels) in landscape orientation'
        ))

    def create_admission_letter_templates(self):
        # First, check if there are existing admission letter templates
        existing_count = AdmissionLetterTemplate.objects.count()
        if existing_count > 0:
            self.stdout.write(self.style.WARNING(
                f'Removing {existing_count} existing admission letter templates to create new ones.'
            ))
            AdmissionLetterTemplate.objects.all().delete()

        # Default templates to create
        templates = [
            # Template 1: New Student Admission Letter
            {
                'name': 'New Student Admission Letter',
                'header_text': 'OFFICIAL ADMISSION LETTER',
                'body_template': '''
<div style="text-align: center;">
    <h1 style="color: #2c3e50; font-family: 'Times New Roman', serif; margin-bottom: 5px;">DEIGRATIA MONTESSORY SCHOOL</h1>
    <p style="color: #7f8c8d; font-size: 16px; margin-top: 0;">Excellence in Education</p>
    <hr style="width: 80%; border: 1px solid #3498db; margin: 10px auto 20px;">
</div>

<div style="text-align: right; margin-bottom: 20px;">
    <p>Reference: {reference_number}<br>
    Date: {current_date}</p>
</div>

<div style="margin-bottom: 20px;">
    <p><strong>Dear {student_name},</strong></p>
</div>

<div style="text-align: center; margin-bottom: 20px;">
    <h2 style="color: #2c3e50; font-family: 'Times New Roman', serif;">CONFIRMATION OF ADMISSION</h2>
</div>

<div style="margin-bottom: 30px; text-align: justify; line-height: 1.5;">
    <p>We are pleased to inform you that you have been offered admission to <strong>Deigratia Montessory School</strong> for the academic year {academic_year}. Congratulations!</p>
    
    <p>Please find below the details of your admission:</p>
    
    <table style="width: 80%; margin: 20px auto; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7; width: 40%;"><strong>Student Name:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{student_name}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Student ID:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{student_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Grade/Class:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{grade}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Section:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{section}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Academic Year:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{academic_year}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Admission Date:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{admission_date}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>School Start Date:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{start_date}</td>
        </tr>
    </table>
    
    <p>The school session will commence on <strong>{start_date}</strong>. Please report to the school office by 8:00 AM on the first day with the following documents:</p>
    
    <ol>
        <li>Original copy of previous academic records</li>
        <li>Birth certificate</li>
        <li>Two recent passport-sized photographs</li>
        <li>Transfer certificate (if applicable)</li>
        <li>Medical certificate</li>
    </ol>
    
    <p style="background-color: #f8f9fa; padding: 15px; border-left: 5px solid #3498db; margin: 15px 0;">
        <strong>Your School Management System Login Credentials:</strong><br>
        Username: {student_id}<br>
        PIN: {pin}
    </p>
    
    <p>These credentials will give you access to your academic records, assignments, grades, and other important school resources. Please keep them confidential and secure.</p>
    
    <p>We look forward to welcoming you to our school community and are confident that you will have a rewarding educational experience at Deigratia Montessory School.</p>
</div>

<div style="margin-top: 40px;">
    <p>Sincerely,</p>
    <p style="margin-top: 30px;">
        <strong>Mrs. Elizabeth Okafor</strong><br>
        Principal<br>
        Deigratia Montessory School
    </p>
</div>
''',
                'footer_text': '''
<div style="text-align: center; margin-top: 30px; font-size: 12px; color: #7f8c8d;">
    <p>Deigratia Montessory School | 123 Education Avenue, Lagos, Nigeria | Tel: +234-123-456-7890 | Email: info@deigratia.edu.ng</p>
</div>
''',
                'signatory_name': 'Mrs. Elizabeth Okafor',
                'signatory_position': 'Principal',
                'is_active': True
            },
            
            # Template 2: Promotion/Continuation Letter
            {
                'name': 'Promotion/Continuation Letter',
                'header_text': 'ACADEMIC PROMOTION NOTIFICATION',
                'body_template': '''
<div style="text-align: center;">
    <h1 style="color: #2c3e50; font-family: 'Times New Roman', serif; margin-bottom: 5px;">DEIGRATIA MONTESSORY SCHOOL</h1>
    <p style="color: #7f8c8d; font-size: 16px; margin-top: 0;">Excellence in Education</p>
    <hr style="width: 80%; border: 1px solid #27ae60; margin: 10px auto 20px;">
</div>

<div style="text-align: right; margin-bottom: 20px;">
    <p>Reference: {reference_number}<br>
    Date: {current_date}</p>
</div>

<div style="margin-bottom: 20px;">
    <p><strong>Dear {student_name},</strong></p>
</div>

<div style="text-align: center; margin-bottom: 20px;">
    <h2 style="color: #27ae60; font-family: 'Times New Roman', serif;">PROMOTION TO THE NEXT ACADEMIC LEVEL</h2>
</div>

<div style="margin-bottom: 30px; text-align: justify; line-height: 1.5;">
    <p>We are pleased to inform you that based on your academic performance and conduct during the previous academic year, you have been <strong>promoted</strong> to the next grade level for the upcoming academic year {academic_year}.</p>
    
    <p>Your promotion details are as follows:</p>
    
    <table style="width: 80%; margin: 20px auto; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7; width: 40%;"><strong>Student Name:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{student_name}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Student ID:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{student_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Previous Grade:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{previous_grade}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Promoted to Grade:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{grade}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Section:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{section}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Academic Year:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{academic_year}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>School Start Date:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{start_date}</td>
        </tr>
    </table>
    
    <p>The new academic session will begin on <strong>{start_date}</strong>. Please ensure that you report to your new class by 8:00 AM on the first day with all required learning materials. A list of required textbooks and supplies for your new grade is attached to this letter.</p>
    
    <p>We encourage you to continue your commitment to academic excellence and look forward to your continued growth and success in the new grade level.</p>
    
    <p style="background-color: #f8f9fa; padding: 15px; border-left: 5px solid #27ae60; margin: 15px 0;">
        <strong>Your School Management System Login Credentials:</strong><br>
        Username: {student_id}<br>
        PIN: {pin}
    </p>
    
    <p>These credentials will give you access to your academic records, assignments, grades, and other important school resources. Please keep them confidential and secure.</p>
    
    <p>Should you have any questions or require any clarification, please do not hesitate to contact the school office.</p>
</div>

<div style="margin-top: 40px;">
    <p>Congratulations and best wishes for the new academic year!</p>
    <p style="margin-top: 30px;">
        <strong>Mr. Samuel Adeyemi</strong><br>
        Academic Coordinator<br>
        Deigratia Montessory School
    </p>
</div>
''',
                'footer_text': '''
<div style="text-align: center; margin-top: 30px; font-size: 12px; color: #7f8c8d;">
    <p>Deigratia Montessory School | 123 Education Avenue, Lagos, Nigeria | Tel: +234-123-456-7890 | Email: info@deigratia.edu.ng</p>
</div>
''',
                'signatory_name': 'Mr. Samuel Adeyemi',
                'signatory_position': 'Academic Coordinator',
                'is_active': True
            },
            
            # Template 3: Scholarship Award Letter
            {
                'name': 'Scholarship Award Letter',
                'header_text': 'SCHOLARSHIP AWARD NOTIFICATION',
                'body_template': '''
<div style="text-align: center;">
    <h1 style="color: #2c3e50; font-family: 'Times New Roman', serif; margin-bottom: 5px;">DEIGRATIA MONTESSORY SCHOOL</h1>
    <p style="color: #7f8c8d; font-size: 16px; margin-top: 0;">Excellence in Education</p>
    <hr style="width: 80%; border: 1px solid #e74c3c; margin: 10px auto 20px;">
</div>

<div style="text-align: right; margin-bottom: 20px;">
    <p>Reference: SCH-{reference_number}<br>
    Date: {current_date}</p>
</div>

<div style="margin-bottom: 20px;">
    <p><strong>Dear {student_name},</strong></p>
</div>

<div style="text-align: center; margin-bottom: 20px;">
    <h2 style="color: #e74c3c; font-family: 'Times New Roman', serif;">SCHOLARSHIP AWARD NOTIFICATION</h2>
</div>

<div style="margin-bottom: 30px; text-align: justify; line-height: 1.5;">
    <p>It is with great pleasure that we inform you that you have been selected as a recipient of the <strong>Deigratia Academic Excellence Scholarship</strong> for the {academic_year} academic year.</p>
    
    <p>This scholarship is awarded to students who have demonstrated exceptional academic achievement, leadership qualities, and outstanding character. Your performance in the scholarship examination and your previous academic records have distinguished you among your peers.</p>
    
    <p>Details of your scholarship award:</p>
    
    <table style="width: 80%; margin: 20px auto; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7; width: 40%;"><strong>Student Name:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{student_name}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Student ID:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{student_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Grade/Class:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{grade}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Scholarship Type:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">Academic Excellence Scholarship</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Scholarship Coverage:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{scholarship_coverage}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>Duration:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">One Academic Year (Renewable)</td>
        </tr>
        <tr>
            <td style="padding: 8px; border: 1px solid #bdc3c7;"><strong>School Start Date:</strong></td>
            <td style="padding: 8px; border: 1px solid #bdc3c7;">{start_date}</td>
        </tr>
    </table>
    
    <p>Please note that this scholarship is renewable for the next academic year subject to maintaining a minimum academic performance of 85% in all subjects and exemplary behavior throughout the academic year.</p>
    
    <p>To formally accept this scholarship, please visit the school's Scholarship Office with your parents/guardians no later than {acceptance_deadline} to complete the necessary documentation.</p>
    
    <p style="background-color: #f8f9fa; padding: 15px; border-left: 5px solid #e74c3c; margin: 15px 0;">
        <strong>Your School Management System Login Credentials:</strong><br>
        Username: {student_id}<br>
        PIN: {pin}
    </p>
    
    <p>These credentials will give you access to your academic records, assignments, grades, and other important school resources. Please keep them confidential and secure.</p>
    
    <p>We congratulate you on this achievement and look forward to seeing you continue to excel in your academic pursuits at Deigratia Montessory School.</p>
</div>

<div style="margin-top: 40px;">
    <p>Congratulations once again!</p>
    <p style="margin-top: 30px;">
        <strong>Dr. Olufemi Johnson</strong><br>
        Scholarship Committee Chair<br>
        Deigratia Montessory School
    </p>
</div>
''',
                'footer_text': '''
<div style="text-align: center; margin-top: 30px; font-size: 12px; color: #7f8c8d;">
    <p>Deigratia Montessory School | 123 Education Avenue, Lagos, Nigeria | Tel: +234-123-456-7890 | Email: scholarships@deigratia.edu.ng</p>
</div>
''',
                'signatory_name': 'Dr. Olufemi Johnson',
                'signatory_position': 'Scholarship Committee Chair',
                'is_active': True
            }
        ]

        # Create each template
        created_count = 0
        for template_data in templates:
            name = template_data['name']
            
            # Create the template
            AdmissionLetterTemplate.objects.create(**template_data)
            created_count += 1
            self.stdout.write(self.style.SUCCESS(
                f'Created admission letter template: {name}'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {created_count} default admission letter templates'
        ))