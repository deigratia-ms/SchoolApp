from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q, Sum, Avg, F, ExpressionWrapper, FloatField
from django.core.paginator import Paginator
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from openpyxl import Workbook
from io import BytesIO

from datetime import datetime, timedelta, date
import calendar
import csv
import json

from .models import AttendanceStatus

# Import the custom decorator
from users.decorators import admin_or_teacher_required

@login_required
@admin_or_teacher_required
def export_report(request):
    """
    Export attendance data to Excel format.
    
    Security features:
    - Only administrators and teachers can access this view
    - Teachers can only export data for classrooms they teach
    - Input validation for all parameters to prevent security exploits
    - Strict permission checks based on user role
    
    Returns:
    - Excel file with attendance data based on the specified filters
    - Redirects to reports page with error message if permission denied
    """
    try:
        user = request.user
        
        # Get filter parameters from request with validation
        classroom_id = request.GET.get('classroom', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        
        # Base query with role-based filtering
        if user.role == 'ADMIN':
            # Admins can access all records, but we'll still apply filters
            records_query = AttendanceRecord.objects.all()
        elif user.role == 'TEACHER':
            # Teachers can only access their own classes
            try:
                teacher = Teacher.objects.get(user=user)
                # Start with only classes this teacher teaches
                records_query = AttendanceRecord.objects.filter(
                    Q(classroom__class_teacher=teacher) |
                    Q(classroom__subjects__teacher=teacher)
                ).distinct()
            except Teacher.DoesNotExist:
                messages.error(request, "Teacher profile not found.")
                return redirect('attendance:reports')
        else:
            # This shouldn't happen due to the decorator, but as a safeguard
            messages.error(request, "You don't have permission to export attendance data.")
            return redirect('attendance:reports')
        
        # Apply classroom filter with permission check
        if classroom_id and classroom_id.isdigit():
            # Verify the classroom exists
            try:
                classroom = ClassRoom.objects.get(id=classroom_id)
                
                # For teachers, check if they have permission to access this classroom
                if user.role == 'TEACHER':
                    teacher = Teacher.objects.get(user=user)
                    # Check if teacher teaches this class or is the class teacher
                    has_permission = (
                        classroom.class_teacher == teacher or
                        ClassSubject.objects.filter(classroom=classroom, teacher=teacher).exists()
                    )
                    
                    if not has_permission:
                        # Teacher doesn't have access to this classroom
                        messages.error(request, "You don't have permission to export attendance data for this classroom.")
                        return redirect('attendance:reports')
                
                # Apply the filter now that permission is confirmed
                records_query = records_query.filter(classroom_id=classroom_id)
                
            except ClassRoom.DoesNotExist:
                messages.error(request, "Selected classroom does not exist.")
                return redirect('attendance:reports')
    
        # Apply date filters with validation
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                records_query = records_query.filter(date__gte=date_from_obj)
            except ValueError:
                messages.warning(request, "Invalid 'from' date format. Using no start date filter.")
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                records_query = records_query.filter(date__lte=date_to_obj)
            except ValueError:
                messages.warning(request, "Invalid 'to' date format. Using no end date filter.")
        
        # Check if any records match the criteria
        if not records_query.exists():
            messages.warning(request, "No attendance records found matching the specified criteria.")
            return redirect('attendance:reports')
            
        # Get the records with optimized querying
        records = records_query.order_by('date').select_related('classroom')
        
        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance Report"
        
        # Add headers with more information
        headers = [
            'Date', 'Classroom', 'Student', 'Student ID', 'Status', 'Remarks'
        ]
        ws.append(headers)
        
        # Add data with optimized querying
        for record in records:
            student_attendances = StudentAttendance.objects.filter(
                attendance_record=record
            ).select_related('student', 'student__user')
            
            for attendance in student_attendances:
                try:
                    student_name = attendance.student.user.get_full_name()
                    student_id = attendance.student.student_id
                except:
                    # Handle potential null references gracefully
                    student_name = "Unknown Student"
                    student_id = "N/A"
                
                ws.append([
                    record.date.strftime('%Y-%m-%d'),
                    record.classroom.name,
                    student_name,
                    student_id,
                    attendance.status,
                    attendance.remarks or ''  # Handle None values
                ])
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Add datetime to filename for uniqueness
        filename = f"attendance_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename={filename}'
        
        # Save workbook to response
        output = BytesIO()
        wb.save(output)
        response.write(output.getvalue())
        
        return response
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in export_report: {str(e)}")
        
        # Show a user-friendly error message
        messages.error(request, f"An error occurred while generating the report: {str(e)}")
        return redirect('attendance:reports')
from .models import AttendanceRecord, StudentAttendance, AttendanceReport, AttendanceNotification
from users.models import Student, Teacher, CustomUser
from courses.models import ClassRoom, ClassSubject

# Helper function for various role checks
def is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'

def is_teacher(user):
    return user.is_authenticated and user.role == 'TEACHER'

def is_student(user):
    return user.is_authenticated and user.role == 'STUDENT'

def is_parent(user):
    return user.is_authenticated and user.role == 'PARENT'

# Attendance Home
@login_required
def attendance_home(request):
    """
    Home page for attendance module with quick links and statistics based on user role.
    """
    context = {}
    user = request.user
    
    # Stats for all roles
    total_attendance_records = AttendanceRecord.objects.count()
    today = timezone.now().date()
    
    # Current month range
    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    
    # Count records for the current month
    month_records = AttendanceRecord.objects.filter(date__range=[first_day, last_day]).count()
    
    # Basic stats for all users
    context.update({
        'total_attendance_records': total_attendance_records,
        'month_records': month_records,
        'today': today
    })
    
    # Role-specific content
    if is_admin(user):
        # Admin sees full school statistics
        classes = ClassRoom.objects.all()
        recent_records = AttendanceRecord.objects.all().order_by('-date')[:10]
        
        # Calculate school-wide attendance percentage
        total_present = StudentAttendance.objects.filter(status='PRESENT').count()
        total_absences = StudentAttendance.objects.filter(status='ABSENT').count()
        total_attendance = total_present + total_absences
        
        attendance_percentage = 0
        if total_attendance > 0:
            attendance_percentage = (total_present / total_attendance) * 100
            
        context.update({
            'classes': classes,
            'recent_records': recent_records,
            'attendance_percentage': attendance_percentage,
            'total_present': total_present,
            'total_absences': total_absences
        })
        
    elif is_teacher(user):
        # Teacher sees statistics for classes they teach
        teacher = user.teacher
        
        # Get classes taught by this teacher
        classes = ClassRoom.objects.filter(
            Q(class_teacher=teacher) | 
            Q(subjects__teacher=teacher)
        ).distinct()
        
        # Recent attendance records for classes taught by this teacher
        recent_records = AttendanceRecord.objects.filter(
            Q(classroom__class_teacher=teacher) |
            Q(classroom__subjects__teacher=teacher)
        ).distinct().order_by('-date')[:10]
        
        # Classes that need attendance today
        classes_needing_attendance = []
        for classroom in classes:
            if not AttendanceRecord.objects.filter(classroom=classroom, date=today).exists():
                classes_needing_attendance.append(classroom)
        
        context.update({
            'classes': classes,
            'recent_records': recent_records,
            'classes_needing_attendance': classes_needing_attendance
        })
        
    elif is_student(user):
        # Student sees their own attendance statistics
        try:
            student = user.student
            
            # Get student's attendance records
            student_attendance = StudentAttendance.objects.filter(student=student)
            
            # Calculate attendance percentage
            total_present = student_attendance.filter(status='PRESENT').count()
            total_attendance = student_attendance.count()
            
            attendance_percentage = 0
            if total_attendance > 0:
                attendance_percentage = (total_present / total_attendance) * 100
                
            # Get recent attendance records
            recent_attendance = student_attendance.order_by('-attendance_record__date')[:10]
            
            context.update({
                'student': student,
                'attendance_percentage': attendance_percentage,
                'total_present': total_present,
                'total_attendance': total_attendance,
                'recent_attendance': recent_attendance
            })
            
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
    
    elif is_parent(user):
        # Parent sees attendance statistics for their children
        try:
            parent = user.parent
            children = parent.children.all()
            
            # Stats for each child
            children_stats = []
            
            for child in children:
                child_attendance = StudentAttendance.objects.filter(student=child)
                total_present = child_attendance.filter(status='PRESENT').count()
                total_attendance = child_attendance.count()
                
                attendance_percentage = 0
                if total_attendance > 0:
                    attendance_percentage = (total_present / total_attendance) * 100
                
                recent_attendance = child_attendance.order_by('-attendance_record__date')[:5]
                
                children_stats.append({
                    'student': child,
                    'attendance_percentage': attendance_percentage,
                    'total_present': total_present,
                    'total_attendance': total_attendance,
                    'recent_attendance': recent_attendance
                })
            
            context.update({
                'children_stats': children_stats
            })
            
        except Exception as e:
            messages.error(request, f"Error retrieving children's attendance: {str(e)}")
    
    return render(request, 'attendance/home.html', context)

# Take Attendance
@login_required
@user_passes_test(is_teacher)
def take_attendance(request):
    """
    Display classes that the teacher can take attendance for.
    """
    teacher = request.user.teacher
    
    # Get current date
    today = timezone.now().date()
    
    # Get classes taught by this teacher with additional data
    classes = ClassRoom.objects.filter(
        Q(class_teacher=teacher) | 
        Q(subjects__teacher=teacher)
    ).distinct().order_by('name', 'section')
    
    # Check if the teacher is a class teacher for any class
    is_subject_teacher = not ClassRoom.objects.filter(class_teacher=teacher).exists()
    
    teacher_classes = []
    for classroom in classes:
        # Get attendance record for today if exists
        attendance_record = AttendanceRecord.objects.filter(
            classroom=classroom,
            date=today
        ).first()
        
        # Get student counts
        students_count = Student.objects.filter(
            enrolled_subjects__classroom=classroom
        ).distinct().count()
        
        # Get attendance counts if record exists
        present_count = 0
        absent_count = 0
        late_count = 0
        excused_count = 0
        
        if attendance_record:
            student_attendances = StudentAttendance.objects.filter(
                attendance_record=attendance_record
            )
            present_count = student_attendances.filter(status='PRESENT').count()
            absent_count = student_attendances.filter(status='ABSENT').count()
            late_count = student_attendances.filter(status='LATE').count()
            excused_count = student_attendances.filter(status='EXCUSED').count()
        
        teacher_classes.append({
            'id': classroom.id,
            'name': classroom.name,
            'section': classroom.section,
            'students_count': students_count,
            'has_attendance': attendance_record is not None,
            'attendance_record': attendance_record,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'excused_count': excused_count,
            'is_class_teacher': classroom.class_teacher == teacher,
            'class_teacher': classroom.class_teacher
        })
    
    # Calculate completion percentage
    completed_attendance_count = len([c for c in teacher_classes if c['has_attendance']])
    attendance_completion_percentage = round(
        (completed_attendance_count / len(teacher_classes)) * 100, 2
    ) if teacher_classes else 0
    
    context = {
        'teacher_classes': teacher_classes,
        'today': today,
        'selected_date': today,
        'completed_attendance_count': completed_attendance_count,
        'attendance_completion_percentage': attendance_completion_percentage,
        'recent_records': AttendanceRecord.objects.filter(
            Q(classroom__class_teacher=teacher) |
            Q(classroom__subjects__teacher=teacher)
        ).distinct().order_by('-date')[:5]
    }
    
    return render(request, 'attendance/take_attendance.html', context)

@login_required
@user_passes_test(is_teacher)
def take_class_attendance(request, classroom_id):
    """
    Take attendance for a specific class.
    Only class teachers can mark daily attendance.
    """
    teacher = request.user.teacher
    classroom = get_object_or_404(ClassRoom, id=classroom_id)
    
    # Check if the teacher is the class teacher
    has_permission = (classroom.class_teacher == teacher)
    
    if not has_permission:
        messages.error(request, "Only class teachers can mark daily attendance for this class.")
        return redirect('attendance:take_attendance')
    
    # Get all students in this class
    class_subjects = ClassSubject.objects.filter(classroom=classroom)
    students = Student.objects.filter(
        enrolled_subjects__in=class_subjects
    ).distinct().order_by('user__first_name', 'user__last_name')
    
    today = request.GET.get('date', None)
    if today:
        try:
            today = datetime.strptime(today, '%Y-%m-%d').date()
        except ValueError:
            today = timezone.now().date()
    else:
        today = timezone.now().date()
    
    # Check if attendance already exists for this date
    existing_record = AttendanceRecord.objects.filter(classroom=classroom, date=today).first()
    
    if request.method == 'POST':
        # Create or get attendance record
        if existing_record:
            attendance_record = existing_record
        else:
            attendance_record = AttendanceRecord.objects.create(
                classroom=classroom,
                date=today,
                taken_by=teacher
            )
        
        # Process student attendances
        for student in students:
            status = request.POST.get(f'status_{student.id}', 'ABSENT')
            remarks = request.POST.get(f'remarks_{student.id}', '')
            
            student_attendance, created = StudentAttendance.objects.update_or_create(
                attendance_record=attendance_record,
                student=student,
                defaults={
                    'status': status,
                    'remarks': remarks
                }
            )
        
        messages.success(request, f"Attendance for {classroom.name} on {today.strftime('%Y-%m-%d')} has been recorded.")
        
        # Redirect to attendance record detail
        return redirect('attendance:record_detail', record_id=attendance_record.id)
    
    # For GET request, initialize student_statuses with all students
    student_statuses = {}
    for student in students:
        student_statuses[student.id] = {
            'status': 'ABSENT',  # Default status
            'remarks': ''  # Default remarks
        }

    # If attendance record exists, update statuses with existing data
    if existing_record:
        student_attendances = StudentAttendance.objects.filter(attendance_record=existing_record)
        for sa in student_attendances:
            student_statuses[sa.student.id]['status'] = sa.status
            student_statuses[sa.student.id]['remarks'] = sa.remarks

    context = {
        'classroom': classroom,
        'students': students,
        'today': today,
        'existing_record': existing_record,
        'student_statuses': student_statuses,
        'statuses': AttendanceStatus.choices
    }
    
    return render(request, 'attendance/mark_attendance.html', context)

# Individual attendance status editing
@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def edit_attendance_status(request, student_attendance_id):
    """
    Edit the attendance status for a specific student attendance record.
    """
    student_attendance = get_object_or_404(StudentAttendance, id=student_attendance_id)
    user = request.user
    record = student_attendance.attendance_record
    
    # Check permissions
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        has_permission = (record.taken_by == teacher or 
                        record.classroom.class_teacher == teacher or
                        ClassSubject.objects.filter(classroom=record.classroom, teacher=teacher).exists())
    
    if not has_permission:
        messages.error(request, "You don't have permission to edit this attendance record.")
        return redirect('attendance:record_detail', record_id=record.id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        remarks = request.POST.get('remarks', '')
        
        if status in dict(AttendanceStatus.choices):
            student_attendance.status = status
            student_attendance.remarks = remarks
            student_attendance.save()
            
            messages.success(request, f"Attendance status for {student_attendance.student.user.get_full_name()} has been updated.")
        else:
            messages.error(request, "Invalid attendance status.")
        
        return redirect('attendance:record_detail', record_id=record.id)
    
    context = {
        'student_attendance': student_attendance,
        'statuses': StudentAttendance.STATUS_CHOICES,
        'record': record
    }
    
    return render(request, 'attendance/edit_attendance_status.html', context)

# Attendance Notifications
@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def attendance_notifications(request):
    """
    View attendance notifications.
    """
    user = request.user
    
    # Get notifications based on role
    if is_admin(user):
        notifications = AttendanceNotification.objects.all().order_by('-created_at')
    elif is_teacher(user):
        teacher = user.teacher
        # Get notifications for students in classes taught by this teacher
        taught_classes = ClassRoom.objects.filter(
            Q(class_teacher=teacher) | 
            Q(subjects__teacher=teacher)
        ).distinct()
        
        # Get students in these classes
        students = Student.objects.filter(
            enrolled_subjects__classroom__in=taught_classes
        ).distinct()
        
        notifications = AttendanceNotification.objects.filter(
            student__in=students
        ).order_by('-created_at')
    else:
        notifications = AttendanceNotification.objects.none()
    
    # Pagination
    paginator = Paginator(notifications, 20)  # 20 notifications per page
    page_number = request.GET.get('page')
    notifications_page = paginator.get_page(page_number)
    
    context = {
        'notifications': notifications_page
    }
    
    return render(request, 'attendance/notifications.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def create_notification(request):
    """
    Create a new attendance notification.
    """
    user = request.user
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        message = request.POST.get('message')
        send_to_parent = 'send_to_parent' in request.POST
        
        if not (student_id and message):
            messages.error(request, "Student and message are required.")
            return redirect('attendance:create_notification')
        
        try:
            student = Student.objects.get(id=student_id)
            
            # Check teacher permissions
            if is_teacher(user):
                teacher = user.teacher
                # Check if teacher teaches this student
                student_class_subjects = ClassSubject.objects.filter(students=student)
                has_permission = (
                    ClassRoom.objects.filter(class_teacher=teacher, subjects__in=student_class_subjects).exists() or
                    ClassSubject.objects.filter(teacher=teacher, students=student).exists()
                )
                
                if not has_permission:
                    messages.error(request, "You don't have permission to create a notification for this student.")
                    return redirect('attendance:notifications')
            
            # Create notification
            notification = AttendanceNotification.objects.create(
                student=student,
                message=message,
                sent_to_parent=send_to_parent
            )
            
            messages.success(request, f"Notification for {student.user.get_full_name()} has been created.")
            return redirect('attendance:notifications')
        
        except Student.DoesNotExist:
            messages.error(request, "Selected student does not exist.")
            return redirect('attendance:create_notification')
    
    # GET request
    # Get students for dropdown based on user role
    if is_admin(user):
        students = Student.objects.all().order_by('user__first_name', 'user__last_name')
    elif is_teacher(user):
        teacher = user.teacher
        taught_classes = ClassRoom.objects.filter(
            Q(class_teacher=teacher) | 
            Q(subjects__teacher=teacher)
        ).distinct()
        
        students = Student.objects.filter(
            enrolled_subjects__classroom__in=taught_classes
        ).distinct().order_by('user__first_name', 'user__last_name')
    else:
        students = Student.objects.none()
    
    context = {
        'students': students
    }
    
    return render(request, 'attendance/create_notification.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def send_notification(request, notification_id):
    """
    Send a notification to parent.
    """
    notification = get_object_or_404(AttendanceNotification, id=notification_id)
    
    # Check permissions
    user = request.user
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        # Check if teacher teaches this student
        student = notification.student
        student_class_subjects = ClassSubject.objects.filter(students=student)
        has_permission = (
            ClassRoom.objects.filter(class_teacher=teacher, subjects__in=student_class_subjects).exists() or
            ClassSubject.objects.filter(teacher=teacher, students=student).exists()
        )
    
    if not has_permission:
        messages.error(request, "You don't have permission to send this notification.")
        return redirect('attendance:notifications')
    
    # Mark as sent to parent
    notification.sent_to_parent = True
    notification.save()
    
    # In a real system, this would trigger an email/SMS to the parent
    # For this demo, we'll just mark it as sent
    
    messages.success(request, f"Notification has been sent to {notification.student.user.get_full_name()}'s parent.")
    return redirect('attendance:notifications')

@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read.
    """
    notification = get_object_or_404(AttendanceNotification, id=notification_id)
    user = request.user
    
    # Check permissions
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        # Check if teacher teaches this student
        student = notification.student
        student_class_subjects = ClassSubject.objects.filter(students=student)
        has_permission = (
            ClassRoom.objects.filter(class_teacher=teacher, subjects__in=student_class_subjects).exists() or
            ClassSubject.objects.filter(teacher=teacher, students=student).exists()
        )
    
    elif is_student(user):
        # Students can only mark their own notifications
        has_permission = (user.student == notification.student)
    
    elif is_parent(user):
        # Parents can mark notifications for their children
        try:
            parent = user.parent
            has_permission = parent.children.filter(id=notification.student.id).exists()
        except Exception:
            pass
    
    if not has_permission:
        messages.error(request, "You don't have permission to mark this notification as read.")
        return redirect('attendance:notifications')
    
    # Mark as read
    notification.is_read = True
    notification.save()
    
    messages.success(request, "Notification has been marked as read.")
    return redirect('attendance:notifications')

# Teacher Views
@login_required
@user_passes_test(is_teacher)
def teacher_attendance_dashboard(request):
    """
    Dashboard for teachers to manage attendance for their classes.
    """
    teacher = request.user.teacher
    
    # Get classes taught by this teacher
    classes = ClassRoom.objects.filter(
        Q(class_teacher=teacher) | 
        Q(subjects__teacher=teacher)
    ).distinct()
    
    # Today's date
    today = timezone.now().date()
    
    # Check which classes already have attendance taken today
    attendance_status = {}
    
    for classroom in classes:
        attendance_status[classroom.id] = AttendanceRecord.objects.filter(
            classroom=classroom, 
            date=today
        ).exists()
    
    # Recent records
    recent_records = AttendanceRecord.objects.filter(
        Q(classroom__class_teacher=teacher) |
        Q(classroom__subjects__teacher=teacher)
    ).distinct().order_by('-date')[:10]
    
    # Classes with low attendance (less than 80%)
    low_attendance_classes = []
    
    for classroom in classes:
        # Get attendance records for the last 30 days
        thirty_days_ago = today - timedelta(days=30)
        attendance_records = AttendanceRecord.objects.filter(
            classroom=classroom,
            date__gte=thirty_days_ago
        )
        
        if attendance_records.exists():
            # Get all student attendances
            student_attendances = StudentAttendance.objects.filter(
                attendance_record__in=attendance_records
            )
            
            total = student_attendances.count()
            present = student_attendances.filter(status='PRESENT').count()
            
            if total > 0:
                attendance_percentage = (present / total) * 100
                
                if attendance_percentage < 80:
                    low_attendance_classes.append({
                        'classroom': classroom,
                        'percentage': attendance_percentage
                    })
    
    context = {
        'classes': classes,
        'attendance_status': attendance_status,
        'recent_records': recent_records,
        'low_attendance_classes': low_attendance_classes,
        'today': today
    }
    
    return render(request, 'attendance/teacher_dashboard.html', context)

@login_required
@user_passes_test(is_teacher)
def teacher_classes(request):
    """
    Display all classes taught by the teacher with attendance statistics.
    """
    teacher = request.user.teacher
    
    # Get classes taught by this teacher
    classes = ClassRoom.objects.filter(
        Q(class_teacher=teacher) | 
        Q(subjects__teacher=teacher)
    ).distinct().order_by('name', 'section')
    
    # Calculate attendance statistics for each class
    class_stats = []
    
    for classroom in classes:
        # Get attendance records for the current academic year
        today = timezone.now().date()
        start_date = today.replace(month=9, day=1)
        
        if today.month < 9:
            start_date = start_date.replace(year=today.year - 1)
        
        attendance_records = AttendanceRecord.objects.filter(
            classroom=classroom,
            date__gte=start_date
        )
        
        record_count = attendance_records.count()
        students = Student.objects.filter(
            enrolled_subjects__classroom=classroom
        ).distinct()
        student_count = students.count()
        
        # Get all student attendances
        student_attendances = StudentAttendance.objects.filter(
            attendance_record__in=attendance_records
        )
        
        total = student_attendances.count()
        present = student_attendances.filter(status='PRESENT').count()
        absent = student_attendances.filter(status='ABSENT').count()
        late = student_attendances.filter(status='LATE').count()
        excused = student_attendances.filter(status='EXCUSED').count()
        
        attendance_percentage = 0
        if total > 0:
            attendance_percentage = (present / total) * 100
        
        class_stats.append({
            'classroom': classroom,
            'record_count': record_count,
            'student_count': student_count,
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'attendance_percentage': attendance_percentage
        })
    
    context = {
        'class_stats': class_stats
    }
    
    return render(request, 'attendance/teacher_classes.html', context)

# Attendance Records
@login_required
def attendance_records(request):
    """
    Display attendance records with filtering options.
    Teachers see records for their classes, admins see all records,
    students see their own records, parents see their children's records.
    """
    user = request.user
    
    # Set up filters
    classroom_filter = request.GET.get('classroom', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            date_from = None
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            date_to = None
    
    # Base query
    records_query = AttendanceRecord.objects.all()
    
    # Filter by role
    if is_admin(user):
        # Admin sees all records (with optional filters)
        pass
    
    elif is_teacher(user):
        teacher = user.teacher
        # Teacher sees records for classes they teach
        records_query = records_query.filter(
            Q(classroom__class_teacher=teacher) |
            Q(classroom__subjects__teacher=teacher)
        ).distinct()
    
    elif is_student(user):
        try:
            student = user.student
            # Student sees records where they're marked
            student_attendance_records = StudentAttendance.objects.filter(
                student=student
            ).values_list('attendance_record_id', flat=True)
            records_query = records_query.filter(id__in=student_attendance_records)
        except Student.DoesNotExist:
            records_query = AttendanceRecord.objects.none()
    
    elif is_parent(user):
        try:
            parent = user.parent
            children = parent.children.all()
            
            # Get attendance records for all children
            if children:
                student_attendance_records = StudentAttendance.objects.filter(
                    student__in=children
                ).values_list('attendance_record_id', flat=True)
                records_query = records_query.filter(id__in=student_attendance_records)
            else:
                records_query = AttendanceRecord.objects.none()
        except Exception:
            records_query = AttendanceRecord.objects.none()
    
    else:
        # Default empty queryset for other users
        records_query = AttendanceRecord.objects.none()
    
    # Apply filters
    if classroom_filter and classroom_filter.isdigit():
        records_query = records_query.filter(classroom_id=classroom_filter)
    
    if date_from:
        records_query = records_query.filter(date__gte=date_from)
    
    if date_to:
        records_query = records_query.filter(date__lte=date_to)
    
    # Order by date (most recent first)
    records_query = records_query.order_by('-date')
    
    # Paginate results
    paginator = Paginator(records_query, 15)  # 15 records per page
    page_number = request.GET.get('page')
    records = paginator.get_page(page_number)
    
    # Get all classrooms for filter dropdown (based on user role)
    if is_admin(user):
        classrooms = ClassRoom.objects.all().order_by('name', 'section')
    elif is_teacher(user):
        teacher = user.teacher
        classrooms = ClassRoom.objects.filter(
            Q(class_teacher=teacher) |
            Q(subjects__teacher=teacher)
        ).distinct().order_by('name', 'section')
    elif is_student(user):
        try:
            student = user.student
            classrooms = ClassRoom.objects.filter(
                subjects__students=student
            ).distinct().order_by('name', 'section')
        except Student.DoesNotExist:
            classrooms = ClassRoom.objects.none()
    elif is_parent(user):
        try:
            parent = user.parent
            children = parent.children.all()
            
            if children:
                classrooms = ClassRoom.objects.filter(
                    subjects__students__in=children
                ).distinct().order_by('name', 'section')
            else:
                classrooms = ClassRoom.objects.none()
        except Exception:
            classrooms = ClassRoom.objects.none()
    else:
        classrooms = ClassRoom.objects.none()
    
    # Get student statuses
    student_statuses = {}
    for record in records_query:
        student_attendances = StudentAttendance.objects.filter(attendance_record=record)
        for sa in student_attendances:
            student_statuses[sa.student.id] = {
                'status': sa.status,
                'remarks': sa.remarks
            }
    
    context = {
        'records': records,
        'classrooms': classrooms,
        'classroom_filter': classroom_filter,
        'date_from': date_from.strftime('%Y-%m-%d') if date_from else '',
        'date_to': date_to.strftime('%Y-%m-%d') if date_to else '',
        'student_statuses': student_statuses
    }
    
    return render(request, 'attendance/records.html', context)

@login_required
def record_detail(request, record_id):
    """
    Display details of a specific attendance record.
    """
    record = get_object_or_404(AttendanceRecord, id=record_id)
    user = request.user
    
    # Check user permissions
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        has_permission = (record.taken_by == teacher or 
                        record.classroom.class_teacher == teacher or
                        ClassSubject.objects.filter(classroom=record.classroom, teacher=teacher).exists())
    
    elif is_student(user):
        try:
            student = user.student
            has_permission = StudentAttendance.objects.filter(
                attendance_record=record,
                student=student
            ).exists()
        except Student.DoesNotExist:
            pass
    
    elif is_parent(user):
        try:
            parent = user.parent
            children = parent.children.all()
            
            has_permission = StudentAttendance.objects.filter(
                attendance_record=record,
                student__in=children
            ).exists()
        except Exception:
            pass
    
    if not has_permission:
        messages.error(request, "You don't have permission to view this attendance record.")
        return redirect('attendance:records')
    
    # Get student attendances based on user role
    if is_parent(user):
        parent = user.parent
        # Only get records for parent's children
        student_attendances = StudentAttendance.objects.filter(
            attendance_record=record,
            student__in=parent.children.all()
        ).select_related('student', 'student__user').order_by(
            'student__user__first_name', 'student__user__last_name'
        )
    else:
        # Get all student attendances for this record
        student_attendances = StudentAttendance.objects.filter(
            attendance_record=record
        ).select_related('student', 'student__user').order_by(
            'student__user__first_name', 'student__user__last_name'
        )
    
    # Calculate statistics based on filtered attendance records
    stats = {
        'total': student_attendances.count(),
        'present': student_attendances.filter(status='PRESENT').count(),
        'absent': student_attendances.filter(status='ABSENT').count(),
        'late': student_attendances.filter(status='LATE').count(),
        'excused': student_attendances.filter(status='EXCUSED').count(),
    }

    # Add full class stats for teachers and admins
    if is_teacher(user) or is_admin(user):
        all_attendances = StudentAttendance.objects.filter(attendance_record=record)
        stats.update({
            'class_total': all_attendances.count(),
            'class_present': all_attendances.filter(status='PRESENT').count(),
            'class_absent': all_attendances.filter(status='ABSENT').count(),
            'class_late': all_attendances.filter(status='LATE').count(),
            'class_excused': all_attendances.filter(status='EXCUSED').count(),
        })
    
    # Calculate percentages
    if stats['total'] > 0:
        stats['present_percent'] = (stats['present'] / stats['total']) * 100
        stats['absent_percent'] = (stats['absent'] / stats['total']) * 100
        stats['late_percent'] = (stats['late'] / stats['total']) * 100
        stats['excused_percent'] = (stats['excused'] / stats['total']) * 100
    else:
        stats['present_percent'] = 0
        stats['absent_percent'] = 0
        stats['late_percent'] = 0
        stats['excused_percent'] = 0
    
    context = {
        'record': record,
        'student_attendances': student_attendances,
        'stats': stats,
        'is_teacher': is_teacher(user),
        'is_admin': is_admin(user)
    }
    
    return render(request, 'attendance/record_detail.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def edit_record(request, record_id):
    """
    Edit an attendance record.
    """
    record = get_object_or_404(AttendanceRecord, id=record_id)
    user = request.user
    
    # Check teacher permissions
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        has_permission = (record.taken_by == teacher or 
                        record.classroom.class_teacher == teacher or
                        Student.objects.filter(enrolled_subjects__classroom=record.classroom, teacher=teacher).exists())
    
    if not has_permission:
        messages.error(request, "You don't have permission to edit this attendance record.")
        return redirect('attendance:records')
    
    if request.method == 'POST':
        # Update record notes
        record.notes = request.POST.get('notes', '')
        record.save()
        
        # Get all students in this class
        class_subjects = ClassSubject.objects.filter(classroom=record.classroom)
        students = Student.objects.filter(
            enrolled_subjects__in=class_subjects
        ).distinct()
        
        # Update student attendances
        for student in students:
            status = request.POST.get(f'status_{student.id}', 'ABSENT')
            remarks = request.POST.get(f'remarks_{student.id}', '')
            
            student_attendance, created = StudentAttendance.objects.update_or_create(
                attendance_record=record,
                student=student,
                defaults={
                    'status': status,
                    'remarks': remarks
                }
            )
        
        messages.success(request, f"Attendance record for {record.classroom.name} on {record.date.strftime('%Y-%m-%d')} has been updated.")
        return redirect('attendance:record_detail', record_id=record.id)
    
    # Get all students in this class
    class_subjects = ClassSubject.objects.filter(classroom=record.classroom)
    students = Student.objects.filter(
        enrolled_subjects__in=class_subjects
    ).distinct().order_by('user__first_name', 'user__last_name')
    
    # Get existing attendance statuses
    student_statuses = {}
    student_attendances = StudentAttendance.objects.filter(attendance_record=record)
    
    for sa in student_attendances:
        student_statuses[sa.student.id] = {
            'status': sa.status,
            'remarks': sa.remarks
        }
    
    context = {
        'record': record,
        'students': students,
        'student_statuses': student_statuses,
        'statuses': AttendanceStatus.choices
    }
    
    return render(request, 'attendance/edit_record.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def delete_record(request, record_id):
    """
    Delete an attendance record.
    """
    record = get_object_or_404(AttendanceRecord, id=record_id)
    user = request.user
    
    # Check teacher permissions
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        has_permission = (record.taken_by == teacher or 
                        record.classroom.class_teacher == teacher)
    
    if not has_permission:
        messages.error(request, "You don't have permission to delete this attendance record.")
        return redirect('attendance:records')
    
    if request.method == 'POST':
        classroom_name = record.classroom.name
        record_date = record.date.strftime('%Y-%m-%d')
        
        # Delete the record (will cascade to student attendances)
        record.delete()
        
        messages.success(request, f"Attendance record for {classroom_name} on {record_date} has been deleted.")
        return redirect('attendance:records')
    
    context = {
        'record': record
    }
    
    return render(request, 'attendance/delete_record.html', context)

# Student Attendance
@login_required
def student_attendance(request, student_id):
    """
    View attendance records for a specific student.
    """
    student = get_object_or_404(Student, id=student_id)
    user = request.user
    
    # Check permissions
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        # Check if teacher teaches this student
        student_class_subjects = ClassSubject.objects.filter(students=student)
        has_permission = (
            ClassRoom.objects.filter(class_teacher=teacher, subjects__in=student_class_subjects).exists() or
            ClassSubject.objects.filter(teacher=teacher, students=student).exists()
        )
    
    elif is_student(user):
        # Students can only view their own attendance
        has_permission = (user.student == student)
    
    elif is_parent(user):
        try:
            parent = user.parent
            # Parents can view their children's attendance
            has_permission = parent.children.filter(id=student.id).exists()
        except Exception:
            pass
    
    if not has_permission:
        messages.error(request, "You don't have permission to view this student's attendance.")
        return redirect('attendance:records')
    
    # Get attendance records for this student
    student_attendances = StudentAttendance.objects.filter(
        student=student
    ).select_related(
        'attendance_record',
        'attendance_record__classroom'
    ).order_by('-attendance_record__date')
    
    # Filter options
    class_filter = request.GET.get('class', None)
    period_filter = request.GET.get('period', 'all')
    
    # Apply class filter
    if class_filter and class_filter.isdigit():
        student_attendances = student_attendances.filter(attendance_record__classroom_id=class_filter)
    
    # Apply period filter
    today = timezone.now().date()
    
    if period_filter == 'current_month':
        # Current month
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        student_attendances = student_attendances.filter(
            attendance_record__date__range=[first_day, last_day]
        )
        period_label = f"Current Month ({first_day.strftime('%b %Y')})"
    
    elif period_filter == 'current_term':
        # Simplified term calculation (adjust based on your school calendar)
        # Assuming terms are Jan-Apr, May-Aug, Sep-Dec
        month = today.month
        if month <= 4:
            first_day = today.replace(month=1, day=1)
            last_day = today.replace(month=4, day=30)
        elif month <= 8:
            first_day = today.replace(month=5, day=1)
            last_day = today.replace(month=8, day=31)
        else:
            first_day = today.replace(month=9, day=1)
            last_day = today.replace(month=12, day=31)
        
        student_attendances = student_attendances.filter(
            attendance_record__date__range=[first_day, last_day]
        )
        period_label = f"Current Term ({first_day.strftime('%b %d')} - {last_day.strftime('%b %d, %Y')})"
    
    elif period_filter == 'current_year':
        # Academic year (assuming Sep-Aug)
        if today.month >= 9:
            first_day = today.replace(month=9, day=1)
            last_day = today.replace(year=today.year + 1, month=8, day=31)
        else:
            first_day = today.replace(year=today.year - 1, month=9, day=1)
            last_day = today.replace(month=8, day=31)
        
        student_attendances = student_attendances.filter(
            attendance_record__date__range=[first_day, last_day]
        )
        period_label = f"Current Academic Year ({first_day.strftime('%b %Y')} - {last_day.strftime('%b %Y')})"
    
    else:
        period_filter = 'all'  # Reset for template context
        period_label = "All Time"
    
    # Calculate attendance statistics
    total_records = student_attendances.count()
    present_count = student_attendances.filter(status='PRESENT').count()
    absent_count = student_attendances.filter(status='ABSENT').count()
    late_count = student_attendances.filter(status='LATE').count()
    excused_count = student_attendances.filter(status='EXCUSED').count()
    
    # Calculate attendance percentage
    attendance_percentage = 0
    if total_records > 0:
        attendance_percentage = (present_count / total_records) * 100
    
    # Get attendance by class
    class_stats = {}
    
    class_subjects = ClassSubject.objects.filter(students=student)
    classrooms = ClassRoom.objects.filter(subjects__in=class_subjects).distinct()
    
    for classroom in classrooms:
        class_attendances = student_attendances.filter(attendance_record__classroom=classroom)
        class_total = class_attendances.count()
        class_present = class_attendances.filter(status='PRESENT').count()
        
        class_percentage = 0
        if class_total > 0:
            class_percentage = (class_present / class_total) * 100
        
        class_stats[classroom.id] = {
            'name': f"{classroom.name} {classroom.section or ''}".strip(),
            'total': class_total,
            'present': class_present,
            'percentage': class_percentage
        }
    
    # Paginate results
    paginator = Paginator(student_attendances, 15)  # 15 records per page
    page_number = request.GET.get('page')
    attendance_page = paginator.get_page(page_number)
    
    # Generate attendance trend data
    trend_dates = []
    trend_present = []
    trend_absent = []
    trend_late = []
    trend_excused = []
    
    # Get last 30 days attendance
    for i in range(29, -1, -1):
        date = timezone.now().date() - timezone.timedelta(days=i)
        attendance = student_attendances.filter(attendance_record__date=date).first()
        
        trend_dates.append(date.strftime('%Y-%m-%d'))
        if attendance:
            trend_present.append(1 if attendance.status == 'PRESENT' else 0)
            trend_absent.append(1 if attendance.status == 'ABSENT' else 0)
            trend_late.append(1 if attendance.status == 'LATE' else 0)
            trend_excused.append(1 if attendance.status == 'EXCUSED' else 0)
        else:
            trend_present.append(0)
            trend_absent.append(0)
            trend_late.append(0)
            trend_excused.append(0)

    attendance_trend_data = {
        'labels': trend_dates,
        'present': trend_present,
        'absent': trend_absent,
        'late': trend_late,
        'excused': trend_excused
    }

    context = {
        'student': student,
        'attendances': attendance_page,
        'total_records': total_records,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'attendance_percentage': attendance_percentage,
        'class_stats': class_stats,
        'classrooms': classrooms,
        'class_filter': class_filter,
        'period_filter': period_filter,
        'period_label': period_label,
        'attendance_trend_data': json.dumps(attendance_trend_data),
    }
    
    return render(request, 'attendance/student_record.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def mark_attendance(request, class_id, date=None):
    """
    Mark attendance for an entire class.
    """
    # Redirect to take_class_attendance with the specified date
    if date:
        return redirect(f"/attendance/take-class-attendance/{class_id}/?date={date}")
    else:
        return redirect(f"/attendance/take-class-attendance/{class_id}/")

# Student Views
@login_required
@user_passes_test(lambda u: u.role == 'STUDENT')
def my_attendance(request):
    """
    Display a student's attendance records with statistics and filtering options.
    Shows attendance percentage, days present/absent/late, and detailed records.
    """
    try:
        # Get the current student
        student = Student.objects.get(user=request.user)
        
        # Get filter parameter
        period = request.GET.get('period', 'all')
        
        # Base query for attendance records
        attendance_records_query = StudentAttendance.objects.filter(
            student=student
        ).select_related(
            'attendance_record', 
            'attendance_record__classroom',
            'attendance_record__taken_by',
            'attendance_record__taken_by__user'
        ).order_by('-attendance_record__date')
        
        # Apply period filter
        today = timezone.now().date()
        if period == 'current_month':
            # Current month records
            first_day = today.replace(day=1)
            last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            attendance_records_query = attendance_records_query.filter(
                attendance_record__date__range=[first_day, last_day]
            )
            period_description = f"Current Month ({first_day.strftime('%b %Y')})"
        elif period == 'current_term':
            # Simplified term calculation - adjust based on your school calendar
            # Assuming terms are Jan-Apr, May-Aug, Sep-Dec
            month = today.month
            if month <= 4:
                first_day = today.replace(month=1, day=1)
                last_day = today.replace(month=4, day=30)
            elif month <= 8:
                first_day = today.replace(month=5, day=1)
                last_day = today.replace(month=8, day=31)
            else:
                first_day = today.replace(month=9, day=1)
                last_day = today.replace(month=12, day=31)
            
            attendance_records_query = attendance_records_query.filter(
                attendance_record__date__range=[first_day, last_day]
            )
            period_description = f"Current Term ({first_day.strftime('%b %d')} - {last_day.strftime('%b %d, %Y')})"
        elif period == 'current_year':
            # Academic year (assuming Sep-Aug)
            if today.month >= 9:
                first_day = today.replace(month=9, day=1)
                last_day = today.replace(year=today.year + 1, month=8, day=31)
            else:
                first_day = today.replace(year=today.year - 1, month=9, day=1)
                last_day = today.replace(month=8, day=31)
            
            attendance_records_query = attendance_records_query.filter(
                attendance_record__date__range=[first_day, last_day]
            )
            period_description = f"Current Academic Year ({first_day.strftime('%b %Y')} - {last_day.strftime('%b %Y')})"
        else:
            period = 'all'  # Reset to 'all' for template context
            period_description = "All Time"
        
        # Calculate attendance statistics
        records_with_status = attendance_records_query.values('status').annotate(count=Count('status'))
        
        # Initialize counters
        days_present = 0
        days_absent = 0
        days_late = 0
        days_excused = 0
        
        # Process counts by status
        for record in records_with_status:
            if record['status'] == 'PRESENT':
                days_present = record['count']
            elif record['status'] == 'ABSENT':
                days_absent = record['count']
            elif record['status'] == 'LATE':
                days_late = record['count']
            elif record['status'] == 'EXCUSED':
                days_excused = record['count']
        
        # Calculate total days and attendance percentage
        total_days = days_present + days_absent + days_late + days_excused
        attendance_percentage = (days_present / total_days * 100) if total_days > 0 else 0
        
        # Get weekly statistics (last 7 days)
        one_week_ago = today - timedelta(days=7)
        weekly_records = attendance_records_query.filter(attendance_record__date__gte=one_week_ago)
        weekly_stats = weekly_records.values('status').annotate(count=Count('status'))
        
        # Initialize weekly counters
        weekly_present = 0
        weekly_absent = 0
        weekly_late = 0
        weekly_excused = 0
        
        # Process weekly counts by status
        for record in weekly_stats:
            if record['status'] == 'PRESENT':
                weekly_present = record['count']
            elif record['status'] == 'ABSENT':
                weekly_absent = record['count']
            elif record['status'] == 'LATE':
                weekly_late = record['count']
            elif record['status'] == 'EXCUSED':
                weekly_excused = record['count']
        
        # Calculate weekly total and percentage
        weekly_total = weekly_present + weekly_absent + weekly_late + weekly_excused
        weekly_attendance_percentage = (weekly_present / weekly_total * 100) if weekly_total > 0 else 0
        
        # Get recent records for trend display (last 10 school days)
        recent_records = attendance_records_query[:10]
        
        # Calculate monthly overview data
        first_day_month = today.replace(day=1)
        last_day_month = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        monthly_records = attendance_records_query.filter(
            attendance_record__date__range=[first_day_month, last_day_month]
        )
        monthly_stats = monthly_records.values('status').annotate(count=Count('status'))
        
        # Prepare monthly data for chart
        monthly_data = {}
        monthly_present = 0
        monthly_absent = 0
        monthly_late = 0
        monthly_excused = 0
        
        for record in monthly_stats:
            if record['status'] == 'PRESENT':
                monthly_present = record['count']
            elif record['status'] == 'ABSENT':
                monthly_absent = record['count']
            elif record['status'] == 'LATE':
                monthly_late = record['count']
            elif record['status'] == 'EXCUSED':
                monthly_excused = record['count']
        
        monthly_total = monthly_present + monthly_absent + monthly_late + monthly_excused
        
        if monthly_total > 0:
            monthly_data = {
                'present_percentage': round(monthly_present / monthly_total * 100),
                'absent_percentage': round(monthly_absent / monthly_total * 100),
                'late_percentage': round(monthly_late / monthly_total * 100),
                'excused_percentage': round(monthly_excused / monthly_total * 100),
            }
        
        # Get class-wise attendance stats
        class_subjects = ClassSubject.objects.filter(students=student)
        classrooms = ClassRoom.objects.filter(subjects__in=class_subjects).distinct()
        
        class_stats = []
        for classroom in classrooms:
            class_records = attendance_records_query.filter(attendance_record__classroom=classroom)
            class_total = class_records.count()
            
            if class_total > 0:
                class_present = class_records.filter(status='PRESENT').count()
                class_percentage = (class_present / class_total) * 100
                
                class_stats.append({
                    'classroom': classroom,
                    'total': class_total,
                    'present': class_present,
                    'percentage': class_percentage
                })
        
        # Sort by class name
        class_stats.sort(key=lambda x: x['classroom'].name)
        
        # Paginate attendance records
        paginator = Paginator(attendance_records_query, 15)  # 15 records per page
        page_number = request.GET.get('page')
        attendance_records = paginator.get_page(page_number)
        
        context = {
            'student': student,
            'attendance_records': attendance_records,
            'days_present': days_present,
            'days_absent': days_absent,
            'days_late': days_late,
            'days_excused': days_excused,
            'total_days': total_days,
            'attendance_percentage': attendance_percentage,
            'weekly_present': weekly_present,
            'weekly_absent': weekly_absent,
            'weekly_late': weekly_late,
            'weekly_excused': weekly_excused,
            'weekly_attendance_percentage': weekly_attendance_percentage,
            'recent_records': recent_records,
            'monthly_data': monthly_data,
            'class_stats': class_stats,
            'period': period,
            'period_description': period_description,
        }
        
        return render(request, 'attendance/my_attendance.html', context)
    
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found.")
        return redirect('dashboard:student_dashboard')

# Parent Views
@login_required
@user_passes_test(lambda u: u.role == 'PARENT')
def parent_children_attendance(request):
    """
    Display attendance overview for all children of a parent.
    """
    try:
        parent = request.user.parent
        children = parent.children.all()
        
        children_attendance = []
        
        for child in children:
            # Get child's attendance records - using select_related for better performance
            child_attendance = StudentAttendance.objects.filter(
                student=child
            ).select_related(
                'attendance_record', 
                'attendance_record__classroom'
            )
            
            # Calculate attendance statistics
            total_records = child_attendance.count()
            present_count = child_attendance.filter(status='PRESENT').count()
            absent_count = child_attendance.filter(status='ABSENT').count()
            late_count = child_attendance.filter(status='LATE').count()
            excused_count = child_attendance.filter(status='EXCUSED').count()
            
            # Calculate attendance percentage
            attendance_percentage = 0
            if total_records > 0:
                attendance_percentage = (present_count / total_records) * 100
            
            # Get recent attendance records
            recent_records = child_attendance.order_by('-attendance_record__date')[:5]
            
            children_attendance.append({
                'student': child,
                'total_records': total_records,
                'present_count': present_count,
                'absent_count': absent_count,
                'late_count': late_count,
                'excused_count': excused_count,
                'attendance_percentage': attendance_percentage,
                'recent_records': recent_records
            })
        
        context = {
            'children_attendance': children_attendance,
            'today': timezone.now().date()
        }
        
        return render(request, 'attendance/parent_children_attendance.html', context)
    
    except Exception as e:
        # Log the actual exception for debugging
        import traceback
        print(f"Error in parent_children_attendance: {str(e)}")
        print(traceback.format_exc())
        
        messages.error(request, f"Error retrieving children's attendance: {str(e)}")
        return redirect('dashboard:parent_dashboard')

@login_required
@user_passes_test(lambda u: u.role == 'PARENT')
def parent_child_attendance(request, student_id):
    """
    Display detailed attendance for a specific child of a parent.
    """
    try:
        parent = request.user.parent
        student = get_object_or_404(Student, id=student_id)
        
        # Check if this student is a child of the parent
        if not parent.children.filter(id=student.id).exists():
            messages.error(request, "You do not have permission to view this student's attendance.")
            return redirect('attendance:parent_children_attendance')
        
        # Now the same logic as student_attendance view but for a parent
        return student_attendance(request, student_id)
    
    except Exception as e:
        messages.error(request, f"Error retrieving child's attendance: {str(e)}")
        return redirect('attendance:parent_children_attendance')

# Attendance Reports
@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def attendance_reports(request):
    """
    Display attendance reports and provide options to generate new reports.
    """
    user = request.user
    
    # Get existing reports based on role
    if is_admin(user):
        reports = AttendanceReport.objects.all().order_by('-generated_at')
    elif is_teacher(user):
        teacher = user.teacher
        reports = AttendanceReport.objects.filter(
            Q(created_by=user) |
            Q(classroom__class_teacher=teacher) |
            Q(classroom__subjects__teacher=teacher)
        ).distinct().order_by('-generated_at')
    else:
        reports = AttendanceReport.objects.none()
    
    # Filter options
    classroom_filter = request.GET.get('classroom', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    period_type = request.GET.get('period_type', None)
    
    # Apply filters
    if classroom_filter and classroom_filter.isdigit():
        reports = reports.filter(classroom_id=classroom_filter)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            reports = reports.filter(created_at__date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d'). date()
            reports = reports.filter(created_at__date__lte=date_to)
        except ValueError:
            pass
    
    if period_type:
        reports = reports.filter(period_type=period_type)
    
    # Get classrooms for filter dropdown
    if is_admin(user):
        classrooms = ClassRoom.objects.all().order_by('name', 'section')
    elif is_teacher(user):
        teacher = user.teacher
        classrooms = ClassRoom.objects.filter(
            Q(class_teacher=teacher) | 
            Q(subjects__teacher=teacher)
        ).distinct().order_by('name', 'section')
    else:
        classrooms = ClassRoom.objects.none()
    
    context = {
        'reports': reports,
        'classrooms': classrooms,
        'classroom_filter': classroom_filter,
        'date_from': date_from.strftime('%Y-%m-%d') if date_from else '',
        'date_to': date_to.strftime('%Y-%m-%d') if date_to else '',
        'period_type': period_type,
        'report_types': AttendanceReport.REPORT_TYPES
    }
    
    return render(request, 'attendance/reports.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def generate_report(request, student_id=None):
    """
    Generate a new attendance report. If student_id is provided,
    generates a report for a single student.
    """
    user = request.user

    if student_id:
        # Generate report for individual student
        student = get_object_or_404(Student, id=student_id)
        today = timezone.now().date()
        start_date = today.replace(month=9, day=1)  # Start of academic year
        if today.month < 9:
            start_date = start_date.replace(year=today.year - 1)

        # Get all attendance records for this student
        student_attendances = StudentAttendance.objects.filter(
            student=student,
            attendance_record__date__range=[start_date, today]
        ).select_related('attendance_record', 'attendance_record__classroom')

        # Calculate statistics
        total_records = student_attendances.count()
        present_count = student_attendances.filter(status='PRESENT').count()
        absent_count = student_attendances.filter(status='ABSENT').count()
        late_count = student_attendances.filter(status='LATE').count()
        excused_count = student_attendances.filter(status='EXCUSED').count()

        attendance_percentage = (present_count / total_records * 100) if total_records > 0 else 0

        # Generate report title
        report_title = f"Attendance Report for {student.user.get_full_name()} ({start_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')})"

        # Prepare report data
        report_data = {
            'type': 'individual',
            'student_name': student.user.get_full_name(),
            'period': f"{start_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}",
            'generated_by': user.get_full_name(),
            'total_days': total_records,
            'stats': {
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'excused': excused_count,
                'percentage': round(attendance_percentage, 2)
            },
            'records': []
        }

        # Add detailed attendance records
        for attendance in student_attendances.order_by('-attendance_record__date'):
            report_data['records'].append({
                'date': attendance.attendance_record.date.strftime('%Y-%m-%d'),
                'class': attendance.attendance_record.classroom.name,
                'status': attendance.status,
                'remarks': attendance.remarks
            })

        # Create the report
        report = AttendanceReport.objects.create(
            title=report_title,
            report_type='individual',
            data=report_data,
            created_by=user,
            date_range_start=start_date,
            date_range_end=today
        )

        messages.success(request, f"Individual report for {student.user.get_full_name()} has been generated successfully.")
        return redirect('attendance:report_detail', report_id=report.id)

    elif request.method == 'POST':
        report_type = request.POST.get('report_type')
        classroom_id = request.POST.get('classroom')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        include_remarks = 'include_remarks' in request.POST
        
        # Validate inputs
        if not (report_type and classroom_id and date_from and date_to):
            messages.error(request, "Please fill in all required fields.")
            return redirect('attendance:generate_report')
        
        try:
            # Get classroom
            classroom = ClassRoom.objects.get(id=classroom_id)
            
            # Check if the teacher is the class teacher
            if is_teacher(user) and classroom.class_teacher != user.teacher:
                messages.error(request, "Only the class teacher can generate reports for this class.")
                return redirect('attendance:reports')

            # Parse dates
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            # Generate report title
            report_title = f"{classroom.name} Attendance Report ({date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')})"
            
            # Get attendance records in date range
            attendance_records = AttendanceRecord.objects.filter(
                classroom=classroom,
                date__range=[date_from, date_to]
            ).order_by('date')
            
            if not attendance_records.exists():
                messages.error(request, "No attendance records found for the selected period.")
                return redirect('attendance:generate_report')
            
            # Get all students in this class
            class_subjects = ClassSubject.objects.filter(classroom=classroom)
            students = Student.objects.filter(
                enrolled_subjects__in=class_subjects
            ).distinct().order_by('user__first_name', 'user__last_name')
            
            # Calculate statistics based on report type
            report_data = {
                'type': report_type,
                'classroom': classroom.name,
                'period': f"{date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}",
                'generated_by': user.get_full_name(),
                'total_days': attendance_records.count(),
                'students': []
            }
            
            for student in students:
                student_attendances = StudentAttendance.objects.filter(
                    attendance_record__in=attendance_records,
                    student=student
                )
                
                present_count = student_attendances.filter(status='PRESENT').count()
                absent_count = student_attendances.filter(status='ABSENT').count()
                late_count = student_attendances.filter(status='LATE').count()
                excused_count = student_attendances.filter(status='EXCUSED').count()
                
                total_count = present_count + absent_count + late_count + excused_count
                attendance_percentage = 0
                if total_count > 0:
                    attendance_percentage = (present_count / total_count) * 100
                
                student_data = {
                    'name': student.user.get_full_name(),
                    'present': present_count,
                    'absent': absent_count,
                    'late': late_count,
                    'excused': excused_count,
                    'total': total_count,
                    'percentage': round(attendance_percentage, 2)
                }
                
                if include_remarks:
                    # Add remarks from attendance records
                    remarks = []
                    for att in student_attendances.exclude(remarks='').order_by('-attendance_record__date'):
                        remarks.append({
                            'date': att.attendance_record.date.strftime('%Y-%m-%d'),
                            'text': att.remarks,
                            'status': att.status
                        })
                    student_data['remarks'] = remarks
                
                report_data['students'].append(student_data)
            
            # Create the report
            report = AttendanceReport.objects.create(
                title=report_title,
                report_type=report_type,
                classroom=classroom,
                date_range_start=date_from,
                date_range_end=date_to,
                data=report_data,
                created_by=user
            )
            
            messages.success(request, f"Report '{report_title}' has been generated successfully.")
            return redirect('attendance:report_detail', report_id=report.id)
        
        except ClassRoom.DoesNotExist:
            messages.error(request, "Selected classroom does not exist.")
        except ValueError as e:
            messages.error(request, f"Invalid date format: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error generating report: {str(e)}")
        
        return redirect('attendance:generate_report')
    
    # GET request
    # Get classrooms based on user role
    if is_admin(user):
        classrooms = ClassRoom.objects.all().order_by('name', 'section')
    elif is_teacher(user):
        teacher = user.teacher
        classrooms = ClassRoom.objects.filter(
            Q(class_teacher=teacher) | 
            Q(subjects__teacher=teacher)
        ).distinct().order_by('name', 'section')
    else:
        classrooms = ClassRoom.objects.none()
    
    context = {
        'classrooms': classrooms,
        'report_types': AttendanceReport.REPORT_TYPES
    }
    
    return render(request, 'attendance/generate_report.html', context)

@login_required
def report_detail(request, report_id):
    """
    Display details of a specific attendance report.
    """
    report = get_object_or_404(AttendanceReport, id=report_id)
    user = request.user
    
    # Check permissions
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        has_permission = (
            report.created_by == user or
            report.classroom.class_teacher == teacher or
            ClassSubject.objects.filter(classroom=report.classroom, teacher=teacher).exists()
        )
    
    elif is_student(user):
        student = user.student
        # Students can view reports for their classes
        has_permission = ClassSubject.objects.filter(
            classroom=report.classroom,
            students=student
        ).exists()
    
    elif is_parent(user):
        parent = user.parent
        # Parents can view reports for their children's classes
        has_permission = ClassSubject.objects.filter(
            classroom=report.classroom,
            students__in=parent.children.all()
        ).exists()
    
    if not has_permission:
        messages.error(request, "You don't have permission to view this report.")
        return redirect('attendance:reports')
    
    context = {
        'report': report,
        'report_data': report.data,
        'is_admin_or_teacher': is_admin(user) or is_teacher(user)
    }
    
    return render(request, 'attendance/report_detail.html', context)

@login_required
def print_report(request, report_id):
    """
    Render a printable version of an attendance report.
    """
    report = get_object_or_404(AttendanceReport, id=report_id)
    user = request.user
    
    # Check permissions (same as report_detail)
    has_permission = False
    
    if is_admin(user):
        has_permission = True
    
    elif is_teacher(user):
        teacher = user.teacher
        has_permission = (
            report.created_by == user or
            report.classroom.class_teacher == teacher or
            ClassSubject.objects.filter(classroom=report.classroom, teacher=teacher).exists()
        )
    
    elif is_student(user):
        student = user.student
        has_permission = ClassSubject.objects.filter(
            classroom=report.classroom,
            students=student
        ).exists()
    
    elif is_parent(user):
        parent = user.parent
        has_permission = ClassSubject.objects.filter(
            classroom=report.classroom,
            students__in=parent.children.all()
        ).exists()
    
    if not has_permission:
        messages.error(request, "You don't have permission to print this report.")
        return redirect('attendance:reports')
    
    context = {
        'report': report,
        'report_data': report.data,
        'print_mode': True,
        'school_name': 'Ricas School Management System'  # You may want to get this from settings
    }
    
    return render(request, 'attendance/print_report.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def class_report(request, classroom_id):
    """
    Generate a quick report for a specific class.
    """
    classroom = get_object_or_404(ClassRoom, id=classroom_id)
    user = request.user
    
    # Check teacher permissions
    if is_teacher(user) and not (
        classroom.class_teacher == user.teacher or
        ClassSubject.objects.filter(classroom=classroom, teacher=user.teacher).exists()
    ):
        messages.error(request, "You don't have permission to generate a report for this class.")
        return redirect('attendance:reports')
    
    # Generate title and redirect to generate_report with pre-filled values
    return redirect(f"/attendance/generate-report/?classroom={classroom_id}")

# API views for AJAX functionality
@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def api_mark_attendance(request):
    """
    AJAX endpoint for marking attendance.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'})
    
    try:
        data = json.loads(request.body)
        classroom_id = data.get('classroom_id')
        date = data.get('date')
        student_statuses = data.get('student_statuses', {})
        notes = data.get('notes', '')
        
        if not (classroom_id and date and student_statuses):
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})
        
        # Parse date
        try:
            attendance_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
        
        # Get classroom
        classroom = get_object_or_404(ClassRoom, id=classroom_id)
        
        # Check teacher permissions
        teacher = request.user.teacher
        has_permission = (
            classroom.class_teacher == teacher or
            ClassSubject.objects.filter(classroom=classroom, teacher=teacher).exists()
        )
        
        if not has_permission:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        # Create or get attendance record
        attendance_record, created = AttendanceRecord.objects.get_or_create(
            classroom=classroom,
            date=attendance_date,
            defaults={
                'taken_by': teacher,
                'notes': notes
            }
        )
        
        if not created:
            # Update existing record
            attendance_record.notes = notes
            attendance_record.save()
        
        # Process student attendances
        for student_id, status_data in student_statuses.items():
            try:
                student = Student.objects.get(id=student_id)
                status = status_data.get('status', 'ABSENT')
                remarks = status_data.get('remarks', '')
                
                StudentAttendance.objects.update_or_create(
                    attendance_record=attendance_record,
                    student=student,
                    defaults={
                        'status': status,
                        'remarks': remarks
                    }
                )
            except Student.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True, 
            'record_id': attendance_record.id,
            'message': f"Attendance for {classroom.name} on {attendance_date.strftime('%Y-%m-%d')} has been recorded."
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def api_get_attendance_data(request):
    """
    AJAX endpoint for retrieving attendance data.
    """
    classroom_id = request.GET.get('classroom_id')
    date = request.GET.get('date')
    
    if not (classroom_id and date):
        return JsonResponse({'success': False, 'error': 'Missing required parameters'})
    
    try:
        # Parse date
        attendance_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Get classroom
        classroom = get_object_or_404(ClassRoom, id=classroom_id)
        
        # Check permissions
        user = request.user
        has_permission = False
        
        if is_admin(user):
            has_permission = True
        
        elif is_teacher(user):
            teacher = user.teacher
            has_permission = (
                classroom.class_teacher == teacher or
                ClassSubject.objects.filter(classroom=classroom, teacher=teacher).exists()
            )
        
        if not has_permission:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        # Get attendance record if exists
        attendance_record = AttendanceRecord.objects.filter(
            classroom=classroom,
            date=attendance_date
        ).first()
        
        if not attendance_record:
            return JsonResponse({
                'success': True,
                'exists': False,
                'message': f"No attendance record found for {classroom.name} on {attendance_date.strftime('%Y-%m-%d')}."
            })
        
        # Get student attendances
        student_attendances = StudentAttendance.objects.filter(
            attendance_record=attendance_record
        ).select_related('student', 'student__user')
        
        # Format attendance data
        attendance_data = {
            'record_id': attendance_record.id,
            'classroom': classroom.name,
            'date': attendance_date.strftime('%Y-%m-%d'),
            'notes': attendance_record.notes,
            'taken_by': attendance_record.taken_by.user.get_full_name(),
            'students': {}
        }
        
        for sa in student_attendances:
            attendance_data['students'][sa.student.id] = {
                'name': sa.student.user.get_full_name(),
                'status': sa.status,
                'remarks': sa.remarks
            }
        
        return JsonResponse({
            'success': True,
            'exists': True,
            'data': attendance_data
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def api_get_attendance_stats(request):
    """
    AJAX endpoint for retrieving attendance statistics.
    """
    classroom_id = request.GET.get('classroom_id')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not classroom_id:
        return JsonResponse({'success': False, 'error': 'Missing classroom ID'})
    
    try:
        # Get classroom
        classroom = get_object_or_404(ClassRoom, id=classroom_id)
        
        # Check permissions
        user = request.user
        has_permission = False
        
        if is_admin(user):
            has_permission = True
        
        elif is_teacher(user):
            teacher = user.teacher
            has_permission = (
                classroom.class_teacher == teacher or
                ClassSubject.objects.filter(classroom=classroom, teacher=teacher).exists()
            )
        
        elif is_student(user):
            student = user.student
            has_permission = ClassSubject.objects.filter(
                classroom=classroom,
                students=student
            ).exists()
        
        elif is_parent(user):
            parent = user.parent
            has_permission = ClassSubject.objects.filter(
                classroom=classroom,
                students__in=parent.children.all()
            ).exists()
        
        if not has_permission:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        # Build base query
        records_query = AttendanceRecord.objects.filter(classroom=classroom)
        
        # Apply date filters
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                records_query = records_query.filter(date__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                records_query = records_query.filter(date__lte=date_to)
            except ValueError:
                pass
        
        # Get attendance records
        attendance_records = records_query.order_by('date')
        
        # Get all students in this class
        class_subjects = ClassSubject.objects.filter(classroom=classroom)
        students = Student.objects.filter(
            enrolled_subjects__in=class_subjects
        ).distinct()
        
        # Calculate overall statistics
        total_records = attendance_records.count()
        
        # Get all student attendances
        student_attendances = StudentAttendance.objects.filter(
            attendance_record__in=attendance_records
        )
        
        present_count = student_attendances.filter(status='PRESENT').count()
        absent_count = student_attendances.filter(status='ABSENT').count()
        late_count = student_attendances.filter(status='LATE').count()
        excused_count = student_attendances.filter(status='EXCUSED').count()
        
        total_count = present_count + absent_count + late_count + excused_count
        attendance_percentage = 0
        if total_count > 0:
            attendance_percentage = (present_count / total_count) * 100
        
        # Calculate per-student statistics
        student_stats = []
        
        for student in students:
            student_attendances = StudentAttendance.objects.filter(
                attendance_record__in=attendance_records,
                student=student
            )
            
            student_present = student_attendances.filter(status='PRESENT').count()
            student_absent = student_attendances.filter(status='ABSENT').count()
            student_late = student_attendances.filter(status='LATE').count()
            student_excused = student_attendances.filter(status='EXCUSED').count()
            
            student_total = student_present + student_absent + student_late + student_excused
            student_percentage = 0
            if student_total > 0:
                student_percentage = (student_present / student_total) * 100
            
            student_stats.append({
                'id': student.id,
                'name': student.user.get_full_name(),
                'present': student_present,
                'absent': student_absent,
                'late': student_late,
                'excused': student_excused,
                'total': student_total,
                'percentage': round(student_percentage, 2)
            })
        
        # Sort students by attendance percentage (highest first)
        student_stats.sort(key=lambda x: x['percentage'], reverse=True)
        
        # Calculate daily statistics (for chart)
        daily_stats = []
        
        for record in attendance_records:
            record_attendances = StudentAttendance.objects.filter(attendance_record=record)
            
            record_present = record_attendances.filter(status='PRESENT').count()
            record_absent = record_attendances.filter(status='ABSENT').count()
            record_late = record_attendances.filter(status='LATE').count()
            record_excused = record_attendances.filter(status='EXCUSED').count()
            
            record_total = record_present + record_absent + record_late + record_excused
            record_percentage = 0
            if record_total > 0:
                record_percentage = (record_present / record_total) * 100
            
            daily_stats.append({
                'date': record.date.strftime('%Y-%m-%d'),
                'present': record_present,
                'absent': record_absent,
                'late': record_late,
                'excused': record_excused,
                'total': record_total,
                'percentage': round(record_percentage, 2)
            })
        
        return JsonResponse({
            'success': True,
            'classroom': {
                'id': classroom.id,
                'name': classroom.name,
                'section': classroom.section
            },
            'date_range': {
                'from': date_from.strftime('%Y-%m-%d') if date_from else None,
                'to': date_to.strftime('%Y-%m-%d') if date_to else None
            },
            'total_days': total_records,
            'overall_stats': {
                'present': present_count,
                'absent': absent_count,
                'late': late_count,
                'excused': excused_count,
                'total': total_count,
                'percentage': round(attendance_percentage, 2)
            },
            'student_stats': student_stats,
            'daily_stats': daily_stats
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
