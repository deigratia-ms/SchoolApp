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

Run this script after migrations have been applied:
python manage.py shell < scripts/populate_sample_data.py
"""

import os
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
    CustomUser, Teacher, Student, Parent, SchoolSettings
)
from courses.models import (
    Subject, ClassRoom, ClassSubject, Schedule
)
from assignments.models import (
    Assignment, Question, Choice, StudentSubmission, StudentAnswer,
    Grade
)
from communications.models import (
    Message, Notification, Event
)
from attendance.models import (
    AttendanceRecord, StudentAttendance
)
from fees.models import (
    Term, StudentFee, Payment, Receipt
)

# Helper functions
def create_user(email, password, first_name, last_name, role):
    """Create a user with the given details"""
    user = CustomUser.objects.create(
        email=email,
        password=make_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=True,
        is_verified=True
    )
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
    admin_user = create_user(
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
        subject, _ = Subject.objects.get_or_create(
            code=subject_data['code'],
            defaults={
                'name': subject_data['name'],
                'description': f"GES curriculum subject: {subject_data['name']}"
            }
        )
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
        classroom, _ = ClassRoom.objects.get_or_create(
            name=classroom_data['name'],
            section=classroom_data['section'],
            defaults={
                'grade_level': classroom_data['grade_level'],
                'capacity': 30
            }
        )
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

        teacher = Teacher.objects.create(
            user=user,
            employee_id=f'TCH{1001+i}',
            date_of_birth=random_date(
                datetime.date(1970, 1, 1),
                datetime.date(1995, 12, 31)
            ),
            qualification='Bachelor of Education',
            date_employed=random_date(
                datetime.date(2010, 1, 1),
                datetime.date(2022, 12, 31)
            ),
            specialty=subject.name if subject else 'General Education'
        )
        teachers.append(teacher)

        # Assign class teachers to classrooms
        if i < len(classrooms):
            classrooms[i].class_teacher = teacher
            classrooms[i].save()

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
        # Primary 3 students
        {'first_name': 'Kojo', 'last_name': 'Annan', 'classroom': 'Primary 3'},
        {'first_name': 'Yaa', 'last_name': 'Amoako', 'classroom': 'Primary 3'},
        {'first_name': 'Kwaku', 'last_name': 'Manu', 'classroom': 'Primary 3'},
        {'first_name': 'Afia', 'last_name': 'Danso', 'classroom': 'Primary 3'},
        {'first_name': 'Kwadwo', 'last_name': 'Sarpong', 'classroom': 'Primary 3'},
        # Primary 4 students
        {'first_name': 'Afua', 'last_name': 'Ansah', 'classroom': 'Primary 4'},
        {'first_name': 'Kwasi', 'last_name': 'Opoku', 'classroom': 'Primary 4'},
        {'first_name': 'Abla', 'last_name': 'Adjei', 'classroom': 'Primary 4'},
        {'first_name': 'Fiifi', 'last_name': 'Badu', 'classroom': 'Primary 4'},
        {'first_name': 'Efua', 'last_name': 'Agyemang', 'classroom': 'Primary 4'},
        # Primary 5 students
        {'first_name': 'Kobina', 'last_name': 'Asamoah', 'classroom': 'Primary 5'},
        {'first_name': 'Esi', 'last_name': 'Boakye', 'classroom': 'Primary 5'},
        {'first_name': 'Kwamena', 'last_name': 'Nkrumah', 'classroom': 'Primary 5'},
        {'first_name': 'Adzo', 'last_name': 'Ofori', 'classroom': 'Primary 5'},
        {'first_name': 'Kosi', 'last_name': 'Addo', 'classroom': 'Primary 5'},
        # Primary 6 students
        {'first_name': 'Serwaa', 'last_name': 'Amankwah', 'classroom': 'Primary 6'},
        {'first_name': 'Nii', 'last_name': 'Quaye', 'classroom': 'Primary 6'},
        {'first_name': 'Akweley', 'last_name': 'Tetteh', 'classroom': 'Primary 6'},
        {'first_name': 'Koby', 'last_name': 'Acheampong', 'classroom': 'Primary 6'},
        {'first_name': 'Maame', 'last_name': 'Kyei', 'classroom': 'Primary 6'},
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
        # JHS 3 students
        {'first_name': 'Akosua', 'last_name': 'Okyere', 'classroom': 'JHS 3'},
        {'first_name': 'Kwame', 'last_name': 'Asiedu', 'classroom': 'JHS 3'},
        {'first_name': 'Ama', 'last_name': 'Aidoo', 'classroom': 'JHS 3'},
        {'first_name': 'Kofi', 'last_name': 'Duah', 'classroom': 'JHS 3'},
        {'first_name': 'Akua', 'last_name': 'Fosu', 'classroom': 'JHS 3'},
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

        student = Student.objects.create(
            user=user,
            student_id=student_id,
            pin='12345',  # Simple PIN for testing
            date_of_birth=random_date(
                datetime.date(2005, 1, 1),
                datetime.date(2015, 12, 31)
            ),
            grade=classroom
        )

        # Add student to classroom
        if classroom:
            classroom.students.add(student)

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
        {'first_name': 'Mercy', 'last_name': 'Frimpong', 'children': ['Akosua Frimpong', 'Akosua Okyere']},
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

        parent = Parent.objects.create(
            user=user,
            occupation=random.choice(['Teacher', 'Doctor', 'Engineer', 'Lawyer', 'Business Owner', 'Civil Servant']),
            relationship='Parent'
        )

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
        'Primary 1': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Creative Arts', 'Physical Education'],
        'Primary 2': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Creative Arts', 'Physical Education'],
        'Primary 3': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Creative Arts', 'Physical Education'],
        'Primary 4': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Creative Arts', 'Physical Education', 'Information and Communication Technology'],
        'Primary 5': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Creative Arts', 'Physical Education', 'Information and Communication Technology'],
        'Primary 6': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Creative Arts', 'Physical Education', 'Information and Communication Technology'],
        'JHS 1': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Information and Communication Technology', 'French', 'Pre-Technical Skills', 'Pre-Vocational Skills', 'Physical Education'],
        'JHS 2': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Information and Communication Technology', 'French', 'Pre-Technical Skills', 'Pre-Vocational Skills', 'Physical Education'],
        'JHS 3': ['English Language', 'Mathematics', 'Integrated Science', 'Social Studies', 'Ghanaian Language', 'Religious and Moral Education', 'Information and Communication Technology', 'French', 'Pre-Technical Skills', 'Pre-Vocational Skills', 'Physical Education'],
    }

    class_subjects = []
    for classroom in classrooms:
        if classroom.name in grade_subjects:
            for subject_name in grade_subjects[classroom.name]:
                subject = next((s for s in subjects if s.name == subject_name), None)
                if subject:
                    # Find a teacher for this subject
                    subject_teachers = [t for t in teachers if t.specialty == subject_name]
                    teacher = subject_teachers[0] if subject_teachers else random.choice(teachers)

                    class_subject = ClassSubject.objects.create(
                        classroom=classroom,
                        subject=subject,
                        teacher=teacher
                    )

                    # Add all students in the classroom to this subject
                    for student in classroom.students.all():
                        class_subject.students.add(student)

                    class_subjects.append(class_subject)

    # Create schedules
    print("Creating class schedules...")
    days_of_week = [0, 1, 2, 3, 4]  # Monday to Friday
    time_slots = [
        (datetime.time(8, 0), datetime.time(8, 45)),   # 8:00 - 8:45
        (datetime.time(8, 50), datetime.time(9, 35)),  # 8:50 - 9:35
        (datetime.time(9, 40), datetime.time(10, 25)), # 9:40 - 10:25
        (datetime.time(10, 45), datetime.time(11, 30)), # 10:45 - 11:30 (after break)
        (datetime.time(11, 35), datetime.time(12, 20)), # 11:35 - 12:20
        (datetime.time(12, 25), datetime.time(13, 10)), # 12:25 - 13:10
        (datetime.time(13, 45), datetime.time(14, 30)), # 13:45 - 14:30 (after lunch)
    ]

    for class_subject in class_subjects:
        # Assign 2-3 periods per week for each subject
        num_periods = random.randint(2, 3)
        assigned_slots = []

        for _ in range(num_periods):
            # Try to find a free slot
            attempts = 0
            while attempts < 10:  # Limit attempts to avoid infinite loop
                day = random.choice(days_of_week)
                slot_index = random.randint(0, len(time_slots) - 1)
                slot = (day, slot_index)

                if slot not in assigned_slots:
                    assigned_slots.append(slot)
                    start_time, end_time = time_slots[slot_index]

                    Schedule.objects.create(
                        class_subject=class_subject,
                        day_of_week=day,
                        start_time=start_time,
                        end_time=end_time
                    )
                    break

                attempts += 1

    # Create assignments and quizzes
    print("Creating assignments and quizzes...")
    for class_subject in class_subjects:
        # Create 1-3 assignments per subject
        num_assignments = random.randint(1, 3)
        for i in range(num_assignments):
            # Determine if it's a quiz or regular assignment
            is_quiz = random.choice([True, False])

            # Create the assignment
            assignment = Assignment.objects.create(
                title=f"{'Quiz' if is_quiz else 'Assignment'} {i+1} on {class_subject.subject.name}",
                description=f"{'A quiz' if is_quiz else 'An assignment'} on {class_subject.subject.name} for {class_subject.classroom.name}",
                class_subject=class_subject,
                teacher=class_subject.teacher,
                due_date=timezone.now() + datetime.timedelta(days=random.randint(7, 30)),
                total_points=100,
                is_quiz=is_quiz,
                is_published=True
            )

            # Create questions for the assignment
            num_questions = random.randint(5, 10)
            for j in range(num_questions):
                question = Question.objects.create(
                    assignment=assignment,
                    text=f"Question {j+1} for {assignment.title}",
                    points=assignment.total_points / num_questions
                )

                # Create choices for multiple choice questions
                if is_quiz:
                    for k in range(4):
                        Choice.objects.create(
                            question=question,
                            text=f"Option {k+1} for Question {j+1}",
                            is_correct=(k == 0)  # First option is correct
                        )

            # Create student submissions for some students
            for student in class_subject.students.all():
                # 70% chance of submission
                if random.random() < 0.7:
                    submission = StudentSubmission.objects.create(
                        assignment=assignment,
                        student=student,
                        submission_date=timezone.now() - datetime.timedelta(days=random.randint(1, 5)),
                        status='submitted'
                    )

                    # Create answers for each question
                    for question in assignment.questions.all():
                        if is_quiz and question.choices.exists():
                            # For quizzes, select a choice
                            choice = random.choice(question.choices.all())
                            StudentAnswer.objects.create(
                                submission=submission,
                                question=question,
                                selected_choice=choice
                            )
                        else:
                            # For regular assignments, provide a text answer
                            StudentAnswer.objects.create(
                                submission=submission,
                                question=question,
                                text_answer=f"Answer from {student.user.first_name} for question {question.text}"
                            )

                    # Grade the submission (80% chance)
                    if random.random() < 0.8:
                        # Calculate a random score between 60 and 100
                        score = random.randint(60, 100)
                        Grade.objects.create(
                            student=student,
                            assignment=assignment,
                            score=score,
                            feedback=f"Good job! You scored {score}%.",
                            graded_by=class_subject.teacher,
                            graded_date=timezone.now() - datetime.timedelta(days=random.randint(0, 3))
                        )

    # Create attendance records
    print("Creating attendance records...")
    # Generate attendance for the past 30 days
    for i in range(30):
        date = timezone.now().date() - datetime.timedelta(days=i)

        # Skip weekends
        if date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            continue

        for classroom in classrooms:
            # Create attendance record for this class on this day
            attendance_record = AttendanceRecord.objects.create(
                classroom=classroom,
                date=date,
                taken_by=classroom.class_teacher
            )

            # Mark attendance for each student
            for student in classroom.students.all():
                # 90% chance of being present
                is_present = random.random() < 0.9

                StudentAttendance.objects.create(
                    attendance_record=attendance_record,
                    student=student,
                    status='present' if is_present else random.choice(['absent', 'late']),
                    notes='' if is_present else 'Excused absence' if random.random() < 0.5 else 'Unexcused absence'
                )

    # Create messages
    print("Creating messages...")
    message_subjects = [
        "Upcoming School Event", "Homework Reminder", "Parent-Teacher Meeting",
        "Field Trip Information", "Exam Schedule", "School Closure Notice",
        "Curriculum Update", "Sports Day Announcement", "School Performance"
    ]

    message_contents = [
        "Please be informed about the upcoming event. All students are expected to participate.",
        "This is a reminder to complete your homework assignments by the due date.",
        "We would like to invite you to attend the parent-teacher meeting scheduled for next week.",
        "We are planning a field trip to the science museum. Please return the permission slip.",
        "The examination schedule has been finalized. Please prepare accordingly.",
        "Due to unforeseen circumstances, the school will be closed tomorrow.",
        "We have updated the curriculum for the next term. Please review the changes.",
        "The annual sports day will be held next month. Students should prepare for their events.",
        "The school performance will take place in the auditorium. All parents are invited to attend."
    ]

    # Create 20 random messages
    for _ in range(20):
        sender = random.choice(teachers)
        recipient = random.choice(parents + teachers + [admin_user])
        subject_index = random.randint(0, len(message_subjects) - 1)

        Message.objects.create(
            sender=sender.user,
            recipient=recipient.user if hasattr(recipient, 'user') else recipient,
            subject=message_subjects[subject_index],
            content=message_contents[subject_index],
            date_sent=timezone.now() - datetime.timedelta(days=random.randint(0, 30)),
            is_read=random.choice([True, False])
        )

    # Create notifications
    print("Creating notifications...")
    notification_types = [
        "Assignment", "Quiz", "Grade", "Attendance", "Message", "Announcement", "Event"
    ]

    notification_titles = [
        "New Assignment Posted", "Quiz Reminder", "Grade Updated",
        "Attendance Marked", "New Message Received", "School Announcement", "Upcoming Event"
    ]

    notification_messages = [
        "A new assignment has been posted for your class.",
        "Don't forget about the upcoming quiz.",
        "Your grade has been updated. Check your academic record.",
        "Your attendance has been marked for today.",
        "You have received a new message. Check your inbox.",
        "There is a new announcement from the school administration.",
        "There is an upcoming event at the school. Mark your calendar."
    ]

    # Create 30 random notifications
    for _ in range(30):
        user = random.choice([s.user for s in students] + [p.user for p in parents] + [t.user for t in teachers])
        type_index = random.randint(0, len(notification_types) - 1)

        Notification.objects.create(
            user=user,
            title=notification_titles[type_index],
            message=notification_messages[type_index],
            type=notification_types[type_index],
            is_read=random.choice([True, False]),
            created_at=timezone.now() - datetime.timedelta(days=random.randint(0, 30))
        )

    # Create events
    print("Creating events...")
    event_titles = [
        "Parent-Teacher Conference", "School Assembly", "Science Fair",
        "Sports Day", "Cultural Day", "Career Day", "End of Term Ceremony",
        "School Trip", "Music Concert", "Art Exhibition"
    ]

    event_descriptions = [
        "A meeting between parents and teachers to discuss student progress.",
        "A general assembly for all students and staff.",
        "Students will showcase their science projects.",
        "A day of sports competitions between classes.",
        "A celebration of different cultures represented in our school.",
        "Professionals from various fields will speak about career opportunities.",
        "A ceremony to mark the end of the academic term.",
        "An educational trip to a place of interest.",
        "A concert featuring performances by our music students.",
        "An exhibition of artwork created by our students."
    ]

    # Create 10 events
    for i in range(10):
        start_date = timezone.now() + datetime.timedelta(days=random.randint(-15, 45))

        Event.objects.create(
            title=event_titles[i],
            description=event_descriptions[i],
            start_date=start_date,
            end_date=start_date + datetime.timedelta(hours=random.randint(1, 8)),
            location=random.choice(["School Hall", "Auditorium", "Sports Field", "Classroom Block", "Library"]),
            created_by=admin_user
        )

    # Create terms and fees
    print("Creating terms and fees...")
    terms_data = [
        {"name": "First Term", "start_date": datetime.date(2023, 9, 1), "end_date": datetime.date(2023, 12, 15)},
        {"name": "Second Term", "start_date": datetime.date(2024, 1, 10), "end_date": datetime.date(2024, 4, 5)},
        {"name": "Third Term", "start_date": datetime.date(2024, 4, 25), "end_date": datetime.date(2024, 7, 31)}
    ]

    terms = []
    for term_data in terms_data:
        term = Term.objects.create(
            name=term_data["name"],
            start_date=term_data["start_date"],
            end_date=term_data["end_date"],
            is_current=term_data["name"] == "First Term"
        )
        terms.append(term)

    # Create student fees
    fee_categories = {
        "KG 1": 1000, "KG 2": 1000,
        "Primary 1": 1200, "Primary 2": 1200, "Primary 3": 1200,
        "Primary 4": 1500, "Primary 5": 1500, "Primary 6": 1500,
        "JHS 1": 1800, "JHS 2": 1800, "JHS 3": 1800
    }

    for student in students:
        if student.grade and student.grade.name in fee_categories:
            fee_amount = fee_categories[student.grade.name]

            for term in terms:
                student_fee = StudentFee.objects.create(
                    student=student,
                    term=term,
                    amount=fee_amount,
                    description=f"Tuition fee for {term.name}, {student.grade.name}",
                    due_date=term.start_date + datetime.timedelta(days=30)
                )

                # 80% chance of payment for current term, 100% for past terms
                if (term.is_current and random.random() < 0.8) or not term.is_current:
                    payment_date = max(term.start_date, timezone.now().date() - datetime.timedelta(days=random.randint(0, 60)))

                    # Some students pay in full, others in installments
                    if random.random() < 0.7:
                        # Full payment
                        payment = Payment.objects.create(
                            student_fee=student_fee,
                            amount=fee_amount,
                            payment_date=payment_date,
                            payment_method=random.choice(["Cash", "Bank Transfer", "Mobile Money"]),
                            received_by=admin_user
                        )

                        Receipt.objects.create(
                            payment=payment,
                            receipt_number=f"REC-{1000+payment.id}",
                            issued_date=payment_date
                        )
                    else:
                        # Installment payments
                        first_amount = fee_amount * 0.6
                        second_amount = fee_amount * 0.4

                        # First installment
                        payment1 = Payment.objects.create(
                            student_fee=student_fee,
                            amount=first_amount,
                            payment_date=payment_date,
                            payment_method=random.choice(["Cash", "Bank Transfer", "Mobile Money"]),
                            received_by=admin_user
                        )

                        Receipt.objects.create(
                            payment=payment1,
                            receipt_number=f"REC-{1000+payment1.id}",
                            issued_date=payment_date
                        )

                        # Second installment (if not current term or 70% chance)
                        if not term.is_current or random.random() < 0.7:
                            payment2 = Payment.objects.create(
                                student_fee=student_fee,
                                amount=second_amount,
                                payment_date=payment_date + datetime.timedelta(days=random.randint(15, 45)),
                                payment_method=random.choice(["Cash", "Bank Transfer", "Mobile Money"]),
                                received_by=admin_user
                            )

                            Receipt.objects.create(
                                payment=payment2,
                                receipt_number=f"REC-{1000+payment2.id}",
                                issued_date=payment_date + datetime.timedelta(days=random.randint(15, 45))
                            )

    print("Database population completed successfully!")

# Run the population script
if __name__ == "__main__":
    populate_database()
