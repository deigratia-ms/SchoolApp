from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.core.exceptions import PermissionDenied

from courses.models import ClassSubject, ClassRoom
from .models import Student, Teacher, Parent

def role_required(role_name):
    """
    Base decorator to check if the user has a specific role.
    
    Args:
        role_name (str): The role name to check ('ADMIN', 'TEACHER', 'STUDENT', 'PARENT')
        
    Returns:
        function: Decorated function that checks the user's role
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role == role_name:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, f"Only {role_name.lower()}s have access to this page.")
                # Redirect to appropriate dashboard based on user role
                if request.user.role == 'ADMIN':
                    return redirect('dashboard:admin_dashboard')
                elif request.user.role == 'TEACHER':
                    return redirect('dashboard:teacher_dashboard')
                elif request.user.role == 'STUDENT':
                    return redirect('dashboard:student_dashboard')
                elif request.user.role == 'PARENT':
                    return redirect('dashboard:parent_dashboard')
                else:
                    return redirect('users:login')
        return wrapper
    return decorator

# Role-specific decorators
def admin_required(view_func):
    """
    Decorator to ensure only admin users can access a view.
    
    Usage:
        @admin_required
        def admin_only_view(request):
            # View logic here
    """
    return role_required('ADMIN')(view_func)

def teacher_required(view_func):
    """
    Decorator to ensure only teacher users can access a view.
    
    Usage:
        @teacher_required
        def teacher_only_view(request):
            # View logic here
    """
    return role_required('TEACHER')(view_func)

def student_required(view_func):
    """
    Decorator to ensure only student users can access a view.
    
    Usage:
        @student_required
        def student_only_view(request):
            # View logic here
    """
    return role_required('STUDENT')(view_func)

def parent_required(view_func):
    """
    Decorator to ensure only parent users can access a view.
    
    Usage:
        @parent_required
        def parent_only_view(request):
            # View logic here
    """
    return role_required('PARENT')(view_func)

def admin_or_teacher_required(view_func):
    """
    Decorator to ensure only admin or teacher users can access a view.
    
    Usage:
        @admin_or_teacher_required
        def admin_or_teacher_view(request):
            # View logic here
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role in ['ADMIN', 'TEACHER']:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Only administrators and teachers have access to this page.")
            # Redirect to appropriate dashboard
            if request.user.role == 'STUDENT':
                return redirect('dashboard:student_dashboard')
            elif request.user.role == 'PARENT':
                return redirect('dashboard:parent_dashboard')
            else:
                return redirect('users:login')
    return wrapper

# Relationship-based permission decorators
def can_view_student_attendance(view_func):
    """
    Decorator to ensure only users with permission can view a student's attendance.
    
    Allowed users:
    - Admins (all students)
    - Teachers (only students they teach)
    - Parents (only their children)
    - Students (only themselves)
    
    This decorator expects a student_id parameter in the view function.
    
    Usage:
        @can_view_student_attendance
        def view_student_attendance(request, student_id):
            # View logic here
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Get the student_id parameter
        student_id = kwargs.get('student_id')
        if not student_id:
            messages.error(request, "Student ID is required.")
            return redirect('dashboard:dashboard')
        
        try:
            student = Student.objects.get(id=student_id)
            user = request.user
            
            # Admins can view all students' attendance
            if user.role == 'ADMIN':
                return view_func(request, *args, **kwargs)
            
            # Students can only view their own attendance
            elif user.role == 'STUDENT':
                if user.student and user.student.id == student.id:
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, "You can only view your own attendance.")
                    return redirect('dashboard:student_dashboard')
            
            # Parents can only view their children's attendance
            elif user.role == 'PARENT':
                try:
                    parent = Parent.objects.get(user=user)
                    if parent.children.filter(id=student.id).exists():
                        return view_func(request, *args, **kwargs)
                    else:
                        messages.error(request, "You can only view your own children's attendance.")
                        return redirect('dashboard:parent_dashboard')
                except Parent.DoesNotExist:
                    messages.error(request, "Parent profile not found.")
                    return redirect('dashboard:parent_dashboard')
            
            # Teachers can only view attendance for students they teach
            elif user.role == 'TEACHER':
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Check if teacher teaches this student
                    student_class_subjects = ClassSubject.objects.filter(students=student)
                    has_permission = (
                        ClassRoom.objects.filter(class_teacher=teacher, subjects__in=student_class_subjects).exists() or
                        ClassSubject.objects.filter(teacher=teacher, students=student).exists()
                    )
                    
                    if has_permission:
                        return view_func(request, *args, **kwargs)
                    else:
                        messages.error(request, "You can only view attendance for students you teach.")
                        return redirect('dashboard:teacher_dashboard')
                except Teacher.DoesNotExist:
                    messages.error(request, "Teacher profile not found.")
                    return redirect('dashboard:teacher_dashboard')
            
            else:
                messages.error(request, "You don't have permission to view this attendance record.")
                return redirect('dashboard:dashboard')
                
        except Student.DoesNotExist:
            messages.error(request, "Student not found.")
            return redirect('dashboard:dashboard')
    
    return wrapper

def can_edit_assignment(view_func):
    """
    Decorator to ensure only users with permission can edit an assignment.
    
    Allowed users:
    - Admins (all assignments)
    - Teachers (only assignments they created or for classes they teach)
    
    This decorator expects an assignment_id parameter in the view function.
    
    Usage:
        @can_edit_assignment
        def edit_assignment(request, assignment_id):
            # View logic here
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Get the assignment_id parameter
        assignment_id = kwargs.get('assignment_id')
        if not assignment_id:
            messages.error(request, "Assignment ID is required.")
            return redirect('assignments:assignment_list')
        
        try:
            # Import Assignment model here to avoid circular imports
            from assignments.models import Assignment
            
            assignment = Assignment.objects.get(id=assignment_id)
            user = request.user
            
            # Admins can edit all assignments
            if user.role == 'ADMIN':
                return view_func(request, *args, **kwargs)
            
            # Teachers can only edit assignments they created or for classes they teach
            elif user.role == 'TEACHER':
                try:
                    teacher = Teacher.objects.get(user=user)
                    
                    # Check if teacher created the assignment
                    if assignment.created_by == user:
                        return view_func(request, *args, **kwargs)
                    
                    # Check if teacher teaches the class this assignment is for
                    has_permission = False
                    
                    if assignment.class_subject:
                        has_permission = (
                            assignment.class_subject.teacher == teacher or
                            assignment.class_subject.classroom.class_teacher == teacher
                        )
                    
                    if has_permission:
                        return view_func(request, *args, **kwargs)
                    else:
                        messages.error(request, "You can only edit assignments you created or for classes you teach.")
                        return redirect('assignments:assignment_detail', assignment_id=assignment.id)
                        
                except Teacher.DoesNotExist:
                    messages.error(request, "Teacher profile not found.")
                    return redirect('dashboard:teacher_dashboard')
            
            else:
                messages.error(request, "Only administrators and teachers can edit assignments.")
                return redirect('assignments:assignment_detail', assignment_id=assignment.id)
                
        except Exception as e:
            messages.error(request, f"Error checking permissions: {str(e)}")
            return redirect('assignments:assignment_list')
    
    return wrapper

def can_manage_class(view_func):
    """
    Decorator to ensure only users with permission can manage a class.
    
    Allowed users:
    - Admins (all classes)
    - Teachers (only classes they teach)
    
    This decorator expects a classroom_id parameter in the view function.
    
    Usage:
        @can_manage_class
        def manage_classroom(request, classroom_id):
            # View logic here
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Get the classroom_id parameter
        classroom_id = kwargs.get('classroom_id')
        if not classroom_id:
            messages.error(request, "Classroom ID is required.")
            return redirect('courses:class_list')
        
        try:
            classroom = ClassRoom.objects.get(id=classroom_id)
            user = request.user
            
            # Admins can manage all classes
            if user.role == 'ADMIN':
                return view_func(request, *args, **kwargs)
            
            # Teachers can only manage classes they teach
            elif user.role == 'TEACHER':
                try:
                    teacher = Teacher.objects.get(user=user)
                    
                    # Check if teacher teaches this class
                    has_permission = (
                        classroom.class_teacher == teacher or
                        ClassSubject.objects.filter(classroom=classroom, teacher=teacher).exists()
                    )
                    
                    if has_permission:
                        return view_func(request, *args, **kwargs)
                    else:
                        messages.error(request, "You can only manage classes you teach.")
                        return redirect('courses:class_list')
                        
                except Teacher.DoesNotExist:
                    messages.error(request, "Teacher profile not found.")
                    return redirect('dashboard:teacher_dashboard')
            
            else:
                messages.error(request, "Only administrators and teachers can manage classes.")
                return redirect('dashboard:dashboard')
                
        except ClassRoom.DoesNotExist:
            messages.error(request, "Classroom not found.")
            return redirect('courses:class_list')
    
    return wrapper

def can_view_child_data(view_func):
    """
    Decorator to ensure only parents can view their children's data or admins can view any child data.
    
    Allowed users:
    - Admins (all students)
    - Parents (only their children)
    
    This decorator expects a student_id parameter in the view function.
    
    Usage:
        @can_view_child_data
        def view_child_data(request, student_id):
            # View logic here
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Get the student_id parameter
        student_id = kwargs.get('student_id')
        if not student_id:
            messages.error(request, "Student ID is required.")
            return redirect('dashboard:dashboard')
        
        try:
            student = Student.objects.get(id=student_id)
            user = request.user
            
            # Admins can view all student data
            if user.role == 'ADMIN':
                return view_func(request, *args, **kwargs)
            
            # Parents can only view their children's data
            elif user.role == 'PARENT':
                try:
                    parent = Parent.objects.get(user=user)
                    if parent.children.filter(id=student.id).exists():
                        return view_func(request, *args, **kwargs)
                    else:
                        messages.error(request, "You can only view your own children's data.")
                        return redirect('dashboard:parent_dashboard')
                except Parent.DoesNotExist:
                    messages.error(request, "Parent profile not found.")
                    return redirect('dashboard:parent_dashboard')
            
            else:
                messages.error(request, "Only administrators and parents have access to this view.")
                return redirect('dashboard:dashboard')
                
        except Student.DoesNotExist:
            messages.error(request, "Student not found.")
            return redirect('dashboard:dashboard')
    
    return wrapper