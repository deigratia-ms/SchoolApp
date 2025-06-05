from django.core.management.base import BaseCommand
from users.models import Student
from courses.models import ClassRoom, ClassSubject

class Command(BaseCommand):
    help = 'Backfills the ClassSubject.students ManyToManyField for existing students.'

    def handle(self, *args, **options):
        self.stdout.write('Starting backfilling of ClassSubject.students...')

        students = Student.objects.all()
        for student in students:
            if student.grade:
                classroom = student.grade
                self.stdout.write(f"Processing student: {student.user.get_full_name()} (Grade: {classroom.name})")

                class_subjects = ClassSubject.objects.filter(classroom=classroom)
                for class_subject in class_subjects:
                    if student not in class_subject.students.all():
                        class_subject.students.add(student)
                        self.stdout.write(f"  - Added to ClassSubject: {class_subject.subject.name}")
                    else:
                        self.stdout.write(f"  - Already in ClassSubject: {class_subject.subject.name}")
            else:
                self.stdout.write(f"Skipping student (no grade assigned): {student.user.get_full_name()}")

        self.stdout.write(self.style.SUCCESS('Successfully backfilled ClassSubject.students.'))