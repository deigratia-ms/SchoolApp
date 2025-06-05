from django.urls import path
from . import views
from . import views_quiz

app_name = 'assignments'

urlpatterns = [
    # Assignments
    path('', views.assignment_list, name='assignment_list'),
    path('create/', views.create_assignment, name='create_assignment'),
    path('<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('<int:assignment_id>/edit/', views.edit_assignment, name='edit_assignment'),
    path('<int:assignment_id>/delete/', views.delete_assignment, name='delete_assignment'),

    # Questions
    path('<int:assignment_id>/questions/', views.question_list, name='question_list'),
    path('<int:assignment_id>/questions/create/', views.create_question, name='create_question'),
    path('questions/<int:question_id>/', views.question_detail, name='question_detail'),
    path('questions/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),

    # Choices for MCQs
    path('questions/<int:question_id>/choices/create/', views.create_choice, name='create_choice'),
    path('choices/<int:choice_id>/edit/', views.edit_choice, name='edit_choice'),
    path('choices/<int:choice_id>/delete/', views.delete_choice, name='delete_choice'),

    # Student Submissions
    path('<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),
    path('submissions/', views.submission_list, name='submission_list'),
    path('submissions/<int:submission_id>/', views.submission_detail, name='submission_detail'),
    path('submissions/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),

    # New Quiz Creation Flow (Teacher)
    path('quiz/create/', views_quiz.quiz_settings, name='create_quiz'),
    path('quiz/<int:quiz_id>/settings/', views_quiz.quiz_settings, name='quiz_settings'),
    path('quiz/<int:quiz_id>/questions/', views_quiz.quiz_questions, name='quiz_questions'),
    path('quiz/<int:quiz_id>/review/', views_quiz.quiz_review, name='quiz_review'),
    path('quiz/<int:quiz_id>/import-questions/', views_quiz.import_questions, name='import_questions'),
    path('quiz/delete-question/', views_quiz.delete_question, name='delete_question'),

    # New Quiz Taking Flow (Student)
    path('quiz/<int:quiz_id>/start/', views_quiz.quiz_start, name='quiz_start'),
    path('quiz-version/<int:quiz_version_id>/take/', views_quiz.take_quiz, name='take_quiz'),
    path('quiz-version/<int:quiz_version_id>/save-answer/', views_quiz.save_answer, name='save_answer'),
    path('quiz-version/<int:quiz_version_id>/submit/', views_quiz.submit_quiz, name='submit_quiz'),
    path('quiz-version/<int:quiz_version_id>/complete/', views_quiz.quiz_complete, name='quiz_complete'),
    path('quiz-version/<int:quiz_version_id>/result/', views_quiz.view_quiz_result, name='view_quiz_result'),

    # Legacy Quiz Taking (to be removed)
    path('<int:assignment_id>/take-quiz/', views.take_quiz, name='legacy_take_quiz'),
    path('<int:assignment_id>/retake-quiz/', views.retake_quiz, name='legacy_retake_quiz'),
    path('<int:assignment_id>/quiz-result/', views.quiz_result, name='legacy_quiz_result'),

    # Grading
    path('submissions/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
    path('submissions/<int:submission_id>/auto-grade/', views.auto_grade_submission, name='auto_grade_submission'),

    # Grades
    path('enter-term-grades/', views.enter_term_grades, name='enter_term_grades'),

    # Report Cards
    path('report-cards/', views.report_card_list, name='report_card_list'),
    path('report-cards/generate/', views.generate_report_cards, name='generate_report_cards'),
    path('report-cards/<int:report_card_id>/', views.view_report_card, name='view_report_card'),
    path('report-cards/<int:report_card_id>/print/', views.print_report_card, name='print_report_card'),
    path('report-cards/<int:report_card_id>/detail/', views.report_card_detail, name='report_card_detail'),
    path('report-cards/generate/<int:student_id>/', views.generate_report_card, name='generate_report_card'),

    # Report Card Exports
    path('report-cards/<int:report_card_id>/export/<str:format_type>/', views.export_report_card, name='export_report_card'),
    path('report-cards/export-all/<str:format_type>/', views.export_all_report_cards, name='export_all_report_cards'),

    # Teacher Gradebook
    path('gradebook/', views.gradebook, name='gradebook'),
    path('gradebook/<int:class_subject_id>/', views.class_gradebook, name='class_gradebook'),

    # Student Grade Views
    path('my-grades/', views.student_grades, name='student_grades'),
    path('my-assignments/', views.student_assignments, name='student_assignments'),

    # Parent Views
    path('parent-assignments/', views.parent_assignments, name='parent_assignments'),
    path('parent-grades/', views.parent_grades, name='parent_grades'),

    # API Endpoints for AJAX
    path('api/auto-grade/<int:submission_id>/', views.api_auto_grade_quiz, name='api_auto_grade_quiz'),
    path('api/grade-assignment/<int:submission_id>/', views.api_grade_assignment, name='api_grade_assignment'),
    path('api/toggle-feedback/<int:grade_id>/', views.api_toggle_feedback, name='api_toggle_feedback'),
]
