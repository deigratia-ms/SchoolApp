from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import default_storage
from django.db.models import Q
from django.db import models, transaction
from django.urls import reverse
from django.utils.text import slugify
from .models import Subject, ClassRoom, ClassSubject, CourseMaterial, YouTubeVideo, Schedule
from users.models import Teacher, Student, Parent
from django.forms import modelform_factory, inlineformset_factory
import os
import mimetypes
import json
from datetime import datetime, timedelta
from django.utils import timezone

# Helper function for admin check
def is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'

# Helper function for teacher check
def is_teacher(user):
    return user.is_authenticated and user.role == 'TEACHER'

# Helper function for student check
def is_student(user):
    return user.is_authenticated and user.role == 'STUDENT'

# Helper function for parent check
def is_parent(user):
    return user.is_authenticated and user.role == 'PARENT'

# Helper function to check if teacher is assigned to a class subject
def teacher_assigned_to_class_subject(user, class_subject_id):
    if not is_teacher(user):
        return False
    teacher = user.teacher_profile
    class_subject = get_object_or_404(ClassSubject, id=class_subject_id)
    return class_subject.teacher == teacher

# Classes views
@login_required
def class_list(request):
    # For admin, show all classes
    # For teachers, show classes they teach
    # For students, show classes they're enrolled in
    # For parents, show their children's classes
    if request.user.role == 'ADMIN':
        classes = ClassRoom.objects.all().order_by('name', 'section')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        classes = ClassRoom.objects.filter(
            models.Q(class_teacher=teacher) |
            models.Q(subjects__teacher=teacher)
        ).distinct().order_by('name', 'section')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        class_subjects = ClassSubject.objects.filter(students=student)
        classes = ClassRoom.objects.filter(subjects__in=class_subjects).distinct().order_by('name', 'section')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        class_subjects = ClassSubject.objects.filter(students__in=students)
        classes = ClassRoom.objects.filter(subjects__in=class_subjects).distinct().order_by('name', 'section')
    else:
        classes = ClassRoom.objects.none()

    # Get all teachers for the class teacher assignment dropdown
    teachers = Teacher.objects.all().order_by('user__first_name', 'user__last_name')

    # Get all subjects for the subject dropdown
    subjects = Subject.objects.all().order_by('name')

    return render(request, 'courses/class_list.html', {
        'classes': classes,
        'teachers': teachers,
        'subjects': subjects
    })

@login_required
@user_passes_test(is_admin)
def create_class(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        section = request.POST.get('section')
        capacity = request.POST.get('capacity', 30)
        teacher_id = request.POST.get('class_teacher')
        grade_level = request.POST.get('grade_level')

        if not name:
            messages.error(request, 'Class name is required.')
            return redirect('courses:create_class')

        if not grade_level or not grade_level.isdigit():
            messages.error(request, 'Grade level is required and must be a number.')
            return redirect('courses:create_class')

        try:
            if teacher_id:
                teacher = Teacher.objects.get(id=teacher_id)
            else:
                teacher = None

            classroom = ClassRoom.objects.create(
                name=name,
                section=section,
                capacity=capacity,
                class_teacher=teacher,
                grade_level=int(grade_level)
            )
            messages.success(request, f'Class {classroom.name} {classroom.section or ""} created successfully.')
            return redirect('courses:class_list')
        except Exception as e:
            messages.error(request, f'Error creating class: {str(e)}')
            return redirect('courses:create_class')

    teachers = Teacher.objects.all()
    return render(request, 'courses/create_class.html', {'teachers': teachers})

@login_required
def class_detail(request, class_id):
    classroom = get_object_or_404(ClassRoom, id=class_id)
    class_subjects = ClassSubject.objects.filter(classroom=classroom)

    # Check if user has permission to view this class
    if request.user.role == 'ADMIN':
        pass  # Admin can view all classes
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if teacher != classroom.class_teacher and not class_subjects.filter(teacher=teacher).exists():
            messages.error(request, 'You do not have permission to view this class.')
            return redirect('courses:class_list')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        if not class_subjects.filter(students=student).exists():
            messages.error(request, 'You do not have permission to view this class.')
            return redirect('courses:class_list')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        if not class_subjects.filter(students__in=students).exists():
            messages.error(request, 'You do not have permission to view this class.')
            return redirect('courses:class_list')
    else:
        messages.error(request, 'You do not have permission to view this class.')
        return redirect('courses:class_list')

    # Get all subjects for this class
    subjects = []
    for class_subject in class_subjects:
        subject_info = {
            'id': class_subject.id,
            'name': class_subject.subject.name,
            'code': class_subject.subject.code,
            'teacher': class_subject.teacher.user.get_full_name() if class_subject.teacher else "No Teacher Assigned",
            'students_count': class_subject.students.count(),
            'materials_count': class_subject.materials.count(),
            'videos_count': class_subject.videos.count(),
        }
        subjects.append(subject_info)

    # Get all teachers for the teacher assignment dropdown
    teachers = Teacher.objects.all().order_by('user__first_name', 'user__last_name')

    context = {
        'classroom': classroom,
        'subjects': subjects,
        'is_class_teacher': request.user.role == 'TEACHER' and request.user.teacher_profile == classroom.class_teacher,
        'is_admin': request.user.role == 'ADMIN',
        'teachers': teachers,
    }

    return render(request, 'courses/class_detail.html', context)

@login_required
@user_passes_test(is_admin)
def edit_class(request, class_id):
    classroom = get_object_or_404(ClassRoom, id=class_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        section = request.POST.get('section')
        capacity = request.POST.get('capacity', 30)
        teacher_id = request.POST.get('class_teacher')
        grade_level = request.POST.get('grade_level')

        if not name:
            messages.error(request, 'Class name is required.')
            return redirect('courses:edit_class', class_id=class_id)

        if not grade_level or not grade_level.isdigit():
            messages.error(request, 'Grade level is required and must be a number.')
            return redirect('courses:edit_class', class_id=class_id)

        try:
            if teacher_id:
                teacher = Teacher.objects.get(id=teacher_id)
            else:
                teacher = None

            classroom.name = name
            classroom.section = section
            classroom.capacity = capacity
            classroom.class_teacher = teacher
            classroom.grade_level = int(grade_level)
            classroom.save()

            messages.success(request, f'Class {classroom.name} {classroom.section or ""} updated successfully.')
            return redirect('courses:class_detail', class_id=class_id)
        except Exception as e:
            messages.error(request, f'Error updating class: {str(e)}')
            return redirect('courses:edit_class', class_id=class_id)

    teachers = Teacher.objects.all()
    context = {
        'classroom': classroom,
        'teachers': teachers,
    }
    return render(request, 'courses/edit_class.html', context)

@login_required
@user_passes_test(is_admin)
def delete_class(request, class_id):
    classroom = get_object_or_404(ClassRoom, id=class_id)

    if request.method == 'POST':
        try:
            classroom_name = f"{classroom.name} {classroom.section or ''}".strip()
            classroom.delete()
            messages.success(request, f'Class {classroom_name} deleted successfully.')
            return redirect('courses:class_list')
        except Exception as e:
            messages.error(request, f'Error deleting class: {str(e)}')
            return redirect('courses:class_detail', class_id=class_id)

    context = {
        'classroom': classroom,
        'class_subjects': ClassSubject.objects.filter(classroom=classroom),
    }
    return render(request, 'courses/delete_class.html', context)

# Subjects views
@login_required
def subject_list(request):
    if request.user.role == 'ADMIN':
        subjects = Subject.objects.all().order_by('name')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(teacher=teacher)
        subject_ids = class_subjects.values_list('subject_id', flat=True).distinct()
        subjects = Subject.objects.filter(id__in=subject_ids).order_by('name')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        class_subjects = ClassSubject.objects.filter(students=student)
        subject_ids = class_subjects.values_list('subject_id', flat=True).distinct()
        subjects = Subject.objects.filter(id__in=subject_ids).order_by('name')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        class_subjects = ClassSubject.objects.filter(students__in=students)
        subject_ids = class_subjects.values_list('subject_id', flat=True).distinct()
        subjects = Subject.objects.filter(id__in=subject_ids).order_by('name')
    else:
        subjects = Subject.objects.none()

    # Add classes and teachers for dropdown menus in the "Add to Class" modal
    classes = ClassRoom.objects.all().order_by('name', 'section')
    teachers = Teacher.objects.all().order_by('user__first_name', 'user__last_name')

    # Add indicators for recent assignments and materials (within the past 7 days)
    one_week_ago = timezone.now() - timedelta(days=7)

    # Get subject IDs with recent assignments
    try:
        # Try to import Assignment model
        from assignments.models import Assignment
        recent_assignments = Assignment.objects.filter(
            created_at__gte=one_week_ago
        ).values_list('class_subject__subject_id', flat=True).distinct()
    except (ImportError, AttributeError):
        recent_assignments = []

    # Get subject IDs with recent materials
    recent_materials = CourseMaterial.objects.filter(
        created_at__gte=one_week_ago
    ).values_list('class_subject__subject_id', flat=True).distinct()

    # Add indicators to subject objects
    for subject in subjects:
        subject.recent_assignments = subject.id in recent_assignments
        subject.recent_materials = subject.id in recent_materials

    context = {
        'subjects': subjects,
        'classes': classes,
        'teachers': teachers
    }

    return render(request, 'courses/subject_list.html', context)

@login_required
@user_passes_test(is_admin)
def create_subject(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description')
        selected_classes = request.POST.getlist('selected_classes')
        teacher_id = request.POST.get('teacher')

        if not name or not code:
            messages.error(request, 'Subject name and code are required.')
            return redirect('courses:create_subject')

        try:
            # Check if subject with same code already exists
            if Subject.objects.filter(code=code).exists():
                messages.error(request, f'Subject with code {code} already exists. Please use a different code.')
                return redirect('courses:create_subject')

            # Create the subject
            subject = Subject.objects.create(
                name=name,
                code=code,
                description=description
            )

            # Apply to selected classes
            created_count = 0

            if selected_classes:
                classrooms = ClassRoom.objects.filter(id__in=selected_classes)

                if teacher_id:
                    try:
                        # If teacher is provided, create class subjects with this teacher
                        teacher = Teacher.objects.get(id=teacher_id)
                        for classroom in classrooms:
                            # Skip if this exact combination already exists (safety check)
                            if not ClassSubject.objects.filter(classroom=classroom, subject=subject).exists():
                                ClassSubject.objects.create(
                                    classroom=classroom,
                                    subject=subject,
                                    teacher=teacher
                                )
                                created_count += 1
                        messages.success(request, f'Subject {subject.name} created and applied to {created_count} classes with teacher {teacher.user.get_full_name()} successfully.')
                    except Teacher.DoesNotExist:
                        # Handle case where teacher doesn't exist
                        messages.warning(request, f'Subject {subject.name} created but selected teacher does not exist. Please assign teachers to each class-subject combination.')
                else:
                    # If no teacher is provided, create class subjects with null teacher
                    for classroom in classrooms:
                        # Skip if this exact combination already exists (safety check)
                        if not ClassSubject.objects.filter(classroom=classroom, subject=subject).exists():
                            ClassSubject.objects.create(
                                classroom=classroom,
                                subject=subject,
                                teacher=None
                            )
                            created_count += 1
                    messages.success(request, f'Subject {subject.name} created and applied to {created_count} classes successfully. Please assign teachers to each class-subject combination.')
            else:
                # Subject created but not applied to any classes
                messages.success(request, f'Subject {subject.name} created successfully. You can now assign it to classes.')

            return redirect('courses:subject_list')
        except IntegrityError as e:
            if 'UNIQUE constraint' in str(e):
                # Handle unique constraint violation
                messages.error(request, f'A subject with code {code} already exists. Please use a different code.')
            elif 'NOT NULL constraint' in str(e):
                # Handle NOT NULL constraint violation
                messages.error(request, f'Teacher is required. Please select a teacher or check your database constraints.')
            else:
                # Handle other integrity errors
                messages.error(request, f'Database error while creating subject: {str(e)}')
            return redirect('courses:create_subject')
        except Exception as e:
            # Log the error for debugging
            print(f"Error creating subject: {str(e)}")
            messages.error(request, f'Error creating subject: {str(e)}')
            return redirect('courses:create_subject')

    # Get all teachers for the default teacher dropdown
    teachers = Teacher.objects.all().order_by('user__first_name', 'user__last_name')
    # Get all classrooms for the class selection
    classrooms = ClassRoom.objects.all().order_by('name', 'section')

    return render(request, 'courses/create_subject.html', {
        'teachers': teachers,
        'classrooms': classrooms
    })

@login_required
def subject_detail(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    # Get all classes that offer this subject
    class_subjects = ClassSubject.objects.filter(subject=subject)

    # Check if user has permission to view this subject
    if request.user.role == 'ADMIN':
        pass  # Admin can view all subjects
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if not class_subjects.filter(teacher=teacher).exists():
            messages.error(request, 'You do not have permission to view this subject.')
            return redirect('courses:subject_list')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        if not class_subjects.filter(students=student).exists():
            messages.error(request, 'You do not have permission to view this subject.')
            return redirect('courses:subject_list')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        if not class_subjects.filter(students__in=students).exists():
            messages.error(request, 'You do not have permission to view this subject.')
            return redirect('courses:subject_list')
        # Filter class_subjects to only include those related to parent's children
        class_subjects = class_subjects.filter(students__in=students).distinct()
    else:
        messages.error(request, 'You do not have permission to view this subject.')
        return redirect('courses:subject_list')

    # Calculate one week ago
    one_week_ago = timezone.now() - timedelta(days=7)

    # Initialize context with common data
    context = {
        'subject': subject,
        'one_week_ago': one_week_ago,
        'is_admin': request.user.role == 'ADMIN',
        'is_parent': request.user.role == 'PARENT',
        'is_teacher': request.user.role == 'TEACHER',
        'is_student': request.user.role == 'STUDENT',
    }

    # Fetch educational content based on user role
    if request.user.role == 'ADMIN':
        # Admin sees everything
        # Prepare class information for admin view
        classes = []
        for class_subject in class_subjects:
            class_info = {
                'id': class_subject.id,
                'name': class_subject.classroom.name,
                'section': class_subject.classroom.section,
                'teacher': class_subject.teacher.user.get_full_name() if class_subject.teacher else "No Teacher Assigned",
                'students_count': class_subject.students.count(),
            }
            classes.append(class_info)

        context.update({
            'classes': classes,
            'all_teachers': Teacher.objects.all().order_by('user__first_name', 'user__last_name')
        })

    elif request.user.role == 'TEACHER':
        # Teachers see their classes and educational content
        teacher = request.user.teacher_profile
        teacher_class_subjects = class_subjects.filter(teacher=teacher)

        classes = []
        for class_subject in teacher_class_subjects:
            class_info = {
                'id': class_subject.id,
                'name': class_subject.classroom.name,
                'section': class_subject.classroom.section,
                'students_count': class_subject.students.count(),
            }
            classes.append(class_info)

        context.update({
            'classes': classes
        })

    # For parents, students, and teachers, fetch educational content
    if request.user.role in ['PARENT', 'STUDENT', 'TEACHER']:
        relevant_class_subjects = class_subjects
        if request.user.role == 'PARENT':
            students = request.user.parent_profile.children.all()
            relevant_class_subjects = class_subjects.filter(students__in=students).distinct()
            context['parent_children'] = students
        elif request.user.role == 'STUDENT':
            relevant_class_subjects = class_subjects.filter(students=request.user.student_profile)

        # Fetch materials
        materials = CourseMaterial.objects.filter(
            class_subject__in=relevant_class_subjects
        ).order_by('-created_at')

        # Fetch videos
        videos = YouTubeVideo.objects.filter(
            models.Q(class_subject__in=relevant_class_subjects) |
            models.Q(is_general=True, class_subject__subject=subject)
        ).order_by('-created_at')

        # Fetch schedules
        schedules = Schedule.objects.filter(
            class_subject__in=relevant_class_subjects
        ).order_by('day_of_week', 'start_time')

        # Try to fetch assignments if assignments app is available
        try:
            from assignments.models import Assignment
            assignments = Assignment.objects.filter(
                class_subject__in=relevant_class_subjects
            ).order_by('-due_date')
        except (ImportError, AttributeError):
            assignments = []

        # Get days of week mapping for schedules
        days_of_week = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday',
        }

        context.update({
            'materials': materials,
            'videos': videos,
            'schedules': schedules,
            'assignments': assignments,
            'days_of_week': days_of_week,
        })

    return render(request, 'courses/subject_detail.html', context)

@login_required
@user_passes_test(is_admin)
def edit_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description')
        selected_classes = request.POST.getlist('selected_classes')
        teacher_id = request.POST.get('teacher')

        if not name or not code:
            messages.error(request, 'Subject name and code are required.')
            return redirect('courses:edit_subject', subject_id=subject_id)

        try:
            # Check if subject with same code already exists (excluding this subject)
            if Subject.objects.filter(code=code).exclude(id=subject_id).exists():
                messages.error(request, f'Subject with code {code} already exists.')
                return redirect('courses:edit_subject', subject_id=subject_id)

            # Update subject details
            subject.name = name
            subject.code = code
            subject.description = description
            subject.save()

            # Get currently assigned classes
            current_class_subjects = ClassSubject.objects.filter(subject=subject)
            current_class_ids = set(current_class_subjects.values_list('classroom_id', flat=True))

            # Convert selected classes to set of integers for comparison
            selected_class_ids = set(int(id) for id in selected_classes) if selected_classes else set()

            # Classes to add (selected but not current)
            classes_to_add = selected_class_ids - current_class_ids

            # Classes to remove (current but not selected)
            classes_to_remove = current_class_ids - selected_class_ids

            # Add new class-subject relations
            if classes_to_add and teacher_id:
                teacher = Teacher.objects.get(id=teacher_id)
                for class_id in classes_to_add:
                    classroom = ClassRoom.objects.get(id=class_id)
                    if not ClassSubject.objects.filter(classroom=classroom, subject=subject).exists():
                        ClassSubject.objects.create(
                            classroom=classroom,
                            subject=subject,
                            teacher=teacher
                        )
            elif classes_to_add:
                # Add classes without a teacher
                for class_id in classes_to_add:
                    classroom = ClassRoom.objects.get(id=class_id)
                    if not ClassSubject.objects.filter(classroom=classroom, subject=subject).exists():
                        ClassSubject.objects.create(
                            classroom=classroom,
                            subject=subject,
                            teacher=None
                        )

            # Remove class-subject relations that are no longer selected
            if classes_to_remove:
                ClassSubject.objects.filter(
                    subject=subject,
                    classroom_id__in=classes_to_remove
                ).delete()

            # Prepare success message
            add_count = len(classes_to_add)
            remove_count = len(classes_to_remove)
            message = f'Subject {subject.name} updated successfully.'
            if add_count > 0:
                message += f' Added to {add_count} new class(es).'
            if remove_count > 0:
                message += f' Removed from {remove_count} class(es).'

            messages.success(request, message)
            return redirect('courses:subject_detail', subject_id=subject_id)
        except Exception as e:
            messages.error(request, f'Error updating subject: {str(e)}')
            return redirect('courses:edit_subject', subject_id=subject_id)

    # Get all classrooms
    classrooms = ClassRoom.objects.all().order_by('name', 'section')

    # Get all teachers
    teachers = Teacher.objects.all().order_by('user__first_name', 'user__last_name')

    # Get currently assigned class IDs for this subject
    assigned_class_ids = list(ClassSubject.objects.filter(subject=subject).values_list('classroom_id', flat=True))

    context = {
        'subject': subject,
        'classrooms': classrooms,
        'teachers': teachers,
        'assigned_class_ids': assigned_class_ids,
    }
    return render(request, 'courses/edit_subject.html', context)

@login_required
@user_passes_test(is_admin)
def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == 'POST':
        try:
            subject_name = subject.name
            subject.delete()
            messages.success(request, f'Subject {subject_name} deleted successfully.')
            return redirect('courses:subject_list')
        except Exception as e:
            messages.error(request, f'Error deleting subject: {str(e)}')
            return redirect('courses:subject_detail', subject_id=subject_id)

    context = {
        'subject': subject,
        'class_subjects': ClassSubject.objects.filter(subject=subject),
    }
    return render(request, 'courses/delete_subject.html', context)

# Class Subjects views
@login_required
def class_subject_list(request):
    if request.user.role == 'ADMIN':
        class_subjects = ClassSubject.objects.all().order_by('classroom__name', 'subject__name')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(teacher=teacher).order_by('classroom__name', 'subject__name')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        class_subjects = ClassSubject.objects.filter(students=student).order_by('classroom__name', 'subject__name')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        class_subjects = ClassSubject.objects.filter(students__in=students).distinct().order_by('classroom__name', 'subject__name')
    else:
        class_subjects = ClassSubject.objects.none()

    # Calculate counts for dashboard statistics
    unique_classrooms = set()
    unique_subjects = set()
    unique_teachers = set()

    for cs in class_subjects:
        unique_classrooms.add(cs.classroom_id)
        unique_subjects.add(cs.subject_id)
        if cs.teacher_id:
            unique_teachers.add(cs.teacher_id)

    classes_count = len(unique_classrooms)
    subjects_count = len(unique_subjects)
    teachers_count = len(unique_teachers)

    # Get all grade levels for filtering
    grade_levels = ClassRoom.objects.filter(
        id__in=unique_classrooms
    ).values_list('grade_level', flat=True).distinct().order_by('grade_level')

    # Get all subject areas (first 3-4 letters of code) for filtering
    subject_areas = []
    subject_codes = Subject.objects.filter(
        id__in=unique_subjects
    ).values_list('code', flat=True)

    for code in subject_codes:
        if code and len(code) >= 3:
            area = code[:3]  # Get first 3 letters of code
            if area not in subject_areas:
                subject_areas.append(area)

    subject_areas.sort()

    # Get all teachers for filtering
    teachers = Teacher.objects.filter(
        id__in=unique_teachers
    ).select_related('user').order_by('user__first_name', 'user__last_name')

    context = {
        'class_subjects': class_subjects,
        'classes_count': classes_count,
        'subjects_count': subjects_count,
        'teachers_count': teachers_count,
        'grade_levels': grade_levels,
        'subject_areas': subject_areas,
        'teachers': teachers
    }

    return render(request, 'courses/class_subject_list.html', context)

@login_required
@user_passes_test(is_admin)
def create_class_subject(request):
    if request.method == 'POST':
        classroom_id = request.POST.get('classroom')
        subject_id = request.POST.get('subject')
        teacher_id = request.POST.get('teacher')

        if not classroom_id or not subject_id or not teacher_id:
            messages.error(request, 'Classroom, subject, and teacher are required.')
            return redirect('courses:create_class_subject')

        try:
            classroom = ClassRoom.objects.get(id=classroom_id)
            subject = Subject.objects.get(id=subject_id)
            teacher = Teacher.objects.get(id=teacher_id)

            # Check if this class-subject combination already exists
            if ClassSubject.objects.filter(classroom=classroom, subject=subject).exists():
                messages.error(request, f'This class-subject combination already exists.')
                return redirect('courses:create_class_subject')

            class_subject = ClassSubject.objects.create(
                classroom=classroom,
                subject=subject,
                teacher=teacher
            )
            messages.success(request, f'Class subject {subject.name} for {classroom.name} taught by {teacher.user.get_full_name()} created successfully.')
            return redirect('courses:class_subject_list')
        except Exception as e:
            messages.error(request, f'Error creating class subject: {str(e)}')
            return redirect('courses:create_class_subject')

    classrooms = ClassRoom.objects.all().order_by('name', 'section')
    subjects = Subject.objects.all().order_by('name')
    teachers = Teacher.objects.all()

    context = {
        'classrooms': classrooms,
        'subjects': subjects,
        'teachers': teachers,
    }
    return render(request, 'courses/create_class_subject.html', context)

@login_required
def class_subject_detail(request, class_subject_id):
    class_subject = get_object_or_404(ClassSubject, id=class_subject_id)

    # Check if user has permission to view this class subject
    if request.user.role == 'ADMIN':
        pass  # Admin can view all class subjects
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if teacher != class_subject.teacher and teacher != class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to view this class subject.')
            return redirect('courses:class_subject_list')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        if not class_subject.students.filter(id=student.id).exists():
            messages.error(request, 'You do not have permission to view this class subject.')
            return redirect('courses:class_subject_list')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        if not class_subject.students.filter(id__in=students.values_list('id', flat=True)).exists():
            messages.error(request, 'You do not have permission to view this class subject.')
            return redirect('courses:class_subject_list')
    else:
        messages.error(request, 'You do not have permission to view this class subject.')
        return redirect('courses:class_subject_list')

    # Get materials
    materials = CourseMaterial.objects.filter(class_subject=class_subject).order_by('-created_at')

    # Get videos
    videos = YouTubeVideo.objects.filter(
        models.Q(class_subject=class_subject) |
        models.Q(is_general=True)
    ).order_by('-created_at')

    # Get students
    students = class_subject.students.all().order_by('user__first_name', 'user__last_name')

    # Get schedule
    schedules = Schedule.objects.filter(class_subject=class_subject).order_by('day_of_week', 'start_time')

    # Create days of week mapping without relying on Schedule.DAY_CHOICES
    days_of_week = {
        0: 'Monday',
        1: 'Tuesday',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday',
    }

    context = {
        'class_subject': class_subject,
        'materials': materials,
        'videos': videos,
        'students': students,
        'schedules': schedules,
        'is_teacher': request.user.role == 'TEACHER' and (request.user.teacher_profile == class_subject.teacher or request.user.teacher_profile == class_subject.classroom.class_teacher),
        'is_admin': request.user.role == 'ADMIN',
        'days_of_week': days_of_week,
    }

    # For parent users, add their children to context to filter the students list
    if request.user.role == 'PARENT':
        parent = request.user.parent_profile
        parent_children = parent.children.all()
        context['parent_children'] = parent_children

    return render(request, 'courses/class_subject_detail.html', context)

@login_required
@user_passes_test(is_admin)
def edit_class_subject(request, class_subject_id):
    class_subject = get_object_or_404(ClassSubject, id=class_subject_id)

    if request.method == 'POST':
        teacher_id = request.POST.get('teacher')
        next_url = request.POST.get('next')

        if not teacher_id:
            messages.error(request, 'Teacher is required.')
            return redirect('courses:edit_class_subject', class_subject_id=class_subject_id)

        try:
            teacher = Teacher.objects.get(id=teacher_id)

            class_subject.teacher = teacher
            class_subject.save()

            messages.success(request, f'Teacher assignment updated successfully.')

            # If next_url is provided and starts with '/', redirect there
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            elif next_url == 'class_detail':
                # If it's from the class detail page, redirect back there
                return redirect('courses:class_detail', class_id=class_subject.classroom.id)
            else:
                # Default redirect to the class subject detail
                return redirect('courses:class_subject_detail', class_subject_id=class_subject_id)
        except Exception as e:
            messages.error(request, f'Error updating class subject: {str(e)}')
            return redirect('courses:edit_class_subject', class_subject_id=class_subject_id)

    teachers = Teacher.objects.all()

    context = {
        'class_subject': class_subject,
        'teachers': teachers,
    }
    return render(request, 'courses/edit_class_subject.html', context)

@login_required
@user_passes_test(is_admin)
def delete_class_subject(request, class_subject_id):
    class_subject = get_object_or_404(ClassSubject, id=class_subject_id)

    # Check if user has permission to delete this class subject
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to delete this class subject.')
        return redirect('courses:class_subject_list')

    if request.method == 'POST':
        try:
            classroom = class_subject.classroom
            subject = class_subject.subject
            class_subject.delete()
            messages.success(request, f'Class subject {subject.name} for {classroom.name} deleted successfully.')
            return redirect('courses:class_subject_list')
        except Exception as e:
            messages.error(request, f'Error deleting class subject: {str(e)}')
            return redirect('courses:class_subject_detail', class_subject_id=class_subject_id)

    context = {
        'class_subject': class_subject,
    }
    return render(request, 'courses/delete_class_subject.html', context)

@login_required
@user_passes_test(is_admin)
def manage_class_students(request, class_subject_id):
    class_subject = get_object_or_404(ClassSubject, id=class_subject_id)

    if request.method == 'POST':
        new_student_ids = set(int(id) for id in request.POST.getlist('students'))

        try:
            # Get currently enrolled students
            current_student_ids = set(class_subject.students.values_list('id', flat=True))

            # Students to add
            students_to_add = new_student_ids - current_student_ids

            # Students to remove
            students_to_remove = current_student_ids - new_student_ids

            # Handle removals first
            if students_to_remove:
                class_subject.students.remove(*Student.objects.filter(id__in=students_to_remove))

            # Handle additions
            students_added = set()
            if students_to_add:
                # Get all subjects taught in this classroom
                class_subjects = ClassSubject.objects.filter(classroom=class_subject.classroom)

                # For new students, enroll them in all subjects taught in this classroom
                new_students = Student.objects.filter(id__in=students_to_add)
                for cs in class_subjects:
                    cs.students.add(*new_students)
                    students_added.update(students_to_add)

            # For existing students, ensure they're in this subject
            if new_student_ids - students_added:
                existing_students = Student.objects.filter(id__in=new_student_ids - students_added)
                class_subject.students.add(*existing_students)

            messages.success(request, f'Students updated successfully for {class_subject.subject.name}. New students will be enrolled in all subjects taught in {class_subject.classroom.name}.')

            # Check for 'next' parameter to determine redirect
            next_url = request.POST.get('next')
            if next_url == 'class_detail':
                # Redirect back to the class detail page
                return redirect('courses:class_detail', class_id=class_subject.classroom.id)
            else:
                # Default redirect to the class subject detail page
                return redirect('courses:class_subject_detail', class_subject_id=class_subject_id)
        except Exception as e:
            messages.error(request, f'Error updating students: {str(e)}')
            return redirect('courses:manage_class_students', class_subject_id=class_subject_id)

    # Get all students
    all_students = Student.objects.all().order_by('user__first_name', 'user__last_name')

    # Get currently enrolled students
    enrolled_students = class_subject.students.all()
    enrolled_student_ids = [s.id for s in enrolled_students]

    context = {
        'class_subject': class_subject,
        'all_students': all_students,
        'enrolled_student_ids': enrolled_student_ids,
    }
    return render(request, 'courses/manage_class_students.html', context)

# Course Materials views
@login_required
def material_list(request):
    # Get filter parameters
    class_filter = request.GET.get('class', '')
    subject_filter = request.GET.get('subject', '')
    type_filter = request.GET.get('type', '')
    search_term = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-created_at')  # Default sort by creation date

    # Base queryset
    if request.user.role == 'ADMIN':
        materials = CourseMaterial.objects.all()
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        # Get materials for classes the teacher teaches
        class_subjects = ClassSubject.objects.filter(
            models.Q(teacher=teacher) |
            models.Q(classroom__class_teacher=teacher)
        )
        # Include both materials for their classes AND materials they created
        materials = CourseMaterial.objects.filter(
            models.Q(class_subject__in=class_subjects) |
            models.Q(created_by=request.user)
        ).distinct()
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        class_subjects = ClassSubject.objects.filter(students=student)
        materials = CourseMaterial.objects.filter(class_subject__in=class_subjects)
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        class_subjects = ClassSubject.objects.filter(students__in=students)
        materials = CourseMaterial.objects.filter(class_subject__in=class_subjects).distinct()
    else:
        materials = CourseMaterial.objects.none()

    # Apply filters
    if class_filter:
        materials = materials.filter(class_subject__classroom__id=class_filter)
    if subject_filter:
        materials = materials.filter(class_subject__subject__id=subject_filter)
    if type_filter:
        if type_filter == 'notes':
            materials = materials.filter(content__isnull=False).exclude(content='')
        elif type_filter == 'files':
            materials = materials.filter(file__isnull=False)
        elif type_filter == 'pdf':
            materials = materials.filter(file__icontains='.pdf')
        elif type_filter == 'doc':
            materials = materials.filter(Q(file__icontains='.doc') | Q(file__icontains='.docx'))
        elif type_filter == 'ppt':
            materials = materials.filter(Q(file__icontains='.ppt') | Q(file__icontains='.pptx'))
        elif type_filter == 'img':
            materials = materials.filter(Q(file__icontains='.jpg') | Q(file__icontains='.jpeg') | Q(file__icontains='.png') | Q(file__icontains='.gif'))
        elif type_filter == 'other':
            materials = materials.exclude(
                Q(file__icontains='.pdf') | Q(file__icontains='.doc') | Q(file__icontains='.docx') |
                Q(file__icontains='.ppt') | Q(file__icontains='.pptx') | Q(file__icontains='.jpg') |
                Q(file__icontains='.jpeg') | Q(file__icontains='.png') | Q(file__icontains='.gif')
            )

    # Filter out drafts for non-creators
    if request.user.role not in ['ADMIN', 'TEACHER']:
        materials = materials.filter(is_draft=False)
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        # Teachers can see their own drafts and published materials from others
        materials = materials.filter(
            Q(is_draft=False) |
            Q(created_by=request.user)
        )

    # Add a draft filter option
    draft_filter = request.GET.get('draft')
    if draft_filter == 'yes':
        materials = materials.filter(is_draft=True)
    elif draft_filter == 'no':
        materials = materials.filter(is_draft=False)

    # Apply search
    if search_term:
        materials = materials.filter(
            Q(title__icontains=search_term) |
            Q(description__icontains=search_term) |
            Q(class_subject__subject__name__icontains=search_term) |
            Q(class_subject__classroom__name__icontains=search_term)
        )

    # Apply sorting
    materials = materials.order_by(sort_by)

    # Get all classes and subjects for filter options
    if request.user.role == 'ADMIN':
        classes = ClassRoom.objects.all().order_by('name', 'section')
        subjects = Subject.objects.all().order_by('name')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        classes = ClassRoom.objects.filter(
            Q(class_teacher=teacher) |
            Q(subjects__teacher=teacher)
        ).distinct().order_by('name', 'section')
        class_subjects = ClassSubject.objects.filter(teacher=teacher)
        subject_ids = class_subjects.values_list('subject_id', flat=True).distinct()
        subjects = Subject.objects.filter(id__in=subject_ids).order_by('name')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        class_subjects = ClassSubject.objects.filter(students=student)
        classes = ClassRoom.objects.filter(subjects__in=class_subjects).distinct().order_by('name', 'section')
        subject_ids = class_subjects.values_list('subject_id', flat=True).distinct()
        subjects = Subject.objects.filter(id__in=subject_ids).order_by('name')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        class_subjects = ClassSubject.objects.filter(students__in=students)
        classes = ClassRoom.objects.filter(subjects__in=class_subjects).distinct().order_by('name', 'section')
        subject_ids = class_subjects.values_list('subject_id', flat=True).distinct()
        subjects = Subject.objects.filter(id__in=subject_ids).order_by('name')
    else:
        classes = ClassRoom.objects.none()
        subjects = Subject.objects.none()

    context = {
        'materials': materials,
        'classes': classes,
        'subjects': subjects,
        'selected_class': class_filter,
        'selected_subject': subject_filter,
        'selected_type': type_filter,
        'search_term': search_term,
        'sort_by': sort_by,
    }
    return render(request, 'courses/material_list.html', context)

@login_required
def create_material(request):
    # Only teachers and admins can create materials
    if not is_admin(request.user) and not is_teacher(request.user):
        messages.error(request, 'You do not have permission to create materials.')
        return redirect('courses:material_list')

    if request.method == 'POST':
        class_subject_id = request.POST.get('class_subject')
        title = request.POST.get('title')
        description = request.POST.get('description')
        content = request.POST.get('content')
        file = request.FILES.get('file')
        is_draft = request.POST.get('is_draft') == 'on'

        if not class_subject_id or not title:
            messages.error(request, 'Class subject and title are required.')
            return redirect('courses:create_material')

        # Ensure at least content or file is provided
        if not content and not file:
            messages.error(request, 'Please provide either content or a file attachment.')
            return redirect('courses:create_material')

        try:
            class_subject = ClassSubject.objects.get(id=class_subject_id)

            # Check if user has permission to add material to this class subject
            if request.user.role == 'TEACHER':
                teacher = request.user.teacher_profile
                if teacher != class_subject.teacher and teacher != class_subject.classroom.class_teacher:
                    messages.error(request, 'You do not have permission to add material to this class subject.')
                    return redirect('courses:create_material')

            material = CourseMaterial.objects.create(
                class_subject=class_subject,
                title=title,
                description=description,
                content=content,
                file=file,
                is_draft=is_draft,
                created_by=request.user
            )

            # Create notifications for students and parents
            try:
                from communications.utils import create_material_notification
                create_material_notification(material, request.user)
            except Exception as e:
                print(f"Error creating notifications: {e}")

            messages.success(request, f'Material {material.title} created successfully.')
            return redirect('courses:material_detail', material_id=material.id)
        except Exception as e:
            messages.error(request, f'Error creating material: {str(e)}')
            return redirect('courses:create_material')

    # Get class subjects that the user has permission to add materials to
    if request.user.role == 'ADMIN':
        class_subjects = ClassSubject.objects.all().order_by('classroom__name', 'subject__name')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(
            models.Q(teacher=teacher) |
            models.Q(classroom__class_teacher=teacher)
        ).order_by('classroom__name', 'subject__name')
    else:
        class_subjects = ClassSubject.objects.none()

    context = {
        'class_subjects': class_subjects,
    }
    return render(request, 'courses/create_material.html', context)

@login_required
def material_detail(request, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id)

    # Check if user has permission to view this material
    if request.user.role == 'ADMIN':
        pass  # Admin can view all materials
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if teacher != material.class_subject.teacher and teacher != material.class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to view this material.')
            return redirect('courses:material_list')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        if not material.class_subject.students.filter(id=student.id).exists():
            messages.error(request, 'You do not have permission to view this material.')
            return redirect('courses:material_list')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        if not material.class_subject.students.filter(id__in=students.values_list('id', flat=True)).exists():
            messages.error(request, 'You do not have permission to view this material.')
            return redirect('courses:material_list')
    else:
        messages.error(request, 'You do not have permission to view this material.')
        return redirect('courses:material_list')

    # Get previous and next materials in the same subject for navigation
    prev_material = None
    next_material = None

    # Base queryset for materials in the same class_subject
    related_materials = CourseMaterial.objects.filter(class_subject=material.class_subject)

    # For students and parents, only show published materials
    if request.user.role in ['STUDENT', 'PARENT']:
        related_materials = related_materials.filter(is_draft=False)
    # For teachers, show their own drafts and published materials
    elif request.user.role == 'TEACHER':
        if request.user != material.created_by:
            related_materials = related_materials.filter(is_draft=False)

    # Order by creation date
    related_materials = related_materials.order_by('created_at')

    # Find previous material
    prev_materials = related_materials.filter(created_at__lt=material.created_at).order_by('-created_at')
    if prev_materials.exists():
        prev_material = prev_materials.first()

    # Find next material
    next_materials = related_materials.filter(created_at__gt=material.created_at).order_by('created_at')
    if next_materials.exists():
        next_material = next_materials.first()

    context = {
        'material': material,
        'is_creator': request.user == material.created_by,
        'is_teacher': request.user.role == 'TEACHER' and (request.user.teacher_profile == material.class_subject.teacher or request.user.teacher_profile == material.class_subject.classroom.class_teacher),
        'is_admin': request.user.role == 'ADMIN',
        'prev_material': prev_material,
        'next_material': next_material,
    }
    return render(request, 'courses/material_detail.html', context)

@login_required
def edit_material(request, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id)

    # Check if user has permission to edit this material
    if request.user.role == 'ADMIN':
        pass  # Admin can edit all materials
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if teacher != material.class_subject.teacher and teacher != material.class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to edit this material.')
            return redirect('courses:material_list')
    else:
        messages.error(request, 'You do not have permission to edit this material.')
        return redirect('courses:material_list')

    # Get class subjects that the user has permission to add materials to
    if request.user.role == 'ADMIN':
        class_subjects = ClassSubject.objects.all().order_by('classroom__name', 'subject__name')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(
            models.Q(teacher=teacher) |
            models.Q(classroom__class_teacher=teacher)
        ).order_by('classroom__name', 'subject__name')
    else:
        class_subjects = ClassSubject.objects.none()

    if request.method == 'POST':
        class_subject_id = request.POST.get('class_subject')
        title = request.POST.get('title')
        description = request.POST.get('description')
        content = request.POST.get('content')
        file = request.FILES.get('file')
        remove_file = request.POST.get('remove_file') == 'on'
        is_draft = request.POST.get('is_draft') == 'on'

        if not title:
            messages.error(request, 'Title is required.')
            return redirect('courses:edit_material', material_id=material_id)

        # Ensure at least content or file is provided (unless removing file)
        if not content and not file and not material.file:
            messages.error(request, 'Please provide either content or a file attachment.')
            return redirect('courses:edit_material', material_id=material_id)

        try:
            # Update class subject if changed
            if class_subject_id and int(class_subject_id) != material.class_subject.id:
                try:
                    new_class_subject = ClassSubject.objects.get(id=class_subject_id)
                    # Check if user has permission to add material to this class subject
                    if request.user.role == 'TEACHER':
                        teacher = request.user.teacher_profile
                        if teacher != new_class_subject.teacher and teacher != new_class_subject.classroom.class_teacher:
                            messages.error(request, 'You do not have permission to add material to this class subject.')
                            return redirect('courses:edit_material', material_id=material_id)
                    material.class_subject = new_class_subject
                except ClassSubject.DoesNotExist:
                    messages.error(request, 'Invalid class subject selected.')
                    return redirect('courses:edit_material', material_id=material_id)

            material.title = title
            material.description = description
            material.content = content
            material.is_draft = is_draft

            # Handle file upload or removal
            if remove_file and material.file:
                # Delete the existing file
                if os.path.isfile(material.file.path):
                    os.remove(material.file.path)
                material.file = None
            elif file:
                # If there's a new file and an existing file, delete the old one
                if material.file:
                    if os.path.isfile(material.file.path):
                        os.remove(material.file.path)
                material.file = file

            material.save()

            messages.success(request, f'Material {material.title} updated successfully.')
            return redirect('courses:material_detail', material_id=material.id)
        except Exception as e:
            messages.error(request, f'Error updating material: {str(e)}')
            return redirect('courses:edit_material', material_id=material_id)

    context = {
        'material': material,
        'class_subjects': class_subjects,
    }
    return render(request, 'courses/edit_material.html', context)

@login_required
def delete_material(request, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id)

    # Check if user has permission to delete this material
    if request.user.role == 'ADMIN':
        pass  # Admin can delete all materials
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if teacher != material.class_subject.teacher and teacher != material.class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to delete this material.')
            return redirect('courses:material_list')
    else:
        messages.error(request, 'You do not have permission to delete this material.')
        return redirect('courses:material_list')

    if request.method == 'POST':
        try:
            # If there's a file, delete it
            if material.file:
                if os.path.isfile(material.file.path):
                    os.remove(material.file.path)

            material_title = material.title
            material.delete()

            messages.success(request, f'Material {material_title} deleted successfully.')
            return redirect('courses:material_list')
        except Exception as e:
            messages.error(request, f'Error deleting material: {str(e)}')
            return redirect('courses:material_detail', material_id=material_id)

    context = {
        'material': material,
    }
    return render(request, 'courses/delete_material.html', context)

@login_required
@user_passes_test(lambda u: is_teacher(u) or is_admin(u))
def manage_materials(request):
    """View for teachers and admins to manage learning materials"""
    materials = CourseMaterial.objects.all().order_by('-created_at')

    # Get all classes and subjects for filtering
    classrooms = ClassRoom.objects.all().order_by('name')
    subjects = Subject.objects.all().order_by('name')

    # Filter based on user role
    if is_teacher(request.user):
        teacher = get_object_or_404(Teacher, user=request.user)
        materials = materials.filter(
            models.Q(class_subject__teacher=teacher) |
            models.Q(class_subject__classroom__class_teacher=teacher) |
            models.Q(created_by=request.user)  # Ensure teachers see materials they created
        )

        # Filter classrooms and subjects to only those the teacher has access to
        teacher_class_subjects = ClassSubject.objects.filter(
            models.Q(teacher=teacher) |
            models.Q(classroom__class_teacher=teacher)
        )
        classrooms = ClassRoom.objects.filter(id__in=teacher_class_subjects.values('classroom')).distinct()
        subjects = Subject.objects.filter(id__in=teacher_class_subjects.values('subject')).distinct()

    # Apply class filter
    class_filter = request.GET.get('class')
    if class_filter:
        materials = materials.filter(class_subject__classroom__id=class_filter)

    # Apply subject filter
    subject_filter = request.GET.get('subject')
    if subject_filter:
        materials = materials.filter(class_subject__subject__id=subject_filter)

    # Apply draft filter
    draft_filter = request.GET.get('draft')
    if draft_filter == 'yes':
        materials = materials.filter(is_draft=True)
    elif draft_filter == 'no':
        materials = materials.filter(is_draft=False)

    # Apply type filter if specified
    material_type = request.GET.get('type')
    if material_type and material_type != 'all':
        if material_type == 'notes':
            materials = materials.filter(content__isnull=False).exclude(content='')
        elif material_type == 'files':
            materials = materials.filter(file__isnull=False)
        elif material_type == 'pdf':
            materials = materials.filter(file__endswith='.pdf')
        elif material_type == 'doc':
            materials = materials.filter(Q(file__endswith='.doc') | Q(file__endswith='.docx'))
        elif material_type == 'ppt':
            materials = materials.filter(Q(file__endswith='.ppt') | Q(file__endswith='.pptx'))
        elif material_type == 'other':
            materials = materials.exclude(
                Q(file__endswith='.pdf') |
                Q(file__endswith='.doc') |
                Q(file__endswith='.docx') |
                Q(file__endswith='.ppt') |
                Q(file__endswith='.pptx')
            )

    context = {
        'materials': materials,
        'classrooms': classrooms,
        'subjects': subjects,
        'selected_class': class_filter,
        'selected_subject': subject_filter,
        'selected_type': material_type or '',
        'selected_draft': draft_filter or ''
    }

    return render(request, 'courses/manage_materials.html', context)

# YouTube Videos views
@login_required
def video_list(request):
    if request.user.role == 'ADMIN':
        videos = YouTubeVideo.objects.all().order_by('-created_at')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(teacher=teacher)
        videos = YouTubeVideo.objects.filter(
            models.Q(class_subject__in=class_subjects) |
            models.Q(is_general=True)
        ).order_by('-created_at')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        class_subjects = ClassSubject.objects.filter(students=student)
        videos = YouTubeVideo.objects.filter(
            models.Q(class_subject__in=class_subjects) |
            models.Q(is_general=True)
        ).order_by('-created_at')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        class_subjects = ClassSubject.objects.filter(students__in=students)
        videos = YouTubeVideo.objects.filter(
            models.Q(class_subject__in=class_subjects) |
            models.Q(is_general=True)
        ).distinct().order_by('-created_at')
    else:
        videos = YouTubeVideo.objects.none()

    context = {
        'videos': videos,
    }
    return render(request, 'courses/video_list.html', context)

@login_required
def create_video(request):
    # Only teachers and admins can create videos
    if not is_admin(request.user) and not is_teacher(request.user):
        messages.error(request, 'You do not have permission to create videos.')
        return redirect('courses:video_list')

    if request.method == 'POST':
        class_subject_id = request.POST.get('class_subject')
        title = request.POST.get('title')
        description = request.POST.get('description')
        youtube_url = request.POST.get('youtube_url')
        is_general = request.POST.get('is_general') == 'on'

        if not title or not youtube_url:
            messages.error(request, 'Title and YouTube URL are required.')
            return redirect('courses:create_video')

        try:
            if not is_general and not class_subject_id:
                messages.error(request, 'Class subject is required for non-general videos.')
                return redirect('courses:create_video')

            if class_subject_id:
                class_subject = ClassSubject.objects.get(id=class_subject_id)

                # Check if user has permission to add video to this class subject
                if request.user.role == 'TEACHER':
                    teacher = request.user.teacher_profile
                    if teacher != class_subject.teacher and teacher != class_subject.classroom.class_teacher:
                        messages.error(request, 'You do not have permission to add video to this class subject.')
                        return redirect('courses:create_video')
            else:
                class_subject = None

            video = YouTubeVideo.objects.create(
                class_subject=class_subject,
                title=title,
                description=description,
                youtube_url=youtube_url,
                is_general=is_general,
                created_by=request.user
            )

            # Create notifications for students and parents
            try:
                from communications.utils import create_video_notification
                create_video_notification(video, request.user)
            except Exception as e:
                print(f"Error creating notifications: {e}")

            messages.success(request, f'Video {video.title} created successfully.')
            return redirect('courses:video_detail', video_id=video.id)
        except Exception as e:
            messages.error(request, f'Error creating video: {str(e)}')
            return redirect('courses:create_video')

    # Get class subjects that the user has permission to add videos to
    if request.user.role == 'ADMIN':
        class_subjects = ClassSubject.objects.all().order_by('classroom__name', 'subject__name')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(
            models.Q(teacher=teacher) |
            models.Q(classroom__class_teacher=teacher)
        ).order_by('classroom__name', 'subject__name')
    else:
        class_subjects = ClassSubject.objects.none()

    context = {
        'class_subjects': class_subjects,
    }
    return render(request, 'courses/create_video.html', context)

@login_required
def student_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # Check if user has permission to view this student's details
    if request.user.role == 'ADMIN':
        pass  # Admin can view all students
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        # Check if teacher teaches this student or is class teacher
        class_subjects = ClassSubject.objects.filter(students=student)
        if not (class_subjects.filter(teacher=teacher).exists() or
                (student.grade and student.grade.class_teacher == teacher)):
            messages.error(request, 'You do not have permission to view this student.')
            return redirect('courses:class_list')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        if not parent.children.filter(id=student_id).exists():
            messages.error(request, 'You do not have permission to view this student.')
            return redirect('dashboard:parent_dashboard')
    elif request.user.role == 'STUDENT':
        if request.user.student_profile.id != student_id:
            messages.error(request, 'You do not have permission to view this student.')
            return redirect('dashboard:student_dashboard')
    else:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard:index')

    # Get the student's classroom (if any)
    classroom = student.grade

    # Get the student's enrolled subjects
    class_subjects = ClassSubject.objects.filter(students=student)
    enrolled_subjects = []
    for cs in class_subjects:
        subject_info = {
            'id': cs.id,
            'name': cs.subject.name,
            'code': cs.subject.code,
            'teacher': cs.teacher.user.get_full_name() if cs.teacher else None,
        }
        enrolled_subjects.append(subject_info)

    # Get attendance statistics
    try:
        from attendance.models import AttendanceRecord, StudentAttendance

        # Get the student's attendance records
        student_attendances = StudentAttendance.objects.filter(student=student).order_by('-attendance_record__date')
        recent_attendance = student_attendances[:10]  # Last 10 attendance records

        # Calculate attendance stats
        total_records = student_attendances.count()
        present_count = student_attendances.filter(status='PRESENT').count()
        absent_count = student_attendances.filter(status='ABSENT').count()
        late_count = student_attendances.filter(status='LATE').count()
        excused_count = student_attendances.filter(status='EXCUSED').count()

        # Calculate attendance rate
        attendance_rate = 0
        if total_records > 0:
            attendance_rate = round((present_count / total_records) * 100, 1)

        # Calculate individual rates
        present_rate = 0 if total_records == 0 else round((present_count / total_records) * 100, 1)
        absent_rate = 0 if total_records == 0 else round((absent_count / total_records) * 100, 1)
        late_rate = 0 if total_records == 0 else round((late_count / total_records) * 100, 1)
        excused_rate = 0 if total_records == 0 else round((excused_count / total_records) * 100, 1)
    except (ImportError, AttributeError):
        recent_attendance = []
        present_count = absent_count = late_count = excused_count = 0
        attendance_rate = present_rate = absent_rate = late_rate = excused_rate = 0

    # Try to get assignments data
    try:
        from assignments.models import Assignment, Submission, GradeThreshold

        # Get upcoming assignments
        upcoming_assignments = Assignment.objects.filter(
            class_subject__in=class_subjects,
            due_date__gte=timezone.now()
        ).order_by('due_date')[:5]

        # Get recent grades
        recent_grades = Submission.objects.filter(
            student=student,
            graded=True
        ).select_related('assignment', 'assignment__class_subject__subject').order_by('-created_at')[:5]

        # Calculate subject grades
        subject_grades = []
        for cs in class_subjects:
            submissions = Submission.objects.filter(
                student=student,
                assignment__class_subject=cs,
                graded=True
            )

            if submissions.exists():
                total_score = sum(sub.score for sub in submissions)
                avg_score = round(total_score / submissions.count(), 1)

                subject_grades.append({
                    'subject_name': cs.subject.name,
                    'average': avg_score,
                    'teacher_name': cs.teacher.user.get_full_name() if cs.teacher else None,
                })

        # Calculate overall grade
        overall_grade = None
        if subject_grades:
            avg_scores = [sg['average'] for sg in subject_grades]
            overall_score = sum(avg_scores) / len(avg_scores)

            # Try to get grade threshold for the score
            try:
                grade_thresholds = GradeThreshold.objects.filter(
                    grading_scale__is_default=True
                ).order_by('-min_score')

                for threshold in grade_thresholds:
                    if overall_score >= threshold.min_score:
                        overall_grade = threshold.letter_grade
                        break
            except:
                # If no grade threshold found, just use the numerical score
                overall_grade = f"{overall_score:.1f}%"

        assignments_count = Assignment.objects.filter(class_subject__in=class_subjects).count()
    except (ImportError, AttributeError):
        upcoming_assignments = []
        recent_grades = []
        subject_grades = []
        overall_grade = None
        assignments_count = 0

    context = {
        'student': student,
        'classroom': classroom,
        'enrolled_subjects': enrolled_subjects,
        'recent_attendance': recent_attendance,
        'attendance_rate': attendance_rate,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'excused_count': excused_count,
        'present_rate': present_rate,
        'absent_rate': absent_rate,
        'late_rate': late_rate,
        'excused_rate': excused_rate,
        'upcoming_assignments': upcoming_assignments,
        'recent_grades': recent_grades,
        'subject_grades': subject_grades,
        'overall_grade': overall_grade,
        'assignments_count': assignments_count,
        'is_admin': request.user.role == 'ADMIN',
        'is_class_teacher': request.user.role == 'TEACHER' and student.grade and student.grade.class_teacher == request.user.teacher_profile,
    }

    return render(request, 'courses/student_detail.html', context)

@login_required
def video_detail(request, video_id):
    video = get_object_or_404(YouTubeVideo, id=video_id)

    # Check if user has permission to view this video
    if video.is_general:
        pass  # Anyone can view general videos
    elif request.user.role == 'ADMIN':
        pass  # Admin can view all videos
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if video.class_subject and teacher != video.class_subject.teacher and teacher != video.class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to view this video.')
            return redirect('courses:video_list')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        if video.class_subject and not video.class_subject.students.filter(id=student.id).exists():
            messages.error(request, 'You do not have permission to view this video.')
            return redirect('courses:video_list')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        if video.class_subject and not video.class_subject.students.filter(id__in=students.values_list('id', flat=True)).exists():
            messages.error(request, 'You do not have permission to view this video.')
            return redirect('courses:video_list')
    else:
        messages.error(request, 'You do not have permission to view this video.')
        return redirect('courses:video_list')

    # Extract YouTube video ID from URL
    youtube_id = None
    if 'youtube.com' in video.youtube_url:
        youtube_id = video.youtube_url.split('v=')[1].split('&')[0]
    elif 'youtu.be' in video.youtube_url:
        youtube_id = video.youtube_url.split('/')[-1]

    context = {
        'video': video,
        'youtube_id': youtube_id,
        'is_creator': request.user == video.created_by,
        'is_teacher': request.user.role == 'TEACHER' and (not video.class_subject or request.user.teacher_profile == video.class_subject.teacher or request.user.teacher_profile == video.class_subject.classroom.class_teacher),
        'is_admin': request.user.role == 'ADMIN',
    }
    return render(request, 'courses/video_detail.html', context)

@login_required
def edit_video(request, video_id):
    video = get_object_or_404(YouTubeVideo, id=video_id)

    # Check if user has permission to edit this video
    if request.user.role == 'ADMIN':
        pass  # Admin can edit all videos
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if video.class_subject and teacher != video.class_subject.teacher and teacher != video.class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to edit this video.')
            return redirect('courses:video_list')
    else:
        messages.error(request, 'You do not have permission to edit this video.')
        return redirect('courses:video_list')

    if request.method == 'POST':
        class_subject_id = request.POST.get('class_subject')
        title = request.POST.get('title')
        description = request.POST.get('description')
        youtube_url = request.POST.get('youtube_url')
        is_general = request.POST.get('is_general') == 'on'

        if not title or not youtube_url:
            messages.error(request, 'Title and YouTube URL are required.')
            return redirect('courses:edit_video', video_id=video_id)

        try:
            if not is_general and not class_subject_id:
                messages.error(request, 'Class subject is required for non-general videos.')
                return redirect('courses:edit_video', video_id=video_id)

            if class_subject_id:
                class_subject = ClassSubject.objects.get(id=class_subject_id)

                # Check if user has permission to assign video to this class subject
                if request.user.role == 'TEACHER':
                    teacher = request.user.teacher_profile
                    if teacher != class_subject.teacher and teacher != class_subject.classroom.class_teacher:
                        messages.error(request, 'You do not have permission to assign video to this class subject.')
                        return redirect('courses:edit_video', video_id=video_id)
            else:
                class_subject = None

            video.class_subject = class_subject
            video.title = title
            video.description = description
            video.youtube_url = youtube_url
            video.is_general = is_general
            video.save()

            messages.success(request, f'Video {video.title} updated successfully.')
            return redirect('courses:video_detail', video_id=video.id)
        except Exception as e:
            messages.error(request, f'Error updating video: {str(e)}')
            return redirect('courses:edit_video', video_id=video_id)

    # Get class subjects that the user has permission to assign videos to
    if request.user.role == 'ADMIN':
        class_subjects = ClassSubject.objects.all().order_by('classroom__name', 'subject__name')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(
            models.Q(teacher=teacher) |
            models.Q(classroom__class_teacher=teacher)
        ).order_by('classroom__name', 'subject__name')
    else:
        class_subjects = ClassSubject.objects.none()

    context = {
        'video': video,
        'class_subjects': class_subjects,
    }
    return render(request, 'courses/edit_video.html', context)

@login_required
def delete_video(request, video_id):
    video = get_object_or_404(YouTubeVideo, id=video_id)

    # Check if user has permission to delete this video
    if request.user.role == 'ADMIN':
        pass  # Admin can delete all videos
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if video.class_subject and teacher != video.class_subject.teacher and teacher != video.class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to delete this video.')
            return redirect('courses:video_list')
    else:
        messages.error(request, 'You do not have permission to delete this video.')
        return redirect('courses:video_list')

    if request.method == 'POST':
        try:
            video_title = video.title
            video.delete()

            messages.success(request, f'Video {video_title} deleted successfully.')
            return redirect('courses:video_list')
        except Exception as e:
            messages.error(request, f'Error deleting video: {str(e)}')
            return redirect('courses:video_detail', video_id=video_id)

    context = {
        'video': video,
    }
    return render(request, 'courses/delete_video.html', context)

# Schedule views
@login_required
def schedule_list(request):
    if request.user.role == 'ADMIN':
        schedules = Schedule.objects.all().order_by('class_subject__classroom__name', 'class_subject__subject__name', 'day_of_week', 'start_time')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(
            models.Q(teacher=teacher) |
            models.Q(classroom__class_teacher=teacher)
        )
        schedules = Schedule.objects.filter(class_subject__in=class_subjects).order_by('day_of_week', 'start_time')
    elif request.user.role == 'STUDENT':
        student = request.user.student_profile
        class_subjects = ClassSubject.objects.filter(students=student)
        schedules = Schedule.objects.filter(class_subject__in=class_subjects).order_by('day_of_week', 'start_time')
    elif request.user.role == 'PARENT':
        parent = request.user.parent_profile
        students = parent.children.all()
        class_subjects = ClassSubject.objects.filter(students__in=students)
        schedules = Schedule.objects.filter(class_subject__in=class_subjects).distinct().order_by('day_of_week', 'start_time')
    else:
        schedules = Schedule.objects.none()

    # Create days of week mapping without relying on Schedule.DAY_CHOICES
    days_of_week = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    # Group schedules by day of week
    schedules_by_day = {}
    for day_num, day_name in days_of_week:
        schedules_by_day[day_num] = {
            'name': day_name,
            'schedules': []
        }

    for schedule in schedules:
        schedules_by_day[schedule.day_of_week]['schedules'].append(schedule)

    # Add current day of week to context
    current_day_of_week = timezone.now().weekday()  # Returns 0-6 (Monday=0, Sunday=6)

    # Calculate next day of week (0=Monday, 6=Sunday)
    next_day_of_week = (current_day_of_week + 1) % 7

    context = {
        'schedules_by_day': schedules_by_day,
        'current_day_of_week': current_day_of_week,
        'next_day_of_week': next_day_of_week,
        'can_create': request.user.role in ['ADMIN', 'TEACHER'],
    }
    return render(request, 'courses/schedule_list.html', context)

@login_required
def create_schedule(request):
    # Only teachers and admins can create schedules
    if not is_admin(request.user) and not is_teacher(request.user):
        messages.error(request, 'You do not have permission to create schedules.')
        return redirect('courses:schedule_list')

    if request.method == 'POST':
        class_subject_id = request.POST.get('class_subject')
        day_of_week = request.POST.get('day_of_week')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        if not class_subject_id or not day_of_week or not start_time or not end_time:
            messages.error(request, 'All fields are required.')
            return redirect('courses:create_schedule')

        try:
            class_subject = ClassSubject.objects.get(id=class_subject_id)

            # Check if user has permission to add schedule to this class subject
            if request.user.role == 'TEACHER':
                teacher = request.user.teacher_profile
                if teacher != class_subject.teacher and teacher != class_subject.classroom.class_teacher:
                    messages.error(request, 'You do not have permission to add schedule to this class subject.')
                    return redirect('courses:create_schedule')

            # Convert times to datetime.time objects
            start_time = datetime.strptime(start_time, '%H:%M').time()
            end_time = datetime.strptime(end_time, '%H:%M').time()

            # Check if end time is after start time
            if end_time <= start_time:
                messages.error(request, 'End time must be after start time.')
                return redirect('courses:create_schedule')

            # Check for schedule conflicts
            conflicts = Schedule.objects.filter(
                class_subject__classroom=class_subject.classroom,
                day_of_week=day_of_week
            ).filter(
                models.Q(start_time__lt=end_time, end_time__gt=start_time)
            )

            if conflicts.exists():
                conflict_list = ', '.join([f"{c.class_subject.subject.name} ({c.start_time.strftime('%H:%M')} - {c.end_time.strftime('%H:%M')})" for c in conflicts])
                messages.error(request, f'Schedule conflicts with existing schedules: {conflict_list}')
                return redirect('courses:create_schedule')

            schedule = Schedule.objects.create(
                class_subject=class_subject,
                day_of_week=int(day_of_week),
                start_time=start_time,
                end_time=end_time
            )

            messages.success(request, f'Schedule created successfully.')
            return redirect('courses:schedule_list')
        except Exception as e:
            messages.error(request, f'Error creating schedule: {str(e)}')
            return redirect('courses:create_schedule')

    # Get class subjects that the user has permission to add schedules to
    if request.user.role == 'ADMIN':
        class_subjects = ClassSubject.objects.all().order_by('classroom__name', 'subject__name')
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        class_subjects = ClassSubject.objects.filter(
            models.Q(teacher=teacher) |
            models.Q(classroom__class_teacher=teacher)
        ).order_by('classroom__name', 'subject__name')
    else:
        class_subjects = ClassSubject.objects.none()

    # Create days of week mapping without relying on Schedule.DAY_CHOICES
    days_of_week = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    context = {
        'class_subjects': class_subjects,
        'days_of_week': days_of_week,
    }
    return render(request, 'courses/create_schedule.html', context)

@login_required
def edit_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)

    # Check if user has permission to edit this schedule
    if request.user.role == 'ADMIN':
        pass  # Admin can edit all schedules
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if teacher != schedule.class_subject.teacher and teacher != schedule.class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to edit this schedule.')
            return redirect('courses:schedule_list')
    else:
        messages.error(request, 'You do not have permission to edit this schedule.')
        return redirect('courses:schedule_list')

    if request.method == 'POST':
        day_of_week = request.POST.get('day_of_week')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')

        if not day_of_week or not start_time or not end_time:
            messages.error(request, 'All fields are required.')
            return redirect('courses:edit_schedule', schedule_id=schedule_id)

        try:
            # Convert times to datetime.time objects
            start_time = datetime.strptime(start_time, '%H:%M').time()
            end_time = datetime.strptime(end_time, '%H:%M').time()

            # Check if end time is after start time
            if end_time <= start_time:
                messages.error(request, 'End time must be after start time.')
                return redirect('courses:edit_schedule', schedule_id=schedule_id)

            # Check for schedule conflicts (excluding this schedule)
            conflicts = Schedule.objects.filter(
                class_subject__classroom=schedule.class_subject.classroom,
                day_of_week=day_of_week
            ).exclude(id=schedule_id).filter(
                models.Q(start_time__lt=end_time, end_time__gt=start_time)
            )

            if conflicts.exists():
                conflict_list = ', '.join([f"{c.class_subject.subject.name} ({c.start_time.strftime('%H:%M')} - {c.end_time.strftime('%H:%M')})" for c in conflicts])
                messages.error(request, f'Schedule conflicts with existing schedules: {conflict_list}')
                return redirect('courses:edit_schedule', schedule_id=schedule_id)

            schedule.day_of_week = int(day_of_week)
            schedule.start_time = start_time
            schedule.end_time = end_time
            schedule.save()

            messages.success(request, f'Schedule updated successfully.')
            return redirect('courses:schedule_list')
        except Exception as e:
            messages.error(request, f'Error updating schedule: {str(e)}')
            return redirect('courses:edit_schedule', schedule_id=schedule_id)

    # Create days of week mapping without relying on Schedule.DAY_CHOICES
    days_of_week = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    context = {
        'schedule': schedule,
        'days_of_week': days_of_week,
        'start_time': schedule.start_time.strftime('%H:%M'),
        'end_time': schedule.end_time.strftime('%H:%M'),
    }
    return render(request, 'courses/edit_schedule.html', context)

@login_required
def delete_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)

    # Check if user has permission to delete this schedule
    if request.user.role == 'ADMIN':
        pass  # Admin can delete all schedules
    elif request.user.role == 'TEACHER':
        teacher = request.user.teacher_profile
        if teacher != schedule.class_subject.teacher and teacher != schedule.class_subject.classroom.class_teacher:
            messages.error(request, 'You do not have permission to delete this schedule.')
            return redirect('courses:schedule_list')
    else:
        messages.error(request, 'You do not have permission to delete this schedule.')
        return redirect('courses:schedule_list')

    if request.method == 'POST':
        try:
            schedule.delete()
            messages.success(request, f'Schedule deleted successfully.')
            return redirect('courses:schedule_list')
        except Exception as e:
            messages.error(request, f'Error deleting schedule: {str(e)}')
            return redirect('courses:schedule_list')

    context = {
        'schedule': schedule,
    }
    return render(request, 'courses/delete_schedule.html', context)


# Teacher assignment
@login_required
@user_passes_test(is_admin)
def assign_class_teacher(request, class_id):
    """Assign a teacher to a class."""
    classroom = get_object_or_404(ClassRoom, id=class_id)

    if request.method == 'POST':
        teacher_id = request.POST.get('class_teacher')

        try:
            if teacher_id:
                teacher = Teacher.objects.get(id=teacher_id)
            else:
                teacher = None

            classroom.class_teacher = teacher
            classroom.save()

            if teacher:
                messages.success(request, f'Assigned {teacher.user.get_full_name()} as class teacher for {classroom.name} {classroom.section or ""}.')
            else:
                messages.success(request, f'Removed class teacher from {classroom.name} {classroom.section or ""}.')

            # Check for 'next' parameter to determine redirect
            next_url = request.POST.get('next')
            if next_url == 'class_list':
                return redirect('courses:class_list')
            else:
                return redirect('courses:class_detail', class_id=class_id)
        except Exception as e:
            messages.error(request, f'Error assigning teacher: {str(e)}')
            # Redirect to class list on error for consistency
            return redirect('courses:class_list')

    # GET requests are not supported for this view
    return redirect('courses:class_list')

# Advanced Admin Operations
@login_required
@user_passes_test(is_admin)
def apply_subject_to_all(request):
    """Apply a subject to all classes with the same teacher."""
    if request.method == 'POST':
        subject_id = request.POST.get('subject_id')
        teacher_id = request.POST.get('teacher')
        skip_existing = request.POST.get('skip_existing') == 'on'

        if not subject_id:
            messages.error(request, 'Subject is required.')
            return redirect('courses:subject_list')

        try:
            subject = Subject.objects.get(id=subject_id)
            teacher = None
            if teacher_id:
                try:
                    teacher = Teacher.objects.get(id=teacher_id)
                except Teacher.DoesNotExist:
                    messages.warning(request, f'Selected teacher does not exist. Subject will be applied without a teacher.')

            classes = ClassRoom.objects.all()

            # Get existing class-subject combinations to avoid duplicates
            existing_combinations = ClassSubject.objects.filter(subject=subject)
            existing_class_ids = [cs.classroom.id for cs in existing_combinations]

            created_count = 0
            skipped_count = 0

            with transaction.atomic():
                for classroom in classes:
                    # Skip if this class already has this subject and skip_existing is True
                    if skip_existing and classroom.id in existing_class_ids:
                        skipped_count += 1
                        continue

                    # Skip if this exact combination already exists (safety check)
                    if ClassSubject.objects.filter(classroom=classroom, subject=subject).exists():
                        skipped_count += 1
                        continue

                    # Create the new class-subject combination
                    ClassSubject.objects.create(
                        classroom=classroom,
                        subject=subject,
                        teacher=teacher
                    )
                    created_count += 1

            if created_count > 0:
                messages.success(
                    request,
                    f'Applied subject "{subject.name}" to {created_count} classes with teacher {teacher.user.get_full_name() if teacher else "not assigned"}.'
                    + (f' Skipped {skipped_count} classes that already had this subject.' if skipped_count > 0 else '')
                )
            else:
                if skipped_count > 0:
                    messages.info(request, f'All classes already have subject "{subject.name}". No changes made.')
                else:
                    messages.warning(request, f'No classes found to apply subject "{subject.name}".')

            return redirect('courses:subject_detail', subject_id=subject.id)

        except Subject.DoesNotExist:
            messages.error(request, f'Subject with ID {subject_id} does not exist.')
            return redirect('courses:subject_list')
        except Teacher.DoesNotExist:
            messages.error(request, f'Teacher with ID {teacher_id} does not exist.')
            return redirect('courses:subject_list')
        except Exception as e:
            messages.error(request, f'Error applying subject to all classes: {str(e)}')
            return redirect('courses:subject_list')

    # GET requests are not supported for this view
    return redirect('courses:subject_list')

@login_required
@user_passes_test(is_admin)
def bulk_apply_subjects_to_all(request):
    """Apply multiple subjects to all classes."""
    if request.method == 'POST':
        subject_ids = request.POST.getlist('subject_ids')
        teacher_id = request.POST.get('teacher')
        skip_existing = request.POST.get('skip_existing', 'on') == 'on'

        if not subject_ids:
            messages.error(request, 'No subjects selected.')
            return redirect('courses:subject_list')

        try:
            teacher = None
            if teacher_id:
                try:
                    teacher = Teacher.objects.get(id=teacher_id)
                except Teacher.DoesNotExist:
                    messages.warning(request, f'Selected teacher does not exist. Subjects will be applied without a teacher.')

            classes = ClassRoom.objects.all()
            total_created = 0
            total_skipped = 0
            successful_subjects = []

            with transaction.atomic():
                for subject_id in subject_ids:
                    try:
                        subject = Subject.objects.get(id=subject_id)

                        # Get existing class-subject combinations to avoid duplicates
                        existing_combinations = ClassSubject.objects.filter(subject=subject)
                        existing_class_ids = [cs.classroom.id for cs in existing_combinations]

                        created_count = 0
                        skipped_count = 0

                        for classroom in classes:
                            # Skip if this class already has this subject and skip_existing is True
                            if skip_existing and classroom.id in existing_class_ids:
                                skipped_count += 1
                                continue

                            # Skip if this exact combination already exists (safety check)
                            if ClassSubject.objects.filter(classroom=classroom, subject=subject).exists():
                                skipped_count += 1
                                continue

                            # Create the new class-subject combination
                            ClassSubject.objects.create(
                                classroom=classroom,
                                subject=subject,
                                teacher=teacher
                            )
                            created_count += 1

                        total_created += created_count
                        total_skipped += skipped_count

                        if created_count > 0:
                            successful_subjects.append(subject.name)

                    except Subject.DoesNotExist:
                        # Skip invalid subject IDs and continue with the rest
                        continue

            if total_created > 0:
                subject_names = ", ".join(successful_subjects)
                messages.success(
                    request,
                    f'Successfully applied {len(successful_subjects)} subjects ({subject_names}) to a total of {total_created} class combinations'
                    + (f' and skipped {total_skipped} existing combinations.' if total_skipped > 0 else '.')
                )
            else:
                if total_skipped > 0:
                    messages.info(request, f'All selected subjects are already applied to all classes. No changes made.')
                else:
                    messages.warning(request, f'No classes found to apply the selected subjects.')

            return redirect('courses:subject_list')

        except Exception as e:
            messages.error(request, f'Error applying subjects to all classes: {str(e)}')
            return redirect('courses:subject_list')

    # GET requests are not supported for this view
    return redirect('courses:subject_list')


@login_required
@user_passes_test(is_admin)
def bulk_assign_teacher(request):
    """Assign a teacher to multiple classes at once."""
    if request.method == 'POST':
        class_ids = request.POST.getlist('class_ids')
        teacher_id = request.POST.get('teacher_id')

        if not class_ids or not teacher_id:
            messages.error(request, 'You must select at least one class and a teacher.')
            return redirect('courses:class_list')

        try:
            teacher = None if teacher_id == '' else Teacher.objects.get(id=teacher_id)

            with transaction.atomic():
                updated_count = 0
                for class_id in class_ids:
                    classroom = ClassRoom.objects.get(id=class_id)
                    classroom.class_teacher = teacher
                    classroom.save()
                    updated_count += 1

            if teacher:
                messages.success(request, f'Assigned teacher {teacher.user.get_full_name()} to {updated_count} classes.')
            else:
                messages.success(request, f'Removed class teacher from {updated_count} classes.')

            return redirect('courses:class_list')

        except Teacher.DoesNotExist:
            messages.error(request, f'Teacher with ID {teacher_id} does not exist.')
            return redirect('courses:class_list')
        except ClassRoom.DoesNotExist:
            messages.error(request, f'One or more selected classes do not exist.')
            return redirect('courses:class_list')
        except Exception as e:
            messages.error(request, f'Error assigning teacher to classes: {str(e)}')
            return redirect('courses:class_list')

    # GET requests are not supported for this view
    return redirect('courses:class_list')


@login_required
@user_passes_test(is_admin)
def bulk_add_subject(request):
    """Add a subject to multiple classes at once."""
    if request.method == 'POST':
        class_ids = request.POST.getlist('class_ids')
        subject_id = request.POST.get('subject_id')
        teacher_id = request.POST.get('teacher_id')

        if not class_ids or not subject_id or not teacher_id:
            messages.error(request, 'You must select at least one class, a subject, and a teacher.')
            return redirect('courses:class_list')

        try:
            subject = Subject.objects.get(id=subject_id)
            teacher = Teacher.objects.get(id=teacher_id)

            created_count = 0
            skipped_count = 0

            with transaction.atomic():
                for class_id in class_ids:
                    classroom = ClassRoom.objects.get(id=class_id)

                    # Skip if this exact combination already exists
                    if ClassSubject.objects.filter(classroom=classroom, subject=subject).exists():
                        skipped_count += 1
                        continue

                    # Create the new class-subject combination
                    ClassSubject.objects.create(
                        classroom=classroom,
                        subject=subject,
                        teacher=teacher
                    )
                    created_count += 1

            if created_count > 0:
                messages.success(
                    request,
                    f'Added subject "{subject.name}" to {created_count} classes with teacher {teacher.user.get_full_name()}.'
                    + (f' Skipped {skipped_count} classes that already had this subject.' if skipped_count > 0 else '')
                )
            else:
                if skipped_count > 0:
                    messages.info(request, f'All selected classes already have subject "{subject.name}". No changes made.')
                else:
                    messages.warning(request, f'No classes found to add subject "{subject.name}".')

            return redirect('courses:class_list')

        except Subject.DoesNotExist:
            messages.error(request, f'Subject with ID {subject_id} does not exist.')
            return redirect('courses:class_list')
        except Teacher.DoesNotExist:
            messages.error(request, f'Teacher with ID {teacher_id} does not exist.')
            return redirect('courses:class_list')
        except ClassRoom.DoesNotExist:
            messages.error(request, f'One or more selected classes do not exist.')
            return redirect('courses:class_list')
        except Exception as e:
            messages.error(request, f'Error adding subject to classes: {str(e)}')
            return redirect('courses:class_list')

    # GET requests are not supported for this view
    return redirect('courses:class_list')

@login_required
def get_subject_assigned_classes(request, subject_id):
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        class_subjects = ClassSubject.objects.filter(subject=subject).select_related(
            'classroom', 'teacher', 'teacher__user'
        )

        classes = []
        for cs in class_subjects:
            try:
                teacher_name = cs.teacher.user.get_full_name() if cs.teacher and cs.teacher.user else "No Teacher"
                classes.append({
                    'name': cs.classroom.name,
                    'section': cs.classroom.section,
                    'teacher_name': teacher_name,
                    'class_subject_id': cs.id
                })
            except Exception as e:
                # Skip this class if there's an issue with its data
                continue

        return JsonResponse({
            'classes': classes,
            'class_subjects': classes  # Add this to be compatible with both formats
        })
    except Exception as e:
        # Return an empty result if there's any error
        return JsonResponse({
            'classes': [],
            'class_subjects': [],
            'error': str(e)
        })

def get_class_subjects_by_query(request):
    """
    Retrieves class subjects for a given subject ID provided as a query parameter.
    This endpoint is specifically designed to match the JavaScript fetch in templates/courses/subject_list.html
    and does not require login to avoid redirect to login page (which would return HTML instead of JSON).
    """
    try:
        subject_id = request.GET.get('subject_id')
        if not subject_id:
            return JsonResponse({
                'class_subjects': [],
                'error': 'Subject ID is required'
            })

        subject = get_object_or_404(Subject, id=subject_id)
        class_subjects = ClassSubject.objects.filter(subject=subject).select_related(
            'classroom', 'teacher', 'teacher__user'
        )

        result = []
        for cs in class_subjects:
            try:
                # Format the data exactly as expected by the JavaScript
                # in templates/courses/subject_list.html
                classroom_name = f"{cs.classroom.name}"
                if cs.classroom.section:
                    classroom_name += f" ({cs.classroom.section})"

                teacher_name = cs.teacher.user.get_full_name() if cs.teacher and cs.teacher.user else "No Teacher"

                result.append({
                    'id': cs.id,
                    'classroom_name': classroom_name,
                    'teacher_name': teacher_name
                })
            except Exception as e:
                # Skip this class if there's an issue with its data
                continue

        return JsonResponse({
            'class_subjects': result
        })
    except Subject.DoesNotExist:
        return JsonResponse({
            'class_subjects': [],
            'error': f'Subject with ID {subject_id} does not exist'
        })
    except Exception as e:
            # Return an empty result with error details if there's any error
            return JsonResponse({
                'class_subjects': [],
                'error': str(e)
            })

@login_required
def get_class_subjects(request, class_id):
    """
    API endpoint to retrieve subjects assigned to a specific class.
    Returns JSON data with subjects and their details.
    """
    try:
        classroom = get_object_or_404(ClassRoom, id=class_id)
        class_subjects = ClassSubject.objects.filter(classroom=classroom).select_related(
            'subject', 'teacher', 'teacher__user'
        )

        subjects = []
        for cs in class_subjects:
            try:
                teacher_name = cs.teacher.user.get_full_name() if cs.teacher and cs.teacher.user else "No Teacher"
                subjects.append({
                    'id': cs.id,
                    'subject_id': cs.subject.id,
                    'name': cs.subject.name,
                    'code': cs.subject.code,
                    'teacher_name': teacher_name,
                    'teacher_id': cs.teacher.id if cs.teacher else None,
                    'students_count': cs.students.count()
                })
            except Exception as e:
                # Skip this subject if there's an issue with its data
                continue

        return JsonResponse({
            'subjects': subjects,
            'class_name': str(classroom)
        })
    except Exception as e:
        # Return an empty result if there's any error
        return JsonResponse({
            'subjects': [],
            'error': str(e)
        })
