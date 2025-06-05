from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q, F, Case, When, Value, IntegerField, Max, Min
from django.db.models.functions import TruncMonth, TruncWeek, ExtractWeekDay, ExtractYear
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime, timedelta, date
import json
import calendar

from users.models import CustomUser, Teacher, Student, Parent, StaffMember, SchoolSettings
from courses.models import ClassSubject, ClassRoom, CourseMaterial, YouTubeVideo, Subject, Schedule
from assignments.models import Assignment, StudentSubmission, Grade, ReportCard
from attendance.models import AttendanceRecord, StudentAttendance, AttendanceReport
from communications.models import Message, Announcement, Notification, Event
from fees.models import Term, StudentFee, Payment, Receipt
from .models import DashboardPreference, Widget, UserWidget

# Helper functions for role-based access
def is_admin(user):
    return user.is_authenticated and user.role == CustomUser.Role.ADMIN

def is_teacher(user):
    return user.is_authenticated and user.role == CustomUser.Role.TEACHER

def is_student(user):
    return user.is_authenticated and user.role == CustomUser.Role.STUDENT

def is_parent(user):
    return user.is_authenticated and user.role == CustomUser.Role.PARENT

def is_accountant(user):
    return user.is_authenticated and user.role == CustomUser.Role.ACCOUNTANT

def is_secretary(user):
    return user.is_authenticated and user.role == CustomUser.Role.SECRETARY

def is_receptionist(user):
    return user.is_authenticated and user.role == CustomUser.Role.RECEPTIONIST

def is_security(user):
    return user.is_authenticated and user.role == CustomUser.Role.SECURITY

def is_janitor(user):
    return user.is_authenticated and user.role == CustomUser.Role.JANITOR

def is_cook(user):
    return user.is_authenticated and user.role == CustomUser.Role.COOK

def is_cleaner(user):
    return user.is_authenticated and user.role == CustomUser.Role.CLEANER

def is_staff_member(user):
    return user.is_authenticated and user.role == CustomUser.Role.STAFF

def is_non_teaching_staff(user):
    """Check if user is any type of non-teaching staff"""
    return user.is_authenticated and user.role in [
        CustomUser.Role.ACCOUNTANT, CustomUser.Role.SECRETARY, CustomUser.Role.RECEPTIONIST,
        CustomUser.Role.SECURITY, CustomUser.Role.JANITOR, CustomUser.Role.COOK,
        CustomUser.Role.CLEANER, CustomUser.Role.STAFF
    ]

@login_required
def index(request):
    """
    Main dashboard index - redirects to role-specific dashboard
    """
    user = request.user

    if is_admin(user):
        return redirect('dashboard:admin_dashboard')
    elif is_teacher(user):
        return redirect('dashboard:teacher_dashboard')
    elif is_student(user):
        return redirect('dashboard:student_dashboard')
    elif is_parent(user):
        return redirect('dashboard:parent_dashboard')
    elif is_non_teaching_staff(user):
        return redirect('dashboard:staff_dashboard')
    else:
        # Default fallback
        return render(request, 'dashboard/index.html')

@user_passes_test(is_admin)
def admin_dashboard(request):
    """
    Admin dashboard showing system-wide statistics and management options
    """
    # Fetch system stats
    total_students = Student.objects.count()
    total_teachers = Teacher.objects.count()
    total_parents = Parent.objects.count()
    total_classes = ClassRoom.objects.count()

    # Get recent users
    recent_users = CustomUser.objects.order_by('-date_joined')[:10]

    # Get upcoming events
    upcoming_events = Event.objects.filter(
        end_date__gte=timezone.now()
    ).order_by('start_date')[:5]

    # Get recent announcements
    recent_announcements = Announcement.objects.filter(
        target_type='ALL'
    ).order_by('-created_at')[:5]

    # Get school settings
    try:
        school_settings = SchoolSettings.objects.first()
    except:
        school_settings = None

    # Get fee statistics
    current_term = Term.objects.filter(is_current=True).first()

    if current_term:
        # Calculate total fees for current term
        total_fees = StudentFee.objects.filter(
            class_fee__term=current_term
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Calculate total collected fees
        total_collected = StudentFee.objects.filter(
            class_fee__term=current_term
        ).aggregate(total=Sum('amount_paid'))['total'] or 0

        # Calculate outstanding balance
        total_outstanding = total_fees - total_collected

        # Calculate collection percentage
        collection_percentage = (total_collected / total_fees * 100) if total_fees > 0 else 0
        outstanding_percentage = (total_outstanding / total_fees * 100) if total_fees > 0 else 0

        # Get recent payments (last 7 days)
        recent_payments = Payment.objects.filter(
            payment_date__gte=timezone.now() - timedelta(days=7)
        )
        recent_payments_count = recent_payments.count()
    else:
        total_fees = 0
        total_collected = 0
        total_outstanding = 0
        collection_percentage = 0
        outstanding_percentage = 0
        recent_payments_count = 0

    # Get user widgets
    user_widgets = get_user_widgets(request.user)

    # Get enrollment trends
    enrollment_trends = []
    current_year = timezone.now().year
    for month in range(1, 13):
        month_name = calendar.month_name[month]
        count = CustomUser.objects.filter(
            date_joined__year=current_year,
            date_joined__month=month,
            role=CustomUser.Role.STUDENT
        ).count()
        enrollment_trends.append({
            'month': month_name,
            'count': count
        })

    # Get system activity
    system_activity = []
    for i in range(7):
        day = timezone.now() - timedelta(days=i)
        day_name = day.strftime('%A')
        logins = CustomUser.objects.filter(
            last_login__date=day.date()
        ).count()
        assignments = Assignment.objects.filter(
            created_at__date=day.date()
        ).count()
        submissions = StudentSubmission.objects.filter(
            submission_date__date=day.date()
        ).count()

        system_activity.append({
            'day': day_name,
            'logins': logins,
            'assignments': assignments,
            'submissions': submissions
        })
    system_activity.reverse()

    # Get attendance overview
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    attendance_overview = {
        'today': {
            'present': StudentAttendance.objects.filter(attendance_record__date=today, status='PRESENT').count(),
            'absent': StudentAttendance.objects.filter(attendance_record__date=today, status='ABSENT').count(),
            'late': StudentAttendance.objects.filter(attendance_record__date=today, status='LATE').count(),
            'excused': StudentAttendance.objects.filter(attendance_record__date=today, status='EXCUSED').count()
        },
        'this_week': {}
    }

    for i in range(7):
        day = week_start + timedelta(days=i)
        day_name = day.strftime('%a')

        attendance_overview['this_week'][day_name] = {
            'present': StudentAttendance.objects.filter(attendance_record__date=day, status='PRESENT').count(),
            'absent': StudentAttendance.objects.filter(attendance_record__date=day, status='ABSENT').count(),
            'late': StudentAttendance.objects.filter(attendance_record__date=day, status='LATE').count(),
            'excused': StudentAttendance.objects.filter(attendance_record__date=day, status='EXCUSED').count()
        }

    # Get grade distribution
    grade_distribution = {
        'A': Grade.objects.filter(score__gte=90).count(),
        'B': Grade.objects.filter(score__gte=80, score__lt=90).count(),
        'C': Grade.objects.filter(score__gte=70, score__lt=80).count(),
        'D': Grade.objects.filter(score__gte=60, score__lt=70).count(),
        'F': Grade.objects.filter(score__lt=60).count()
    }

    # Calculate total grades
    total_grades = sum(grade_distribution.values())

    # Get recent activities/logs
    recent_activities = []

    # Get recent assignments
    recent_assignments = Assignment.objects.order_by('-created_at')[:5]
    for assignment in recent_assignments:
        recent_activities.append({
            'type': 'assignment',
            'icon': 'fas fa-clipboard-list',
            'color': 'primary',
            'text': f"New assignment '{assignment.title}' created for {assignment.class_subject.classroom.name}",
            'user': assignment.created_by.get_full_name(),
            'time': assignment.created_at,
            'url': '#'
        })

    # Get recent submissions
    recent_submissions = StudentSubmission.objects.order_by('-submission_date')[:5]
    for submission in recent_submissions:
        recent_activities.append({
            'type': 'submission',
            'icon': 'fas fa-file-alt',
            'color': 'success',
            'text': f"{submission.student.user.get_full_name()} submitted '{submission.assignment.title}'",
            'user': submission.student.user.get_full_name(),
            'time': submission.submission_date,
            'url': '#'
        })

    # Get recent grades
    recent_grades = Grade.objects.order_by('-created_at')[:5]
    for grade in recent_grades:
        recent_activities.append({
            'type': 'grade',
            'icon': 'fas fa-star',
            'color': 'warning',
            'text': f"{grade.created_by.get_full_name()} graded {grade.student.user.get_full_name()}'s submission with {grade.score}%",
            'user': grade.created_by.get_full_name(),
            'time': grade.created_at,
            'url': '#'
        })

    # Get recent announcements for activity feed
    for announcement in recent_announcements:
        recent_activities.append({
            'type': 'announcement',
            'icon': 'fas fa-bullhorn',
            'color': 'info',
            'text': f"New announcement: {announcement.title}",
            'user': announcement.created_by.get_full_name(),
            'time': announcement.created_at,
            'url': '#'
        })

    # Sort activities by time
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:10]

    # Get unread notifications
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]

    context = {
        'user': request.user,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_parents': total_parents,
        'total_classes': total_classes,
        'recent_users': recent_users,
        'upcoming_events': upcoming_events,
        'recent_announcements': recent_announcements,
        'school_settings': school_settings,
        'user_widgets': user_widgets,
        'enrollment_trends': enrollment_trends,
        'system_activity': system_activity,
        'attendance_overview': attendance_overview,
        'grade_distribution': grade_distribution,
        'total_grades': total_grades,
        'recent_activities': recent_activities,
        'unread_notifications': unread_notifications,
        'enrollment_trends_json': json.dumps([item['count'] for item in enrollment_trends]),
        'enrollment_labels_json': json.dumps([item['month'] for item in enrollment_trends]),
        'grade_distribution_json': json.dumps(list(grade_distribution.values())),
        'grade_labels_json': json.dumps(list(grade_distribution.keys())),
        # Fee statistics
        'total_fees': total_fees,
        'total_collected': total_collected,
        'total_outstanding': total_outstanding,
        'collection_percentage': collection_percentage,
        'outstanding_percentage': outstanding_percentage,
        'recent_payments_count': recent_payments_count,
        'current_term': current_term,
    }

    return render(request, 'dashboard/admin_dashboard.html', context)

@user_passes_test(is_teacher)
def teacher_dashboard(request):
    """
    Teacher dashboard showing classes, assignments, and teaching materials
    """
    user = request.user

    # Get teacher profile and check if subject teacher
    try:
        teacher = Teacher.objects.get(user=user)
        is_subject_teacher = not ClassRoom.objects.filter(class_teacher=teacher).exists()
    except Teacher.DoesNotExist:
        teacher = None
        is_subject_teacher = False

    # Get assigned classrooms
    assigned_classrooms = []
    class_teacher_of = []
    class_teacher_of = []
    if teacher:
        # Get classrooms where teacher is class teacher
        pass

    # Get teacher profile and check if subject teacher
    try:
        teacher = Teacher.objects.get(user=user)
        # Check if this is a subject teacher (not a class teacher for any class)
        class_teacher_of = ClassRoom.objects.filter(class_teacher=teacher).distinct()
        is_subject_teacher = not class_teacher_of.exists()
    except Teacher.DoesNotExist:
        teacher = None
        class_teacher_of = []
        is_subject_teacher = False

    # Get assigned classrooms
    assigned_classrooms = []
    if teacher:
        # Get classrooms from subjects taught by teacher
        assigned_subjects = ClassSubject.objects.filter(teacher=teacher).distinct()
        assigned_classrooms = list(set([subject.classroom for subject in assigned_subjects]))

        # Combine and deduplicate classrooms
        unique_classrooms = list(set(list(class_teacher_of) + assigned_classrooms))
        recent_submissions = StudentSubmission.objects.filter(
            assignment__class_subject__teacher=teacher,
            is_graded=False
        ).order_by('-submission_date')[:5]

        # Get recent assignments
        if is_subject_teacher:
            # For subject teachers, only show assignments for subjects they teach
            recent_assignments = Assignment.objects.filter(
                class_subject__teacher=teacher
            ).order_by('-created_at')[:5]
        else:
            # For class teachers, show all assignments for their assigned classes
            recent_assignments = Assignment.objects.filter(
                class_subject__classroom__in=class_teacher_of
            ).order_by('-created_at')[:5]

        # Recent assignments are already defined above in the conditional block

    # Get recent announcements
    recent_announcements = Announcement.objects.filter(
        target_type__in=['ALL', 'TEACHERS']
    ).order_by('-created_at')[:5]

    # Get today's attendance records with students
    today_attendance = []
    class_teacher_data = []  # Initialize class_teacher_data before conditional
    if teacher and class_teacher_of:
      for classroom in class_teacher_of:
          attendance_record = AttendanceRecord.objects.filter(
              classroom=classroom,
              date=date.today()
          ).first()
          if attendance_record:
              students = classroom.students.all()
              today_attendance.append({
                  'classroom': classroom,
                  'record': attendance_record,
                  'students': students
              })
          class_teacher_data.append({
              'classroom': classroom,
              'student_count': classroom.students.count()
          })
    # Get user widgets
    user_widgets = get_user_widgets(request.user)

    # Get upcoming deadlines
    today = timezone.now()
    upcoming_deadlines = Assignment.objects.filter(
        class_subject__teacher=teacher,
        due_date__gte=today
    ).order_by('due_date')[:5]

    # Get grading progress
    submission_stats = {
        'total': StudentSubmission.objects.filter(
            assignment__class_subject__teacher=teacher
        ).count(),
        'graded': StudentSubmission.objects.filter(
            assignment__class_subject__teacher=teacher,
            is_graded=True
        ).count()
    }

    submission_stats['pending'] = submission_stats['total'] - submission_stats['graded']
    if submission_stats['total'] > 0:
        submission_stats['progress'] = round((submission_stats['graded'] / submission_stats['total']) * 100)
    else:
        submission_stats['progress'] = 0

    # Get class performance statistics
    class_performance = []

    if teacher:
        if is_subject_teacher:
            # Filter ClassSubjects to only include those taught by the teacher
            teacher_subjects = ClassSubject.objects.filter(teacher=teacher)
        else:
            # For class teachers, show all subjects for their assigned class
            teacher_subjects = ClassSubject.objects.filter(classroom__in=class_teacher_of)

        for class_subject in teacher_subjects:
            # Get average grade for this subject
            avg_grade = Grade.objects.filter(
                student__in=class_subject.students.all(),
                class_subject=class_subject
            ).aggregate(avg=Avg('score'))['avg']

        for class_subject in teacher_subjects:
            # Get average grade for this subject
            avg_grade = Grade.objects.filter(
                student__in=class_subject.students.all(),
                class_subject=class_subject
            ).aggregate(avg=Avg('score'))['avg']

            if avg_grade is None:
                avg_grade = 0

            # Get assignment completion rate
            assignments = Assignment.objects.filter(class_subject=class_subject).count()
            if assignments > 0:
                submissions = StudentSubmission.objects.filter(
                    assignment__class_subject=class_subject
                ).count()
                total_possible = assignments * class_subject.students.count()
                if total_possible > 0:
                    completion_rate = round((submissions / total_possible) * 100)
                else:
                    completion_rate = 0
            else:
                completion_rate = 0

            class_performance.append({
                'class_name': f"{class_subject.classroom.name} - {class_subject.subject.name}",
                'avg_grade': round(avg_grade, 1) if avg_grade else 0,
                'completion_rate': completion_rate,
                'student_count': class_subject.students.count()
            })

    # Get calendar events (assignments, exams, personal)
    calendar_events = []

    # Add assignments as events
    assignments = Assignment.objects.filter(
        class_subject__teacher=teacher,
        due_date__gte=today - timedelta(days=30),
        due_date__lte=today + timedelta(days=60)
    )

    for assignment in assignments:
        event_type = 'bg-primary'
        if assignment.assignment_type == 'QUIZ':
            event_type = 'bg-success'
        elif assignment.assignment_type == 'TEST':
            event_type = 'bg-warning'
        elif assignment.assignment_type == 'EXAM':
            event_type = 'bg-danger'

        calendar_events.append({
            'title': assignment.title,
            'start': assignment.due_date.isoformat(),
            'end': (assignment.due_date + timedelta(hours=1)).isoformat(),
            'className': event_type,
            'url': '#'
        })

    # Add school events
    school_events = Event.objects.filter(
        start_date__gte=today - timedelta(days=30),
        end_date__lte=today + timedelta(days=60)
    )

    # Filter for school-wide events or events specific to this teacher's classes
    if teacher and class_teacher_of:
        school_events = school_events.filter(
            Q(is_school_wide=True) |
            Q(specific_class__in=class_teacher_of)
        )
    else:
        school_events = school_events.filter(is_school_wide=True)

    for event in school_events:
        calendar_events.append({
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat(),
            'className': 'bg-info',
            'url': '#'
        })

    # Get attendance statistics
    attendance_stats = {}

    for classroom in class_teacher_of:
        classroom_stats = {
            'present': StudentAttendance.objects.filter(
                attendance_record__classroom=classroom,
                attendance_record__date=today,
                status='PRESENT'
            ).count(),
            'absent': StudentAttendance.objects.filter(
                attendance_record__classroom=classroom,
                attendance_record__date=today,
                status='ABSENT'
            ).count(),
            'late': StudentAttendance.objects.filter(
                attendance_record__classroom=classroom,
                attendance_record__date=today,
                status='LATE'
            ).count(),
            'excused': StudentAttendance.objects.filter(
                attendance_record__classroom=classroom,
                attendance_record__date=today,
                status='EXCUSED'
            ).count()
        }

        total = classroom_stats['present'] + classroom_stats['absent'] + \
                classroom_stats['late'] + classroom_stats['excused']

        if total > 0:
            classroom_stats['present_percentage'] = round((classroom_stats['present'] / total) * 100)
            classroom_stats['absent_percentage'] = round((classroom_stats['absent'] / total) * 100)
            classroom_stats['late_percentage'] = round((classroom_stats['late'] / total) * 100)
            classroom_stats['excused_percentage'] = round((classroom_stats['excused'] / total) * 100)
        else:
            classroom_stats['present_percentage'] = 0
            classroom_stats['absent_percentage'] = 0
            classroom_stats['late_percentage'] = 0
            classroom_stats['excused_percentage'] = 0

        attendance_stats[classroom.name] = classroom_stats

    # Get unread messages count
    unread_messages_count = Message.objects.filter(
        recipient=user,
        is_read=False
    ).count()

    # Get unread notifications
    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).order_by('-created_at')[:5]

    context = {
        'user': user,
        'teacher': teacher,
        'assigned_classes': assigned_subjects,
        'class_teacher_of': class_teacher_data,
        'unique_classrooms': unique_classrooms,
        'recent_assignments': recent_assignments,
        'recent_submissions': recent_submissions,
        'recent_announcements': recent_announcements,
        'today_attendance': today_attendance,
        'user_widgets': user_widgets,
        'upcoming_deadlines': upcoming_deadlines,
        'submission_stats': submission_stats,
        'class_performance': class_performance,
        'calendar_events': json.dumps(calendar_events),
        'attendance_stats': attendance_stats,
        'unread_messages_count': unread_messages_count,
        'unread_notifications': unread_notifications,
    }

    return render(request, 'dashboard/teacher_dashboard.html', context)

@user_passes_test(is_student)
def student_dashboard(request):
    """
    Student dashboard showing classes, assignments, and grades
    """
    user = request.user
    today = timezone.now()

    # Get student profile
    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        student = None

    # Get enrolled subjects
    enrolled_subjects = []
    if student:
        enrolled_subjects = ClassSubject.objects.filter(students=student)

    # Get upcoming assignments
    upcoming_assignments = []
    if student:
        upcoming_assignments = Assignment.objects.filter(
            class_subject__in=enrolled_subjects,
            due_date__gte=today
        ).order_by('due_date')[:5]

    # Get recent grades
    recent_grades = []
    if student:
        recent_grades = Grade.objects.filter(
            student=student
        ).order_by('-created_at')[:5]

    # Get recent announcements
    recent_announcements = Announcement.objects.filter(
        target_type__in=['ALL', 'STUDENTS']
    ).order_by('-created_at')[:5]

    # Get attendance record
    attendance_records = []
    if student:
        attendance_records = StudentAttendance.objects.filter(
            student=student
        ).order_by('-attendance_record__date')[:10]

    # Get course materials
    course_materials = []
    if student and enrolled_subjects:
        course_materials = CourseMaterial.objects.filter(
            class_subject__in=enrolled_subjects
        ).order_by('-created_at')[:10]

    # Get YouTube videos
    youtube_videos = []
    if student and enrolled_subjects:
        youtube_videos = YouTubeVideo.objects.filter(
            class_subject__in=enrolled_subjects
        ).order_by('-created_at')[:5]

    # Get user widgets
    user_widgets = get_user_widgets(request.user)

    # Get overall grade average
    overall_grade = 0
    if student:
        grades = Grade.objects.filter(student=student)
        if grades.exists():
            overall_grade = grades.aggregate(avg=Avg('score'))['avg']
            if overall_grade:
                overall_grade = round(overall_grade, 1)

    # Get attendance statistics - create separate querysets for each status to avoid filtering after slice
    if student:
        attendance_stats = {
            'present': StudentAttendance.objects.filter(student=student, status='PRESENT').count(),
            'absent': StudentAttendance.objects.filter(student=student, status='ABSENT').count(),
            'late': StudentAttendance.objects.filter(student=student, status='LATE').count(),
            'excused': StudentAttendance.objects.filter(student=student, status='EXCUSED').count()
        }

        total_days = sum(attendance_stats.values())
        attendance_stats['total_days'] = total_days
        if total_days > 0:
            attendance_stats['attendance_rate'] = round((attendance_stats['present'] / total_days) * 100)
        else:
            attendance_stats['attendance_rate'] = 0
    else:
        attendance_stats = {
            'present': 0,
            'absent': 0,
            'late': 0,
            'excused': 0,
            'attendance_rate': 0
        }

    # Calculate enrolled subjects count
    enrolled_subjects_count = enrolled_subjects.count() if enrolled_subjects else 0

    # Get grade trends by subject
    subject_grades = []
    if student and enrolled_subjects:
        for subject in enrolled_subjects:
            subject_avg = Grade.objects.filter(
                student=student,
                class_subject=subject
            ).aggregate(avg=Avg('score'))['avg']

            if subject_avg is not None:
                subject_grades.append({
                    'subject': subject.subject.name,
                    'average': round(subject_avg, 1)
                })

    # Get assignment completion rate
    total_assignments = Assignment.objects.filter(
        class_subject__in=enrolled_subjects
    ).count()

    if total_assignments > 0:
        completed = StudentSubmission.objects.filter(
            assignment__class_subject__in=enrolled_subjects,
            student=student
        ).count()

        completion_rate = round((completed / total_assignments) * 100)
    else:
        completion_rate = 0

    # Get calendar events
    calendar_events = []

    # Add assignments as events
    for assignment in upcoming_assignments:
        event_type = 'bg-primary'
        if assignment.assignment_type == 'QUIZ':
            event_type = 'bg-success'
        elif assignment.assignment_type == 'TEST':
            event_type = 'bg-warning'
        elif assignment.assignment_type == 'EXAM':
            event_type = 'bg-danger'

        calendar_events.append({
            'title': assignment.title,
            'start': assignment.due_date.isoformat(),
            'end': (assignment.due_date + timedelta(hours=1)).isoformat(),
            'className': event_type,
            'url': '#'
        })

    # Add school events - fixed to use correct Event model fields
    school_events = Event.objects.filter(
        start_date__gte=today - timedelta(days=30),
        end_date__lte=today + timedelta(days=60)
    )

    # Filter for school-wide events or events specific to this student's classes
    if student and enrolled_subjects:
        # Get all classrooms the student is part of through their enrolled subjects
        student_classrooms = [subject.classroom for subject in enrolled_subjects]
        school_events = school_events.filter(
            Q(is_school_wide=True) |
            Q(specific_class__in=student_classrooms) |
            Q(specific_subject__in=enrolled_subjects)
        )
    else:
        school_events = school_events.filter(is_school_wide=True)

    for event in school_events:
        calendar_events.append({
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat(),
            'className': 'bg-info',
            'url': '#'
        })

    # Get schedule
    schedule = {}
    weekday_mapping = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4,
        'Saturday': 5,
        'Sunday': 6
    }
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    if student and enrolled_subjects:
        # Get all classrooms the student is part of
        student_classrooms = list(set([subject.classroom for subject in enrolled_subjects]))

        # If student has at least one classroom, use the first one for schedule
        if student_classrooms:
            primary_classroom = student_classrooms[0]
            # Get class subjects for this classroom
            classroom_subjects = ClassSubject.objects.filter(classroom=primary_classroom)

            for day in weekdays:
                # Convert day string to numeric value
                day_num = weekday_mapping.get(day, 0)
                day_schedule = Schedule.objects.filter(
                    class_subject__in=classroom_subjects,
                    day_of_week=day_num
                ).order_by('start_time')

                schedule[day] = day_schedule

    # Get today's schedule
    today_weekday = timezone.now().strftime('%A')
    if today_weekday in schedule:
        today_schedule = schedule[today_weekday]
    else:
        today_schedule = []

    # Get unread notifications
    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).order_by('-created_at')[:5]

    # Get recent report cards
    recent_report_cards = ReportCard.objects.filter(
        student=student
    ).order_by('-generated_date')[:2]

    # Get student fees
    student_fees = []
    if student:
        # Get current term
        current_term = Term.objects.filter(is_current=True).first()

        # Get student fees for current term
        if current_term:
            student_fees = StudentFee.objects.filter(
                student=student,
                class_fee__term=current_term
            ).select_related('class_fee', 'class_fee__fee_category').order_by('class_fee__fee_category__name')

    # Calculate average grade
    avg_grade = None
    if recent_grades:
        total_score = sum(grade.score for grade in recent_grades)
        avg_grade = round(total_score / len(recent_grades), 1)

    # Get student's primary classroom for display
    student_classroom = None
    if student:
        # Check if student has a ForeignKey grade (classroom) assigned
        if hasattr(student, 'grade') and student.grade:
            student_classroom = student.grade
        # If not, check course_classrooms many-to-many relationship
        else:
            student_classrooms = student.course_classrooms.all()
            if student_classrooms.exists():
                student_classroom = student_classrooms.first()

    context = {
        'user': user,
        'student': student,
        'student_classroom': student_classroom,
        'enrolled_subjects': enrolled_subjects,
        'enrolled_subjects_count': enrolled_subjects_count,
        'upcoming_assignments': upcoming_assignments,
        'recent_grades': recent_grades,
        'avg_grade': avg_grade,
        'recent_announcements': recent_announcements,
        'attendance_records': attendance_records,
        'course_materials': course_materials,
        'youtube_videos': youtube_videos,
        'user_widgets': user_widgets,
        'overall_grade': overall_grade,
        'attendance_stats': attendance_stats,
        'subject_grades': subject_grades,
        'completion_rate': completion_rate,
        'student_fees': student_fees,
        'calendar_events': json.dumps(calendar_events),
        'schedule': schedule,
        'today_schedule': today_schedule,
        'unread_notifications': unread_notifications,
        'recent_report_cards': recent_report_cards,
        'subject_grades_json': json.dumps([s['average'] for s in subject_grades]),
        'subject_labels_json': json.dumps([s['subject'] for s in subject_grades]),
    }

    return render(request, 'dashboard/student_dashboard.html', context)

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.db.models import Avg, Q
from django.utils import timezone
from datetime import timedelta
import json

@user_passes_test(is_parent)
def parent_dashboard(request):
    """Parent dashboard showing children's information"""
    # Implementation remains the same


@user_passes_test(is_non_teaching_staff)
def staff_dashboard(request):
    """Dashboard for non-teaching staff members"""
    user = request.user

    # Get staff profile
    try:
        staff_member = StaffMember.objects.get(user=user)
    except StaffMember.DoesNotExist:
        staff_member = None

    # Get staff salary information
    from payroll.models import StaffSalary
    try:
        staff_salary = StaffSalary.objects.get(user=user)
    except StaffSalary.DoesNotExist:
        staff_salary = None

    # Get recent announcements
    recent_announcements = Announcement.objects.filter(
        Q(target_type='ALL') | Q(target_type='STAFF')
    ).order_by('-created_at')[:5]

    # Get upcoming events
    upcoming_events = Event.objects.filter(
        end_date__gte=timezone.now()
    ).order_by('start_date')[:5]

    # Accountant-specific data
    pending_payrolls = None
    pending_fees = None
    if is_accountant(user):
        from payroll.models import Payroll
        from fees.models import StudentFee

        # Get pending payrolls
        pending_payrolls = Payroll.objects.filter(status='PENDING').count()

        # Get pending fees
        pending_fees = StudentFee.objects.filter(status='PENDING').count()

    context = {
        'staff_member': staff_member,
        'staff_salary': staff_salary,
        'recent_announcements': recent_announcements,
        'announcements_count': Announcement.objects.filter(
            Q(target_type='ALL') | Q(target_type='STAFF')
        ).count(),
        'upcoming_events': upcoming_events,
        'upcoming_events_count': Event.objects.filter(end_date__gte=timezone.now()).count(),
        'pending_payrolls': pending_payrolls,
        'pending_fees': pending_fees,
    }

    return render(request, 'dashboard/staff_dashboard.html', context)


@user_passes_test(is_parent)
def parent_dashboard(request):
    """
    Parent dashboard showing children's performance, assignments, and attendance
    """
    user = request.user

    # Get parent profile
    parent = Parent.objects.filter(user=user).first()
    children = parent.children.all() if parent else []

    # Get selected child from query params or first child
    selected_child_id = request.GET.get('child_id')
    selected_child = next((child for child in children if str(child.id) == selected_child_id), children[0] if children else None)

    # Get selected child's data
    child_data = {}
    child_fees = []
    if selected_child:
        enrolled_subjects = ClassSubject.objects.filter(students=selected_child)

        upcoming_assignments = list(Assignment.objects.filter(
            class_subject__in=enrolled_subjects,
            due_date__gt=timezone.now()
        ).order_by('due_date')[:5])  # Slice applied directly

        recent_grades = list(Grade.objects.filter(student=selected_child).order_by('-created_at')[:5])
        attendance_records = list(StudentAttendance.objects.filter(student=selected_child).order_by('-attendance_record__date')[:10])

        overall_grade = Grade.objects.filter(student=selected_child).aggregate(avg=Avg('score'))['avg'] or 0
        overall_grade = round(overall_grade, 1) if overall_grade else 0

        # Calculate attendance statistics
        attendance_stats = {status: sum(1 for record in attendance_records if record.status == status) for status in ['PRESENT', 'ABSENT', 'LATE', 'EXCUSED']}
        total_days = sum(attendance_stats.values())
        attendance_stats['total_days'] = total_days
        attendance_stats['attendance_rate'] = round((attendance_stats['PRESENT'] / total_days) * 100) if total_days else 0

        # Add attendance_stats to child_data
        child_data['attendance_stats'] = attendance_stats

        # Get current term
        current_term = Term.objects.filter(is_current=True).first()

        # Get student fees for current term
        if current_term:
            child_fees = StudentFee.objects.filter(
                student=selected_child,
                class_fee__term=current_term
            ).select_related('class_fee', 'class_fee__fee_category').order_by('class_fee__fee_category__name')
            child_data['fees'] = child_fees

            # Calculate total fees for this child
            child_total_amount = sum(fee.amount for fee in child_fees)
            child_total_paid = sum(fee.amount_paid for fee in child_fees)
            child_total_balance = child_total_amount - child_total_paid

            child_data['total_fees'] = {
                'amount': child_total_amount,
                'paid': child_total_paid,
                'balance': child_total_balance,
                'payment_percentage': (child_total_paid / child_total_amount * 100) if child_total_amount > 0 else 0
            }

        subject_grades = [
            {
                'subject': subject.subject.name,
                'average': round(Grade.objects.filter(student=selected_child, class_subject=subject).aggregate(avg=Avg('score'))['avg'] or 0, 1)
            }
            for subject in enrolled_subjects
        ]

        recent_report_cards = list(ReportCard.objects.filter(student=selected_child).order_by('-generated_date')[:2])
        today = timezone.now()

        calendar_events = [
            {
                'title': assignment.title,
                'start': assignment.due_date.isoformat(),
                'end': (assignment.due_date + timedelta(hours=1)).isoformat(),
                'className': {'QUIZ': 'bg-success', 'TEST': 'bg-warning', 'EXAM': 'bg-danger'}.get(assignment.assignment_type, 'bg-primary'),
                'url': '#'
            }
            for assignment in upcoming_assignments
        ]

        school_events = Event.objects.filter(
            Q(start_date__gte=today - timedelta(days=30)) &
            Q(end_date__lte=today + timedelta(days=60)) &
            (Q(is_school_wide=True) | Q(specific_class__in=[s.classroom for s in enrolled_subjects]) | Q(specific_subject__in=enrolled_subjects))
        )

        calendar_events.extend([
            {
                'title': event.title,
                'start': event.start_date.isoformat(),
                'end': event.end_date.isoformat(),
                'className': 'bg-info',
                'url': '#'
            }
            for event in school_events
        ])

        child_data = {
            'enrolled_subjects': enrolled_subjects,
            'upcoming_assignments': upcoming_assignments,
            'recent_grades': recent_grades,
            'attendance_records': attendance_records,
            'overall_grade': overall_grade,
            'attendance_stats': attendance_stats,
            'subject_grades': subject_grades,
            'recent_report_cards': recent_report_cards,
            'calendar_events': json.dumps(calendar_events),
            'subject_grades_json': json.dumps([s['average'] for s in subject_grades]),
            'subject_labels_json': json.dumps([s['subject'] for s in subject_grades]),
        }

    recent_announcements = list(Announcement.objects.filter(target_type__in=['ALL', 'PARENTS']).order_by('-created_at')[:5])
    user_widgets = get_user_widgets(request.user)
    unread_notifications = list(Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5])

    # Create a dictionary to store data for each child
    child_data_dict = {}

    # Calculate total fees for all children
    total_fees = {
        'amount': 0,
        'paid': 0,
        'balance': 0
    }

    # Store the selected child's data in the dictionary
    if selected_child:
        child_data_dict[selected_child.id] = child_data

    # For each child, get their fee data
    for child in children:
        # Skip if we already have data for the selected child
        if child.id == selected_child.id and selected_child:
            continue

        # Get current term
        current_term = Term.objects.filter(is_current=True).first()

        # Get student fees for current term
        if current_term:
            child_fees = StudentFee.objects.filter(
                student=child,
                class_fee__term=current_term
            ).select_related('class_fee', 'class_fee__fee_category').order_by('class_fee__fee_category__name')

            # Calculate total fees for this child
            child_total_amount = sum(fee.amount for fee in child_fees)
            child_total_paid = sum(fee.amount_paid for fee in child_fees)
            child_total_balance = child_total_amount - child_total_paid

            # Store in the dictionary
            child_data_dict[child.id] = {
                'total_fees': {
                    'amount': child_total_amount,
                    'paid': child_total_paid,
                    'balance': child_total_balance,
                    'payment_percentage': (child_total_paid / child_total_amount * 100) if child_total_amount > 0 else 0
                }
            }

            # Add to the total
            total_fees['amount'] += child_total_amount
            total_fees['paid'] += child_total_paid
            total_fees['balance'] += child_total_balance

    if total_fees['amount'] > 0:
        total_fees['payment_percentage'] = (total_fees['paid'] / total_fees['amount'] * 100)
    else:
        total_fees['payment_percentage'] = 0

    comparative_data = {
        'attendance': [
            {'name': child.user.first_name, 'rate': round((StudentAttendance.objects.filter(student=child, status='PRESENT').count() / StudentAttendance.objects.filter(student=child).count()) * 100) if StudentAttendance.objects.filter(student=child).count() > 0 else 0}
            for child in children
        ],
        'grades': [
            {'name': child.user.first_name, 'grade': round(Grade.objects.filter(student=child).aggregate(avg=Avg('score'))['avg'] or 0, 1)}
            for child in children
        ],
        'fees': [
            {'name': child.user.first_name, 'balance': child_data_dict.get(child.id, {}).get('total_fees', {}).get('balance', 0)}
            for child in children
        ]
    } if len(children) > 1 else None

    return render(request, 'dashboard/parent_dashboard.html', {
        'user': user,
        'parent': parent,
        'children': children,
        'selected_child': selected_child,
        'child_data': child_data,
        'child_fees': child_fees if 'fees' not in child_data else child_data['fees'],
        'recent_announcements': recent_announcements,
        'user_widgets': user_widgets,
        'unread_notifications': unread_notifications,
        'comparative_data': comparative_data,
        'total_fees': total_fees,
        'child_data_dict': child_data_dict,
    })


@login_required
def parent_child_detail(request, child_id):
    """
    Display detailed information about a specific child for parent users.
    """
    user = request.user

    # Get parent profile
    parent = Parent.objects.filter(user=user).first()
    if not parent:
        messages.error(request, "Parent profile not found.")
        return redirect('dashboard:index')

    # Get all children
    children = parent.children.all()

    # Get selected child
    child = get_object_or_404(Student, id=child_id)

    # Verify that the selected child belongs to this parent
    if child not in children:
        messages.error(request, "You don't have permission to view this student's information.")
        return redirect('dashboard:parent_dashboard')

    # Get child's academic data
    enrolled_subjects = ClassSubject.objects.filter(students=child)

    # Get upcoming assignments - filter first, then convert to list after slicing
    upcoming_assignments = Assignment.objects.filter(
        class_subject__in=enrolled_subjects,
        due_date__gt=timezone.now()
    ).order_by('due_date')[:5]
    upcoming_assignments = list(upcoming_assignments)

    # Get all assignments (for the assignments tab)
    all_assignments = Assignment.objects.filter(
        class_subject__in=enrolled_subjects
    ).order_by('-due_date')

    # Get recent submissions - filter first, then convert to list after slicing
    recent_submissions = StudentSubmission.objects.filter(
        student=child
    ).order_by('-submission_date')[:10]
    recent_submissions = list(recent_submissions)

    # Get recent grades - filter first, then convert to list after slicing
    recent_grades = Grade.objects.filter(
        student=child
    ).order_by('-created_at')[:10]
    recent_grades = list(recent_grades)

    # Get attendance records - filter first, then convert to list after slicing
    attendance_records = StudentAttendance.objects.filter(
        student=child
    ).order_by('-attendance_record__date')[:30]
    attendance_records = list(attendance_records)

    # Calculate attendance statistics using the list
    # First calculate all attendance counts
    present_count = sum(1 for record in attendance_records if record.status == 'PRESENT')
    absent_count = sum(1 for record in attendance_records if record.status == 'ABSENT')
    late_count = sum(1 for record in attendance_records if record.status == 'LATE')
    excused_count = sum(1 for record in attendance_records if record.status == 'EXCUSED')

    # Calculate total days
    total_days = present_count + absent_count + late_count + excused_count

    # Create attendance stats dictionary with all values including total_days
    attendance_stats = {
        'PRESENT': present_count,
        'ABSENT': absent_count,
        'LATE': late_count,
        'EXCUSED': excused_count,
        'total_days': total_days,
        'attendance_rate': round((present_count / total_days) * 100, 1) if total_days > 0 else 0
    }

    # Get course materials
    course_materials = CourseMaterial.objects.filter(
        class_subject__in=enrolled_subjects
    ).order_by('-created_at')[:10]

    # Get subject performance
    subject_grades = []
    for subject in enrolled_subjects:
        # Get grades for this subject
        subject_grades_query = Grade.objects.filter(
            student=child,
            class_subject=subject
        )

        avg_score = subject_grades_query.aggregate(avg=Avg('score'))['avg']
        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        subject_grades.append({
            'subject': subject.subject.name,
            'average': avg_score
        })

    # Get report cards
    recent_report_cards = ReportCard.objects.filter(
        student=child
    ).order_by('-generated_date')[:2]

    # Calculate overall grade average
    overall_grade = 0
    if recent_grades:
        grades_avg = Grade.objects.filter(student=child).aggregate(avg=Avg('score'))['avg']
        if grades_avg:
            overall_grade = round(grades_avg, 1)

    # Get calendar events
    calendar_events = []

    # Add assignments to calendar
    for assignment in upcoming_assignments:
        event_type = 'bg-primary'
        if assignment.assignment_type == 'QUIZ':
            event_type = 'bg-success'
        elif assignment.assignment_type == 'TEST':
            event_type = 'bg-warning'
        elif assignment.assignment_type == 'EXAM':
            event_type = 'bg-danger'

        calendar_events.append({
            'title': assignment.title,
            'start': assignment.due_date.isoformat(),
            'end': (assignment.due_date + timedelta(hours=1)).isoformat(),
            'className': event_type,
            'url': '#'
        })

    # Add school events
    today = timezone.now()
    school_events = Event.objects.filter(
        start_date__gte=today - timedelta(days=30),
        end_date__lte=today + timedelta(days=60)
    )

    # Filter for school-wide events or events specific to this student's classes
    student_classrooms = [subject.classroom for subject in enrolled_subjects]
    school_events = school_events.filter(
        Q(is_school_wide=True) |
        Q(specific_class__in=student_classrooms) |
        Q(specific_subject__in=enrolled_subjects)
    )

    for event in school_events:
        calendar_events.append({
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat(),
            'className': 'bg-info',
            'url': '#'
        })

    # Get recent announcements
    recent_announcements = Announcement.objects.filter(
        target_type__in=['ALL', 'PARENTS', 'STUDENTS']
    ).order_by('-created_at')[:5]

    # Get unread notifications
    unread_notifications = Notification.objects.filter(
        user=user,
        is_read=False
    ).order_by('-created_at')[:5]

    # Get current term
    current_term = Term.objects.filter(is_current=True).first()

    # Get student fees for current term
    child_fees = []
    if current_term:
        child_fees = StudentFee.objects.filter(
            student=child,
            class_fee__term=current_term
        ).select_related('class_fee', 'class_fee__fee_category', 'class_fee__term').order_by('class_fee__fee_category__name')

        # Get fee payment history
        fee_payments = Payment.objects.filter(
            student_fee__student=child
        ).select_related('student_fee', 'student_fee__class_fee', 'student_fee__class_fee__fee_category').order_by('-payment_date')[:10]

        # Calculate total fees for this child
        child_total_amount = sum(fee.amount for fee in child_fees)
        child_total_paid = sum(fee.amount_paid for fee in child_fees)
        child_total_balance = child_total_amount - child_total_paid

        child_fees_summary = {
            'amount': child_total_amount,
            'paid': child_total_paid,
            'balance': child_total_balance,
            'payment_percentage': (child_total_paid / child_total_amount * 100) if child_total_amount > 0 else 0
        }
    else:
        fee_payments = []
        child_fees_summary = {
            'amount': 0,
            'paid': 0,
            'balance': 0,
            'payment_percentage': 0
        }

    # Organize child data into a dictionary similar to parent_dashboard view
    child_data = {
        'enrolled_subjects': enrolled_subjects,
        'upcoming_assignments': upcoming_assignments,
        'recent_grades': recent_grades,
        'attendance_records': attendance_records,
        'overall_grade': overall_grade,
        'attendance_stats': attendance_stats,
        'subject_grades': subject_grades,
        'recent_report_cards': recent_report_cards,
        'calendar_events': json.dumps(calendar_events),
        'subject_grades_json': json.dumps([s['average'] for s in subject_grades]),
        'subject_labels_json': json.dumps([s['subject'] for s in subject_grades]),
        'fees': child_fees,
        'fee_payments': fee_payments,
        'fees_summary': child_fees_summary,
    }

    context = {
        'user': user,
        'parent': parent,
        'children': children,
        'child': child,
        'selected_child': child,  # Keep both to ensure compatibility with template
        'child_data': child_data,
        'all_assignments': all_assignments,
        'recent_submissions': recent_submissions,
        'course_materials': course_materials,
        'recent_announcements': recent_announcements,
        'unread_notifications': unread_notifications,
        # Include these at root level as well for template compatibility
        'attendance_stats': attendance_stats,
        'overall_grade': overall_grade,
        'enrolled_subjects': enrolled_subjects,
        'upcoming_assignments': upcoming_assignments,
        'recent_grades': recent_grades,
        'subject_grades': subject_grades,
        'subject_grades_json': json.dumps([s['average'] for s in subject_grades]),
        'subject_labels_json': json.dumps([s['subject'] for s in subject_grades]),
        # Add fees data
        'child_fees': child_fees,
        'fee_payments': fee_payments if 'fee_payments' in locals() else [],
        'fees_summary': child_data.get('fees_summary', {}),
        'current_term': current_term,
    }

    return render(request, 'dashboard/parent_child_detail.html', context)



@login_required
def manage_widgets(request):
    """
    Manage dashboard widgets (add, remove, configure)
    """
    # Get available widgets for user role
    available_widgets = []

    if is_admin(request.user):
        available_widgets = Widget.objects.filter(visible_to_admin=True, is_active=True)
    elif is_teacher(request.user):
        available_widgets = Widget.objects.filter(visible_to_teacher=True, is_active=True)
    elif is_student(request.user):
        available_widgets = Widget.objects.filter(visible_to_student=True, is_active=True)
    elif is_parent(request.user):
        available_widgets = Widget.objects.filter(visible_to_parent=True, is_active=True)

    # Get user's current widgets
    user_widgets = UserWidget.objects.filter(user=request.user).order_by('position')

    # Handle add widget
    if request.method == 'POST' and 'add_widget' in request.POST:
        widget_id = request.POST.get('widget_id')

        try:
            widget = Widget.objects.get(id=widget_id)

            # Check if user already has this widget
            if not UserWidget.objects.filter(user=request.user, widget=widget).exists():
                # Get highest position
                highest_position = UserWidget.objects.filter(user=request.user).order_by('-position').first()
                position = 1
                if highest_position:
                    position = highest_position.position + 1

                UserWidget.objects.create(
                    user=request.user,
                    widget=widget,
                    position=position,
                    size=widget.default_size
                )

                messages.success(request, f'Widget "{widget.name}" added successfully.')
            else:
                messages.warning(request, 'You already have this widget on your dashboard.')
        except Widget.DoesNotExist:
            messages.error(request, 'Widget not found.')

        return redirect('dashboard:manage_widgets')

    context = {
        'user': request.user,
        'available_widgets': available_widgets,
        'user_widgets': user_widgets,
    }

    return render(request, 'dashboard/manage_widgets.html', context)

@login_required
def toggle_widget(request, widget_id):
    """
    Toggle widget visibility
    """
    user_widget = get_object_or_404(UserWidget, id=widget_id, user=request.user)

    user_widget.is_visible = not user_widget.is_visible
    user_widget.save()

    action = 'shown' if user_widget.is_visible else 'hidden'
    messages.success(request, f'Widget "{user_widget.widget.name}" is now {action}.')

    return redirect('dashboard:manage_widgets')

@login_required
def reorder_widgets(request):
    """
    Reorder widgets (AJAX)
    """
    if request.method == 'POST' and request.is_ajax():
        widget_order = request.POST.getlist('widget_order[]')

        for i, widget_id in enumerate(widget_order, 1):
            try:
                user_widget = UserWidget.objects.get(id=widget_id, user=request.user)
                user_widget.position = i
                user_widget.save()
            except UserWidget.DoesNotExist:
                pass

        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error'}, status=400)  # Add this line to return an error response

import logging
logger = logging.getLogger(__name__)

@login_required
def dashboard_preferences(request):
    """
    Set dashboard preferences (theme, color scheme, etc.)
    """
    # Get or create user preferences
    preferences, created = DashboardPreference.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # Debug log the request
        logger.debug(f"Processing preferences update for user {request.user.id}")
        logger.debug(f"POST data: {request.POST}")

        try:
            # Update preferences
            preferences.theme = request.POST.get('theme', 'default')
            preferences.color_scheme = request.POST.get('color_scheme', 'blue')
            preferences.sidebar_collapsed = 'sidebar_collapsed' in request.POST

            # Notification preferences
            preferences.email_notifications = 'email_notifications' in request.POST
            preferences.assignment_notifications = 'assignment_notifications' in request.POST
            preferences.message_notifications = 'message_notifications' in request.POST
            preferences.grade_notifications = 'grade_notifications' in request.POST
            preferences.attendance_notifications = 'attendance_notifications' in request.POST

            preferences.save()
            logger.debug(f"Preferences saved for user {request.user.id}")

            # Check if request is AJAX
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if is_ajax:
                # Return JSON response for AJAX requests
                response_data = {
                    'status': 'success',
                    'message': 'Dashboard preferences updated successfully.',
                    'preferences': {
                        'theme': preferences.theme,
                        'color_scheme': preferences.color_scheme,
                        'sidebar_collapsed': preferences.sidebar_collapsed,
                        'email_notifications': preferences.email_notifications,
                        'assignment_notifications': preferences.assignment_notifications,
                        'message_notifications': preferences.message_notifications,
                        'grade_notifications': preferences.grade_notifications,
                        'attendance_notifications': preferences.attendance_notifications
                    }
                }
                logger.debug(f"Returning AJAX response: {response_data}")
                return JsonResponse(response_data)
            else:
                # For regular form submissions, redirect with success message
                messages.success(request, 'Dashboard preferences updated successfully.')
                return redirect('dashboard:preferences')
        except Exception as e:
            logger.error(f"Error saving preferences: {e}")

            # Check if request is AJAX
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error saving preferences: {str(e)}'
                }, status=500)
            else:
                messages.error(request, f'Error saving preferences: {str(e)}')
                return redirect('dashboard:preferences')

    context = {
        'user': request.user,
        'preferences': preferences,
    }

    return render(request, 'dashboard/preferences.html', context)

@login_required
def reset_widgets(request):
    """
    Reset user's widgets to default configuration
    """
    # Delete all user's widgets
    UserWidget.objects.filter(user=request.user).delete()

    # Create default widgets
    create_default_widgets(request.user)

    messages.success(request, 'Dashboard widgets have been reset to default configuration.')
    return redirect('dashboard:manage_widgets')

@user_passes_test(is_admin)
def admin_activities(request):
    """
    Display recent system activities and new user registrations for admins
    """
    # Get recent assignments (creation)
    recent_assignments = Assignment.objects.order_by('-created_at')[:10]
    assignment_activities = []
    for assignment in recent_assignments:
        assignment_activities.append({
            'type': 'assignment',
            'icon': 'fas fa-clipboard-list',
            'color': 'primary',
            'text': f"New assignment '{assignment.title}' created for {assignment.class_subject.classroom.name}",
            'user': assignment.created_by.get_full_name(),
            'time': assignment.created_at,
            'url': reverse('assignments:assignment_detail', kwargs={'assignment_id': assignment.id})
        })

    # Get recent submissions
    recent_submissions = StudentSubmission.objects.order_by('-submission_date')[:10]
    submission_activities = []
    for submission in recent_submissions:
        submission_activities.append({
            'type': 'submission',
            'icon': 'fas fa-file-alt',
            'color': 'success',
            'text': f"{submission.student.user.get_full_name()} submitted '{submission.assignment.title}'",
            'user': submission.student.user.get_full_name(),
            'time': submission.submission_date,
            'url': reverse('assignments:submission_detail', kwargs={'submission_id': submission.id})
        })

    # Get recent grades
    recent_grades = Grade.objects.order_by('-created_at')[:10]
    grade_activities = []
    for grade in recent_grades:
        grade_activities.append({
            'type': 'grade',
            'icon': 'fas fa-star',
            'color': 'warning',
            'text': f"{grade.created_by.get_full_name()} graded {grade.student.user.get_full_name()}'s submission with {grade.score}%",
            'user': grade.created_by.get_full_name(),
            'time': grade.created_at,
            'url': '#'
        })

    # Get recent announcements
    recent_announcements = Announcement.objects.order_by('-created_at')[:10]
    announcement_activities = []
    for announcement in recent_announcements:
        announcement_activities.append({
            'type': 'announcement',
            'icon': 'fas fa-bullhorn',
            'color': 'info',
            'text': f"New announcement: {announcement.title}",
            'user': announcement.created_by.get_full_name(),
            'time': announcement.created_at,
            'url': reverse('communications:announcement_detail', kwargs={'announcement_id': announcement.id})
        })

    # Combine all activities
    recent_activities = (
        assignment_activities +
        submission_activities +
        grade_activities +
        announcement_activities
    )

    # Sort activities by time
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:20]

    # Get recent users
    recent_users = CustomUser.objects.order_by('-date_joined')[:15]

    context = {
        'recent_activities': recent_activities,
        'recent_users': recent_users,
        'title': 'Recent Activities & Users'
    }

    return render(request, 'dashboard/admin_activities.html', context)

@login_required
def update_widget_size(request):
    """
    Update widget size (AJAX)
    """
    if request.method == 'POST':
        widget_id = request.POST.get('widget_id')
        size = request.POST.get('size')

        if not widget_id or not size or size not in ['small', 'medium', 'large', 'full']:
            return JsonResponse({'status': 'error', 'message': 'Invalid widget ID or size'}, status=400)

        try:
            user_widget = UserWidget.objects.get(id=widget_id, user=request.user)
            user_widget.size = size
            user_widget.save()

            return JsonResponse({
                'status': 'success',
                'message': f'Widget size updated to {size}'
            })
        except UserWidget.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Widget not found'}, status=404)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def remove_widget(request):
    """
    Remove widget from dashboard
    """
    if request.method == 'POST':
        widget_id = request.POST.get('widget_id')

        if not widget_id:
            messages.error(request, 'Widget ID is required.')
            return redirect('dashboard:manage_widgets')

        try:
            user_widget = UserWidget.objects.get(id=widget_id, user=request.user)
            widget_name = user_widget.widget.name
            user_widget.delete()

            messages.success(request, f'Widget "{widget_name}" removed successfully.')
        except UserWidget.DoesNotExist:
            messages.error(request, 'Widget not found.')

        return redirect('dashboard:manage_widgets')

    messages.error(request, 'Invalid request method.')
    return redirect('dashboard:manage_widgets')

@login_required
def get_notifications(request):
    """
    Get user notifications (AJAX)
    """
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]

    notifications_data = []
    for notification in unread_notifications:
        notifications_data.append({
            'id': notification.id,
            'message': notification.message,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            'icon': notification.icon,
            'link': notification.link
        })

    return JsonResponse({
        'status': 'success',
        'notifications': notifications_data,
        'count': unread_notifications.count()
    })

@login_required
def mark_notification_read(request, notification_id):
    """
    Mark notification as read
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()

    return JsonResponse({'status': 'success'})


# Admin Attendance Tracking Views
@user_passes_test(is_admin)
def admin_attendance_overview(request):
    """
    Provides an overview of attendance across the school
    """
    # Get date range from request or default to current month
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = date.today()
    if not start_date:
        # Default to first day of current month
        start_date = date(today.year, today.month, 1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        # Default to today
        end_date = today
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get all classes
    classes = ClassRoom.objects.all()

    # Get attendance overview for the date range
    attendance_data = {}

    for classroom in classes:
        # Get attendance records for this class in the date range
        records = AttendanceRecord.objects.filter(
            classroom=classroom,
            date__gte=start_date,
            date__lte=end_date
        )

        # Get total students in this class
        total_students = classroom.get_students().count()

        # Calculate attendance statistics
        if records.exists() and total_students > 0:
            # Calculate attendance metrics
            total_days = (end_date - start_date).days + 1

            # Calculate the number of school days in this range (excluding weekends)
            school_days = 0
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() < 5:  # Monday to Friday (0-4)
                    school_days += 1
                current_date += timedelta(days=1)

            # Get attendance statuses
            present_count = StudentAttendance.objects.filter(
                attendance_record__in=records,
                status='PRESENT'
            ).count()

            absent_count = StudentAttendance.objects.filter(
                attendance_record__in=records,
                status='ABSENT'
            ).count()

            late_count = StudentAttendance.objects.filter(
                attendance_record__in=records,
                status='LATE'
            ).count()

            excused_count = StudentAttendance.objects.filter(
                attendance_record__in=records,
                status='EXCUSED'
            ).count()

            # Expected total attendance entries
            expected_entries = total_students * school_days

            # Calculate attendance rate
            attendance_rate = 0
            if expected_entries > 0:
                attendance_rate = round((present_count / expected_entries) * 100, 1)

            # Add to data
            attendance_data[classroom.id] = {
                'class_name': classroom.name,
                'total_students': total_students,
                'school_days': school_days,
                'present_count': present_count,
                'absent_count': absent_count,
                'late_count': late_count,
                'excused_count': excused_count,
                'attendance_rate': attendance_rate,
                'expected_entries': expected_entries
            }
        else:
            # No records for this class in the date range
            attendance_data[classroom.id] = {
                'class_name': classroom.name,
                'total_students': total_students,
                'school_days': 0,
                'present_count': 0,
                'absent_count': 0,
                'late_count': 0,
                'excused_count': 0,
                'attendance_rate': 0,
                'expected_entries': 0
            }

    # Get attendance trend by day
    daily_trend = {}
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:  # Monday to Friday (0-4)
            daily_records = AttendanceRecord.objects.filter(date=current_date)

            present_count = StudentAttendance.objects.filter(
                attendance_record__in=daily_records,
                status='PRESENT'
            ).count()

            absent_count = StudentAttendance.objects.filter(
                attendance_record__in=daily_records,
                status='ABSENT'
            ).count()

            late_count = StudentAttendance.objects.filter(
                attendance_record__in=daily_records,
                status='LATE'
            ).count()

            excused_count = StudentAttendance.objects.filter(
                attendance_record__in=daily_records,
                status='EXCUSED'
            ).count()

            total = present_count + absent_count + late_count + excused_count

            if total > 0:
                attendance_rate = round((present_count / total) * 100, 1)
            else:
                attendance_rate = 0

            daily_trend[current_date.strftime('%Y-%m-%d')] = {
                'date': current_date.strftime('%b %d'),
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'excused': excused_count,
                'total': total,
                'attendance_rate': attendance_rate
            }

        current_date += timedelta(days=1)

    # Sort daily trend by date
    daily_trend = {k: daily_trend[k] for k in sorted(daily_trend.keys())}

    # Calculate overall attendance rate
    total_present = sum(data['present_count'] for data in attendance_data.values())
    total_expected = sum(data['expected_entries'] for data in attendance_data.values())

    overall_attendance_rate = 0
    if total_expected > 0:
        overall_attendance_rate = round((total_present / total_expected) * 100, 1)

    # Get top 5 classes with best attendance
    top_classes = sorted(
        [data for data in attendance_data.values() if data['expected_entries'] > 0],
        key=lambda x: x['attendance_rate'],
        reverse=True
    )[:5]

    # Get bottom 5 classes with worst attendance
    bottom_classes = sorted(
        [data for data in attendance_data.values() if data['expected_entries'] > 0],
        key=lambda x: x['attendance_rate']
    )[:5]

    context = {
        'classes': classes,
        'attendance_data': attendance_data,
        'start_date': start_date,
        'end_date': end_date,
        'overall_attendance_rate': overall_attendance_rate,
        'top_classes': top_classes,
        'bottom_classes': bottom_classes,
        'daily_trend': daily_trend,
        # For charts
        'daily_labels': json.dumps([daily_trend[date]['date'] for date in daily_trend]),
        'daily_attendance_rates': json.dumps([daily_trend[date]['attendance_rate'] for date in daily_trend]),
        'class_labels': json.dumps([classroom.name for classroom in classes]),
        'class_attendance_rates': json.dumps([attendance_data[classroom.id]['attendance_rate'] for classroom in classes]),
    }

    return render(request, 'dashboard/admin_attendance_overview.html', context)

@user_passes_test(is_admin)
def admin_class_attendance(request, class_id):
    """
    Detailed attendance view for a specific class
    """
    classroom = get_object_or_404(ClassRoom, id=class_id)

    # Get date range from request or default to current month
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = date.today()
    if not start_date:
        # Default to first day of current month
        start_date = date(today.year, today.month, 1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        # Default to today
        end_date = today
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get attendance records for this class in the date range
    records = AttendanceRecord.objects.filter(
        classroom=classroom,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')

    # Get students in this class
    students = classroom.get_students()

    # Calculate attendance statistics for each student
    student_stats = {}

    for student in students:
        # Calculate attendance for this student
        present_count = StudentAttendance.objects.filter(
            attendance_record__in=records,
            student=student,
            status='PRESENT'
        ).count()

        absent_count = StudentAttendance.objects.filter(
            attendance_record__in=records,
            student=student,
            status='ABSENT'
        ).count()

        late_count = StudentAttendance.objects.filter(
            attendance_record__in=records,
            student=student,
            status='LATE'
        ).count()

        excused_count = StudentAttendance.objects.filter(
            attendance_record__in=records,
            student=student,
            status='EXCUSED'
        ).count()

        # Calculate attendance rate
        total_records = records.count()
        if total_records > 0:
            attendance_rate = round((present_count / total_records) * 100, 1)
        else:
            attendance_rate = 0

        student_stats[student.id] = {
            'student': student,
            'present': present_count,
            'absent': absent_count,
            'late': late_count,
            'excused': excused_count,
            'attendance_rate': attendance_rate
        }

    # Sort students by attendance rate (descending)
    sorted_students = sorted(
        student_stats.values(),
        key=lambda x: x['attendance_rate'],
        reverse=True
    )

    # Calculate class average attendance rate
    total_present = sum(stats['present'] for stats in student_stats.values())
    total_records = records.count() * students.count()

    class_attendance_rate = 0
    if total_records > 0:
        class_attendance_rate = round((total_present / total_records) * 100, 1)

    # Daily attendance data for chart
    daily_data = {}
    for record in records:
        date_str = record.date.strftime('%Y-%m-%d')

        present_count = StudentAttendance.objects.filter(
            attendance_record=record,
            status='PRESENT'
        ).count()

        absent_count = StudentAttendance.objects.filter(
            attendance_record=record,
            status='ABSENT'
        ).count()

        late_count = StudentAttendance.objects.filter(
            attendance_record=record,
            status='LATE'
        ).count()

        excused_count = StudentAttendance.objects.filter(
            attendance_record=record,
            status='EXCUSED'
        ).count()

        total = present_count + absent_count + late_count + excused_count

        if total > 0:
            rate = round((present_count / total) * 100, 1)
        else:
            rate = 0

        daily_data[date_str] = {
            'date': record.date.strftime('%b %d'),
            'present': present_count,
            'absent': absent_count,
            'late': late_count,
            'excused': excused_count,
            'rate': rate
        }

    # Sort daily data by date
    daily_data = {k: daily_data[k] for k in sorted(daily_data.keys())}

    context = {
        'classroom': classroom,
        'students': students,
        'records': records,
        'student_stats': student_stats,
        'sorted_students': sorted_students,
        'class_attendance_rate': class_attendance_rate,
        'start_date': start_date,
        'end_date': end_date,
        'daily_data': daily_data,
        # For charts
        'daily_labels': json.dumps([data['date'] for data in daily_data.values()]),
        'daily_rates': json.dumps([data['rate'] for data in daily_data.values()]),
        'student_labels': json.dumps([student.user.get_full_name() for student in students]),
        'student_rates': json.dumps([student_stats[student.id]['attendance_rate'] for student in students]),
    }

    return render(request, 'dashboard/admin_class_attendance.html', context)

@user_passes_test(is_admin)
def admin_student_attendance(request, student_id):
    """
    Detailed attendance view for a specific student
    """
    student = get_object_or_404(Student, id=student_id)

    # Get date range from request or default to current month
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = date.today()
    if not start_date:
        # Default to first day of current month
        start_date = date(today.year, today.month, 1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        # Default to today
        end_date = today
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get attendance records for this student in the date range
    attendance_records = StudentAttendance.objects.filter(
        student=student,
        attendance_record__date__gte=start_date,
        attendance_record__date__lte=end_date
    ).order_by('attendance_record__date')

    # Calculate attendance statistics
    present_count = attendance_records.filter(status='PRESENT').count()
    absent_count = attendance_records.filter(status='ABSENT').count()
    late_count = attendance_records.filter(status='LATE').count()
    excused_count = attendance_records.filter(status='EXCUSED').count()

    total_records = attendance_records.count()
    attendance_rate = 0
    if total_records > 0:
        attendance_rate = round((present_count / total_records) * 100, 1)

    # Get monthly attendance data for chart
    monthly_data = {}

    # Calculate the number of months between start_date and end_date
    num_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

    # Generate months between start_date and end_date
    for i in range(num_months):
        month = start_date.month + i
        year = start_date.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1

        month_start = date(year, month, 1)

        # Determine month end
        if month == 12:
            next_month_year = year + 1
            next_month = 1
        else:
            next_month_year = year
            next_month = month + 1

        month_end = date(next_month_year, next_month, 1) - timedelta(days=1)

        # Ensure we don't go beyond the end_date
        month_end = min(month_end, end_date)

        # Get attendance for this month
        month_records = StudentAttendance.objects.filter(
            student=student,
            attendance_record__date__gte=month_start,
            attendance_record__date__lte=month_end
        )

        month_present = month_records.filter(status='PRESENT').count()
        month_absent = month_records.filter(status='ABSENT').count()
        month_late = month_records.filter(status='LATE').count()
        month_excused = month_records.filter(status='EXCUSED').count()

        month_total = month_present + month_absent + month_late + month_excused

        month_rate = 0
        if month_total > 0:
            month_rate = round((month_present / month_total) * 100, 1)

        month_name = month_start.strftime('%b %Y')

        monthly_data[month_name] = {
            'present': month_present,
            'absent': month_absent,
            'late': month_late,
            'excused': month_excused,
            'total': month_total,
            'rate': month_rate
        }

    # Get daily attendance data for chart
    daily_data = {}
    for record in attendance_records:
        date_str = record.attendance_record.date.strftime('%Y-%m-%d')

        daily_data[date_str] = {
            'date': record.attendance_record.date.strftime('%b %d'),
            'status': record.status,
            'className': record.attendance_record.classroom.name if record.attendance_record.classroom else 'Unknown',
            'color': {
                'PRESENT': 'success',
                'ABSENT': 'danger',
                'LATE': 'warning',
                'EXCUSED': 'info'
            }.get(record.status, 'secondary')
        }

    # Sort daily data by date
    daily_data = {k: daily_data[k] for k in sorted(daily_data.keys())}

    # Get classes the student is enrolled in
    enrolled_classes = ClassSubject.objects.filter(students=student)

    context = {
        'student': student,
        'attendance_records': attendance_records,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'total_records': total_records,
        'attendance_rate': attendance_rate,
        'start_date': start_date,
        'end_date': end_date,
        'monthly_data': monthly_data,
        'daily_data': daily_data,
        'enrolled_classes': enrolled_classes,
        # For charts
        'monthly_labels': json.dumps(list(monthly_data.keys())),
        'monthly_rates': json.dumps([data['rate'] for data in monthly_data.values()]),
        'status_counts': json.dumps([present_count, absent_count, late_count, excused_count]),
        'status_labels': json.dumps(['Present', 'Absent', 'Late', 'Excused']),
        'attendance_calendar': json.dumps([{
            'title': f"{data['status']} - {data['className']}",
            'start': date_str,
            'className': f"bg-{data['color']}"
        } for date_str, data in daily_data.items()]),
    }

    return render(request, 'dashboard/admin_student_attendance.html', context)

@user_passes_test(is_admin)
def admin_attendance_reports(request):
    """
    Generate and display various attendance reports
    """
    # Get filter parameters
    classroom_id = request.GET.get('classroom')
    report_type = request.GET.get('report_type', 'daily')  # daily, weekly, monthly
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = date.today()
    if not start_date:
        # Default to first day of current month
        start_date = date(today.year, today.month, 1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        # Default to today
        end_date = today
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get all classrooms for the filter
    classrooms = ClassRoom.objects.all()

    # Initialize report data
    report_data = []

    # Base queryset for attendance records
    base_query = AttendanceRecord.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    )

    # Apply classroom filter if selected
    if classroom_id:
        classroom = get_object_or_404(ClassRoom, id=classroom_id)
        base_query = base_query.filter(classroom=classroom)

    # Generate report based on type
    if report_type == 'daily':
        # Daily attendance report
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date)
            current_date += timedelta(days=1)

        for current_date in date_range:
            # Get records for this date
            date_records = base_query.filter(date=current_date)

            # Get attendance counts
            present_count = StudentAttendance.objects.filter(
                attendance_record__in=date_records,
                status='PRESENT'
            ).count()

            absent_count = StudentAttendance.objects.filter(
                attendance_record__in=date_records,
                status='ABSENT'
            ).count()

            late_count = StudentAttendance.objects.filter(
                attendance_record__in=date_records,
                status='LATE'
            ).count()

            excused_count = StudentAttendance.objects.filter(
                attendance_record__in=date_records,
                status='EXCUSED'
            ).count()

            total = present_count + absent_count + late_count + excused_count

            # Calculate attendance rate
            attendance_rate = 0
            if total > 0:
                attendance_rate = round((present_count / total) * 100, 1)

            # Add to report data
            report_data.append({
                'date': current_date,
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'excused': excused_count,
                'total': total,
                'attendance_rate': attendance_rate
            })

    elif report_type == 'weekly':
        # Weekly attendance report
        weeks = []
        current_date = start_date

        # Find the beginning of the week
        week_start = current_date - timedelta(days=current_date.weekday())

        while week_start <= end_date:
            week_end = week_start + timedelta(days=6)
            weeks.append((week_start, week_end))
            week_start = week_end + timedelta(days=1)

        for week_start, week_end in weeks:
            # Adjust dates to be within the requested range
            effective_start = max(week_start, start_date)
            effective_end = min(week_end, end_date)

            # Get records for this week
            week_records = base_query.filter(
                date__gte=effective_start,
                date__lte=effective_end
            )

            # Get attendance counts
            present_count = StudentAttendance.objects.filter(
                attendance_record__in=week_records,
                status='PRESENT'
            ).count()

            absent_count = StudentAttendance.objects.filter(
                attendance_record__in=week_records,
                status='ABSENT'
            ).count()

            late_count = StudentAttendance.objects.filter(
                attendance_record__in=week_records,
                status='LATE'
            ).count()

            excused_count = StudentAttendance.objects.filter(
                attendance_record__in=week_records,
                status='EXCUSED'
            ).count()

            total = present_count + absent_count + late_count + excused_count

            # Calculate attendance rate
            attendance_rate = 0
            if total > 0:
                attendance_rate = round((present_count / total) * 100, 1)

            # Add to report data
            report_data.append({
                'week_start': effective_start,
                'week_end': effective_end,
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'excused': excused_count,
                'total': total,
                'attendance_rate': attendance_rate
            })

    elif report_type == 'monthly':
        # Monthly attendance report
        months = []
        current_month_start = date(start_date.year, start_date.month, 1)

        while current_month_start <= end_date:
            # Calculate end of month
            if current_month_start.month == 12:
                next_month_year = current_month_start.year + 1
                next_month = 1
            else:
                next_month_year = current_month_start.year
                next_month = current_month_start.month + 1

            current_month_end = date(next_month_year, next_month, 1) - timedelta(days=1)
            months.append((current_month_start, current_month_end))

            # Move to next month
            current_month_start = date(next_month_year, next_month, 1)

        for month_start, month_end in months:
            # Adjust dates to be within the requested range
            effective_start = max(month_start, start_date)
            effective_end = min(month_end, end_date)

            # Get records for this month
            month_records = base_query.filter(
                date__gte=effective_start,
                date__lte=effective_end
            )

            # Get attendance counts
            present_count = StudentAttendance.objects.filter(
                attendance_record__in=month_records,
                status='PRESENT'
            ).count()

            absent_count = StudentAttendance.objects.filter(
                attendance_record__in=month_records,
                status='ABSENT'
            ).count()

            late_count = StudentAttendance.objects.filter(
                attendance_record__in=month_records,
                status='LATE'
            ).count()

            excused_count = StudentAttendance.objects.filter(
                attendance_record__in=month_records,
                status='EXCUSED'
            ).count()

            total = present_count + absent_count + late_count + excused_count

            # Calculate attendance rate
            attendance_rate = 0
            if total > 0:
                attendance_rate = round((present_count / total) * 100, 1)

            # Add to report data
            report_data.append({
                'month_start': effective_start,
                'month_end': effective_end,
                'month_name': effective_start.strftime('%B %Y'),
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'excused': excused_count,
                'total': total,
                'attendance_rate': attendance_rate
            })

    # Calculate overall attendance rate
    total_present = sum(item['present'] for item in report_data)
    total_attendance = sum(item['total'] for item in report_data)

    overall_attendance_rate = 0
    if total_attendance > 0:
        overall_attendance_rate = round((total_present / total_attendance) * 100, 1)

    # Prepare chart data based on report type
    if report_type == 'daily':
        labels = [item['date'].strftime('%b %d') for item in report_data]
    elif report_type == 'weekly':
        labels = [f"{item['week_start'].strftime('%b %d')} - {item['week_end'].strftime('%b %d')}" for item in report_data]
    else:  # monthly
        labels = [item['month_name'] for item in report_data]

    attendance_rates = [item['attendance_rate'] for item in report_data]

    context = {
        'classrooms': classrooms,
        'selected_classroom': classroom_id,
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'report_data': report_data,
        'overall_attendance_rate': overall_attendance_rate,
        # For charts
        'labels': json.dumps(labels),
        'attendance_rates': json.dumps(attendance_rates),
    }

    return render(request, 'dashboard/admin_attendance_reports.html', context)

# Admin Academic Performance Tracking Views
@user_passes_test(is_admin)
def admin_performance_overview(request):
    """
    Overview of academic performance across the school
    """
    # Get filter parameters
    term = request.GET.get('term')
    grade_level = request.GET.get('grade_level')

    # Base query for grades
    grades_query = Grade.objects.all()

    # Apply filters if provided
    if term:
        grades_query = grades_query.filter(term=term)

    # Get all grade levels and terms for filter dropdowns
    all_grade_levels = ClassRoom.objects.values_list('grade_level', flat=True).distinct()
    all_terms = Grade.objects.values_list('term', flat=True).distinct()

    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"All grade levels: {list(all_grade_levels)}")
    logger.debug(f"All terms: {list(all_terms)}")

    # Calculate overall grade statistics
    grade_distribution = {
        'A': grades_query.filter(score__gte=90).count(),
        'B': grades_query.filter(score__gte=80, score__lt=90).count(),
        'C': grades_query.filter(score__gte=70, score__lt=80).count(),
        'D': grades_query.filter(score__gte=60, score__lt=70).count(),
        'F': grades_query.filter(score__lt=60).count()
    }

    # Calculate total grades and average
    total_grades = sum(grade_distribution.values())
    average_score = 0

    if total_grades > 0:
        average_score = round(grades_query.aggregate(avg=Avg('score'))['avg'] or 0, 1)

    # Get performance by class
    classes = ClassRoom.objects.all()
    class_performance = []

    for classroom in classes:
        # Apply grade level filter
        if grade_level and str(classroom.grade_level) != grade_level:
            continue

        # Get students in this class
        students = classroom.get_students()

        # Skip empty classes
        if not students:
            continue

        # Get grades for students in this class
        class_grades = grades_query.filter(student__in=students)

        # Calculate average score
        avg_score = class_grades.aggregate(avg=Avg('score'))['avg']

        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        # Get grade distribution for this class
        class_distribution = {
            'A': class_grades.filter(score__gte=90).count(),
            'B': class_grades.filter(score__gte=80, score__lt=90).count(),
            'C': class_grades.filter(score__gte=70, score__lt=80).count(),
            'D': class_grades.filter(score__gte=60, score__lt=70).count(),
            'F': class_grades.filter(score__lt=60).count()
        }

        # Calculate pass rate
        total_class_grades = sum(class_distribution.values())
        if total_class_grades > 0:
            pass_rate = round(
                (class_distribution['A'] + class_distribution['B'] +
                 class_distribution['C'] + class_distribution['D']) / total_class_grades * 100, 1
            )
        else:
            pass_rate = 0

        class_performance.append({
            'classroom': classroom,
            'avg_score': avg_score,
            'distribution': class_distribution,
            'pass_rate': pass_rate,
            'student_count': students.count(),
            'grade_count': total_class_grades
        })

    # Sort classes by average score (descending)
    class_performance.sort(key=lambda x: x['avg_score'], reverse=True)

    # Get performance by subject
    subjects = Subject.objects.all()
    subject_performance = []

    for subject in subjects:
        # Get class subjects for this subject
        class_subjects = ClassSubject.objects.filter(subject=subject)

        # Get grades for this subject
        subject_grades = grades_query.filter(class_subject__in=class_subjects)

        # Calculate average score
        avg_score = subject_grades.aggregate(avg=Avg('score'))['avg']

        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        # Get grade distribution for this subject
        subject_distribution = {
            'A': subject_grades.filter(score__gte=90).count(),
            'B': subject_grades.filter(score__gte=80, score__lt=90).count(),
            'C': subject_grades.filter(score__gte=70, score__lt=80).count(),
            'D': subject_grades.filter(score__gte=60, score__lt=70).count(),
            'F': subject_grades.filter(score__lt=60).count()
        }

        # Calculate pass rate
        total_subject_grades = sum(subject_distribution.values())
        if total_subject_grades > 0:
            pass_rate = round(
                (subject_distribution['A'] + subject_distribution['B'] +
                 subject_distribution['C'] + subject_distribution['D']) / total_subject_grades * 100, 1
            )
        else:
            pass_rate = 0

        subject_performance.append({
            'subject': subject,
            'avg_score': avg_score,
            'distribution': subject_distribution,
            'pass_rate': pass_rate,
            'grade_count': total_subject_grades
        })

    # Sort subjects by average score (descending)
    subject_performance.sort(key=lambda x: x['avg_score'], reverse=True)

    # Get top 10 students by average score
    students = Student.objects.all()
    student_performance = []

    for student in students:
        # Get grades for this student
        student_grades = grades_query.filter(student=student)

        # Skip students with no grades
        if not student_grades.exists():
            continue

        # Calculate average score
        avg_score = student_grades.aggregate(avg=Avg('score'))['avg']

        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        # Get grade distribution for this student
        student_distribution = {
            'A': student_grades.filter(score__gte=90).count(),
            'B': student_grades.filter(score__gte=80, score__lt=90).count(),
            'C': student_grades.filter(score__gte=70, score__lt=80).count(),
            'D': student_grades.filter(score__gte=60, score__lt=70).count(),
            'F': student_grades.filter(score__lt=60).count()
        }

        student_performance.append({
            'student': student,
            'avg_score': avg_score,
            'distribution': student_distribution,
            'grade_count': student_grades.count()
        })

    # Sort students by average score (descending) and get top 10
    student_performance.sort(key=lambda x: x['avg_score'], reverse=True)
    top_students = student_performance[:10]

    context = {
        'grade_distribution': grade_distribution,
        'total_grades': total_grades,
        'average_score': average_score,
        'class_performance': class_performance,
        'subject_performance': subject_performance,
        'top_students': top_students,
        'all_grade_levels': all_grade_levels,
        'all_terms': all_terms,
        'selected_term': term,
        'selected_grade_level': grade_level,
        # For charts - use DjangoJSONEncoder to handle Decimal values
        'grade_labels': json.dumps(list(grade_distribution.keys()), cls=DjangoJSONEncoder),
        'grade_counts': json.dumps(list(grade_distribution.values()), cls=DjangoJSONEncoder),
        'class_labels': json.dumps([c['classroom'].name for c in class_performance], cls=DjangoJSONEncoder),
        'class_scores': json.dumps([c['avg_score'] for c in class_performance], cls=DjangoJSONEncoder),
        'subject_labels': json.dumps([s['subject'].name for s in subject_performance], cls=DjangoJSONEncoder),
        'subject_scores': json.dumps([s['avg_score'] for s in subject_performance], cls=DjangoJSONEncoder),
    }

    return render(request, 'dashboard/admin_performance_overview.html', context)

@user_passes_test(is_admin)
def admin_class_performance(request, class_id):
    """
    Detailed performance view for a specific class
    """
    classroom = get_object_or_404(ClassRoom, id=class_id)

    # Get filter parameters
    term = request.GET.get('term')
    subject_id = request.GET.get('subject')

    # Get students in this class
    students = classroom.get_students()

    # Get class subjects for this class
    class_subjects = ClassSubject.objects.filter(classroom=classroom)

    # Base query for grades
    grades_query = Grade.objects.filter(
        student__in=students,
        class_subject__in=class_subjects
    )

    # Apply filters if provided
    if term:
        grades_query = grades_query.filter(term=term)

    if subject_id:
        class_subject = get_object_or_404(ClassSubject, id=subject_id)
        grades_query = grades_query.filter(class_subject=class_subject)

    # Get all terms for filter dropdown
    all_terms = grades_query.values_list('term', flat=True).distinct()

    # Calculate overall class statistics
    class_average = grades_query.aggregate(avg=Avg('score'))['avg']
    if class_average is not None:
        class_average = round(class_average, 1)
    else:
        class_average = 0

    # Calculate grade distribution
    grade_distribution = {
        'A': grades_query.filter(score__gte=90).count(),
        'B': grades_query.filter(score__gte=80, score__lt=90).count(),
        'C': grades_query.filter(score__gte=70, score__lt=80).count(),
        'D': grades_query.filter(score__gte=60, score__lt=70).count(),
        'F': grades_query.filter(score__lt=60).count()
    }

    # Calculate pass rate
    total_grades = sum(grade_distribution.values())
    pass_rate = 0
    if total_grades > 0:
        pass_rate = round(
            (grade_distribution['A'] + grade_distribution['B'] +
             grade_distribution['C'] + grade_distribution['D']) / total_grades * 100, 1
        )

    # Calculate performance by subject
    subject_performance = []
    for class_subject in class_subjects:
        # Get grades for this subject
        subject_grades = grades_query.filter(class_subject=class_subject)

        # Calculate average score
        avg_score = subject_grades.aggregate(avg=Avg('score'))['avg']

        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        # Get grade distribution for this subject
        subject_distribution = {
            'A': subject_grades.filter(score__gte=90).count(),
            'B': subject_grades.filter(score__gte=80, score__lt=90).count(),
            'C': subject_grades.filter(score__gte=70, score__lt=80).count(),
            'D': subject_grades.filter(score__gte=60, score__lt=70).count(),
            'F': subject_grades.filter(score__lt=60).count()
        }

        # Calculate pass rate
        total_subject_grades = sum(subject_distribution.values())
        subject_pass_rate = 0
        if total_subject_grades > 0:
            subject_pass_rate = round(
                (subject_distribution['A'] + subject_distribution['B'] +
                 subject_distribution['C'] + subject_distribution['D']) / total_subject_grades * 100, 1
            )

        subject_performance.append({
            'subject': class_subject.subject,
            'class_subject': class_subject,
            'avg_score': avg_score,
            'distribution': subject_distribution,
            'pass_rate': subject_pass_rate,
            'grade_count': total_subject_grades
        })

    # Sort subjects by average score (descending)
    subject_performance.sort(key=lambda x: x['avg_score'], reverse=True)

    # Calculate performance by student
    student_performance = []
    for student in students:
        # Get grades for this student
        student_grades = grades_query.filter(student=student)

        # Skip students with no grades matching the filters
        if not student_grades.exists():
            continue

        # Calculate average score
        avg_score = student_grades.aggregate(avg=Avg('score'))['avg']

        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        # Get subject-wise performance
        student_subjects = {}
        for class_subject in class_subjects:
            subject_grade = student_grades.filter(class_subject=class_subject).first()

            if subject_grade:
                student_subjects[class_subject.subject.name] = subject_grade.score
            else:
                student_subjects[class_subject.subject.name] = None

        student_performance.append({
            'student': student,
            'avg_score': avg_score,
            'subjects': student_subjects,
            'grade_count': student_grades.count()
        })

    # Sort students by average score (descending)
    student_performance.sort(key=lambda x: x['avg_score'], reverse=True)

    # Get assignment statistics
    assignments = Assignment.objects.filter(class_subject__in=class_subjects)

    # Apply term filter if provided
    if term:
        assignments = assignments.filter(term=term)

    # Apply subject filter if provided
    if subject_id:
        assignments = assignments.filter(class_subject=class_subject)

    assignment_stats = []
    for assignment in assignments:
        # Get submissions for this assignment
        submissions = StudentSubmission.objects.filter(
            assignment=assignment,
            student__in=students
        )

        # Get grades for this assignment
        assignment_grades = Grade.objects.filter(
            assignment=assignment,
            student__in=students
        )

        # Calculate statistics
        submission_count = submissions.count()
        graded_count = assignment_grades.count()
        avg_score = assignment_grades.aggregate(avg=Avg('score'))['avg']

        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        assignment_stats.append({
            'assignment': assignment,
            'submission_count': submission_count,
            'graded_count': graded_count,
            'avg_score': avg_score,
            'possible_submissions': students.count()
        })

    # Sort assignments by date (descending)
    assignment_stats.sort(key=lambda x: x['assignment'].due_date, reverse=True)

    context = {
        'classroom': classroom,
        'students': students,
        'class_subjects': class_subjects,
        'class_average': class_average,
        'grade_distribution': grade_distribution,
        'pass_rate': pass_rate,
        'total_grades': total_grades,
        'subject_performance': subject_performance,
        'student_performance': student_performance,
        'assignment_stats': assignment_stats,
        'all_terms': all_terms,
        'selected_term': term,
        'selected_subject': subject_id,
        # For charts
        'grade_labels': json.dumps(list(grade_distribution.keys())),
        'grade_counts': json.dumps(list(grade_distribution.values())),
        'subject_labels': json.dumps([s['subject'].name for s in subject_performance]),
        'subject_scores': json.dumps([s['avg_score'] for s in subject_performance]),
        'student_labels': json.dumps([s['student'].user.get_full_name() for s in student_performance]),
        'student_scores': json.dumps([s['avg_score'] for s in student_performance]),
    }

    return render(request, 'dashboard/admin_class_performance.html', context)

@user_passes_test(is_admin)
def admin_student_performance(request, student_id):
    """
    Detailed performance view for a specific student
    """
    student = get_object_or_404(Student, id=student_id)

    # Get filter parameters
    term = request.GET.get('term')
    subject_id = request.GET.get('subject')

    # Base query for grades
    grades_query = Grade.objects.filter(student=student)

    # Apply filters if provided
    if term:
        grades_query = grades_query.filter(term=term)

    if subject_id:
        subject = get_object_or_404(Subject, id=subject_id)
        grades_query = grades_query.filter(class_subject__subject=subject)

    # Get all terms and subjects for filter dropdowns
    all_terms = grades_query.values_list('term', flat=True).distinct()
    enrolled_subjects = ClassSubject.objects.filter(students=student)
    all_subjects = Subject.objects.filter(
        id__in=enrolled_subjects.values_list('subject_id', flat=True)
    )

    # Calculate overall statistics
    overall_average = grades_query.aggregate(avg=Avg('score'))['avg']
    if overall_average is not None:
        overall_average = round(overall_average, 1)
    else:
        overall_average = 0

    # Calculate grade distribution
    grade_distribution = {
        'A': grades_query.filter(score__gte=90).count(),
        'B': grades_query.filter(score__gte=80, score__lt=90).count(),
        'C': grades_query.filter(score__gte=70, score__lt=80).count(),
        'D': grades_query.filter(score__gte=60, score__lt=70).count(),
        'F': grades_query.filter(score__lt=60).count()
    }

    # Calculate performance by subject
    subject_performance = []
    for subject in all_subjects:
        # Get grades for this subject
        subject_grades = grades_query.filter(class_subject__subject=subject)

        # Skip subjects with no grades matching the filters
        if not subject_grades.exists():
            continue

        # Calculate average score
        avg_score = subject_grades.aggregate(avg=Avg('score'))['avg']

        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        subject_performance.append({
            'subject': subject,
            'avg_score': avg_score,
            'grade_count': subject_grades.count(),
            'highest_score': subject_grades.aggregate(max=Max('score'))['max'] or 0,
            'lowest_score': subject_grades.aggregate(min=Min('score'))['min'] or 0
        })

    # Sort subjects by average score (descending)
    subject_performance.sort(key=lambda x: x['avg_score'], reverse=True)

    # Get performance by term
    term_performance = []
    for term_value in all_terms:
        # Get grades for this term
        term_grades = grades_query.filter(term=term_value)

        # Calculate average score
        avg_score = term_grades.aggregate(avg=Avg('score'))['avg']

        if avg_score is not None:
            avg_score = round(avg_score, 1)
        else:
            avg_score = 0

        term_performance.append({
            'term': term_value,
            'avg_score': avg_score,
            'grade_count': term_grades.count(),
            'highest_score': term_grades.aggregate(max=Max('score'))['max'] or 0,
            'lowest_score': term_grades.aggregate(min=Min('score'))['min'] or 0
        })

    # Sort terms (this depends on your term format)
    # For this example, assuming terms are in format "Term X YYYY" or "Semester X YYYY"
    term_performance.sort(key=lambda x: x['term'])

    # Get all assignments for this student
    assignments = Assignment.objects.filter(
        class_subject__in=enrolled_subjects
    ).order_by('-due_date')

    # Apply term filter if provided
    if term:
        assignments = assignments.filter(term=term)

    # Apply subject filter if provided
    if subject_id:
        assignments = assignments.filter(class_subject__subject=subject)

    # Get submissions and grades for assignments
    assignment_performance = []
    for assignment in assignments:
        # Get submission for this assignment
        submission = StudentSubmission.objects.filter(
            assignment=assignment,
            student=student
        ).first()

        # Get grade for this assignment
        grade = Grade.objects.filter(
            assignment=assignment,
            student=student
        ).first()

        assignment_performance.append({
            'assignment': assignment,
            'submission': submission,
            'grade': grade
        })

    # Get attendance statistics
    attendance_records = StudentAttendance.objects.filter(student=student)

    attendance_stats = {
        'present': attendance_records.filter(status='PRESENT').count(),
        'absent': attendance_records.filter(status='ABSENT').count(),
        'late': attendance_records.filter(status='LATE').count(),
        'excused': attendance_records.filter(status='EXCUSED').count()
    }

    total_attendance = sum(attendance_stats.values())
    if total_attendance > 0:
        attendance_stats['attendance_rate'] = round((attendance_stats['present'] / total_attendance) * 100, 1)
    else:
        attendance_stats['attendance_rate'] = 0

    # Get recent report cards
    report_cards = ReportCard.objects.filter(student=student).order_by('-generated_date')

    context = {
        'student': student,
        'overall_average': overall_average,
        'grade_distribution': grade_distribution,
        'subject_performance': subject_performance,
        'term_performance': term_performance,
        'assignment_performance': assignment_performance,
        'attendance_stats': attendance_stats,
        'report_cards': report_cards,
        'all_terms': all_terms,
        'all_subjects': all_subjects,
        'selected_term': term,
        'selected_subject': subject_id,
        # For charts
        'grade_labels': json.dumps(list(grade_distribution.keys())),
        'grade_counts': json.dumps(list(grade_distribution.values())),
        'subject_labels': json.dumps([s['subject'].name for s in subject_performance]),
        'subject_scores': json.dumps([s['avg_score'] for s in subject_performance]),
        'term_labels': json.dumps([t['term'] for t in term_performance]),
        'term_scores': json.dumps([t['avg_score'] for t in term_performance]),
        'attendance_labels': json.dumps(['Present', 'Absent', 'Late', 'Excused']),
        'attendance_counts': json.dumps([
            attendance_stats['present'],
            attendance_stats['absent'],
            attendance_stats['late'],
            attendance_stats['excused']
        ]),
    }

    return render(request, 'dashboard/admin_student_performance.html', context)

@user_passes_test(is_admin)
def admin_performance_comparison(request):
    """
    Compare performance between classes, subjects, or terms
    """
    # Get filter parameters
    comparison_type = request.GET.get('comparison_type', 'classes')
    term = request.GET.get('term')
    grade_level = request.GET.get('grade_level')

    # Base query for grades
    grades_query = Grade.objects.all()

    # Apply term filter if provided
    if term:
        grades_query = grades_query.filter(term=term)

    # Get all grade levels and terms for filter dropdowns
    all_grade_levels = ClassRoom.objects.values_list('grade_level', flat=True).distinct()
    all_terms = Grade.objects.values_list('term', flat=True).distinct()

    comparison_data = []
    labels = []
    avg_scores = []
    pass_rates = []

    if comparison_type == 'classes':
        # Compare performance between classes
        classes = ClassRoom.objects.all()

        # Apply grade level filter if provided
        if grade_level:
            classes = classes.filter(grade_level=grade_level)

        for classroom in classes:
            # Get students in this class
            students = classroom.get_students()

            # Skip empty classes
            if not students:
                continue

            # Get grades for students in this class
            class_grades = grades_query.filter(student__in=students)

            # Skip if no grades
            if not class_grades.exists():
                continue

            # Calculate average score
            avg_score = class_grades.aggregate(avg=Avg('score'))['avg']

            if avg_score is not None:
                avg_score = round(avg_score, 1)
            else:
                avg_score = 0

            # Calculate pass rate
            pass_count = class_grades.filter(score__gte=60).count()
            total_count = class_grades.count()

            pass_rate = 0
            if total_count > 0:
                pass_rate = round((pass_count / total_count) * 100, 1)

            comparison_data.append({
                'name': classroom.name,
                'avg_score': avg_score,
                'pass_rate': pass_rate,
                'total_grades': total_count
            })

            labels.append(classroom.name)
            avg_scores.append(avg_score)
            pass_rates.append(pass_rate)

    elif comparison_type == 'subjects':
        # Compare performance between subjects
        subjects = Subject.objects.all()

        for subject in subjects:
            # Get grades for this subject
            subject_grades = grades_query.filter(class_subject__subject=subject)

            # Skip if no grades
            if not subject_grades.exists():
                continue

            # Calculate average score
            avg_score = subject_grades.aggregate(avg=Avg('score'))['avg']

            if avg_score is not None:
                avg_score = round(avg_score, 1)
            else:
                avg_score = 0

            # Calculate pass rate
            pass_count = subject_grades.filter(score__gte=60).count()
            total_count = subject_grades.count()

            pass_rate = 0
            if total_count > 0:
                pass_rate = round((pass_count / total_count) * 100, 1)

            comparison_data.append({
                'name': subject.name,
                'avg_score': avg_score,
                'pass_rate': pass_rate,
                'total_grades': total_count
            })

            labels.append(subject.name)
            avg_scores.append(avg_score)
            pass_rates.append(pass_rate)

    elif comparison_type == 'terms':
        # Compare performance between terms
        terms = all_terms

        for term_value in terms:
            # Get grades for this term
            term_grades = grades_query.filter(term=term_value)

            # Skip if no grades
            if not term_grades.exists():
                continue

            # Apply grade level filter if provided
            if grade_level:
                # Find classrooms with this grade level
                classrooms = ClassRoom.objects.filter(grade_level=grade_level)
                # Get students in these classrooms
                students = Student.objects.filter(classsubject__classroom__in=classrooms).distinct()
                # Filter grades by these students
                term_grades = term_grades.filter(student__in=students)

            # Calculate average score
            avg_score = term_grades.aggregate(avg=Avg('score'))['avg']

            if avg_score is not None:
                avg_score = round(avg_score, 1)
            else:
                avg_score = 0

            # Calculate pass rate
            pass_count = term_grades.filter(score__gte=60).count()
            total_count = term_grades.count()

            pass_rate = 0
            if total_count > 0:
                pass_rate = round((pass_count / total_count) * 100, 1)

            comparison_data.append({
                'name': term_value,
                'avg_score': avg_score,
                'pass_rate': pass_rate,
                'total_grades': total_count
            })

            labels.append(term_value)
            avg_scores.append(avg_score)
            pass_rates.append(pass_rate)

    # Sort comparison data by average score (descending)
    comparison_data.sort(key=lambda x: x['avg_score'], reverse=True)

    context = {
        'comparison_type': comparison_type,
        'comparison_data': comparison_data,
        'all_grade_levels': all_grade_levels,
        'all_terms': all_terms,
        'selected_term': term,
        'selected_grade_level': grade_level,
        # For charts - use DjangoJSONEncoder to handle Decimal values
        'labels': json.dumps(labels, cls=DjangoJSONEncoder),
        'avg_scores': json.dumps(avg_scores, cls=DjangoJSONEncoder),
        'pass_rates': json.dumps(pass_rates, cls=DjangoJSONEncoder),
    }

    return render(request, 'dashboard/admin_performance_comparison.html', context)

@user_passes_test(is_admin)
def admin_report_insights(request):
    """
    Provides automated insights from report cards for administrators
    """
    # Get filter parameters
    term = request.GET.get('term')
    grade_level = request.GET.get('grade_level')
    insight_type = request.GET.get('insight_type', 'at_risk')  # at_risk, improvement, decline
    min_reports = int(request.GET.get('min_reports', 2))  # Minimum number of reports required for comparison

    # Get all report cards
    report_cards = ReportCard.objects.all().order_by('-generated_date')

    # Apply filters
    if term:
        report_cards = report_cards.filter(term=term)

    if grade_level:
        report_cards = report_cards.filter(student__grade__grade_level=grade_level)

    # Get all terms and grade levels for filters
    all_terms = ReportCard.objects.values_list('term', flat=True).distinct()
    all_grade_levels = ClassRoom.objects.values_list('grade_level', flat=True).distinct()

    # Maps to store the latest report card per student and term
    student_term_latest_report = {}
    students_with_multiple_reports = set()

    # Identify students with multiple report cards
    for report in report_cards:
        key = (report.student.id, report.term)
        if key not in student_term_latest_report:
            student_term_latest_report[key] = report
        elif report.generated_date > student_term_latest_report[key].generated_date:
            student_term_latest_report[key] = report

        # Track students with multiple terms
        if report.student.id in [k[0] for k in student_term_latest_report.keys()]:
            students_with_multiple_reports.add(report.student.id)

    # Get latest report cards for each student (for at-risk analysis)
    latest_reports = {}
    for (student_id, term), report in student_term_latest_report.items():
        if student_id not in latest_reports or report.generated_date > latest_reports[student_id].generated_date:
            latest_reports[student_id] = report

    # Analysis results containers
    at_risk_students = []
    improved_students = []
    declined_students = []

    # At-risk students analysis
    for student_id, report in latest_reports.items():
        if report.average_score < 60:  # Students with failing overall average
            at_risk_students.append({
                'student': report.student,
                'report_card': report,
                'avg_score': report.average_score,
                'attendance_rate': (report.days_present / (report.days_present + report.days_absent + report.days_late)) * 100 if (report.days_present + report.days_absent + report.days_late) > 0 else 0,
                'subjects_failed': Grade.objects.filter(student=report.student, score__lt=60).count(),
                'risk_level': 'high' if report.average_score < 50 else 'medium'
            })

    # Sort at-risk students by score (ascending)
    at_risk_students.sort(key=lambda x: x['avg_score'])

    # Create a map of student scores by term for performance trend analysis
    student_term_scores = {}
    for (student_id, term), report in student_term_latest_report.items():
        if student_id not in student_term_scores:
            student_term_scores[student_id] = {}
        student_term_scores[student_id][term] = report.average_score

    # Analyze students with multiple report cards for improvement/decline
    for student_id in students_with_multiple_reports:
        student_reports = [(term, report) for (sid, term), report in student_term_latest_report.items() if sid == student_id]

        # Skip if too few reports for comparison
        if len(student_reports) < min_reports:
            continue

        # Sort reports by term (this assumes terms can be sorted lexicographically - adjust as needed)
        student_reports.sort(key=lambda x: x[0])

        # Calculate improvement/decline
        scores = [report.average_score for _, report in student_reports]
        latest_report = student_reports[-1][1]

        # Only proceed if we have enough data points
        if len(scores) >= 2:
            initial_score = scores[0]
            final_score = scores[-1]
            score_change = final_score - initial_score

            # Determine if student has improved or declined
            if score_change >= 10:  # Significant improvement
                improved_students.append({
                    'student': latest_report.student,
                    'report_card': latest_report,
                    'initial_score': initial_score,
                    'final_score': final_score,
                    'change': score_change,
                    'terms_analyzed': len(scores),
                    'trend': scores
                })
            elif score_change <= -10:  # Significant decline
                declined_students.append({
                    'student': latest_report.student,
                    'report_card': latest_report,
                    'initial_score': initial_score,
                    'final_score': final_score,
                    'change': score_change,
                    'terms_analyzed': len(scores),
                    'trend': scores
                })

    # Sort improvement/decline lists
    improved_students.sort(key=lambda x: x['change'], reverse=True)
    declined_students.sort(key=lambda x: x['change'])

    # Calculate overall statistics
    total_student_count = Student.objects.count()
    at_risk_percentage = (len(at_risk_students) / total_student_count) * 100 if total_student_count > 0 else 0

    # Get class-level insights
    class_insights = []
    classrooms = ClassRoom.objects.all()

    for classroom in classrooms:
        class_reports = report_cards.filter(student__grade=classroom)
        if not class_reports.exists():
            continue

        class_avg = class_reports.aggregate(avg=Avg('average_score'))['avg'] or 0

        # Count students below threshold in this class
        below_threshold_count = sum(1 for report in class_reports if report.average_score < 60)
        total_students = classroom.get_students().count()

        if total_students > 0:
            class_insights.append({
                'classroom': classroom,
                'average_score': round(class_avg, 1),
                'at_risk_count': below_threshold_count,
                'at_risk_percentage': (below_threshold_count / total_students) * 100,
                'total_students': total_students
            })

    # Sort class insights by at-risk percentage (descending)
    class_insights.sort(key=lambda x: x['at_risk_percentage'], reverse=True)

    # Subject-level insights
    subject_insights = []
    for subject in Subject.objects.all():
        # Get grades for this subject
        subject_grades = Grade.objects.filter(class_subject__subject=subject)
        if not subject_grades.exists():
            continue

        avg_score = subject_grades.aggregate(avg=Avg('score'))['avg'] or 0
        fail_count = subject_grades.filter(score__lt=60).count()
        total_grades = subject_grades.count()

        if total_grades > 0:
            subject_insights.append({
                'subject': subject,
                'average_score': round(avg_score, 1),
                'fail_count': fail_count,
                'fail_percentage': (fail_count / total_grades) * 100,
                'total_grades': total_grades
            })

    # Sort subject insights by fail percentage (descending)
    subject_insights.sort(key=lambda x: x['fail_percentage'], reverse=True)

    # Generate chart data
    at_risk_counts = [0, 0, 0]  # high, medium, low risk
    for student in at_risk_students:
        if student['risk_level'] == 'high':
            at_risk_counts[0] += 1
        elif student['risk_level'] == 'medium':
            at_risk_counts[1] += 1
        else:
            at_risk_counts[2] += 1

    context = {
        'at_risk_students': at_risk_students,
        'improved_students': improved_students,
        'declined_students': declined_students,
        'class_insights': class_insights,
        'subject_insights': subject_insights,
        'all_terms': all_terms,
        'all_grade_levels': all_grade_levels,
        'selected_term': term,
        'selected_grade_level': grade_level,
        'selected_insight_type': insight_type,
        'at_risk_percentage': round(at_risk_percentage, 1),
        'at_risk_count': len(at_risk_students),
        'improved_count': len(improved_students),
        'declined_count': len(declined_students),
        'total_students': total_student_count,
        'at_risk_counts': json.dumps(at_risk_counts),
        'class_labels': json.dumps([insight['classroom'].name for insight in class_insights[:10]]),
        'class_risks': json.dumps([insight['at_risk_percentage'] for insight in class_insights[:10]]),
        'subject_labels': json.dumps([insight['subject'].name for insight in subject_insights[:10]]),
        'subject_fails': json.dumps([insight['fail_percentage'] for insight in subject_insights[:10]]),
    }

    return render(request, 'dashboard/admin_report_insights.html', context)

@user_passes_test(is_admin)
def admin_performance_trends(request):
    """
    Analyze performance trends over time
    """
    # Get filter parameters
    trend_type = request.GET.get('trend_type', 'term')  # term, monthly, yearly
    subject_id = request.GET.get('subject')
    grade_level = request.GET.get('grade_level')

    # Base query for grades
    grades_query = Grade.objects.all()

    # Apply subject filter if provided
    if subject_id:
        subject = get_object_or_404(Subject, id=subject_id)
        grades_query = grades_query.filter(class_subject__subject=subject)

    # Apply grade level filter if provided
    if grade_level:
        grades_query = grades_query.filter(
            student__grade__grade_level=grade_level
        )

    # Get all subjects and grade levels for filter dropdowns
    all_subjects = Subject.objects.all()
    all_grade_levels = ClassRoom.objects.values_list('grade_level', flat=True).distinct()

    trend_data = []
    labels = []
    avg_scores = []
    pass_rates = []

    if trend_type == 'term':
        # Analyze trend by term
        terms = grades_query.values_list('term', flat=True).distinct()

        for term in terms:
            # Get grades for this term
            term_grades = grades_query.filter(term=term)

            # Calculate average score
            avg_score = term_grades.aggregate(avg=Avg('score'))['avg']

            if avg_score is not None:
                avg_score = round(avg_score, 1)
            else:
                avg_score = 0

            # Calculate pass rate
            pass_count = term_grades.filter(score__gte=60).count()
            total_count = term_grades.count()

            pass_rate = 0
            if total_count > 0:
                pass_rate = round((pass_count / total_count) * 100, 1)

            trend_data.append({
                'period': term,
                'avg_score': avg_score,
                'pass_rate': pass_rate,
                'total_grades': total_count,
                'a_count': term_grades.filter(score__gte=90).count(),
                'b_count': term_grades.filter(score__gte=80, score__lt=90).count(),
                'c_count': term_grades.filter(score__gte=70, score__lt=80).count(),
                'd_count': term_grades.filter(score__gte=60, score__lt=70).count(),
                'f_count': term_grades.filter(score__lt=60).count()
            })

            labels.append(term)
            avg_scores.append(avg_score)
            pass_rates.append(pass_rate)

    elif trend_type == 'monthly':
        # Analyze trend by month
        # Group grades by month
        grades_by_month = grades_query.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            avg_score=Avg('score'),
            total_count=Count('id'),
            pass_count=Count(Case(When(score__gte=60, then=1))),
            a_count=Count(Case(When(score__gte=90, then=1))),
            b_count=Count(Case(When(score__gte=80, score__lt=90, then=1))),
            c_count=Count(Case(When(score__gte=70, score__lt=80, then=1))),
            d_count=Count(Case(When(score__gte=60, score__lt=70, then=1))),
            f_count=Count(Case(When(score__lt=60, then=1)))
        ).order_by('month')

        for month_data in grades_by_month:
            # Skip months with no data
            if not month_data['month']:
                continue

            # Format month
            month_name = month_data['month'].strftime('%b %Y')

            # Calculate pass rate
            pass_rate = 0
            if month_data['total_count'] > 0:
                pass_rate = round((month_data['pass_count'] / month_data['total_count']) * 100, 1)

            trend_data.append({
                'period': month_name,
                'avg_score': round(month_data['avg_score'], 1) if month_data['avg_score'] else 0,
                'pass_rate': pass_rate,
                'total_grades': month_data['total_count'],
                'a_count': month_data['a_count'],
                'b_count': month_data['b_count'],
                'c_count': month_data['c_count'],
                'd_count': month_data['d_count'],
                'f_count': month_data['f_count']
            })

            labels.append(month_name)
            avg_scores.append(round(month_data['avg_score'], 1) if month_data['avg_score'] else 0)
            pass_rates.append(pass_rate)

    elif trend_type == 'yearly':
        # Analyze trend by year
        # Extract year from created_at
        grades_by_year = grades_query.annotate(
            year=ExtractYear('created_at')
        ).values('year').annotate(
            avg_score=Avg('score'),
            total_count=Count('id'),
            pass_count=Count(Case(When(score__gte=60, then=1))),
            a_count=Count(Case(When(score__gte=90, then=1))),
            b_count=Count(Case(When(score__gte=80, score__lt=90, then=1))),
            c_count=Count(Case(When(score__gte=70, score__lt=80, then=1))),
            d_count=Count(Case(When(score__gte=60, score__lt=70, then=1))),
            f_count=Count(Case(When(score__lt=60, then=1)))
        ).order_by('year')

        for year_data in grades_by_year:
            # Skip years with no data
            if not year_data['year']:
                continue

            # Calculate pass rate
            pass_rate = 0
            if year_data['total_count'] > 0:
                pass_rate = round((year_data['pass_count'] / year_data['total_count']) * 100, 1)

            trend_data.append({
                'period': str(year_data['year']),
                'avg_score': round(year_data['avg_score'], 1) if year_data['avg_score'] else 0,
                'pass_rate': pass_rate,
                'total_grades': year_data['total_count'],
                'a_count': year_data['a_count'],
                'b_count': year_data['b_count'],
                'c_count': year_data['c_count'],
                'd_count': year_data['d_count'],
                'f_count': year_data['f_count']
            })

            labels.append(str(year_data['year']))
            avg_scores.append(round(year_data['avg_score'], 1) if year_data['avg_score'] else 0)
            pass_rates.append(pass_rate)

    # Additional data for stacked chart
    a_counts = [item['a_count'] for item in trend_data]
    b_counts = [item['b_count'] for item in trend_data]
    c_counts = [item['c_count'] for item in trend_data]
    d_counts = [item['d_count'] for item in trend_data]
    f_counts = [item['f_count'] for item in trend_data]

    context = {
        'trend_type': trend_type,
        'trend_data': trend_data,
        'all_subjects': all_subjects,
        'all_grade_levels': all_grade_levels,
        'selected_subject': subject_id,
        'selected_grade_level': grade_level,
        # For charts - use DjangoJSONEncoder to handle Decimal values
        'labels': json.dumps(labels, cls=DjangoJSONEncoder),
        'avg_scores': json.dumps(avg_scores, cls=DjangoJSONEncoder),
        'pass_rates': json.dumps(pass_rates, cls=DjangoJSONEncoder),
        'a_counts': json.dumps(a_counts, cls=DjangoJSONEncoder),
        'b_counts': json.dumps(b_counts, cls=DjangoJSONEncoder),
        'c_counts': json.dumps(c_counts, cls=DjangoJSONEncoder),
        'd_counts': json.dumps(d_counts, cls=DjangoJSONEncoder),
        'f_counts': json.dumps(f_counts, cls=DjangoJSONEncoder),
    }

    return render(request, 'dashboard/admin_performance_trends.html', context)

# Grading Scale Administration Views
@user_passes_test(is_admin)
def admin_grading_scales(request):
    """
    List and manage grading scales
    """
    from assignments.models import GradingScale

    # Get all grading scales
    grading_scales = GradingScale.objects.all().order_by('-is_default', 'name')

    context = {
        'grading_scales': grading_scales
    }

    return render(request, 'dashboard/admin_grading_scales.html', context)

@user_passes_test(is_admin)
def admin_create_grading_scale(request):
    """
    Create a new grading scale
    """
    from assignments.models import GradingScale, GradeThreshold

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description')
        is_default = 'is_default' in request.POST

        # Validate name
        if not name:
            messages.error(request, 'Name is required.')
            return redirect('dashboard:admin_create_grading_scale')

        # Create grading scale
        grading_scale = GradingScale.objects.create(
            name=name,
            description=description,
            is_default=is_default,
            created_by=request.user
        )

        # If set as default, unset all other defaults
        if is_default:
            GradingScale.objects.exclude(id=grading_scale.id).update(is_default=False)

        # Process grade thresholds
        grades = request.POST.getlist('grade')
        min_scores = request.POST.getlist('min_percent')

        for i in range(len(grades)):
            if i < len(min_scores) and grades[i] and min_scores[i]:
                try:
                    min_percent = float(min_scores[i])
                    # Calculate max_percent (next threshold min_percent - 0.01 or 100)
                    max_percent = 100.0
                    if i > 0 and i < len(min_scores) - 1:
                        next_min = float(min_scores[i-1])
                        if next_min > min_percent:
                            max_percent = next_min - 0.01

                    # Calculate GPA points based on percentage (4.0 scale)
                    gpa_points = 4.0
                    if min_percent >= 90:
                        gpa_points = 4.0
                    elif min_percent >= 80:
                        gpa_points = 3.0
                    elif min_percent >= 70:
                        gpa_points = 2.0
                    elif min_percent >= 60:
                        gpa_points = 1.0
                    else:
                        gpa_points = 0.0

                    GradeThreshold.objects.create(
                        scale=grading_scale,
                        letter_grade=grades[i],
                        min_percent=min_percent,
                        max_percent=max_percent,
                        gpa_points=gpa_points
                    )
                except ValueError:
                    # Skip invalid number
                    pass

        messages.success(request, f'Grading scale "{name}" created successfully.')
        return redirect('dashboard:admin_grading_scales')

    # Common grade letters for template
    default_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F']

    context = {
        'default_grades': default_grades
    }

    return render(request, 'dashboard/admin_create_grading_scale.html', context)

@user_passes_test(is_admin)
def admin_edit_grading_scale(request, scale_id):
    """
    Edit an existing grading scale
    """
    from assignments.models import GradingScale, GradeThreshold

    # Get grading scale
    grading_scale = get_object_or_404(GradingScale, id=scale_id)

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description')
        is_default = 'is_default' in request.POST

        # Validate name
        if not name:
            messages.error(request, 'Name is required.')
            return redirect('dashboard:admin_edit_grading_scale', scale_id=scale_id)

        # Update grading scale
        grading_scale.name = name
        grading_scale.description = description
        grading_scale.is_default = is_default
        grading_scale.save()

        # If set as default, unset all other defaults
        if is_default:
            GradingScale.objects.exclude(id=grading_scale.id).update(is_default=False)

        # Delete existing thresholds
        GradeThreshold.objects.filter(scale=grading_scale).delete()

        # Process grade thresholds
        grades = request.POST.getlist('grade')
        min_scores = request.POST.getlist('min_score')

        for i in range(len(grades)):
            if i < len(min_scores) and grades[i] and min_scores[i]:
                try:
                    min_percent = float(min_scores[i])
                    # Calculate max_percent (next threshold min_percent - 0.01 or 100)
                    max_percent = 100.0
                    if i > 0 and i < len(min_scores) - 1:
                        next_min = float(min_scores[i-1])
                        if next_min > min_percent:
                            max_percent = next_min - 0.01

                    # Calculate GPA points based on percentage (4.0 scale)
                    gpa_points = 4.0
                    if min_percent >= 90:
                        gpa_points = 4.0
                    elif min_percent >= 80:
                        gpa_points = 3.0
                    elif min_percent >= 70:
                        gpa_points = 2.0
                    elif min_percent >= 60:
                        gpa_points = 1.0
                    else:
                        gpa_points = 0.0

                    GradeThreshold.objects.create(
                        scale=grading_scale,
                        letter_grade=grades[i],
                        min_percent=min_percent,
                        max_percent=max_percent,
                        gpa_points=gpa_points
                    )
                except ValueError:
                    # Skip invalid number
                    pass

        messages.success(request, f'Grading scale "{name}" updated successfully.')
        return redirect('dashboard:admin_grading_scales')

    # Get existing thresholds
    thresholds = GradeThreshold.objects.filter(scale=grading_scale).order_by('-min_percent')

    context = {
        'grading_scale': grading_scale,
        'thresholds': thresholds
    }

    return render(request, 'dashboard/admin_edit_grading_scale.html', context)

@user_passes_test(is_admin)
def admin_delete_grading_scale(request, scale_id):
    """
    Delete a grading scale
    """
    from assignments.models import GradingScale

    # Get grading scale
    grading_scale = get_object_or_404(GradingScale, id=scale_id)

    if request.method == 'POST':
        # Check if it's the default scale
        if grading_scale.is_default:
            messages.error(request, 'Cannot delete the default grading scale.')
            return redirect('dashboard:admin_grading_scales')

        # Delete the scale
        grading_scale.delete()

        messages.success(request, f'Grading scale "{grading_scale.name}" deleted successfully.')
        return redirect('dashboard:admin_grading_scales')

    context = {
        'grading_scale': grading_scale
    }

    return render(request, 'dashboard/admin_delete_grading_scale.html', context)

@user_passes_test(is_admin)
def admin_set_default_grading_scale(request, scale_id):
    """
    Set a grading scale as the default
    """
    from assignments.models import GradingScale

    # Get grading scale
    grading_scale = get_object_or_404(GradingScale, id=scale_id)

    # Set as default and unset all others
    GradingScale.objects.all().update(is_default=False)
    grading_scale.is_default = True
    grading_scale.save()

    messages.success(request, f'"{grading_scale.name}" is now the default grading scale.')
    return redirect('dashboard:admin_grading_scales')

@user_passes_test(is_parent)
def toggle_child_chat(request, child_id):
    """
    Toggle chat permissions for a child by parent
    """
    # Get the parent and child objects
    parent = get_object_or_404(Parent, user=request.user)
    child = get_object_or_404(Student, id=child_id)

    # Verify that this child belongs to the parent
    if child not in parent.children.all():
        messages.error(request, "You don't have permission to modify this student's settings.")
        return redirect('dashboard:parent_dashboard')

    # Toggle the chat_enabled flag
    child.chat_enabled = not child.chat_enabled
    child.save()

    # Add a success message
    status = "enabled" if child.chat_enabled else "disabled"
    messages.success(request, f"Chat permissions for {child.user.get_full_name()} have been {status}.")

    # Redirect back to the child detail page
    return redirect('dashboard:parent_child_detail', child_id=child.id)

@user_passes_test(is_admin)
def admin_create_standard_scale(request):
    """
    Create a standard grading scale from template
    """
    from assignments.models import GradingScale, GradeThreshold

    if request.method != 'POST':
        return redirect('dashboard:admin_grading_scales')

    scale_type = request.POST.get('scale_type', '')

    if scale_type == 'us_standard':
        # Create US Standard Scale
        scale = GradingScale.objects.create(
            name="US Standard Scale",
            description="Standard US grading scale with letter grades (A+ to F)",
            is_default=False,
            created_by=request.user
        )

        # Create thresholds
        thresholds = [
            {'letter_grade': 'A+', 'min_percent': 97, 'max_percent': 100, 'gpa_points': 4.0},
            {'letter_grade': 'A', 'min_percent': 93, 'max_percent': 96.99, 'gpa_points': 4.0},
            {'letter_grade': 'A-', 'min_percent': 90, 'max_percent': 92.99, 'gpa_points': 3.7},
            {'letter_grade': 'B+', 'min_percent': 87, 'max_percent': 89.99, 'gpa_points': 3.3},
            {'letter_grade': 'B', 'min_percent': 83, 'max_percent': 86.99, 'gpa_points': 3.0},
            {'letter_grade': 'B-', 'min_percent': 80, 'max_percent': 82.99, 'gpa_points': 2.7},
            {'letter_grade': 'C+', 'min_percent': 77, 'max_percent': 79.99, 'gpa_points': 2.3},
            {'letter_grade': 'C', 'min_percent': 73, 'max_percent': 76.99, 'gpa_points': 2.0},
            {'letter_grade': 'C-', 'min_percent': 70, 'max_percent': 72.99, 'gpa_points': 1.7},
            {'letter_grade': 'D+', 'min_percent': 67, 'max_percent': 69.99, 'gpa_points': 1.3},
            {'letter_grade': 'D', 'min_percent': 63, 'max_percent': 66.99, 'gpa_points': 1.0},
            {'letter_grade': 'D-', 'min_percent': 60, 'max_percent': 62.99, 'gpa_points': 0.7},
            {'letter_grade': 'F', 'min_percent': 0, 'max_percent': 59.99, 'gpa_points': 0.0}
        ]

        for threshold in thresholds:
            GradeThreshold.objects.create(
                scale=scale,
                letter_grade=threshold['letter_grade'],
                min_percent=threshold['min_percent'],
                max_percent=threshold['max_percent'],
                gpa_points=threshold['gpa_points']
            )

        messages.success(request, 'US Standard Scale created successfully.')

    elif scale_type == 'ten_point':
        # Create 10-Point Scale
        scale = GradingScale.objects.create(
            name="10-Point Scale",
            description="Simple 10-point grading scale with broader grade bands",
            is_default=False,
            created_by=request.user
        )

        # Create thresholds
        thresholds = [
            {'letter_grade': 'A+', 'min_percent': 97, 'max_percent': 100, 'gpa_points': 4.0},
            {'letter_grade': 'A', 'min_percent': 93, 'max_percent': 96.99, 'gpa_points': 4.0},
            {'letter_grade': 'A-', 'min_percent': 90, 'max_percent': 92.99, 'gpa_points': 3.7},
            {'letter_grade': 'B+', 'min_percent': 87, 'max_percent': 89.99, 'gpa_points': 3.3},
            {'letter_grade': 'B', 'min_percent': 83, 'max_percent': 86.99, 'gpa_points': 3.0},
            {'letter_grade': 'B-', 'min_percent': 80, 'max_percent': 82.99, 'gpa_points': 2.7},
            {'letter_grade': 'C+', 'min_percent': 77, 'max_percent': 79.99, 'gpa_points': 2.3},
            {'letter_grade': 'C', 'min_percent': 73, 'max_percent': 76.99, 'gpa_points': 2.0},
            {'letter_grade': 'C-', 'min_percent': 70, 'max_percent': 72.99, 'gpa_points': 1.7},
            {'letter_grade': 'D', 'min_percent': 60, 'max_percent': 69.99, 'gpa_points': 1.0},
            {'letter_grade': 'F', 'min_percent': 0, 'max_percent': 59.99, 'gpa_points': 0.0}
        ]

        for threshold in thresholds:
            GradeThreshold.objects.create(
                scale=scale,
                letter_grade=threshold['letter_grade'],
                min_percent=threshold['min_percent'],
                max_percent=threshold['max_percent'],
                gpa_points=threshold['gpa_points']
            )

        messages.success(request, '10-Point Scale created successfully.')

    elif scale_type == 'elementary':
        # Create Elementary Scale
        scale = GradingScale.objects.create(
            name="Elementary Scale",
            description="Simplified scale for elementary students with descriptive grades",
            is_default=False,
            created_by=request.user
        )

        # Create thresholds
        thresholds = [
            {'letter_grade': 'E', 'min_percent': 90, 'max_percent': 100, 'gpa_points': 4.0, 'description': 'Excellent'},
            {'letter_grade': 'S', 'min_percent': 80, 'max_percent': 89.99, 'gpa_points': 3.0, 'description': 'Satisfactory'},
            {'letter_grade': 'N', 'min_percent': 70, 'max_percent': 79.99, 'gpa_points': 2.0, 'description': 'Needs Improvement'},
            {'letter_grade': 'U', 'min_percent': 0, 'max_percent': 69.99, 'gpa_points': 0.0, 'description': 'Unsatisfactory'}
        ]

        for threshold in thresholds:
            GradeThreshold.objects.create(
                scale=scale,
                letter_grade=threshold['letter_grade'],
                min_percent=threshold['min_percent'],
                max_percent=threshold['max_percent'],
                gpa_points=threshold['gpa_points'],
                description=threshold.get('description', '')
            )

        messages.success(request, 'Elementary Scale created successfully.')

    else:
        messages.error(request, 'Invalid scale type selected.')

    return redirect('dashboard:admin_grading_scales')


@user_passes_test(is_admin)
def admin_student_promotion(request):
    """
    Manage student promotion, repetition, and graduation
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from io import StringIO
    import sys

    # Get all students
    students = Student.objects.all().order_by('status', 'grade__grade_level', 'section')

    # Get filter parameters
    grade_id = request.GET.get('grade')
    status = request.GET.get('status')
    is_repeating = request.GET.get('is_repeating')
    search_query = request.GET.get('search')

    # Apply filters
    if grade_id:
        students = students.filter(grade_id=grade_id)

    if status:
        students = students.filter(status=status)

    if is_repeating:
        is_repeating_bool = is_repeating == 'true'
        students = students.filter(is_repeating=is_repeating_bool)

    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(student_id__icontains=search_query)
        )

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(students, 20)  # Show 20 students per page

    try:
        paginated_students = paginator.page(page)
    except PageNotAnInteger:
        paginated_students = paginator.page(1)
    except EmptyPage:
        paginated_students = paginator.page(paginator.num_pages)

    # Handle actions
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_status':
            student_ids = request.POST.getlist('student_ids')
            new_status = request.POST.get('new_status')

            # Update selected students
            updated_count = 0
            if student_ids and new_status:
                for student_id in student_ids:
                    try:
                        student = Student.objects.get(id=student_id)
                        student.status = new_status
                        student.save()
                        updated_count += 1
                    except Student.DoesNotExist:
                        pass

                messages.success(request, f'Updated status for {updated_count} students.')
            else:
                messages.error(request, 'No students selected or status not provided.')

        elif action == 'mark_repeating':
            student_ids = request.POST.getlist('student_ids')
            repeating_value = request.POST.get('repeating_value') == 'true'

            # Update selected students
            updated_count = 0
            if student_ids:
                for student_id in student_ids:
                    try:
                        student = Student.objects.get(id=student_id)
                        student.is_repeating = repeating_value

                        # If marking as repeating, increment years in current grade
                        if repeating_value:
                            student.years_in_current_grade += 1

                        student.save()
                        updated_count += 1
                    except Student.DoesNotExist:
                        pass

                action_text = "repeating" if repeating_value else "not repeating"
                messages.success(request, f'Marked {updated_count} students as {action_text}.')
            else:
                messages.error(request, 'No students selected.')

        elif action == 'promote_students':
            # Additional verification for promotion to avoid accidental use
            confirmation = request.POST.get('confirm_promotion') == 'yes'
            dry_run = request.POST.get('dry_run') == 'true'

            if confirmation:
                # Capture command output
                output = StringIO()
                original_stdout = sys.stdout
                sys.stdout = output

                try:
                    # Call the command with the dry_run flag if set
                    from django.core.management import call_command

                    if dry_run:
                        call_command('promote_students', dry_run=True, verbosity=2)
                        messages.info(request, 'Dry run completed. No changes were made to the database.')
                    else:
                        call_command('promote_students', verbosity=2)
                        messages.success(request, 'Student promotion process completed successfully.')

                    # Store command output in session for display
                    request.session['promotion_output'] = output.getvalue()

                except Exception as e:
                    messages.error(request, f'Error during promotion process: {str(e)}')
                finally:
                    sys.stdout = original_stdout
            else:
                messages.error(request, 'Please confirm promotion by checking the confirmation box.')

    # Get classrooms for filter dropdown
    classrooms = ClassRoom.objects.all().order_by('grade_level', 'name')

    # Get promotion output from session if exists
    promotion_output = request.session.pop('promotion_output', None)

    context = {
        'students': paginated_students,
        'classrooms': classrooms,
        'status_choices': Student.Status.choices,
        'total_students': students.count(),
        'active_students': students.filter(status='ACTIVE').count(),
        'graduated_students': students.filter(status='GRADUATED').count(),
        'transferred_students': students.filter(status='TRANSFERRED').count(),
        'repeating_students': students.filter(is_repeating=True).count(),
        'selected_grade': grade_id,
        'selected_status': status,
        'selected_repeating': is_repeating,
        'search_query': search_query,
        'promotion_output': promotion_output,
    }

    return render(request, 'dashboard/admin_student_promotion.html', context)




@user_passes_test(is_admin)
def activity_log(request):
    """
    Display all system activity logs for admin
    """
    # Get all types of activities for the system

    # Get recent assignments (creation)
    recent_assignments = Assignment.objects.order_by('-created_at')[:20]
    assignment_activities = []
    for assignment in recent_assignments:
        assignment_activities.append({
            'type': 'assignment',
            'icon': 'fas fa-clipboard-list',
            'color': 'primary',
            'text': f"New assignment '{assignment.title}' created for {assignment.class_subject.classroom.name}",
            'user': assignment.created_by.get_full_name(),
            'time': assignment.created_at,
            'url': reverse('assignments:assignment_detail', kwargs={'assignment_id': assignment.id})
        })

    # Get recent submissions
    recent_submissions = StudentSubmission.objects.order_by('-submission_date')[:20]
    submission_activities = []
    for submission in recent_submissions:
        submission_activities.append({
            'type': 'submission',
            'icon': 'fas fa-file-alt',
            'color': 'success',
            'text': f"{submission.student.user.get_full_name()} submitted '{submission.assignment.title}'",
            'user': submission.student.user.get_full_name(),
            'time': submission.submission_date,
            'url': reverse('assignments:submission_detail', kwargs={'submission_id': submission.id})
        })

    # Get recent grades
    recent_grades = Grade.objects.order_by('-created_at')[:20]
    grade_activities = []
    for grade in recent_grades:
        grade_activities.append({
            'type': 'grade',
            'icon': 'fas fa-star',
            'color': 'warning',
            'text': f"{grade.created_by.get_full_name()} graded {grade.student.user.get_full_name()}'s submission with {grade.score}%",
            'user': grade.created_by.get_full_name(),
            'time': grade.created_at,
            'url': reverse('assignments:grade_detail', kwargs={'grade_id': grade.id})
        })

    # Get recent announcements
    recent_announcements = Announcement.objects.order_by('-created_at')[:20]
    announcement_activities = []
    for announcement in recent_announcements:
        announcement_activities.append({
            'type': 'announcement',
            'icon': 'fas fa-bullhorn',
            'color': 'info',
            'text': f"New announcement: {announcement.title}",
            'user': announcement.created_by.get_full_name(),
            'time': announcement.created_at,
            'url': reverse('communications:announcement_detail', kwargs={'announcement_id': announcement.id})
        })

    # Get recent attendance records
    recent_attendance = AttendanceRecord.objects.order_by('-date', '-created_at')[:20]
    attendance_activities = []
    for record in recent_attendance:
        attendance_activities.append({
            'type': 'attendance',
            'icon': 'fas fa-user-check',
            'color': 'primary',
            'text': f"Attendance taken for {record.classroom.name} by {record.taken_by.get_full_name()}",
            'user': record.taken_by.get_full_name(),
            'time': record.created_at,
            'url': reverse('attendance:record_detail', kwargs={'record_id': record.id})
        })

    # Get recent material uploads
    recent_materials = CourseMaterial.objects.order_by('-created_at')[:20]
    material_activities = []
    for material in recent_materials:
        material_activities.append({
            'type': 'material',
            'icon': 'fas fa-file-upload',
            'color': 'info',
            'text': f"New material '{material.title}' uploaded for {material.class_subject.subject.name}",
            'user': material.uploaded_by.get_full_name(),
            'time': material.created_at,
            'url': reverse('courses:material_detail', kwargs={'material_id': material.id})
        })

    # Get recent video uploads
    recent_videos = YouTubeVideo.objects.order_by('-created_at')[:20]
    video_activities = []
    for video in recent_videos:
        video_activities.append({
            'type': 'video',
            'icon': 'fab fa-youtube',
            'color': 'danger',
            'text': f"New video '{video.title}' added for {video.class_subject.subject.name}",
            'user': video.uploaded_by.get_full_name(),
            'time': video.created_at,
            'url': reverse('courses:video_detail', kwargs={'video_id': video.id})
        })

    # Get recent events
    recent_events = Event.objects.order_by('-created_at')[:20]
    event_activities = []
    for event in recent_events:
        event_activities.append({
            'type': 'event',
            'icon': 'fas fa-calendar-plus',
            'color': 'success',
            'text': f"New event '{event.title}' scheduled",
            'user': event.created_by.get_full_name(),
            'time': event.created_at,
            'url': reverse('communications:event_detail', kwargs={'event_id': event.id})
        })

    # Combine all activities
    all_activities = (
        assignment_activities +
        submission_activities +
        grade_activities +
        announcement_activities +
        attendance_activities +
        material_activities +
        video_activities +
        event_activities
    )

    # Sort activities by time
    all_activities.sort(key=lambda x: x['time'], reverse=True)

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(all_activities, 25)  # Show 25 activities per page

    try:
        activities = paginator.page(page)
    except PageNotAnInteger:
        activities = paginator.page(1)
    except EmptyPage:
        activities = paginator.page(paginator.num_pages)

    context = {
        'activities': activities,
        'title': 'System Activity Log'
    }

    return render(request, 'dashboard/activity_log.html', context)


@login_required
def download_report_card(request, report_card_id):
    """
    Download report card as PDF
    """
    report_card = get_object_or_404(ReportCard, id=report_card_id)

    # Check permissions
    if not (is_admin(request.user) or
            is_teacher(request.user) or
            (is_student(request.user) and report_card.student.user == request.user) or
            (is_parent(request.user) and report_card.student in Parent.objects.get(user=request.user).children.all())):
        messages.error(request, "You don't have permission to view this report card.")
        return redirect('dashboard:index')

    # This would typically generate and return a PDF
    # For now, we'll just redirect to the view
    return redirect('assignments:view_report_card', report_card_id=report_card_id)

@login_required
# Assessment Weight Configuration Views
@user_passes_test(is_admin)
def admin_assessment_weights(request):
    """
    List and manage assessment weight configurations
    """
    from assignments.models import AssessmentWeightConfiguration

    # Get all assessment weight configurations
    configs = AssessmentWeightConfiguration.objects.all().order_by('-is_default', 'name')

    context = {
        'configs': configs
    }

    return render(request, 'dashboard/admin_assessment_weights.html', context)

@user_passes_test(is_admin)
def admin_create_assessment_weight(request):
    """
    Create a new assessment weight configuration
    """
    from assignments.models import AssessmentWeightConfiguration

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description')
        is_default = 'is_default' in request.POST

        # Get component weights and inclusion flags
        classwork_weight = float(request.POST.get('classwork_weight', 0))
        include_classwork = 'include_classwork' in request.POST

        quiz_weight = float(request.POST.get('quiz_weight', 0))
        include_quizzes = 'include_quizzes' in request.POST

        test_weight = float(request.POST.get('test_weight', 0))
        include_tests = 'include_tests' in request.POST

        midterm_weight = float(request.POST.get('midterm_weight', 0))
        include_midterm = 'include_midterms' in request.POST  # Form uses midterms (plural)

        project_weight = float(request.POST.get('project_weight', 0))
        include_projects = 'include_projects' in request.POST

        final_exam_weight = float(request.POST.get('exam_weight', 0))  # Form uses exam_weight
        include_final_exam = 'include_exams' in request.POST  # Form uses include_exams

        attendance_weight = float(request.POST.get('attendance_weight', 0))
        include_attendance = 'include_attendance' in request.POST

        term = request.POST.get('term')

        # Calculate total to verify weights sum to 100%
        total_weight = 0
        if include_classwork:
            total_weight += classwork_weight
        if include_quizzes:
            total_weight += quiz_weight
        if include_tests:
            total_weight += test_weight
        if include_midterm:
            total_weight += midterm_weight
        if include_projects:
            total_weight += project_weight
        if include_final_exam:
            total_weight += final_exam_weight
        if include_attendance:
            total_weight += attendance_weight

        # Validate name
        if not name:
            messages.error(request, 'Name is required.')
            return redirect('dashboard:admin_create_assessment_weight')

        try:
            # Create assessment weight configuration
            config = AssessmentWeightConfiguration.objects.create(
                name=name,
                description=description,
                is_default=is_default,
                created_by=request.user,
                academic_term=term,

                # Map form fields to model fields correctly
                classwork_weight=classwork_weight,
                include_classwork=include_classwork,

                quiz_weight=quiz_weight,
                include_quizzes=include_quizzes,

                test_weight=test_weight,
                include_tests=include_tests,

                midterm_weight=midterm_weight,
                include_midterm=include_midterm,  # Correct field name (singular)

                project_weight=project_weight,
                include_projects=include_projects,

                final_exam_weight=final_exam_weight,  # Correct field name
                include_final_exam=include_final_exam,  # Correct field name

                attendance_weight=attendance_weight,
                include_attendance=include_attendance
            )

            messages.success(request, f'Assessment weight configuration "{name}" created successfully.')
            return redirect('dashboard:admin_assessment_weights')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('dashboard:admin_create_assessment_weight')

        # If set as default, unset all other defaults
        if is_default:
            AssessmentWeightConfiguration.objects.exclude(id=config.id).update(is_default=False)

        messages.success(request, f'Assessment weight configuration "{name}" created successfully.')
        return redirect('dashboard:admin_assessment_weights')

    context = {
        'term_choices': [
            ('Term 1', 'Term 1'),
            ('Term 2', 'Term 2'),
            ('Term 3', 'Term 3'),
            ('Semester 1', 'Semester 1'),
            ('Semester 2', 'Semester 2'),
            ('All Terms', 'All Terms'),
        ]
    }

    return render(request, 'dashboard/admin_create_assessment_weight.html', context)

@user_passes_test(is_admin)
def admin_edit_assessment_weight(request, config_id):
    """
    Edit an existing assessment weight configuration
    """
    from assignments.models import AssessmentWeightConfiguration

    # Get assessment weight configuration
    config = get_object_or_404(AssessmentWeightConfiguration, id=config_id)

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description')
        is_default = 'is_default' in request.POST

        # Get component weights and inclusion flags
        classwork_weight = float(request.POST.get('classwork_weight', 0))
        include_classwork = 'include_classwork' in request.POST

        quiz_weight = float(request.POST.get('quiz_weight', 0))
        include_quizzes = 'include_quizzes' in request.POST

        test_weight = float(request.POST.get('test_weight', 0))
        include_tests = 'include_tests' in request.POST

        midterm_weight = float(request.POST.get('midterm_weight', 0))
        include_midterm = 'include_midterms' in request.POST  # Form uses midterms (plural)

        project_weight = float(request.POST.get('project_weight', 0))
        include_projects = 'include_projects' in request.POST

        final_exam_weight = float(request.POST.get('exam_weight', 0))  # Form uses exam_weight
        include_final_exam = 'include_exams' in request.POST  # Form uses include_exams

        attendance_weight = float(request.POST.get('attendance_weight', 0))
        include_attendance = 'include_attendance' in request.POST

        term = request.POST.get('term')

        # Calculate total weight for verification
        total_weight = 0
        if include_classwork:
            total_weight += classwork_weight
        if include_quizzes:
            total_weight += quiz_weight
        if include_tests:
            total_weight += test_weight
        if include_midterm:
            total_weight += midterm_weight
        if include_projects:
            total_weight += project_weight
        if include_final_exam:
            total_weight += final_exam_weight
        if include_attendance:
            total_weight += attendance_weight

        # Validate name
        if not name:
            messages.error(request, 'Name is required.')
            return redirect('dashboard:admin_edit_assessment_weight', config_id=config_id)

        try:
            # Update assessment weight configuration
            config.name = name
            config.description = description
            config.is_default = is_default
            config.academic_term = term
            config.classwork_weight = classwork_weight
            config.include_classwork = include_classwork
            config.quiz_weight = quiz_weight
            config.include_quizzes = include_quizzes
            config.test_weight = test_weight
            config.include_tests = include_tests
            config.midterm_weight = midterm_weight
            config.include_midterm = include_midterm
            config.project_weight = project_weight
            config.include_projects = include_projects
            config.final_exam_weight = final_exam_weight
            config.include_final_exam = include_final_exam
            config.attendance_weight = attendance_weight
            config.include_attendance = include_attendance
            config.save()

            messages.success(request, f'Assessment weight configuration "{name}" updated successfully.')
            return redirect('dashboard:admin_assessment_weights')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('dashboard:admin_edit_assessment_weight', config_id=config_id)

        # If set as default, unset all other defaults
        if is_default:
            AssessmentWeightConfiguration.objects.exclude(id=config.id).update(is_default=False)

        messages.success(request, f'Assessment weight configuration "{name}" updated successfully.')
        return redirect('dashboard:admin_assessment_weights')

    context = {
        'config': config,
        'term_choices': [
            ('Term 1', 'Term 1'),
            ('Term 2', 'Term 2'),
            ('Term 3', 'Term 3'),
            ('Semester 1', 'Semester 1'),
            ('Semester 2', 'Semester 2'),
            ('All Terms', 'All Terms'),
        ]
    }

    return render(request, 'dashboard/admin_edit_assessment_weight.html', context)

@user_passes_test(is_admin)
def admin_delete_assessment_weight(request, config_id):
    """
    Delete an assessment weight configuration
    """
    from assignments.models import AssessmentWeightConfiguration

    # Get assessment weight configuration
    config = get_object_or_404(AssessmentWeightConfiguration, id=config_id)

    if request.method == 'POST':
        # Check if it's the default configuration
        if config.is_default:
            messages.error(request, 'Cannot delete the default assessment weight configuration.')
            return redirect('dashboard:admin_assessment_weights')

        # Delete the configuration
        config.delete()

        messages.success(request, f'Assessment weight configuration "{config.name}" deleted successfully.')
        return redirect('dashboard:admin_assessment_weights')

    context = {
        'config': config
    }

    return render(request, 'dashboard/admin_delete_assessment_weight.html', context)

@user_passes_test(is_admin)
def admin_set_default_assessment_weight(request, config_id):
    """
    Set an assessment weight configuration as the default
    """
    from assignments.models import AssessmentWeightConfiguration

    # Get assessment weight configuration
    config = get_object_or_404(AssessmentWeightConfiguration, id=config_id)

    # Set this configuration as default
    # The model's save method will handle unsetting other defaults
    config.is_default = True
    config.save()

    messages.success(request, f'"{config.name}" is now the default assessment weight configuration.')
    return redirect('dashboard:admin_assessment_weights')

def calendar_view(request):
    """
    Calendar view with events, assignments, exams
    """
    user = request.user
    today = timezone.now()

    # Get calendar events based on user role
    calendar_events = []

    # School-wide events
    school_events = Event.objects.filter(
        end_date__gte=today - timedelta(days=30),
        start_date__lte=today + timedelta(days=60)
    )

    # Filter events based on user role
    if is_teacher(user):
        # For teachers, show school-wide events and events for classes they teach
        try:
            teacher = Teacher.objects.get(user=user)
            class_teacher_of = ClassRoom.objects.filter(class_teacher=teacher)
            school_events = school_events.filter(
                Q(is_school_wide=True) |
                Q(specific_class__in=class_teacher_of)
            )
        except Teacher.DoesNotExist:
            school_events = school_events.filter(is_school_wide=True)
    elif is_student(user):
        # For students, show school-wide events and events for their classes and subjects
        try:
            student = Student.objects.get(user=user)
            enrolled_subjects = ClassSubject.objects.filter(students=student)
            if enrolled_subjects:
                student_classrooms = [subject.classroom for subject in enrolled_subjects]
                school_events = school_events.filter(
                    Q(is_school_wide=True) |
                    Q(specific_class__in=student_classrooms) |
                    Q(specific_subject__in=enrolled_subjects)
                )
            else:
                school_events = school_events.filter(is_school_wide=True)
        except Student.DoesNotExist:
            school_events = school_events.filter(is_school_wide=True)
    elif is_parent(user):
        # For parents, show school-wide events and all events for their children
        try:
            parent = Parent.objects.get(user=user)
            children = parent.children.all()

            if children:
                # Collect all classrooms and subjects for all children
                child_classrooms = []
                child_subjects = []

                for child in children:
                    enrolled_subjects = ClassSubject.objects.filter(students=child)
                    child_subjects.extend(enrolled_subjects)
                    child_classrooms.extend([subject.classroom for subject in enrolled_subjects])

                # Remove duplicates
                child_classrooms = list(set(child_classrooms))

                school_events = school_events.filter(
                    Q(is_school_wide=True) |
                    Q(specific_class__in=child_classrooms) |
                    Q(specific_subject__in=child_subjects)
                )
            else:
                school_events = school_events.filter(is_school_wide=True)
        except Parent.DoesNotExist:
            school_events = school_events.filter(is_school_wide=True)
    else:
        # For admins, show all school-wide events
        school_events = school_events.filter(is_school_wide=True)

    for event in school_events:
        calendar_events.append({
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat(),
            'className': 'bg-info',
            'url': '#',
            'description': event.description
        })

    # Add assignments based on role
    if is_teacher(user):
        # Get teacher's assignments
        try:
            teacher = Teacher.objects.get(user=user)
            assignments = Assignment.objects.filter(
                class_subject__teacher=teacher,
                due_date__gte=today - timedelta(days=30),
                due_date__lte=today + timedelta(days=60)
            )

            for assignment in assignments:
                event_type = 'bg-primary'
                if assignment.assignment_type == 'QUIZ':
                    event_type = 'bg-success'
                elif assignment.assignment_type == 'TEST':
                    event_type = 'bg-warning'
                elif assignment.assignment_type == 'EXAM':
                    event_type = 'bg-danger'

                calendar_events.append({
                    'title': assignment.title,
                    'start': assignment.due_date.isoformat(),
                    'end': (assignment.due_date + timedelta(hours=1)).isoformat(),
                    'className': event_type,
                    'url': '#',
                    'description': assignment.description[:100]
                })
        except Teacher.DoesNotExist:
            pass

    elif is_student(user):
        # Get student's assignments
        try:
            student = Student.objects.get(user=user)
            enrolled_subjects = ClassSubject.objects.filter(students=student)

            assignments = Assignment.objects.filter(
                class_subject__in=enrolled_subjects,
                due_date__gte=today - timedelta(days=30),
                due_date__lte=today + timedelta(days=60)
            )

            for assignment in assignments:
                event_type = 'bg-primary'
                if assignment.assignment_type == 'QUIZ':
                    event_type = 'bg-success'
                elif assignment.assignment_type == 'TEST':
                    event_type = 'bg-warning'
                elif assignment.assignment_type == 'EXAM':
                    event_type = 'bg-danger'

                calendar_events.append({
                    'title': assignment.title,
                    'start': assignment.due_date.isoformat(),
                    'end': (assignment.due_date + timedelta(hours=1)).isoformat(),
                    'className': event_type,
                    'url': '#',
                    'description': assignment.description[:100]
                })
        except Student.DoesNotExist:
            pass

    elif is_parent(user):
        # Get children's assignments
        try:
            parent = Parent.objects.get(user=user)
            children = parent.children.all()

            for child in children:
                enrolled_subjects = ClassSubject.objects.filter(students=child)

                assignments = Assignment.objects.filter(
                    class_subject__in=enrolled_subjects,
                    due_date__gte=today - timedelta(days=30),
                    due_date__lte=today + timedelta(days=60)
                )

                for assignment in assignments:
                    event_type = 'bg-primary'
                    if assignment.assignment_type == 'QUIZ':
                        event_type = 'bg-success'
                    elif assignment.assignment_type == 'TEST':
                        event_type = 'bg-warning'
                    elif assignment.assignment_type == 'EXAM':
                        event_type = 'bg-danger'

                    calendar_events.append({
                        'title': f"{child.user.first_name}: {assignment.title}",
                        'start': assignment.due_date.isoformat(),
                        'end': (assignment.due_date + timedelta(hours=1)).isoformat(),
                        'className': event_type,
                        'url': '#',
                        'description': assignment.description[:100]
                    })
        except Parent.DoesNotExist:
            pass

    context = {
        'user': user,
        'calendar_events': json.dumps(calendar_events)
    }

    return render(request, 'dashboard/calendar.html', context)

# Helper functions
def get_user_widgets(user):
    """
    Get user widgets for dashboard
    """
    # Get or create user preferences
    preferences, created = DashboardPreference.objects.get_or_create(user=user)

    # Get user widgets
    user_widgets = UserWidget.objects.filter(user=user, is_visible=True).order_by('position')

    # If user has no widgets, create default ones
    if not user_widgets.exists():
        create_default_widgets(user)
        user_widgets = UserWidget.objects.filter(user=user, is_visible=True).order_by('position')

    return user_widgets

def create_default_widgets(user):
    """
    Create default widgets for a user based on their role
    """
    role = user.role
    position = 1

    if role == CustomUser.Role.ADMIN:
        widgets = Widget.objects.filter(visible_to_admin=True, is_active=True)
    elif role == CustomUser.Role.TEACHER:
        widgets = Widget.objects.filter(visible_to_teacher=True, is_active=True)
    elif role == CustomUser.Role.STUDENT:
        widgets = Widget.objects.filter(visible_to_student=True, is_active=True)
    elif role == CustomUser.Role.PARENT:
        widgets = Widget.objects.filter(visible_to_parent=True, is_active=True)
    else:
        widgets = Widget.objects.none()

    for widget in widgets:
        UserWidget.objects.create(
            user=user,
            widget=widget,
            position=position,
            size=widget.default_size,
            is_visible=True
        )
        position += 1
