"""
Script to populate the database with sample data for testing all functionalities.
This script creates sample data for:
- School settings
- Users (Admin, Teachers, Students, Parents, Staff)
- Classes and Subjects (following GES curriculum)
- Assignments and Quizzes
- Academic Records
- Attendance Records
- Communications (Messages, Notifications, Events)
- Fees and Payments

Run this script directly:
python populate_db.py
"""

import os
import sys
import django
import random
import datetime
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.hashers import make_password

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ricas_school_manager.settings')
django.setup()

# Import models
from users.models import (
    CustomUser, Teacher, SchoolSettings
)
from courses.models import (
    Subject, ClassRoom
)

# Import these conditionally when needed in the full data population
# We'll import them inside the function when the --full flag is used

# Helper functions
def create_user(email, password, first_name, last_name, role):
    """Create a user with the given details if they don't already exist"""
    # Check if user already exists (if email is provided)
    if email:
        try:
            user = CustomUser.objects.get(email=email)
            print(f"User with email {email} already exists, skipping creation.")
            return user
        except CustomUser.DoesNotExist:
            pass

    # For students without email, check by first and last name
    if not email and role == CustomUser.Role.STUDENT:
        existing_users = CustomUser.objects.filter(
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        if existing_users.exists():
            user = existing_users.first()
            print(f"User {first_name} {last_name} already exists, skipping creation.")
            return user

    # Create new user with a generated email if none provided
    if not email:
        # Generate a unique username-based email for students
        username = f"{first_name.lower()}.{last_name.lower()}"
        count = CustomUser.objects.filter(email__startswith=f"{username}@").count()
        if count > 0:
            username = f"{username}{count+1}"
        email = f"{username}@deigratia.edu.gh"
        print(f"Generated email {email} for {first_name} {last_name}")

    try:
        # Create new user
        user = CustomUser.objects.create(
            email=email,
            password=make_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
            is_verified=True
        )
        print(f"Created new user: {email}")
    except Exception as e:
        print(f"Error creating user {first_name} {last_name}: {str(e)}")
        # Try to get the user if it was created by a signal
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise Exception(f"Could not create or find user for {first_name} {last_name}")

    return user

def random_date(start_date, end_date):
    """Generate a random date between start_date and end_date"""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    return start_date + datetime.timedelta(days=random_days)

# Main function to populate the database
@transaction.atomic
def populate_database():
    print("Starting database population...")

    # Create school settings
    print("Creating school settings...")
    SchoolSettings.objects.get_or_create(
        school_name="Deigratia Montessori School",
        defaults={
            'address': '123 Education Street, Accra, Ghana',
            'contact_phone': '+233 20 123 4567',
            'contact_email': 'info@deigratia.edu.gh',
            'website': 'www.deigratia.edu.gh',
            'school_motto': 'Nurturing Excellence Through Montessori Education',
            'academic_year': '2023-2024',
            'current_term': 'First Term',
            'enable_messaging': True,
            'enable_student_to_student_chat': True,
            'primary_color': '#004d4d',
            'dark_mode': False
        }
    )

    # Create admin user
    print("Creating admin user...")
    create_user(
        email='admin@deigratia.edu.gh',
        password='admin123',
        first_name='Admin',
        last_name='User',
        role=CustomUser.Role.ADMIN
    )

    # Create GES curriculum subjects
    print("Creating subjects based on GES curriculum...")
    subjects_data = [
        # Core subjects
        {'name': 'English Language', 'code': 'ENG'},
        {'name': 'Mathematics', 'code': 'MATH'},
        {'name': 'Integrated Science', 'code': 'SCI'},
        {'name': 'Social Studies', 'code': 'SOC'},
        # Primary school subjects
        {'name': 'Ghanaian Language', 'code': 'GHL'},
        {'name': 'Religious and Moral Education', 'code': 'RME'},
        {'name': 'Creative Arts', 'code': 'CART'},
        {'name': 'Physical Education', 'code': 'PE'},
        {'name': 'Information and Communication Technology', 'code': 'ICT'},
        # JHS additional subjects
        {'name': 'French', 'code': 'FRE'},
        {'name': 'Pre-Technical Skills', 'code': 'PTS'},
        {'name': 'Pre-Vocational Skills', 'code': 'PVS'},
        # SHS subjects - General Arts
        {'name': 'Literature in English', 'code': 'LIT'},
        {'name': 'Economics', 'code': 'ECO'},
        {'name': 'Geography', 'code': 'GEO'},
        {'name': 'Government', 'code': 'GOV'},
        {'name': 'History', 'code': 'HIS'},
        {'name': 'Christian Religious Studies', 'code': 'CRS'},
        {'name': 'Islamic Studies', 'code': 'ISS'},
        # SHS subjects - Science
        {'name': 'Physics', 'code': 'PHY'},
        {'name': 'Chemistry', 'code': 'CHEM'},
        {'name': 'Biology', 'code': 'BIO'},
        {'name': 'Elective Mathematics', 'code': 'EMATH'},
        # SHS subjects - Business
        {'name': 'Financial Accounting', 'code': 'ACC'},
        {'name': 'Business Management', 'code': 'BUS'},
        {'name': 'Cost Accounting', 'code': 'CACC'},
    ]

    subjects = []
    for subject_data in subjects_data:
        try:
            # Try to get existing subject
            subject = Subject.objects.get(code=subject_data['code'])
            print(f"Subject {subject_data['name']} ({subject_data['code']}) already exists, skipping creation.")
        except Subject.DoesNotExist:
            # Create new subject
            subject = Subject.objects.create(
                code=subject_data['code'],
                name=subject_data['name'],
                description=f"GES curriculum subject: {subject_data['name']}"
            )
            print(f"Created subject: {subject_data['name']} ({subject_data['code']})")

        subjects.append(subject)

    # Create classrooms
    print("Creating classrooms...")
    classrooms_data = [
        # Kindergarten
        {'name': 'KG 1', 'section': 'A', 'grade_level': 0},
        {'name': 'KG 2', 'section': 'A', 'grade_level': 0},
        # Primary School
        {'name': 'Primary 1', 'section': 'A', 'grade_level': 1},
        {'name': 'Primary 2', 'section': 'A', 'grade_level': 2},
        {'name': 'Primary 3', 'section': 'A', 'grade_level': 3},
        {'name': 'Primary 4', 'section': 'A', 'grade_level': 4},
        {'name': 'Primary 5', 'section': 'A', 'grade_level': 5},
        {'name': 'Primary 6', 'section': 'A', 'grade_level': 6},
        # Junior High School
        {'name': 'JHS 1', 'section': 'A', 'grade_level': 7},
        {'name': 'JHS 2', 'section': 'A', 'grade_level': 8},
        {'name': 'JHS 3', 'section': 'A', 'grade_level': 9},
    ]

    classrooms = []
    for classroom_data in classrooms_data:
        try:
            # Try to get existing classroom
            classroom = ClassRoom.objects.get(
                name=classroom_data['name'],
                section=classroom_data['section']
            )
            print(f"Classroom {classroom_data['name']} {classroom_data['section']} already exists, skipping creation.")
        except ClassRoom.DoesNotExist:
            # Create new classroom
            classroom = ClassRoom.objects.create(
                name=classroom_data['name'],
                section=classroom_data['section'],
                grade_level=classroom_data['grade_level'],
                capacity=30
            )
            print(f"Created classroom: {classroom_data['name']} {classroom_data['section']}")

        classrooms.append(classroom)

    # Create teachers
    print("Creating teachers...")
    teachers_data = [
        {'email': 'john.smith@deigratia.edu.gh', 'first_name': 'John', 'last_name': 'Smith', 'subject': 'Mathematics'},
        {'email': 'mary.johnson@deigratia.edu.gh', 'first_name': 'Mary', 'last_name': 'Johnson', 'subject': 'English Language'},
        {'email': 'david.brown@deigratia.edu.gh', 'first_name': 'David', 'last_name': 'Brown', 'subject': 'Science'},
        {'email': 'sarah.wilson@deigratia.edu.gh', 'first_name': 'Sarah', 'last_name': 'Wilson', 'subject': 'Social Studies'},
        {'email': 'michael.lee@deigratia.edu.gh', 'first_name': 'Michael', 'last_name': 'Lee', 'subject': 'ICT'},
        {'email': 'jennifer.davis@deigratia.edu.gh', 'first_name': 'Jennifer', 'last_name': 'Davis', 'subject': 'French'},
        {'email': 'robert.taylor@deigratia.edu.gh', 'first_name': 'Robert', 'last_name': 'Taylor', 'subject': 'Physical Education'},
        {'email': 'linda.martin@deigratia.edu.gh', 'first_name': 'Linda', 'last_name': 'Martin', 'subject': 'Creative Arts'},
        {'email': 'james.anderson@deigratia.edu.gh', 'first_name': 'James', 'last_name': 'Anderson', 'subject': 'Religious and Moral Education'},
        {'email': 'patricia.thomas@deigratia.edu.gh', 'first_name': 'Patricia', 'last_name': 'Thomas', 'subject': 'Ghanaian Language'},
    ]

    teachers = []
    for i, teacher_data in enumerate(teachers_data):
        user = create_user(
            email=teacher_data['email'],
            password='teacher123',
            first_name=teacher_data['first_name'],
            last_name=teacher_data['last_name'],
            role=CustomUser.Role.TEACHER
        )

        # Find the subject this teacher teaches
        subject = next((s for s in subjects if s.name == teacher_data['subject']), None)

        # Check if teacher already exists for this user
        try:
            teacher = Teacher.objects.get(user=user)
            print(f"Teacher profile for {user.email} already exists, skipping creation.")
        except Teacher.DoesNotExist:
            # Create teacher profile
            try:
                teacher = Teacher.objects.create(
                    user=user,
                    employee_id=f'TCH{1001+i}',
                    department=subject.name if subject else 'General Education',
                    qualification='Bachelor of Education'
                )
                print(f"Created teacher profile for {user.email}")
            except Exception as e:
                print(f"Error creating teacher profile for {user.email}: {str(e)}")
                # Try to get the teacher if it was created by a signal
                try:
                    teacher = Teacher.objects.get(user=user)
                except Teacher.DoesNotExist:
                    print(f"Could not find or create teacher profile for {user.email}")
                    continue
        teachers.append(teacher)

        # Assign class teachers to classrooms
        if i < len(classrooms):
            classrooms[i].class_teacher = teacher
            classrooms[i].save()

    print("Database population completed for teachers and classrooms!")
    print("To continue with students, parents, and academic data, run this script again with the --full flag")

    # Check if we should continue with the full data population
    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        print("Continuing with full data population...")

        # Import the models needed for full data population
        from users.models import Student, Parent
        from courses.models import ClassSubject, Schedule
        from assignments.models import Assignment, Question, Choice, StudentSubmission, StudentAnswer, Grade
        from communications.models import Message, Notification, Event
        from attendance.models import AttendanceRecord, StudentAttendance
        from fees.models import Term, StudentFee, Payment, Receipt

        # Create students
        print("Creating students...")
        students_data = [
            # Primary 1 students
            {'first_name': 'Kwame', 'last_name': 'Adu', 'classroom': 'Primary 1'},
            {'first_name': 'Ama', 'last_name': 'Mensah', 'classroom': 'Primary 1'},
            {'first_name': 'Kofi', 'last_name': 'Owusu', 'classroom': 'Primary 1'},
            {'first_name': 'Akua', 'last_name': 'Asante', 'classroom': 'Primary 1'},
            {'first_name': 'Yaw', 'last_name': 'Boateng', 'classroom': 'Primary 1'},
            # Primary 2 students
            {'first_name': 'Abena', 'last_name': 'Osei', 'classroom': 'Primary 2'},
            {'first_name': 'Kwesi', 'last_name': 'Appiah', 'classroom': 'Primary 2'},
            {'first_name': 'Adwoa', 'last_name': 'Kumi', 'classroom': 'Primary 2'},
            {'first_name': 'Kwabena', 'last_name': 'Agyei', 'classroom': 'Primary 2'},
            {'first_name': 'Akosua', 'last_name': 'Frimpong', 'classroom': 'Primary 2'},
            # JHS 1 students
            {'first_name': 'Nana', 'last_name': 'Yeboah', 'classroom': 'JHS 1'},
            {'first_name': 'Kukua', 'last_name': 'Gyasi', 'classroom': 'JHS 1'},
            {'first_name': 'Kweku', 'last_name': 'Amponsah', 'classroom': 'JHS 1'},
            {'first_name': 'Adwoa', 'last_name': 'Poku', 'classroom': 'JHS 1'},
            {'first_name': 'Yoofi', 'last_name': 'Mensah', 'classroom': 'JHS 1'},
            # JHS 2 students
            {'first_name': 'Akwasi', 'last_name': 'Afriyie', 'classroom': 'JHS 2'},
            {'first_name': 'Aba', 'last_name': 'Nyarko', 'classroom': 'JHS 2'},
            {'first_name': 'Kwabena', 'last_name': 'Takyi', 'classroom': 'JHS 2'},
            {'first_name': 'Adwoa', 'last_name': 'Darko', 'classroom': 'JHS 2'},
            {'first_name': 'Yaw', 'last_name': 'Agyapong', 'classroom': 'JHS 2'},
        ]

        students = []
        for i, student_data in enumerate(students_data):
            # Create a unique email for students in JHS, otherwise None
            if 'JHS' in student_data['classroom']:
                email = f"{student_data['first_name'].lower()}.{student_data['last_name'].lower()}@student.deigratia.edu.gh"
            else:
                email = None

            user = create_user(
                email=email,
                password='student123',
                first_name=student_data['first_name'],
                last_name=student_data['last_name'],
                role=CustomUser.Role.STUDENT
            )

            # Find the classroom for this student
            classroom = next((c for c in classrooms if c.name == student_data['classroom']), None)

            # Generate student ID
            student_id = f"STU{1001+i}"

            # Check if student already exists by student_id
            existing_student = Student.objects.filter(student_id=student_id).first()
            if existing_student:
                print(f"Student with ID {student_id} already exists, skipping creation.")
                student = existing_student
                students.append(student)
                continue

            # Check if student already exists for this user
            try:
                student = Student.objects.get(user=user)
                print(f"Student profile for {user.email} already exists, skipping creation.")
            except Student.DoesNotExist:
                try:
                    # Create student profile with a unique PIN
                    pin = f"{1000+i}"  # Generate a unique PIN
                    student = Student.objects.create(
                        user=user,
                        student_id=student_id,
                        pin=pin,  # Unique PIN for each student
                        date_of_birth=random_date(
                            datetime.date(2005, 1, 1),
                            datetime.date(2015, 12, 31)
                        ),
                        grade=classroom
                    )
                    print(f"Created student profile: {student_id} with PIN {pin}")

                    # Add student to classroom
                    if classroom:
                        classroom.students.add(student)
                except Exception as e:
                    print(f"Error creating student profile for {student_id}: {str(e)}")
                    # Try to get the student if it was created by a signal
                    try:
                        student = Student.objects.get(user=user)
                    except Student.DoesNotExist:
                        print(f"Could not find or create student profile for {student_id}")
                        continue

            students.append(student)

        # Create parents
        print("Creating parents...")
        parents_data = [
            {'first_name': 'Daniel', 'last_name': 'Adu', 'children': ['Kwame Adu']},
            {'first_name': 'Grace', 'last_name': 'Mensah', 'children': ['Ama Mensah', 'Yoofi Mensah']},
            {'first_name': 'Samuel', 'last_name': 'Owusu', 'children': ['Kofi Owusu']},
            {'first_name': 'Elizabeth', 'last_name': 'Asante', 'children': ['Akua Asante']},
            {'first_name': 'Joseph', 'last_name': 'Boateng', 'children': ['Yaw Boateng']},
            {'first_name': 'Rebecca', 'last_name': 'Osei', 'children': ['Abena Osei']},
            {'first_name': 'Emmanuel', 'last_name': 'Appiah', 'children': ['Kwesi Appiah']},
            {'first_name': 'Victoria', 'last_name': 'Kumi', 'children': ['Adwoa Kumi', 'Adwoa Poku']},
            {'first_name': 'Richard', 'last_name': 'Agyei', 'children': ['Kwabena Agyei', 'Kwabena Takyi']},
            {'first_name': 'Mercy', 'last_name': 'Frimpong', 'children': ['Akosua Frimpong']},
        ]

        parents = []
        for i, parent_data in enumerate(parents_data):
            user = create_user(
                email=f"{parent_data['first_name'].lower()}.{parent_data['last_name'].lower()}@parent.deigratia.edu.gh",
                password='parent123',
                first_name=parent_data['first_name'],
                last_name=parent_data['last_name'],
                role=CustomUser.Role.PARENT
            )

            # Check if parent already exists for this user
            try:
                parent = Parent.objects.get(user=user)
                print(f"Parent profile for {user.email} already exists, skipping creation.")
            except Parent.DoesNotExist:
                try:
                    parent = Parent.objects.create(
                        user=user,
                        occupation=random.choice(['Teacher', 'Doctor', 'Engineer', 'Lawyer', 'Business Owner', 'Civil Servant']),
                        relationship='Parent'
                    )
                    print(f"Created parent profile for {user.email}")
                except Exception as e:
                    print(f"Error creating parent profile for {user.email}: {str(e)}")
                    # Try to get the parent if it was created by a signal
                    try:
                        parent = Parent.objects.get(user=user)
                    except Parent.DoesNotExist:
                        print(f"Could not find or create parent profile for {user.email}")
                        continue

            # Find and add children
            for child_name in parent_data['children']:
                first_name, last_name = child_name.split(' ', 1)
                child_students = [s for s in students if s.user.first_name == first_name and s.user.last_name == last_name]
                if child_students:
                    parent.children.add(child_students[0])

            parents.append(parent)

        # Create class subjects
        print("Creating class subjects...")
        # Define which subjects are taught in which grades
        grade_subjects = {
            'KG 1': ['English Language', 'Mathematics', 'Creative Arts', 'Physical Education'],
            'KG 2': ['English Language', 'Mathematics', 'Creative Arts', 'Physical Education'],
            'Primary 1': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education'],
            'Primary 2': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education'],
            'JHS 1': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'French', 'Information and Communication Technology'],
            'JHS 2': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'French', 'Information and Communication Technology'],
        }

        class_subjects = []
        for classroom in classrooms:
            if classroom.name in grade_subjects:
                for subject_name in grade_subjects[classroom.name]:
                    subject = next((s for s in subjects if s.name == subject_name), None)
                    if subject:
                        # Find a teacher for this subject
                        subject_teachers = [t for t in teachers if t.department == subject_name]
                        teacher = subject_teachers[0] if subject_teachers else random.choice(teachers)

                        # Check if class subject already exists
                        try:
                            class_subject = ClassSubject.objects.get(
                                classroom=classroom,
                                subject=subject
                            )
                            print(f"Class subject {subject.name} for {classroom.name} already exists, skipping creation.")
                        except ClassSubject.DoesNotExist:
                            try:
                                class_subject = ClassSubject.objects.create(
                                    classroom=classroom,
                                    subject=subject,
                                    teacher=teacher
                                )
                                print(f"Created class subject: {subject.name} for {classroom.name}")
                            except Exception as e:
                                print(f"Error creating class subject {subject.name} for {classroom.name}: {str(e)}")
                                continue

                        # Add all students in the classroom to this subject
                        for student in classroom.students.all():
                            class_subject.students.add(student)

                        class_subjects.append(class_subject)

        # Create assignments and quizzes
        print("Creating assignments and quizzes...")
        for class_subject in class_subjects:
            # Create 1-2 assignments per subject
            num_assignments = random.randint(1, 2)
            for i in range(num_assignments):
                # Determine if it's a quiz or regular assignment
                is_quiz = random.choice([True, False])

                # Create assignment title
                title = f"{'Quiz' if is_quiz else 'Assignment'} {i+1} on {class_subject.subject.name}"

                # Check if assignment already exists
                existing_assignment = Assignment.objects.filter(
                    title=title,
                    class_subject=class_subject
                ).first()

                if existing_assignment:
                    print(f"Assignment '{title}' already exists, skipping creation.")
                    assignment = existing_assignment
                else:
                    try:
                        # Create the assignment
                        assignment = Assignment.objects.create(
                            title=title,
                            description=f"{'A quiz' if is_quiz else 'An assignment'} on {class_subject.subject.name} for {class_subject.classroom.name}",
                            class_subject=class_subject,
                            created_by=class_subject.teacher.user,
                            due_date=timezone.now() + datetime.timedelta(days=random.randint(7, 30)),
                            max_score=100,
                            assignment_type='QUIZ' if is_quiz else 'HOMEWORK'
                        )
                        print(f"Created assignment: {title}")
                    except Exception as e:
                        print(f"Error creating assignment '{title}': {str(e)}")
                        continue

                # Skip creating questions if assignment already existed
                if existing_assignment:
                    continue

                # Create questions for the assignment
                num_questions = random.randint(3, 5)
                for j in range(num_questions):
                    question_text = f"Question {j+1} for {assignment.title}"

                    # Check if question already exists
                    existing_question = Question.objects.filter(
                        assignment=assignment,
                        question_text=question_text
                    ).first()

                    if existing_question:
                        print(f"Question '{question_text}' already exists, skipping creation.")
                        question = existing_question
                    else:
                        try:
                            question = Question.objects.create(
                                assignment=assignment,
                                question_text=question_text,
                                points=assignment.max_score / num_questions,
                                question_type='MCQ' if is_quiz else 'SHORT'
                            )
                            print(f"Created question: {question_text}")

                            # Create choices for multiple choice questions
                            if is_quiz:
                                for k in range(4):
                                    choice_text = f"Option {k+1} for Question {j+1}"
                                    try:
                                        Choice.objects.create(
                                            question=question,
                                            choice_text=choice_text,
                                            is_correct=(k == 0)  # First option is correct
                                        )
                                    except Exception as e:
                                        print(f"Error creating choice '{choice_text}': {str(e)}")
                        except Exception as e:
                            print(f"Error creating question '{question_text}': {str(e)}")
                            continue

        # Create attendance records
        print("Creating attendance records...")
        # Generate attendance for the past 10 days
        for i in range(10):
            date = timezone.now().date() - datetime.timedelta(days=i)

            # Skip weekends
            if date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                continue

            for classroom in classrooms:
                if classroom.students.exists():  # Only create records for classrooms with students
                    # Check if attendance record already exists
                    try:
                        attendance_record = AttendanceRecord.objects.get(
                            classroom=classroom,
                            date=date
                        )
                        print(f"Attendance record for {classroom.name} on {date} already exists, skipping creation.")
                    except AttendanceRecord.DoesNotExist:
                        try:
                            # Create attendance record for this class on this day
                            attendance_record = AttendanceRecord.objects.create(
                                classroom=classroom,
                                date=date,
                                taken_by=classroom.class_teacher
                            )
                            print(f"Created attendance record for {classroom.name} on {date}")
                        except Exception as e:
                            print(f"Error creating attendance record for {classroom.name} on {date}: {str(e)}")
                            continue

                    # Mark attendance for each student
                    for student in classroom.students.all():
                        # Check if student attendance already exists
                        existing_attendance = StudentAttendance.objects.filter(
                            attendance_record=attendance_record,
                            student=student
                        ).first()

                        if existing_attendance:
                            print(f"Attendance for student {student.student_id} on {date} already exists, skipping creation.")
                        else:
                            try:
                                # 90% chance of being present
                                is_present = random.random() < 0.9

                                StudentAttendance.objects.create(
                                    attendance_record=attendance_record,
                                    student=student,
                                    status='present' if is_present else random.choice(['absent', 'late']),
                                    notes='' if is_present else 'Excused absence' if random.random() < 0.5 else 'Unexcused absence'
                                )
                            except Exception as e:
                                print(f"Error creating attendance for student {student.student_id} on {date}: {str(e)}")

        print("Database population completed successfully!")

# Run the population script
if __name__ == "__main__":
    populate_database()
