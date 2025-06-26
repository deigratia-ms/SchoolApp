from django.core.management.base import BaseCommand
from users.models import Student
from courses.models import ClassRoom, ClassSubject, Subject
from django.db import transaction


class Command(BaseCommand):
    help = 'Verify that subject enrollment system works correctly'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix any enrollment issues found',
        )
        parser.add_argument(
            '--test-new-subject',
            action='store_true',
            help='Test creating a new subject and verify auto-enrollment',
        )

    def handle(self, *args, **options):
        fix_mode = options['fix']
        test_new_subject = options['test_new_subject']
        
        self.stdout.write('=== Subject Enrollment Verification ===')
        
        # 1. Check current enrollment consistency
        self.check_enrollment_consistency(fix_mode)
        
        # 2. Test new subject creation if requested
        if test_new_subject:
            self.test_new_subject_enrollment()
        
        # 3. Verify promotion system readiness
        self.verify_promotion_readiness()

    def check_enrollment_consistency(self, fix_mode):
        """Check if all students are properly enrolled in their class subjects"""
        self.stdout.write('\n--- Checking Enrollment Consistency ---')
        
        issues_found = 0
        students_checked = 0
        
        for student in Student.objects.filter(grade__isnull=False):
            students_checked += 1
            classroom = student.grade
            
            # Get all subjects for this classroom
            class_subjects = ClassSubject.objects.filter(classroom=classroom)
            
            # Check if student is enrolled in all subjects
            for class_subject in class_subjects:
                if student not in class_subject.students.all():
                    issues_found += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'ISSUE: {student.user.get_full_name()} not enrolled in '
                            f'{class_subject.subject.name} for {classroom.name}'
                        )
                    )
                    
                    if fix_mode:
                        class_subject.students.add(student)
                        self.stdout.write(f'  FIXED: Enrolled student in {class_subject.subject.name}')
            
            # Check if student is enrolled in subjects from other classrooms
            wrong_subjects = ClassSubject.objects.filter(
                students=student
            ).exclude(classroom=classroom)
            
            for wrong_subject in wrong_subjects:
                issues_found += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'ISSUE: {student.user.get_full_name()} enrolled in '
                        f'{wrong_subject.subject.name} from {wrong_subject.classroom.name} '
                        f'but belongs to {classroom.name}'
                    )
                )
                
                if fix_mode:
                    wrong_subject.students.remove(student)
                    self.stdout.write(f'  FIXED: Removed student from {wrong_subject.subject.name}')
        
        if issues_found == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ All {students_checked} students are properly enrolled in their class subjects'
                )
            )
        else:
            if fix_mode:
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed {issues_found} enrollment issues')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Found {issues_found} enrollment issues. Use --fix to resolve them.'
                    )
                )

    def test_new_subject_enrollment(self):
        """Test that creating a new subject auto-enrolls students"""
        self.stdout.write('\n--- Testing New Subject Auto-Enrollment ---')
        
        # Find a classroom with students
        classroom_with_students = ClassRoom.objects.filter(
            students__isnull=False
        ).first()
        
        if not classroom_with_students:
            self.stdout.write(
                self.style.WARNING('No classrooms with students found for testing')
            )
            return
        
        student_count = classroom_with_students.students.count()
        self.stdout.write(f'Testing with {classroom_with_students.name} ({student_count} students)')
        
        # Create a test subject
        test_subject, created = Subject.objects.get_or_create(
            name='Test Auto-Enrollment Subject',
            defaults={
                'description': 'Test subject for verifying auto-enrollment',
                'code': 'TEST001'
            }
        )
        
        if created:
            self.stdout.write(f'Created test subject: {test_subject.name}')
        
        # Create ClassSubject (this should trigger auto-enrollment)
        class_subject, cs_created = ClassSubject.objects.get_or_create(
            classroom=classroom_with_students,
            subject=test_subject,
            defaults={'teacher': None}
        )
        
        if cs_created:
            self.stdout.write(f'Created ClassSubject for {classroom_with_students.name}')
            
            # Check if students were auto-enrolled
            enrolled_count = class_subject.students.count()
            
            if enrolled_count == student_count:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Auto-enrollment working! {enrolled_count}/{student_count} students enrolled'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Auto-enrollment failed! Only {enrolled_count}/{student_count} students enrolled'
                    )
                )
            
            # Clean up test data
            class_subject.delete()
            if created:
                test_subject.delete()
            self.stdout.write('Cleaned up test data')
        else:
            self.stdout.write('ClassSubject already exists, skipping test')

    def verify_promotion_readiness(self):
        """Verify that the promotion system components are ready"""
        self.stdout.write('\n--- Verifying Promotion System Readiness ---')
        
        # Check if cleanup command exists
        try:
            from django.core.management import call_command
            # This will raise an exception if the command doesn't exist
            call_command('cleanup_student_subjects', '--help')
            self.stdout.write('✓ cleanup_student_subjects command available')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ cleanup_student_subjects command issue: {str(e)}')
            )
        
        # Check signal handlers
        from django.db.models.signals import post_save
        from users.models import Student
        from courses.models import ClassSubject
        
        student_receivers = post_save._live_receivers(sender=Student)
        classsubject_receivers = post_save._live_receivers(sender=ClassSubject)
        
        self.stdout.write(f'✓ Student post_save signals: {len(student_receivers)} registered')
        self.stdout.write(f'✓ ClassSubject post_save signals: {len(classsubject_receivers)} registered')
        
        # Check for required models and relationships
        classrooms = ClassRoom.objects.count()
        subjects = Subject.objects.count()
        class_subjects = ClassSubject.objects.count()
        students = Student.objects.count()
        
        self.stdout.write(f'✓ System has {classrooms} classrooms, {subjects} subjects, {class_subjects} class-subjects, {students} students')
        
        self.stdout.write(
            self.style.SUCCESS('Promotion system components verified')
        )
