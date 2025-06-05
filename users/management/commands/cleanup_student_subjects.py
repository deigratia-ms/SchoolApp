from django.core.management.base import BaseCommand
from users.models import Student
from courses.models import ClassSubject

class Command(BaseCommand):
    help = 'Cleans up student enrollments in subjects - removes students from subjects not in their current grade'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup of student subject enrollments...')
        count_removed = 0
        count_added = 0

        students = Student.objects.all()
        total_students = students.count()
        self.stdout.write(f"Processing {total_students} students...")

        for student in students:
            if student.grade:
                self.stdout.write(f"Processing student: {student.user.get_full_name()} (Grade: {student.grade.name})")
                
                # First, check and remove incorrect subject enrollments
                class_subjects_all = ClassSubject.objects.filter(students=student)
                for class_subject in class_subjects_all:
                    if class_subject.classroom.id != student.grade.id:
                        class_subject.students.remove(student)
                        count_removed += 1
                        self.stdout.write(f"  - Removed from ClassSubject: {class_subject.subject.name} ({class_subject.classroom.name})")
                
                # Then ensure student is enrolled in all subjects for their current grade
                class_subjects = ClassSubject.objects.filter(classroom=student.grade)
                for class_subject in class_subjects:
                    if student not in class_subject.students.all():
                        class_subject.students.add(student)
                        count_added += 1
                        self.stdout.write(f"  - Added to ClassSubject: {class_subject.subject.name}")
            else:
                self.stdout.write(f"Skipping student (no grade assigned): {student.user.get_full_name()}")

        self.stdout.write(self.style.SUCCESS(f'Successfully cleaned up student subject enrollments. Removed: {count_removed}, Added: {count_added}'))