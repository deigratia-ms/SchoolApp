from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import Student
from courses.models import ClassRoom, ClassSubject

class Command(BaseCommand):
    help = 'Synchronizes student counts between classrooms and class subjects to fix inconsistencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix inconsistencies (otherwise runs in report-only mode)',
        )

    def handle(self, *args, **options):
        fix_mode = options['fix']
        
        if not fix_mode:
            self.stdout.write(self.style.WARNING(
                "Running in REPORT-ONLY mode. Use --fix to apply changes."
            ))
        
        # 1. Get all classrooms and check student counts
        classrooms = ClassRoom.objects.all()
        inconsistencies_found = False
        
        for classroom in classrooms:
            # Direct students in classroom.students collection
            direct_students = classroom.students.all()
            
            # Students referencing this classroom as their grade
            referenced_students = Student.objects.filter(grade=classroom)
            
            # Get subjects for this classroom
            subjects = ClassSubject.objects.filter(classroom=classroom)
            
            # Check for inconsistencies
            if direct_students.count() != referenced_students.count():
                inconsistencies_found = True
                self.stdout.write(
                    f"Inconsistency in {classroom.name}: "
                    f"{direct_students.count()} directly associated students vs. "
                    f"{referenced_students.count()} students with this grade assigned"
                )
                
                # Find students in one set but not the other
                extra_direct = [s for s in direct_students if s not in referenced_students]
                missing_direct = [s for s in referenced_students if s not in direct_students]
                
                if extra_direct:
                    self.stdout.write(f"  - {len(extra_direct)} students in classroom.students but not assigned this grade")
                if missing_direct:
                    self.stdout.write(f"  - {len(missing_direct)} students with this grade but not in classroom.students")
                
                # Fix if in fix mode
                if fix_mode:
                    with transaction.atomic():
                        # Add missing students to classroom.students
                        for student in missing_direct:
                            classroom.students.add(student)
                            self.stdout.write(f"  - Added {student.user.get_full_name()} to {classroom.name} students collection")
                        
                        # Remove extra students (if they have a different grade assigned)
                        for student in extra_direct:
                            if student.grade != classroom:
                                classroom.students.remove(student)
                                self.stdout.write(f"  - Removed {student.user.get_full_name()} from {classroom.name} students collection")
            
            # Check subject enrollments
            for subject in subjects:
                subject_students = subject.students.all()
                
                # Students should match classroom.students
                if subject_students.count() != direct_students.count():
                    inconsistencies_found = True
                    self.stdout.write(
                        f"Inconsistency in subject {subject.subject.name} for {classroom.name}: "
                        f"{subject_students.count()} enrolled students vs. "
                        f"{direct_students.count()} students in classroom"
                    )
                    
                    # Find students in classroom but not in subject
                    missing_in_subject = [s for s in direct_students if s not in subject_students]
                    
                    # Find students in subject but not in classroom
                    extra_in_subject = [s for s in subject_students if s not in direct_students]
                    
                    if missing_in_subject:
                        self.stdout.write(f"  - {len(missing_in_subject)} students in classroom but not enrolled in subject")
                    if extra_in_subject:
                        self.stdout.write(f"  - {len(extra_in_subject)} students enrolled in subject but not in classroom")
                    
                    # Fix if in fix mode
                    if fix_mode:
                        with transaction.atomic():
                            # Add missing students to subject
                            for student in missing_in_subject:
                                subject.students.add(student)
                                self.stdout.write(f"  - Enrolled {student.user.get_full_name()} in {subject.subject.name}")
                            
                            # Remove students not in classroom
                            for student in extra_in_subject:
                                subject.students.remove(student)
                                self.stdout.write(f"  - Removed {student.user.get_full_name()} from {subject.subject.name}")
        
        # Report summary
        if not inconsistencies_found:
            self.stdout.write(self.style.SUCCESS("No inconsistencies found. Student counts are in sync."))
        elif not fix_mode:
            self.stdout.write(self.style.WARNING(
                "Inconsistencies found. Run with --fix option to resolve them."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("All inconsistencies have been fixed."))