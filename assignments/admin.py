from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import (
    Assignment, Question, Choice, StudentSubmission, StudentAnswer, 
    Grade, ReportCard, GradingScale, GradeThreshold, AssessmentWeightConfiguration
)

class GradeThresholdInline(admin.TabularInline):
    model = GradeThreshold
    extra = 5  # Show 5 empty forms for new thresholds (A, B, C, D, F)
    ordering = ['order', '-min_percent']


@admin.register(AssessmentWeightConfiguration)
class AssessmentWeightConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_term', 'academic_year', 'is_default', 'created_by', 'updated_at')
    list_filter = ('is_default', 'academic_term', 'academic_year')
    search_fields = ('name', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_default', 'academic_term', 'academic_year', 'created_by')
        }),
        ('Weight Percentages', {
            'fields': ('classwork_weight', 'midterm_weight', 'endterm_weight', 'project_weight'),
            'description': 'Set percentage weights for each component (should sum to 100%)'
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(GradingScale)
class GradingScaleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_default', 'academic_term', 'class_level', 'created_by')
    list_filter = ('is_default', 'academic_term', 'class_level')
    search_fields = ('name', 'description')
    inlines = [GradeThresholdInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_default')
        }),
        ('Applicability', {
            'fields': ('academic_term', 'class_level'),
            'classes': ('collapse',),
        }),
        ('Audit Information', {
            'fields': ('created_by',),
            'classes': ('collapse',),
        }),
    )


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'assignment', 'question_type', 'points', 'show_feedback', 'order')
    list_filter = ('question_type', 'show_feedback', 'assignment')
    search_fields = ('question_text', 'assignment__title')
    inlines = [ChoiceInline]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'class_subject', 'assignment_type', 'due_date', 'max_score', 'is_active')
    list_filter = ('assignment_type', 'is_active', 'due_date', 'class_subject__subject')
    search_fields = ('title', 'description', 'class_subject__subject__name')
    date_hierarchy = 'due_date'


class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = ('question', 'selected_choice', 'text_answer', 'file_answer', 'is_correct', 'points_earned')
    can_delete = False


@admin.register(StudentSubmission)
class StudentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'submission_date', 'is_graded', 'score')
    list_filter = ('is_graded', 'submission_date', 'assignment__class_subject__subject')
    search_fields = ('student__user__username', 'assignment__title')
    date_hierarchy = 'submission_date'
    inlines = [StudentAnswerInline]
    readonly_fields = ('submission_date',)


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('submission', 'question', 'selected_choice', 'is_correct', 'points_earned')
    list_filter = ('is_correct', 'question__question_type')
    search_fields = ('submission__student__user__username', 'question__question_text')


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_subject', 'grade_type', 'score', 'max_score', 'letter_grade', 'term')
    list_filter = ('grade_type', 'term', 'class_subject__subject')
    search_fields = ('student__user__username', 'class_subject__subject__name', 'comments')


@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'academic_year', 'average_score', 'get_letter_grade', 'days_present', 'days_absent', 'generated_date')
    list_filter = ('term', 'academic_year', 'generated_date')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'student__user__username', 'teacher_comments')
    date_hierarchy = 'generated_date'
    readonly_fields = ('generated_date', 'average_score', 'average_assignment_score', 'average_quiz_score', 'average_exam_score', 'days_present', 'days_absent', 'attendance_percentage')
    actions = ['regenerate_report_cards', 'export_as_pdf', 'finalize_report_cards']
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'term', 'academic_year')
        }),
        ('Academic Performance', {
            'fields': ('average_score', 'average_assignment_score', 'average_quiz_score', 'average_exam_score', 'overall_grade')
        }),
        ('Attendance', {
            'fields': ('days_present', 'days_absent', 'days_late', 'total_school_days', 'attendance_percentage')
        }),
        ('Comments', {
            'fields': ('teacher_comments', 'principal_comments')
        }),
        ('Audit Information', {
            'fields': ('generated_date', 'generated_by')
        }),
    )
    
    def get_letter_grade(self, obj):
        """Calculate and return the letter grade based on average score."""
        if obj.average_score is None:
            return 'N/A'
            
        # Try to get the appropriate grading scale for this student
        grading_scale = GradingScale.objects.filter(
            Q(is_default=True) | 
            Q(academic_term=obj.term, class_level=obj.student.classroom.grade_level)
        ).order_by('-academic_term', '-class_level', '-is_default').first()
        
        if not grading_scale:
            return 'N/A'
            
        # Find the appropriate grade threshold
        threshold = GradeThreshold.objects.filter(
            grading_scale=grading_scale,
            min_percent__lte=obj.average_score
        ).order_by('-min_percent').first()
        
        return threshold.letter_grade if threshold else 'N/A'
    
    get_letter_grade.short_description = 'Grade'
    
    def finalize_report_cards(self, request, queryset):
        """Finalize the selected report cards for distribution."""
        from django.db import transaction
        
        with transaction.atomic():
            for report_card in queryset:
                # Recalculate attendance and grades
                report_card.calculate_attendance()
                report_card.calculate_grades_from_submissions()
                
                # Notify student and parents
                self.send_report_card_notification(request, report_card)
                
        self.message_user(request, f"{queryset.count()} report cards were successfully finalized and notifications sent.")
    finalize_report_cards.short_description = "Finalize and notify for selected report cards"
    
    def send_report_card_notification(self, request, report_card):
        """Send notification to student and parents about the report card."""
        from communications.models import Notification
        
        # Create notification for student
        Notification.objects.create(
            recipient=report_card.student.user,
            title=f"Report Card for {report_card.term} {report_card.academic_year}",
            content=f"Your report card for {report_card.term} {report_card.academic_year} is now available. Please review it with your parents/guardians.",
            notification_type='ACADEMIC',
            created_by=request.user
        )
        
        # Create notifications for parents
        for parent in report_card.student.parents.all():
            Notification.objects.create(
                recipient=parent.user,
                title=f"Report Card for {report_card.student.user.get_full_name()}",
                content=f"The report card for {report_card.student.user.get_full_name()} for {report_card.term} {report_card.academic_year} is now available.",
                notification_type='ACADEMIC',
                created_by=request.user
            )
    
    def regenerate_report_cards(self, request, queryset):
        """Regenerate the selected report cards with fresh data."""
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        
        # Get unique combinations of term and academic_year from selected report cards
        terms = queryset.values_list('term', 'academic_year').distinct()
        
        if len(terms) > 1:
            self.message_user(request, "Cannot regenerate report cards from different terms at once. Please select report cards from the same term.", level=messages.ERROR)
            return
            
        # Get IDs of students whose report cards are being regenerated
        student_ids = list(queryset.values_list('student_id', flat=True))
        
        # Delete the selected report cards
        queryset.delete()
        
        # Redirect to the generate report cards view with the appropriate parameters
        term, academic_year = terms[0]
        url = reverse('assignments:generate_report_cards')
        return HttpResponseRedirect(f"{url}?term={term}&academic_year={academic_year}&student_ids={','.join(map(str, student_ids))}")
    regenerate_report_cards.short_description = "Regenerate selected report cards"
    
    def export_as_pdf(self, request, queryset):
        """Export selected report cards as PDFs."""
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        
        if queryset.count() > 20:
            self.message_user(request, "For performance reasons, you can only export up to 20 report cards at once.", level=messages.WARNING)
            return
            
        # Get IDs of report cards to export
        report_card_ids = list(queryset.values_list('id', flat=True))
        
        # Redirect to a custom view that handles the PDF generation
        url = reverse('assignments:export_report_cards')
        return HttpResponseRedirect(f"{url}?ids={','.join(map(str, report_card_ids))}")
    export_as_pdf.short_description = "Export selected report cards as PDF"