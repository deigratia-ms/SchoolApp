from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied
from django.conf import settings
import json
import csv
import io
import random
import datetime

from .models import (
    Assignment, Question, Choice, StudentSubmission, StudentAnswer,
    StudentQuizVersion, StudentQuizQuestion, StudentQuizChoice, StudentQuizAnswer
)
from users.models import Student, Teacher
from courses.models import ClassSubject, ClassRoom

# Helper functions
def is_teacher(user):
    return user.is_authenticated and user.role == 'TEACHER'

def is_student(user):
    return user.is_authenticated and user.role == 'STUDENT'

# Teacher Quiz Creation Views
@login_required
@user_passes_test(lambda u: is_teacher(u))
def quiz_settings(request, quiz_id=None):
    """
    Step 1: Quiz Settings
    Create a new quiz or edit an existing one
    """
    # Get teacher's class subjects
    teacher = get_object_or_404(Teacher, user=request.user)

    # Use Q objects to get all class subjects where:
    # 1. Teacher is directly assigned to the subject OR
    # 2. Teacher is the class teacher for the classroom
    from django.db.models import Q
    class_subjects = ClassSubject.objects.filter(
        Q(teacher=teacher) |
        Q(classroom__class_teacher=teacher)
    ).distinct()

    # Get existing quiz if editing
    quiz = None
    if quiz_id:
        quiz = get_object_or_404(Assignment, id=quiz_id, created_by=request.user, assignment_type='QUIZ')

    if request.method == 'POST':
        # Process form data
        title = request.POST.get('title')
        class_subject_id = request.POST.get('class_subject_id')
        description = request.POST.get('description')
        time_limit = request.POST.get('time_limit')
        due_date = request.POST.get('due_date')
        due_time = request.POST.get('due_time')
        questions_to_display = request.POST.get('questions_to_display')
        attempt_limit = request.POST.get('attempt_limit')
        randomize_questions = 'randomize_questions' in request.POST
        randomize_choices = 'randomize_choices' in request.POST

        # Validate required fields
        if not title or not class_subject_id or not due_date or not due_time:
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'assignments/quiz_settings.html', {
                'quiz': quiz,
                'class_subjects': class_subjects
            })

        # Convert time limit to integer if provided
        if time_limit and time_limit.strip():
            time_limit = int(time_limit)
        else:
            time_limit = None

        # Convert questions to display to integer if provided
        if questions_to_display and questions_to_display.strip():
            questions_to_display = int(questions_to_display)
        else:
            questions_to_display = None

        # Convert attempt limit to integer
        attempt_limit = int(attempt_limit) if attempt_limit else 1

        # Combine due date and time
        due_datetime = f"{due_date} {due_time}"
        due_datetime = timezone.datetime.strptime(due_datetime, "%Y-%m-%d %H:%M")
        due_datetime = timezone.make_aware(due_datetime)

        try:
            class_subject = ClassSubject.objects.get(id=class_subject_id)

            if quiz:
                # Update existing quiz
                quiz.title = title
                quiz.class_subject = class_subject
                quiz.description = description
                quiz.time_limit = time_limit
                quiz.due_date = due_datetime
                quiz.questions_to_display = questions_to_display
                quiz.attempt_limit = attempt_limit
                quiz.randomize_questions = randomize_questions
                quiz.randomize_choices = randomize_choices
                quiz.save()
                messages.success(request, f"Quiz '{title}' updated successfully.")
            else:
                # Create new quiz
                quiz = Assignment.objects.create(
                    title=title,
                    class_subject=class_subject,
                    description=description,
                    assignment_type='QUIZ',
                    max_score=100,
                    due_date=due_datetime,
                    is_active=True,
                    time_limit=time_limit,
                    questions_to_display=questions_to_display,
                    attempt_limit=attempt_limit,
                    randomize_questions=randomize_questions,
                    randomize_choices=randomize_choices,
                    created_by=request.user,
                    status='DRAFT'
                )
                messages.success(request, f"Quiz '{title}' created successfully.")

            # Redirect to question bank
            return redirect('assignments:quiz_questions', quiz_id=quiz.id)

        except ClassSubject.DoesNotExist:
            messages.error(request, "Selected class and subject combination does not exist.")

    return render(request, 'assignments/quiz_settings.html', {
        'quiz': quiz,
        'class_subjects': class_subjects
    })

@login_required
@user_passes_test(lambda u: is_teacher(u))
def quiz_questions(request, quiz_id):
    """
    Step 2: Question Bank
    Add questions to the quiz
    """
    quiz = get_object_or_404(Assignment, id=quiz_id, created_by=request.user, assignment_type='QUIZ')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_question':
            # Process question form
            question_text = request.POST.get('question_text')
            question_type = request.POST.get('question_type')
            points = request.POST.get('points', 1)
            tags = request.POST.get('tags')
            image = request.FILES.get('image')

            # Create question
            question = Question.objects.create(
                assignment=quiz,
                question_text=question_text,
                question_type=question_type,
                points=points,
                tags=tags,
                image=image,
                order=quiz.questions.count() + 1
            )

            # Handle different question types
            if question_type == 'MCQ':
                # Multiple choice question
                choice_texts = request.POST.getlist('choice_text[]')
                correct_choice = int(request.POST.get('correct_choice', 0))

                for i, choice_text in enumerate(choice_texts):
                    Choice.objects.create(
                        question=question,
                        choice_text=choice_text,
                        is_correct=(i == correct_choice),
                        order=i
                    )

            elif question_type == 'TF':
                # True/False question
                tf_answer = request.POST.get('tf_answer')

                Choice.objects.create(
                    question=question,
                    choice_text='True',
                    is_correct=(tf_answer == 'true'),
                    order=0
                )

                Choice.objects.create(
                    question=question,
                    choice_text='False',
                    is_correct=(tf_answer == 'false'),
                    order=1
                )

            elif question_type == 'SHORT':
                # Short answer question
                correct_answer = request.POST.get('correct_answer')
                if correct_answer:
                    question.notes = correct_answer
                    question.save()

            messages.success(request, "Question added successfully.")

    return render(request, 'assignments/quiz_questions.html', {
        'quiz': quiz
    })

@login_required
@user_passes_test(lambda u: is_teacher(u))
def delete_question(request):
    """
    Delete a question from a quiz
    """
    if request.method == 'POST':
        question_id = request.POST.get('question_id')

        try:
            question = Question.objects.get(id=question_id)

            # Check if user is the creator of the quiz
            if question.assignment.created_by != request.user:
                return JsonResponse({'success': False, 'error': 'You do not have permission to delete this question.'})

            # Delete the question
            question.delete()

            return JsonResponse({'success': True})

        except Question.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Question not found.'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
@user_passes_test(lambda u: is_teacher(u))
def import_questions(request, quiz_id):
    """
    Import questions from CSV
    """
    quiz = get_object_or_404(Assignment, id=quiz_id, created_by=request.user, assignment_type='QUIZ')

    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            return JsonResponse({'success': False, 'error': 'No file uploaded.'})

        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'success': False, 'error': 'File is not a CSV.'})

        # Process CSV file
        try:
            # Read CSV file
            csv_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_data))

            # Track import results
            imported_count = 0
            errors = []

            # Process each row
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header row
                try:
                    # Extract data from row
                    question_text = row.get('Question', '').strip()
                    option_a = row.get('Option A', '').strip()
                    option_b = row.get('Option B', '').strip()
                    option_c = row.get('Option C', '').strip()
                    option_d = row.get('Option D', '').strip()
                    correct_answer = row.get('Correct Answer', '').strip().upper()
                    question_type = row.get('Type', '').strip().upper()
                    tags = row.get('Tags', '').strip()
                    image_url = row.get('Image URL', '').strip()

                    # Validate required fields
                    if not question_text:
                        errors.append({'row': row_num, 'message': 'Question text is required.'})
                        continue

                    # Validate question type
                    if question_type not in ['MCQ', 'TF']:
                        errors.append({'row': row_num, 'message': f'Invalid question type: {question_type}. Must be MCQ or TF.'})
                        continue

                    # Create question
                    question = Question.objects.create(
                        assignment=quiz,
                        question_text=question_text,
                        question_type=question_type,
                        tags=tags,
                        order=quiz.questions.count() + 1
                    )

                    # Handle different question types
                    if question_type == 'MCQ':
                        # Validate options and correct answer
                        if not option_a or not option_b:
                            errors.append({'row': row_num, 'message': 'Multiple choice questions require at least options A and B.'})
                            question.delete()
                            continue

                        if correct_answer not in ['A', 'B', 'C', 'D']:
                            errors.append({'row': row_num, 'message': f'Invalid correct answer: {correct_answer}. Must be A, B, C, or D.'})
                            question.delete()
                            continue

                        # Create choices
                        choices = [
                            {'text': option_a, 'is_correct': correct_answer == 'A'},
                            {'text': option_b, 'is_correct': correct_answer == 'B'}
                        ]

                        if option_c:
                            choices.append({'text': option_c, 'is_correct': correct_answer == 'C'})

                        if option_d:
                            choices.append({'text': option_d, 'is_correct': correct_answer == 'D'})

                        for i, choice in enumerate(choices):
                            if choice['text']:
                                Choice.objects.create(
                                    question=question,
                                    choice_text=choice['text'],
                                    is_correct=choice['is_correct'],
                                    order=i
                                )

                    elif question_type == 'TF':
                        # Validate correct answer
                        if correct_answer not in ['TRUE', 'FALSE', 'T', 'F']:
                            errors.append({'row': row_num, 'message': f'Invalid correct answer for True/False: {correct_answer}. Must be TRUE or FALSE.'})
                            question.delete()
                            continue

                        # Create choices
                        Choice.objects.create(
                            question=question,
                            choice_text='True',
                            is_correct=correct_answer in ['TRUE', 'T'],
                            order=0
                        )

                        Choice.objects.create(
                            question=question,
                            choice_text='False',
                            is_correct=correct_answer in ['FALSE', 'F'],
                            order=1
                        )

                    imported_count += 1

                except Exception as e:
                    errors.append({'row': row_num, 'message': str(e)})

            return JsonResponse({
                'success': True,
                'imported_count': imported_count,
                'errors': errors
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
@user_passes_test(lambda u: is_teacher(u))
def quiz_review(request, quiz_id):
    """
    Step 3: Review & Publish
    Review quiz details and publish
    """
    quiz = get_object_or_404(Assignment, id=quiz_id, created_by=request.user, assignment_type='QUIZ')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save':
            publish_action = request.POST.get('publish_action')

            if publish_action == 'publish':
                quiz.status = 'PUBLISHED'
                messages.success(request, f"Quiz '{quiz.title}' has been published and is now available to students.")
            else:
                quiz.status = 'DRAFT'
                messages.success(request, f"Quiz '{quiz.title}' has been saved as a draft.")

            quiz.save()

            # Redirect to assignment list
            return redirect('assignments:assignment_list')

    return render(request, 'assignments/quiz_review.html', {
        'quiz': quiz
    })

# Student Quiz Taking Views
@login_required
@user_passes_test(lambda u: is_student(u))
def quiz_start(request, quiz_id):
    """
    Quiz Start Screen
    Show quiz details and allow student to start the quiz
    """
    quiz = get_object_or_404(Assignment, id=quiz_id, assignment_type='QUIZ', status='PUBLISHED', is_active=True)
    student = get_object_or_404(Student, user=request.user)

    # Check if quiz is available
    if quiz.due_date < timezone.now():
        messages.error(request, "This quiz is no longer available.")
        return redirect('assignments:assignment_list')

    # Check if student is enrolled in the class
    if student.grade != quiz.class_subject.classroom:
        messages.error(request, "You are not enrolled in this class.")
        return redirect('assignments:assignment_list')

    # Get previous attempts with submission data
    previous_quiz_versions = StudentQuizVersion.objects.filter(
        student=student,
        assignment=quiz,
        is_completed=True
    ).order_by('-completed_at')

    attempt_count = previous_quiz_versions.count()

    # Build previous attempts list with submission data
    previous_attempts = []
    try:
        submission = StudentSubmission.objects.get(student=student, assignment=quiz)
        for i, quiz_version in enumerate(previous_quiz_versions):
            # Calculate duration
            duration = None
            if quiz_version.completed_at and quiz_version.started_at:
                time_diff = quiz_version.completed_at - quiz_version.started_at
                hours = time_diff.seconds // 3600
                minutes = (time_diff.seconds % 3600) // 60
                seconds = time_diff.seconds % 60

                if hours > 0:
                    duration = f"{hours}h {minutes}m {seconds}s"
                else:
                    duration = f"{minutes}m {seconds}s"

            previous_attempts.append({
                'attempt_number': attempt_count - i,  # Show in reverse order (latest first)
                'completed_at': quiz_version.completed_at,
                'duration': duration,
                'submission': submission,
                'quiz_version': quiz_version
            })
    except StudentSubmission.DoesNotExist:
        # No submission found - this shouldn't happen for completed attempts
        for i, quiz_version in enumerate(previous_quiz_versions):
            previous_attempts.append({
                'attempt_number': attempt_count - i,
                'completed_at': quiz_version.completed_at,
                'duration': 'N/A',
                'submission': None,
                'quiz_version': quiz_version
            })

    # Check if student can attempt the quiz
    can_attempt = True
    attempt_message = ""

    if quiz.attempt_limit > 0 and attempt_count >= quiz.attempt_limit:
        can_attempt = False
        attempt_message = f"You have reached the maximum number of attempts ({quiz.attempt_limit})."

    # Process start quiz request
    if request.method == 'POST':
        # Double-check attempt limit before creating new quiz version
        if quiz.attempt_limit > 0 and attempt_count >= quiz.attempt_limit:
            messages.error(request, f"You have reached the maximum number of attempts ({quiz.attempt_limit}) for this quiz.")
            return redirect('assignments:assignment_list')

        if can_attempt:
            # Create a new quiz version for the student
            quiz_version, message = StudentQuizVersion.create_for_student(student, quiz)

            if quiz_version:
                # Start the quiz
                quiz_version.start_quiz()

                # Redirect to take quiz
                return redirect('assignments:take_quiz', quiz_version_id=quiz_version.id)
            else:
                messages.error(request, message)
        else:
            messages.error(request, attempt_message)

    # Get question count
    question_count = quiz.questions.count()
    if quiz.questions_to_display and quiz.questions_to_display < question_count:
        question_count = quiz.questions_to_display

    return render(request, 'assignments/quiz_start.html', {
        'quiz': quiz,
        'question_count': question_count,
        'can_attempt': can_attempt,
        'attempt_message': attempt_message or f"Attempt #{attempt_count + 1}",
        'attempt_count': attempt_count,
        'previous_attempts': previous_attempts
    })

@login_required
@user_passes_test(lambda u: is_student(u))
def take_quiz(request, quiz_version_id):
    """
    Question-by-Question View
    Allow student to take the quiz one question at a time
    """
    try:
        quiz_version = get_object_or_404(StudentQuizVersion, id=quiz_version_id)
        student = get_object_or_404(Student, user=request.user)
        quiz = quiz_version.assignment

        # Check if student owns this quiz version
        if quiz_version.student != student:
            messages.error(request, "You do not have permission to access this quiz.")
            return redirect('assignments:assignment_list')
    except:
        messages.error(request, "The quiz you're trying to access doesn't exist or has been removed.")
        return redirect('assignments:assignment_list')

    # Check if quiz is completed
    if quiz_version.is_completed:
        messages.info(request, "You have already completed this quiz.")
        return redirect('assignments:quiz_complete', quiz_version_id=quiz_version.id)

    # Check if quiz has timed out
    if quiz_version.is_timed_out:
        # Auto-submit the quiz
        return redirect('assignments:submit_quiz', quiz_version_id=quiz_version.id)

    # Get questions for this quiz version
    questions = quiz_version.questions.all().order_by('order')

    # Ensure each question has an answer object
    for question in questions:
        # Get or create answer
        answer, created = StudentQuizAnswer.objects.get_or_create(student_question=question)
        question.answer = answer

        # Get choices for MCQ and TF questions
        if question.question.question_type in ['MCQ', 'TF']:
            # Get or create student quiz choices
            if not hasattr(question, 'choices') or not question.choices.exists():
                # Get original choices
                original_choices = list(question.question.choices.all())

                # Randomize choices if enabled
                if quiz.randomize_choices:
                    random.shuffle(original_choices)

                # Create student quiz choices
                for i, choice in enumerate(original_choices):
                    StudentQuizChoice.objects.create(
                        student_question=question,
                        choice=choice,
                        order=i
                    )

    return render(request, 'assignments/quiz_take.html', {
        'quiz_version': quiz_version,
        'quiz': quiz,
        'questions': questions,
        'total_questions': questions.count()
    })

@login_required
@user_passes_test(lambda u: is_student(u))
def save_answer(request, quiz_version_id):
    """
    Save Answer (AJAX)
    Save a student's answer to a question
    """
    if request.method == 'POST':
        try:
            quiz_version = get_object_or_404(StudentQuizVersion, id=quiz_version_id)
            student = get_object_or_404(Student, user=request.user)
        except:
            return JsonResponse({'success': False, 'error': 'Quiz version not found'})

        # Check if student owns this quiz version
        if quiz_version.student != student:
            return JsonResponse({'success': False, 'error': 'Permission denied'})

        # Check if quiz is completed
        if quiz_version.is_completed:
            return JsonResponse({'success': False, 'error': 'Quiz is already completed'})

        # Get question
        question_id = request.POST.get('question_id')
        student_question = get_object_or_404(StudentQuizQuestion, id=question_id, quiz_version=quiz_version)

        # Get or create answer
        answer, created = StudentQuizAnswer.objects.get_or_create(student_question=student_question)

        # Save answer based on question type
        if student_question.question.question_type in ['MCQ', 'TF']:
            choice_id = request.POST.get('choice_id')
            if choice_id:
                choice = get_object_or_404(StudentQuizChoice, id=choice_id, student_question=student_question)
                answer.selected_choice = choice
                answer.save()
        else:
            text_answer = request.POST.get('text_answer')
            if text_answer is not None:
                answer.text_answer = text_answer
                answer.save()

        # Mark question as answered
        student_question.answer_saved = True
        student_question.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@user_passes_test(lambda u: is_student(u))
def submit_quiz(request, quiz_version_id):
    """
    Submit Quiz
    Complete the quiz and show results
    """
    try:
        quiz_version = get_object_or_404(StudentQuizVersion, id=quiz_version_id)
        student = get_object_or_404(Student, user=request.user)
        quiz = quiz_version.assignment

        # Check if student owns this quiz version
        if quiz_version.student != student:
            messages.error(request, "You do not have permission to access this quiz.")
            return redirect('assignments:assignment_list')
    except:
        messages.error(request, "The quiz you're trying to submit doesn't exist or has been removed.")
        return redirect('assignments:assignment_list')

    # Check if quiz is already completed
    if quiz_version.is_completed:
        return redirect('assignments:quiz_complete', quiz_version_id=quiz_version.id)

    # Mark quiz as completed
    quiz_version.complete_quiz()

    # Get or create submission record
    submission, created = StudentSubmission.objects.get_or_create(
        student=student,
        assignment=quiz,
        defaults={
            'submission_date': timezone.now(),
            'is_graded': False
        }
    )

    # Calculate current attempt score
    correct_count = 0
    total_points = 0
    max_points = 0
    current_attempt_score = 0

    # Clear previous answers for this submission to avoid duplicates
    StudentAnswer.objects.filter(submission=submission).delete()

    for student_question in quiz_version.questions.all():
        question = student_question.question
        max_points += question.points

        # Get answer
        try:
            answer = StudentQuizAnswer.objects.get(student_question=student_question)

            # Create student answer record for this attempt
            student_answer = StudentAnswer.objects.create(
                submission=submission,
                question=question
            )

            if question.question_type in ['MCQ', 'TF'] and answer.selected_choice:
                # Set selected choice
                student_answer.selected_choice = answer.selected_choice.choice
                student_answer.is_correct = answer.selected_choice.choice.is_correct

                if answer.selected_choice.choice.is_correct:
                    correct_count += 1
                    total_points += question.points

                student_answer.points_earned = question.points if answer.selected_choice.choice.is_correct else 0

            elif question.question_type == 'SHORT' and answer.text_answer:
                # Set text answer
                student_answer.text_answer = answer.text_answer

            student_answer.save()

        except StudentQuizAnswer.DoesNotExist:
            # No answer for this question - create empty answer record
            StudentAnswer.objects.create(
                submission=submission,
                question=question,
                is_correct=False,
                points_earned=0
            )

    # Calculate current attempt score
    current_attempt_score = (total_points / max_points) * 100 if max_points > 0 else 0

    # Auto-grade submission if all questions are MCQ or TF
    mcq_tf_count = quiz_version.questions.filter(question__question_type__in=['MCQ', 'TF']).count()
    total_questions = quiz_version.questions.count()

    if mcq_tf_count == total_questions:
        # All questions are auto-gradable
        submission.is_graded = True

        # Implement highest score logic: only update if current score is higher
        if not created and submission.score is not None:
            # This is a retake - keep the highest score
            submission.score = max(submission.score, current_attempt_score)
        else:
            # First attempt
            submission.score = current_attempt_score

        submission.submission_date = timezone.now()  # Update submission date for retakes
        submission.save()

    # Redirect to completion page
    return redirect('assignments:quiz_complete', quiz_version_id=quiz_version.id)

@login_required
@user_passes_test(lambda u: is_student(u))
def quiz_complete(request, quiz_version_id):
    """
    Quiz Completion Page
    Show quiz results
    """
    try:
        quiz_version = get_object_or_404(StudentQuizVersion, id=quiz_version_id)
        student = get_object_or_404(Student, user=request.user)
        quiz = quiz_version.assignment

        # Check if student owns this quiz version
        if quiz_version.student != student:
            messages.error(request, "You do not have permission to access this quiz.")
            return redirect('assignments:assignment_list')
    except:
        messages.error(request, "The quiz completion page you're trying to access doesn't exist or has been removed.")
        return redirect('assignments:assignment_list')

    # Get submission
    try:
        submission = StudentSubmission.objects.get(student=student, assignment=quiz)
        is_graded = submission.is_graded
        score = submission.score if submission.is_graded else None
        feedback = submission.feedback
    except StudentSubmission.DoesNotExist:
        is_graded = False
        score = None
        feedback = None

    # Calculate statistics
    total_questions = quiz_version.questions.count()
    answered_count = quiz_version.questions.filter(answer_saved=True).count()
    unanswered_count = total_questions - answered_count

    # Calculate correct/incorrect counts for the current quiz version
    correct_count = 0
    incorrect_count = 0

    if is_graded:
        # Get the answers for the current quiz version only
        for student_question in quiz_version.questions.all():
            try:
                answer = StudentQuizAnswer.objects.get(student_question=student_question)
                if student_question.question.question_type in ['MCQ', 'TF'] and answer.selected_choice:
                    if answer.selected_choice.choice.is_correct:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                elif student_question.question.question_type in ['SHORT', 'LONG']:
                    # For text questions, we need to check the StudentAnswer record
                    try:
                        student_answer = StudentAnswer.objects.get(
                            submission=submission,
                            question=student_question.question
                        )
                        if student_answer.is_correct:
                            correct_count += 1
                        else:
                            incorrect_count += 1
                    except StudentAnswer.DoesNotExist:
                        incorrect_count += 1
            except StudentQuizAnswer.DoesNotExist:
                incorrect_count += 1

    # Calculate completion time
    if quiz_version.completed_at and quiz_version.started_at:
        completion_time = quiz_version.completed_at - quiz_version.started_at
        hours = completion_time.seconds // 3600
        minutes = (completion_time.seconds % 3600) // 60
        seconds = completion_time.seconds % 60

        if hours > 0:
            completion_time = f"{hours}h {minutes}m {seconds}s"
        else:
            completion_time = f"{minutes}m {seconds}s"
    else:
        completion_time = "N/A"

    # Check if student can retake the quiz
    can_retake = False

    if quiz.attempt_limit == 0 or StudentQuizVersion.objects.filter(
        student=student,
        assignment=quiz,
        is_completed=True
    ).count() < quiz.attempt_limit:
        can_retake = True

    return render(request, 'assignments/quiz_complete.html', {
        'quiz_version': quiz_version,
        'quiz': quiz,
        'is_graded': is_graded,
        'score': score,
        'feedback': feedback,
        'total_questions': total_questions,
        'answered_count': answered_count,
        'unanswered_count': unanswered_count,
        'correct_count': correct_count,
        'incorrect_count': incorrect_count,
        'completion_time': completion_time,
        'can_retake': can_retake
    })

@login_required
@user_passes_test(lambda u: is_student(u))
def view_quiz_result(request, quiz_version_id):
    """
    View Detailed Quiz Results
    Show detailed results for a completed quiz
    """
    try:
        quiz_version = get_object_or_404(StudentQuizVersion, id=quiz_version_id)
        student = get_object_or_404(Student, user=request.user)
        quiz = quiz_version.assignment

        # Check if student owns this quiz version
        if quiz_version.student != student:
            messages.error(request, "You do not have permission to access this quiz.")
            return redirect('assignments:assignment_list')
    except:
        messages.error(request, "The quiz results you're trying to view don't exist or have been removed.")
        return redirect('assignments:assignment_list')

    # Check if quiz is completed
    if not quiz_version.is_completed:
        messages.error(request, "This quiz is not yet completed.")
        return redirect('assignments:take_quiz', quiz_version_id=quiz_version.id)

    # Get submission
    try:
        submission = StudentSubmission.objects.get(student=student, assignment=quiz)
    except StudentSubmission.DoesNotExist:
        messages.error(request, "No submission found for this quiz.")
        return redirect('assignments:assignment_list')

    # Get answers for this specific quiz version
    answers = []
    correct_count = 0
    incorrect_count = 0
    answered_count = 0

    # Build answers list from the current quiz version
    for student_question in quiz_version.questions.all().order_by('order'):
        try:
            quiz_answer = StudentQuizAnswer.objects.get(student_question=student_question)

            # Create a display object that matches what the template expects
            answer_obj = type('Answer', (), {})()
            answer_obj.question = student_question.question
            answer_obj.is_correct = False
            answer_obj.selected_choice = None
            answer_obj.text_answer = None
            answer_obj.file_answer = None
            answer_obj.feedback = None
            answer_obj.score = 0

            if student_question.question.question_type in ['MCQ', 'TF'] and quiz_answer.selected_choice:
                answer_obj.selected_choice = quiz_answer.selected_choice.choice
                answer_obj.is_correct = quiz_answer.selected_choice.choice.is_correct
                answer_obj.score = student_question.question.points if answer_obj.is_correct else 0

                if answer_obj.is_correct:
                    correct_count += 1
                else:
                    incorrect_count += 1
                answered_count += 1

            elif student_question.question.question_type in ['SHORT', 'LONG'] and quiz_answer.text_answer:
                answer_obj.text_answer = quiz_answer.text_answer
                # For text answers, check if there's a corresponding StudentAnswer record for grading
                try:
                    student_answer = StudentAnswer.objects.get(
                        submission=submission,
                        question=student_question.question
                    )
                    answer_obj.is_correct = student_answer.is_correct
                    answer_obj.feedback = student_answer.feedback
                    answer_obj.score = student_answer.points_earned or 0

                    if answer_obj.is_correct:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                    answered_count += 1
                except StudentAnswer.DoesNotExist:
                    # Not graded yet
                    answered_count += 1
            else:
                # No answer provided
                incorrect_count += 1

            answers.append(answer_obj)

        except StudentQuizAnswer.DoesNotExist:
            # No answer for this question
            answer_obj = type('Answer', (), {})()
            answer_obj.question = student_question.question
            answer_obj.is_correct = False
            answer_obj.selected_choice = None
            answer_obj.text_answer = None
            answer_obj.file_answer = None
            answer_obj.feedback = None
            answer_obj.score = 0
            answers.append(answer_obj)
            incorrect_count += 1

    # Calculate score percentage
    score_percentage = 0
    if quiz.max_score > 0:
        score_percentage = (submission.score / quiz.max_score) * 100

    # Get current time for checking if retake is allowed
    current_time = timezone.now()

    # Get attempt information
    all_attempts = StudentQuizVersion.objects.filter(
        student=student,
        assignment=quiz,
        is_completed=True
    ).order_by('completed_at')

    attempt_number = 1
    for i, attempt in enumerate(all_attempts, 1):
        if attempt.id == quiz_version.id:
            attempt_number = i
            break

    # Check if student can retake
    can_retake = False
    if quiz.attempt_limit == 0 or all_attempts.count() < quiz.attempt_limit:
        can_retake = True

    return render(request, 'assignments/quiz_result.html', {
        'quiz_version': quiz_version,
        'quiz': quiz,
        'assignment': quiz,  # Add assignment alias for template compatibility
        'submission': submission,
        'answers': answers,
        'correct_count': correct_count,
        'incorrect_count': incorrect_count,
        'answered_count': answered_count,
        'score_percentage': score_percentage,
        'current_time': current_time,
        'attempt_number': attempt_number,
        'total_attempts': all_attempts.count(),
        'can_retake': can_retake
    })
