from django.db import models
from django.conf import settings
from django.utils import timezone
from courses.models import ClassSubject
from users.models import Student

class GradingScale(models.Model):
    """
    Model to store customizable grading scales for the school.
    Allows administrators to define grade thresholds and letter grades.
    """
    name = models.CharField(max_length=100)  # e.g., "Standard Scale", "AP Courses Scale"
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)

    # Term/Year this scale applies to (optional)
    academic_term = models.CharField(max_length=50, blank=True, null=True)  # e.g., "2023-2024"

    # Which classes/subjects this scale applies to (optional)
    class_level = models.CharField(max_length=50, blank=True, null=True)  # e.g., "High School", "Middle School"

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_grading_scales')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # If this is being set as default, unset any other defaults
        if self.is_default:
            GradingScale.objects.filter(is_default=True).update(is_default=False)

        # If no default exists and this is the first scale, make it default
        elif not GradingScale.objects.filter(is_default=True).exists() and not GradingScale.objects.exists():
            self.is_default = True

        super().save(*args, **kwargs)

        # Create default thresholds if this is a new scale
        if not self.thresholds.exists():
            GradeThreshold.objects.bulk_create([
                GradeThreshold(
                    scale=self,
                    letter_grade='A',
                    min_percent=80.00,
                    max_percent=100.00,
                    gpa_points=4.00,
                    description='Excellent',
                    order=1
                ),
                GradeThreshold(
                    scale=self,
                    letter_grade='B',
                    min_percent=70.00,
                    max_percent=79.99,
                    gpa_points=3.00,
                    description='Very Good',
                    order=2
                ),
                GradeThreshold(
                    scale=self,
                    letter_grade='C',
                    min_percent=60.00,
                    max_percent=69.99,
                    gpa_points=2.00,
                    description='Good',
                    order=3
                ),
                GradeThreshold(
                    scale=self,
                    letter_grade='D',
                    min_percent=50.00,
                    max_percent=59.99,
                    gpa_points=1.00,
                    description='Pass',
                    order=4
                ),
                GradeThreshold(
                    scale=self,
                    letter_grade='F',
                    min_percent=0.00,
                    max_percent=49.99,
                    gpa_points=0.00,
                    description='Fail',
                    order=5
                )
            ])


class GradeThreshold(models.Model):
    """
    Model to define grade thresholds for a grading scale.
    """
    scale = models.ForeignKey(GradingScale, on_delete=models.CASCADE, related_name='thresholds')
    letter_grade = models.CharField(max_length=5)  # e.g., "A+", "A", "A-", "B+", etc.
    min_percent = models.DecimalField(max_digits=5, decimal_places=2)  # Minimum percentage for this grade
    max_percent = models.DecimalField(max_digits=5, decimal_places=2)  # Maximum percentage for this grade
    gpa_points = models.DecimalField(max_digits=3, decimal_places=2)  # GPA points equivalent
    description = models.CharField(max_length=50, blank=True, null=True)  # e.g., "Excellent", "Good", "Satisfactory"
    color = models.CharField(max_length=20, blank=True, null=True)  # Color for display (e.g., hex code)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-min_percent']
        unique_together = ['scale', 'letter_grade']

    def __str__(self):
        return f"{self.letter_grade} ({self.min_percent}% - {self.max_percent}%)"


class Assignment(models.Model):
    """
    Model to store assignments created by teachers.
    """
    class AssignmentType(models.TextChoices):
        HOMEWORK = 'HOMEWORK', 'Homework'
        QUIZ = 'QUIZ', 'Quiz'
        TEST = 'TEST', 'Test'
        EXAM = 'EXAM', 'Exam'
        PROJECT = 'PROJECT', 'Project'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        ARCHIVED = 'ARCHIVED', 'Archived'

    title = models.CharField(max_length=255)
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='assignments')
    description = models.TextField()
    assignment_type = models.CharField(max_length=20, choices=AssignmentType.choices, default=AssignmentType.HOMEWORK)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    file_attachment = models.FileField(upload_to='assignments/', blank=True, null=True)
    max_score = models.PositiveIntegerField(default=100)

    due_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    time_limit = models.PositiveIntegerField(blank=True, null=True, help_text="Time limit in minutes (for quizzes only). When set, students will have this amount of time to complete the quiz once started.")
    questions_to_display = models.PositiveIntegerField(blank=True, null=True, help_text="Number of questions to randomly select from the question bank. Leave blank to show all questions.")
    randomize_questions = models.BooleanField(default=True, help_text="Whether to randomize the order of questions.")
    randomize_choices = models.BooleanField(default=True, help_text="Whether to randomize the order of multiple choice answers.")
    attempt_limit = models.PositiveIntegerField(default=1, help_text="Number of attempts allowed (0 for unlimited)")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_assignments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.class_subject.subject.name}"


class Question(models.Model):
    """
    Model to store questions for assignments/quizzes.
    """
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = 'MCQ', 'Multiple Choice'
        TRUE_FALSE = 'TF', 'True/False'
        SHORT_ANSWER = 'SHORT', 'Short Answer'
        LONG_ANSWER = 'LONG', 'Long Answer'
        FILE_UPLOAD = 'FILE', 'File Upload'

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QuestionType.choices)
    points = models.PositiveIntegerField(default=1)
    show_feedback = models.BooleanField(default=True)  # Toggle for showing feedback to students
    notes = models.TextField(blank=True, null=True)  # For storing additional information (expected answers, grading hints, etc.)
    tags = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated tags for categorizing questions")
    image = models.ImageField(upload_to='question_images/', blank=True, null=True)

    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Question {self.order}: {self.question_text[:50]}..."

    def get_tag_list(self):
        """Returns the tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',')]


class Choice(models.Model):
    """
    Model to store choices for multiple-choice questions.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.choice_text[:50]}... ({'Correct' if self.is_correct else 'Incorrect'})"


class StudentSubmission(models.Model):
    """
    Model to store student submissions for assignments.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    submission_date = models.DateTimeField(auto_now_add=True)

    # For non-MCQ assignments
    file_submission = models.FileField(upload_to='student_submissions/', blank=True, null=True)
    text_submission = models.TextField(blank=True, null=True)

    is_graded = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'assignment')

    def __str__(self):
        return f"{self.student.user.username}'s submission for {self.assignment.title}"


class StudentAnswer(models.Model):
    """
    Model to store student answers for questions.
    """
    submission = models.ForeignKey(StudentSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='student_answers')

    # For multiple choice questions
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, blank=True, null=True, related_name='selections')

    # For text-based questions
    text_answer = models.TextField(blank=True, null=True)

    # For file upload questions
    file_answer = models.FileField(upload_to='student_answers/', blank=True, null=True)

    is_correct = models.BooleanField(default=False)  # Auto-marked for MCQs
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"Answer to {self.question} by {self.submission.student.user.username}"

    def save(self, *args, **kwargs):
        # Auto-marking for MCQs
        if self.question.question_type == Question.QuestionType.MULTIPLE_CHOICE and self.selected_choice:
            self.is_correct = self.selected_choice.is_correct
            self.points_earned = self.question.points if self.is_correct else 0

        super().save(*args, **kwargs)


class Grade(models.Model):
    """
    Model to store grades for students in each subject.
    """
    class GradeType(models.TextChoices):
        ASSIGNMENT = 'ASSIGNMENT', 'Assignment'
        QUIZ = 'QUIZ', 'Quiz'
        TEST = 'TEST', 'Test'
        EXAM = 'EXAM', 'Exam'
        PROJECT = 'PROJECT', 'Project'
        TERM = 'TERM', 'Term Grade'

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='grades')
    grade_type = models.CharField(max_length=20, choices=GradeType.choices)

    # Can be linked to a submission if it's for an assignment
    submission = models.OneToOneField(StudentSubmission, on_delete=models.SET_NULL, blank=True, null=True, related_name='grade')

    score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.PositiveIntegerField(default=100)

    # For letter grading
    letter_grade = models.CharField(max_length=2, blank=True, null=True)

    comments = models.TextField(blank=True, null=True)
    term = models.CharField(max_length=20, blank=True, null=True)  # First term, second term, etc.

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grades_given')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.user.username}'s {self.grade_type} grade in {self.class_subject.subject.name}"

    @property
    def percentage(self):
        return (self.score / self.max_score) * 100


class ReportCard(models.Model):
    """
    Model to store report cards for students.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='report_cards')
    term = models.CharField(max_length=20)  # First term, second term, etc.
    academic_year = models.CharField(max_length=10)  # e.g., 2023-2024

    # Academic performance statistics
    average_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    average_assignment_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    average_quiz_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    average_exam_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    overall_grade = models.CharField(max_length=2, blank=True, null=True)  # A, B, C, etc.

    # Comments section
    teacher_comments = models.TextField(blank=True, null=True)
    principal_comments = models.TextField(blank=True, null=True)

    # Attendance statistics
    total_school_days = models.PositiveIntegerField(default=0)
    days_present = models.PositiveIntegerField(default=0)
    days_absent = models.PositiveIntegerField(default=0)
    days_late = models.PositiveIntegerField(default=0)

    # Skills and behavior assessment - using E (Excellent), G (Good), S (Satisfactory), N (Needs Improvement)
    responsibility_rating = models.CharField(max_length=1, blank=True, null=True)
    organization_rating = models.CharField(max_length=1, blank=True, null=True)
    independent_work_rating = models.CharField(max_length=1, blank=True, null=True)
    collaboration_rating = models.CharField(max_length=1, blank=True, null=True)
    initiative_rating = models.CharField(max_length=1, blank=True, null=True)
    conduct_rating = models.CharField(max_length=1, blank=True, null=True)

    # Promotion status
    is_promoted = models.BooleanField(default=True)
    promotion_notes = models.TextField(blank=True, null=True)

    # Report generation metadata
    generated_date = models.DateField(auto_now_add=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generated_report_cards')

    class Meta:
        unique_together = ('student', 'term', 'academic_year')

    def __str__(self):
        return f"Report Card: {self.student.user.username} - {self.term} {self.academic_year}"

    @property
    def attendance_percentage(self):
        """Calculate the attendance percentage"""
        if not self.total_school_days:
            return 0
        return round((self.days_present / self.total_school_days) * 100, 1)

    def calculate_grades_from_submissions(self):
        """
        Calculate grades based on student submissions for the term
        """
        from .models import StudentSubmission, Grade
        from django.db.models import Avg

        # Get all subjects the student is enrolled in
        subjects = self.student.enrolled_subjects.all()

        assignment_scores = []
        quiz_scores = []
        exam_scores = []
        overall_scores = []

        for subject in subjects:
            # Get submissions for assignments in this subject during the term
            submissions = StudentSubmission.objects.filter(
                student=self.student,
                assignment__class_subject=subject,
                is_graded=True
            )

            # Calculate average scores by assignment type
            assignment_avg = submissions.filter(
                assignment__assignment_type='HOMEWORK'
            ).aggregate(avg=Avg('score'))['avg'] or 0

            quiz_avg = submissions.filter(
                assignment__assignment_type='QUIZ'
            ).aggregate(avg=Avg('score'))['avg'] or 0

            exam_avg = submissions.filter(
                assignment__assignment_type__in=['TEST', 'EXAM']
            ).aggregate(avg=Avg('score'))['avg'] or 0

            # Calculate total score with weights
            # Weights can be adjusted as needed
            assignment_weight = 0.3  # 30%
            quiz_weight = 0.3        # 30%
            exam_weight = 0.4        # 40%

            total_score = (
                (assignment_avg * assignment_weight) +
                (quiz_avg * quiz_weight) +
                (exam_avg * exam_weight)
            )

            # Store scores for calculating overall averages
            if assignment_avg > 0:
                assignment_scores.append(assignment_avg)
            if quiz_avg > 0:
                quiz_scores.append(quiz_avg)
            if exam_avg > 0:
                exam_scores.append(exam_avg)
            if total_score > 0:
                overall_scores.append(total_score)

        # Calculate overall averages
        self.average_assignment_score = sum(assignment_scores) / len(assignment_scores) if assignment_scores else 0
        self.average_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
        self.average_exam_score = sum(exam_scores) / len(exam_scores) if exam_scores else 0
        self.average_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0

        # Set overall grade
        if self.average_score >= 90:
            self.overall_grade = 'A'
        elif self.average_score >= 80:
            self.overall_grade = 'B'
        elif self.average_score >= 70:
            self.overall_grade = 'C'
        elif self.average_score >= 60:
            self.overall_grade = 'D'
        elif self.average_score >= 50:
            self.overall_grade = 'E'
        else:
            self.overall_grade = 'F'

        self.save()

    def calculate_attendance(self):
        """
        Calculate attendance statistics from attendance records
        """
        from attendance.models import AttendanceRecord
        from users.models import SchoolSettings
        from dateutil.relativedelta import relativedelta
        from django.utils import timezone
        import datetime

        # Get the school settings
        try:
            school_settings = SchoolSettings.objects.get()
        except SchoolSettings.DoesNotExist:
            school_settings = None

        # Determine term dates based on academic year and term
        start_date = None
        end_date = None

        # Parse academic year (e.g., "2023-2024")
        academic_year_parts = self.academic_year.split('-')
        if len(academic_year_parts) == 2:
            start_year = int(academic_year_parts[0])
            end_year = int(academic_year_parts[1])
        else:
            # Default to current year if format is invalid
            current_year = timezone.now().year
            start_year = current_year
            end_year = current_year + 1

        # Define term dates based on school settings or defaults
        if school_settings and hasattr(school_settings, 'term_start_dates') and hasattr(school_settings, 'term_end_dates'):
            # Use school-defined term dates if available
            term_dates = school_settings.get_term_dates(self.term, self.academic_year)
            if term_dates:
                start_date, end_date = term_dates

        # If term dates not defined in settings, use standard academic calendar
        if not start_date or not end_date:
            if self.term == 'First Term':
                # First term typically runs from September to December
                start_date = datetime.date(start_year, 9, 1)
                end_date = datetime.date(start_year, 12, 20)
            elif self.term == 'Second Term':
                # Second term typically runs from January to March/April
                start_date = datetime.date(end_year, 1, 10)
                end_date = datetime.date(end_year, 3, 31)
            elif self.term == 'Third Term':
                # Third term typically runs from April to July
                start_date = datetime.date(end_year, 4, 15)
                end_date = datetime.date(end_year, 7, 31)
            else:
                # Default to current quarter if term is not recognized
                today = timezone.now().date()
                start_date = today - relativedelta(months=3)
                end_date = today

        # Get attendance records for this student in the current term
        attendance_records = AttendanceRecord.objects.filter(
            student=self.student,
            date__gte=start_date,
            date__lte=end_date
        )

        # Update attendance statistics
        self.days_present = attendance_records.filter(status='PRESENT').count()
        self.days_absent = attendance_records.filter(status='ABSENT').count()
        self.days_late = attendance_records.filter(status='LATE').count()

        # Determine total school days from records or calendar
        if school_settings and hasattr(school_settings, 'school_days_per_term'):
            # Use school-defined total days if available
            self.total_school_days = school_settings.get_school_days(self.term, self.academic_year)
        else:
            # If no setting is available, use the sum of all attendance records
            # This assumes that records exist for every school day
            self.total_school_days = self.days_present + self.days_absent + self.days_late

            # If no records, estimate based on typical school calendar (5 days per week)
            if self.total_school_days == 0:
                # Count weekdays (Mon-Fri) between start_date and end_date
                total_days = 0
                current_date = start_date
                while current_date <= end_date:
                    # Weekdays are 0-4 (Mon-Fri)
                    if current_date.weekday() < 5:
                        total_days += 1
                    current_date += datetime.timedelta(days=1)
                self.total_school_days = total_days

        self.save()


class AssessmentWeightConfiguration(models.Model):
    """
    Model to store customizable assessment weight configurations for report card generation.
    Allows administrators to define which assessment components to include in final grades
    and their respective weight percentages.
    """
    name = models.CharField(max_length=100)  # e.g., "Default Configuration", "Final Term Configuration"
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=True)  # Only one configuration is needed

    # Term/Year this configuration applies to (optional)
    academic_term = models.CharField(max_length=50, blank=True, null=True)  # e.g., "First Term", "Second Term"
    academic_year = models.CharField(max_length=20, blank=True, null=True)  # e.g., "2023-2024"

    # Component inclusion flags
    include_classwork = models.BooleanField(default=True)
    include_quizzes = models.BooleanField(default=False)
    include_tests = models.BooleanField(default=False)
    include_midterm = models.BooleanField(default=True)
    include_projects = models.BooleanField(default=True)
    include_final_exam = models.BooleanField(default=True)
    include_attendance = models.BooleanField(default=False)

    # Term report assessment weights (percentages)
    classwork_weight = models.DecimalField(max_digits=5, decimal_places=2, default=10.00,
        help_text="Weight percentage for classwork (10%)")
    quiz_weight = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
        help_text="Weight percentage for quizzes (0%)")
    test_weight = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
        help_text="Weight percentage for tests (0%)")
    midterm_weight = models.DecimalField(max_digits=5, decimal_places=2, default=20.00,
        help_text="Weight percentage for mid-term exams (20%)")
    project_weight = models.DecimalField(max_digits=5, decimal_places=2, default=10.00,
        help_text="Weight percentage for project work (10%)")
    final_exam_weight = models.DecimalField(max_digits=5, decimal_places=2, default=60.00,
        help_text="Weight percentage for final exams (60%)")
    attendance_weight = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
        help_text="Weight percentage for attendance (0%)")

    # Keep for backward compatibility
    endterm_weight = models.DecimalField(max_digits=5, decimal_places=2, default=60.00,
        help_text="Weight percentage for end of term exams (60%)")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_weight_configs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.academic_term and self.academic_year:
            return f"{self.name} - {self.academic_term} {self.academic_year}"
        return self.name

    def save(self, *args, **kwargs):
        # Check if this is a new object or existing one
        is_new = self.pk is None

        # Get original instance if this is an existing object
        if not is_new:
            try:
                original = AssessmentWeightConfiguration.objects.get(pk=self.pk)
                only_changing_default = (
                    original.classwork_weight == self.classwork_weight and
                    original.include_classwork == self.include_classwork and
                    original.quiz_weight == self.quiz_weight and
                    original.include_quizzes == self.include_quizzes and
                    original.test_weight == self.test_weight and
                    original.include_tests == self.include_tests and
                    original.midterm_weight == self.midterm_weight and
                    original.include_midterm == self.include_midterm and
                    original.project_weight == self.project_weight and
                    original.include_projects == self.include_projects and
                    original.final_exam_weight == self.final_exam_weight and
                    original.include_final_exam == self.include_final_exam and
                    original.attendance_weight == self.attendance_weight and
                    original.include_attendance == self.include_attendance
                )
            except AssessmentWeightConfiguration.DoesNotExist:
                only_changing_default = False
        else:
            only_changing_default = False

        # Sync endterm_weight with final_exam_weight for backward compatibility
        self.endterm_weight = self.final_exam_weight

        # Only enforce weight validation if we're not just changing the default flag
        if not only_changing_default:
            # Calculate total weight of enabled components
            total_weight = 0
            if self.include_classwork:
                total_weight += self.classwork_weight
            if self.include_quizzes:
                total_weight += self.quiz_weight
            if self.include_tests:
                total_weight += self.test_weight
            if self.include_midterm:
                total_weight += self.midterm_weight
            if self.include_projects:
                total_weight += self.project_weight
            if self.include_final_exam:
                total_weight += self.final_exam_weight
            if self.include_attendance:
                total_weight += self.attendance_weight

            # Validate that enabled weights sum to 100%
            if total_weight != 100:
                raise ValueError("Assessment weights must sum to 100%")

        # If setting this config as default, unset all others first
        if self.is_default:
            # We need to exclude self to avoid integrity error if self already exists
            if not is_new:
                AssessmentWeightConfiguration.objects.exclude(pk=self.pk).update(is_default=False)
            else:
                AssessmentWeightConfiguration.objects.all().update(is_default=False)

        super().save(*args, **kwargs)

    @classmethod
    def get_default_configuration(cls):
        """
        Get the default assessment weight configuration.
        If no configuration exists, create a default one.
        """
        config = cls.objects.first()  # Only one configuration exists
        if config:
            return config

        # No configuration exists, create a default one
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin = User.objects.filter(is_superuser=True).first()

        if not admin:
            # If no admin exists, cannot create default
            return None

        # Create default configuration with standard weights
        return cls.objects.create(
            name="Default Term Report Configuration",
            description="Standard term report assessment weights (Classwork: 10%, Mid-term: 20%, Final Exam: 60%, Project: 10%)",
            is_default=True,
            include_classwork=True,
            include_midterm=True,
            include_projects=True,
            include_final_exam=True,
            classwork_weight=10.00,
            midterm_weight=20.00,
            project_weight=10.00,
            final_exam_weight=60.00,
            created_by=admin
        )

    def get_enabled_components(self):
        """
        Returns a list of enabled assessment components with their weights
        """
        components = []

        if self.include_classwork:
            components.append({
                'name': 'classwork',
                'label': 'Classwork',
                'weight': float(self.classwork_weight),
                'field_name': 'classwork_score'
            })

        if self.include_quizzes:
            components.append({
                'name': 'quizzes',
                'label': 'Quizzes',
                'weight': float(self.quiz_weight),
                'field_name': 'quiz_score'
            })

        if self.include_tests:
            components.append({
                'name': 'tests',
                'label': 'Tests',
                'weight': float(self.test_weight),
                'field_name': 'test_score'
            })

        if self.include_midterm:
            components.append({
                'name': 'midterm',
                'label': 'Mid-term',
                'weight': float(self.midterm_weight),
                'field_name': 'midterm_score'
            })

        if self.include_projects:
            components.append({
                'name': 'projects',
                'label': 'Projects',
                'weight': float(self.project_weight),
                'field_name': 'project_score'
            })

        if self.include_final_exam:
            components.append({
                'name': 'final_exam',
                'label': 'Final Exam',
                'weight': float(self.final_exam_weight),
                'field_name': 'final_exam_score'
            })

        if self.include_attendance:
            components.append({
                'name': 'attendance',
                'label': 'Attendance',
                'weight': float(self.attendance_weight),
                'field_name': 'attendance_score'
            })

        return components

class ReportCardSubjectGrade(models.Model):
    """
    Model to store subject-specific grades for report cards.
    """
    report_card = models.ForeignKey(ReportCard, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey('courses.Subject', on_delete=models.CASCADE)

    # Component scores
    assignment_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    quiz_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Grade details
    letter_grade = models.CharField(max_length=2)
    remarks = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('report_card', 'subject')

    def __str__(self):
        return f"{self.subject.name} Grade for {self.report_card}"

    def calculate_grade(self):
        """
        Calculate letter grade based on total score
        """
        if self.total_score >= 90:
            self.letter_grade = 'A'
        elif self.total_score >= 80:
            self.letter_grade = 'B'
        elif self.total_score >= 70:
            self.letter_grade = 'C'
        elif self.total_score >= 60:
            self.letter_grade = 'D'
        elif self.total_score >= 50:
            self.letter_grade = 'E'
        else:
            self.letter_grade = 'F'

        self.save()


class StudentQuizVersion(models.Model):
    """
    Model to store per-student quiz versions.
    This allows for randomized questions and answer choices for each student.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_versions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='student_versions')
    attempt_number = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    current_question_index = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['student', 'assignment', 'attempt_number']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.assignment.title} - Attempt #{self.attempt_number}"

    @property
    def duration(self):
        """Returns the duration of the attempt if completed"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None

    @property
    def time_remaining(self):
        """Returns the time remaining for the quiz in seconds"""
        if not self.started_at or not self.assignment.time_limit:
            return None

        time_limit_seconds = self.assignment.time_limit * 60
        elapsed_seconds = (timezone.now() - self.started_at).total_seconds()
        remaining_seconds = time_limit_seconds - elapsed_seconds

        return max(0, remaining_seconds)

    @property
    def is_timed_out(self):
        """Returns True if the quiz has timed out"""
        if not self.time_remaining:
            return False
        return self.time_remaining <= 0

    def start_quiz(self):
        """Marks the quiz as started"""
        if not self.started_at:
            self.started_at = timezone.now()
            self.save()

    def complete_quiz(self):
        """Marks the quiz as completed"""
        self.completed_at = timezone.now()
        self.is_completed = True
        self.save()

    def next_question(self):
        """Moves to the next question"""
        self.current_question_index += 1
        self.save()

    def previous_question(self):
        """Moves to the previous question"""
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.save()

    def get_current_question(self):
        """Returns the current question"""
        try:
            return self.questions.all()[self.current_question_index]
        except IndexError:
            return None

    @classmethod
    def create_for_student(cls, student, assignment):
        """Creates a new quiz version for a student"""
        # Count existing attempts
        attempt_count = cls.objects.filter(
            student=student,
            assignment=assignment
        ).count()

        # Check if attempt limit is reached
        if assignment.attempt_limit > 0 and attempt_count >= assignment.attempt_limit:
            return None, f"Maximum {assignment.attempt_limit} attempts allowed"

        # Create new quiz version
        quiz_version = cls.objects.create(
            student=student,
            assignment=assignment,
            attempt_number=attempt_count + 1
        )

        # Get questions for this quiz
        all_questions = list(assignment.questions.all())

        # Randomize questions if enabled
        if assignment.randomize_questions:
            import random
            random.shuffle(all_questions)

        # Limit number of questions if specified
        if assignment.questions_to_display and assignment.questions_to_display < len(all_questions):
            selected_questions = all_questions[:assignment.questions_to_display]
        else:
            selected_questions = all_questions

        # Create StudentQuizQuestion objects
        for i, question in enumerate(selected_questions):
            StudentQuizQuestion.objects.create(
                quiz_version=quiz_version,
                question=question,
                order=i
            )

        return quiz_version, f"Attempt #{attempt_count + 1}"


class StudentQuizQuestion(models.Model):
    """
    Model to store the questions for a student's quiz version.
    This allows for tracking the order of questions for each student.
    """
    quiz_version = models.ForeignKey(StudentQuizVersion, on_delete=models.CASCADE, related_name='questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='student_quiz_questions')
    order = models.PositiveIntegerField(default=0)
    answer_saved = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']
        unique_together = ['quiz_version', 'question']

    def __str__(self):
        return f"Question {self.order} for {self.quiz_version}"


class StudentQuizChoice(models.Model):
    """
    Model to store the shuffled choices for a student's quiz question.
    This allows for randomized answer choices for each student.
    """
    student_question = models.ForeignKey(StudentQuizQuestion, on_delete=models.CASCADE, related_name='choices')
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='student_choices')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ['student_question', 'choice']

    def __str__(self):
        return f"Choice {self.order} for {self.student_question}"


class StudentQuizAnswer(models.Model):
    """
    Model to store student answers for quiz questions.
    This allows for auto-saving answers as students progress through the quiz.
    """
    student_question = models.ForeignKey(StudentQuizQuestion, on_delete=models.CASCADE, related_name='answers')

    # For multiple choice questions
    selected_choice = models.ForeignKey(StudentQuizChoice, on_delete=models.SET_NULL, blank=True, null=True, related_name='selections')

    # For text-based questions
    text_answer = models.TextField(blank=True, null=True)

    # For file upload questions
    file_answer = models.FileField(upload_to='student_quiz_answers/', blank=True, null=True)

    is_correct = models.BooleanField(default=False)  # Auto-marked for MCQs
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Answer to {self.student_question}"

    def save(self, *args, **kwargs):
        # Auto-marking for MCQs
        if self.student_question.question.question_type in ['MCQ', 'TF'] and self.selected_choice:
            self.is_correct = self.selected_choice.choice.is_correct
            self.points_earned = self.student_question.question.points if self.is_correct else 0

            # Mark the question as answered
            self.student_question.answer_saved = True
            self.student_question.save()

        super().save(*args, **kwargs)


class QuizAttempt(models.Model):
    """
    Model to track quiz attempts for security measures and attempt limitations.
    This enables enforcement of attempt limits and cooldown periods based on student age.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.PositiveSmallIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ['student', 'assignment', 'attempt_number']
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.assignment.title} - Attempt #{self.attempt_number}"

    @property
    def duration(self):
        """Returns the duration of the attempt if completed"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None

    @classmethod
    def get_student_attempts(cls, student, assignment):
        """Returns the number of completed attempts a student has made for a quiz"""
        return cls.objects.filter(
            student=student,
            assignment=assignment,
            is_completed=True
        ).count()

    @classmethod
    def can_attempt_quiz(cls, student, assignment):
        """
        Determines if a student can attempt a quiz based on:
        1. Number of previous attempts
        2. Cooldown period based on student age/grade
        """
        # Get student's grade level to determine age-appropriate limits
        grade_level = student.grade

        # Extract numeric grade if grade_level is a Classroom object
        numeric_grade = None
        if grade_level:
            if hasattr(grade_level, 'grade'):
                # Try to extract numeric value from grade field
                try:
                    # Strip non-numeric characters and convert to int
                    import re
                    grade_str = grade_level.grade
                    numeric_match = re.search(r'\d+', grade_str)
                    if numeric_match:
                        numeric_grade = int(numeric_match.group())
                except (ValueError, AttributeError):
                    # If conversion fails, leave as None
                    pass

        # Default values (elementary school)
        max_attempts = 3
        cooldown_minutes = 5

        # Adjust based on grade level (age group)
        if numeric_grade and numeric_grade >= 9:  # High school (grades 9-12)
            max_attempts = 2
            cooldown_minutes = 30
        elif numeric_grade and numeric_grade >= 6:  # Middle school (grades 6-8)
            max_attempts = 2
            cooldown_minutes = 15

        # Check number of previous attempts
        attempts = cls.objects.filter(
            student=student,
            assignment=assignment,
            is_completed=True
        ).order_by('-completed_at')

        attempt_count = attempts.count()

        # Check if maximum attempts reached
        if attempt_count >= max_attempts:
            return False, f"Maximum {max_attempts} attempts allowed"

        # Check cooldown period if there are previous attempts
        if attempt_count > 0:
            last_attempt = attempts.first()
            if last_attempt and last_attempt.completed_at:
                cooldown_delta = timezone.timedelta(minutes=cooldown_minutes)
                cooldown_ends_at = last_attempt.completed_at + cooldown_delta

                if timezone.now() < cooldown_ends_at:
                    time_remaining = cooldown_ends_at - timezone.now()
                    minutes = int(time_remaining.total_seconds() // 60)
                    seconds = int(time_remaining.total_seconds() % 60)
                    return False, f"Please wait {minutes}m {seconds}s before your next attempt"

        return True, f"Attempt #{attempt_count + 1} of {max_attempts} allowed"

    @classmethod
    def create_attempt(cls, student, assignment):
        """Creates a new quiz attempt"""
        # Count ALL attempts (complete and incomplete) for uniqueness
        next_attempt_number = cls.objects.filter(
            student=student,
            assignment=assignment
        ).count() + 1

        return cls.objects.create(
            student=student,
            assignment=assignment,
            attempt_number=next_attempt_number
        )

    def complete_attempt(self):
        """Marks an attempt as completed"""
        self.completed_at = timezone.now()
        self.is_completed = True
        self.save()