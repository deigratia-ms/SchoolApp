from django.core.management.base import BaseCommand
from website.models import FAQ

class Command(BaseCommand):
    help = 'Initialize default FAQs for the contact page'

    def handle(self, *args, **options):
        # Default FAQs for the contact page
        contact_faqs = [
            {
                'question': 'What are your school hours?',
                'answer': 'Our school operates Monday through Friday, 8:00 AM to 4:00 PM. Extended care options are available from 7:00 AM to 6:00 PM for an additional fee.'
            },
            {
                'question': 'How can I schedule a tour of the school?',
                'answer': 'You can schedule a tour by filling out the contact form on our website, calling our admissions office, or sending an email to our admissions department. Tours are typically conducted on weekdays between 9:00 AM and 2:00 PM.'
            },
            {
                'question': 'Do you offer transportation services?',
                'answer': 'Yes, we offer transportation services for students within a 10-mile radius of the school. Please contact our administrative office for details about routes, pickup times, and fees.'
            },
            {
                'question': 'How can I apply for admission?',
                'answer': 'The admission process begins with submitting an application form, which can be found on our Admissions page. After reviewing your application, we will schedule an assessment and interview. For more detailed information, please visit our Admissions page or contact our admissions office.'
            },
            {
                'question': 'What is the best way to contact a teacher?',
                'answer': 'The best way to contact a teacher is through our school communication platform or via email. Teachers typically respond within 24-48 hours during school days. For urgent matters, please contact the school office.'
            }
        ]

        # Create FAQs if they don't exist
        for i, faq in enumerate(contact_faqs, 1):
            FAQ.objects.get_or_create(
                page='contact',
                question=faq['question'],
                defaults={
                    'answer': faq['answer'],
                    'order': i,
                    'is_active': True
                }
            )
            
        self.stdout.write(self.style.SUCCESS('Successfully initialized contact FAQs'))
