from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from django.core.management import call_command

from users.models import Student, SchoolSettings
from courses.models import ClassRoom, ClassSubject
from assignments.models import ReportCard

import logging
import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Promotes students to the next grade level at the end of an academic year'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulates the promotion without making changes',
        )
        parser.add_argument(
            '--academic-year',
            type=str,
            help='Specify the target academic year for promotion (e.g., "2023-2024"). If not specified, uses next year based on current settings.',
        )
        parser.add_argument(
            '--max-grade-level',
            type=int,
            default=12,
            help='Maximum grade level. Students beyond this will be graduated.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        max_grade_level = options['max_grade_level']
        
        # Get current and target academic years
        current_academic_year = self._get_current_academic_year()
        if not current_academic_year:
            raise CommandError("Current academic year not set in SchoolSettings.")
        
        target_academic_year = options['academic_year']
        if not target_academic_year:
            # Try to determine the next academic year
            try:
                # Assuming academic year format like "2023-2024"
                start_year = int(current_academic_year.split('-')[0])
                target_academic_year = f"{start_year + 1}-{start_year + 2}"
            except (ValueError, IndexError):
                raise CommandError(
                    f"Could not determine target academic year from '{current_academic_year}'. "
                    "Please specify --academic-year."
                )
        
        self.stdout.write(f"Current academic year: {current_academic_year}")
        self.stdout.write(f"Target academic year: {target_academic_year}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made."))
        
        # Process students
        self._process_students(current_academic_year, target_academic_year, max_grade_level, dry_run)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN COMPLETED - No changes were made."))
        else:
            # Update the academic year in settings if this is a real run
            self._update_academic_year(target_academic_year)
            
            # Synchronize class subject enrollments
            self.stdout.write("Synchronizing class subject enrollments...")
            call_command('cleanup_student_subjects')
            
            self.stdout.write(self.style.SUCCESS("Student promotion completed successfully."))
    
    def _get_current_academic_year(self):
        """Get the current academic year from settings."""
        try:
            settings = SchoolSettings.objects.first()
            return settings.academic_year if settings else None
        except Exception as e:
            logger.error(f"Error retrieving academic year: {str(e)}")
            return None
    
    def _update_academic_year(self, new_academic_year):
        """Update the academic year in settings."""
        try:
            settings = SchoolSettings.objects.first()
            if settings:
                settings.academic_year = new_academic_year
                settings.save()
                self.stdout.write(f"Academic year updated to {new_academic_year}")
            else:
                self.stdout.write(self.style.WARNING("No SchoolSettings found to update academic year."))
        except Exception as e:
            logger.error(f"Error updating academic year: {str(e)}")
    
    def _process_students(self, current_academic_year, target_academic_year, max_grade_level, dry_run):
        """Process all students for promotion, repetition, or graduation."""
        # Get counts for reporting
        active_students = Student.objects.filter(status=Student.Status.ACTIVE)
        total_students = active_students.count()
        
        to_promote = active_students.filter(is_repeating=False)
        to_repeat = active_students.filter(is_repeating=True)
        
        self.stdout.write(f"Total active students: {total_students}")
        self.stdout.write(f"Students eligible for promotion: {to_promote.count()}")
        self.stdout.write(f"Students marked for repetition: {to_repeat.count()}")
        
        # Process students marked for repetition
        self._process_repeating_students(to_repeat, dry_run)
        
        # Process students eligible for promotion
        promoted, graduated, no_grade = self._process_promotion(to_promote, max_grade_level, target_academic_year, dry_run)
        
        # Report results
        self.stdout.write(self.style.SUCCESS(f"Promotion summary:"))
        self.stdout.write(f"  - Students promoted: {promoted}")
        self.stdout.write(f"  - Students graduated: {graduated}")
        self.stdout.write(f"  - Students with no grade assignment: {no_grade}")
        self.stdout.write(f"  - Students repeating: {to_repeat.count()}")
    
    def _process_repeating_students(self, students, dry_run):
        """Process students who are marked for repetition."""
        if dry_run:
            self.stdout.write(f"Would process {students.count()} repeating students")
            return
        
        # Update years_in_current_grade and reset is_repeating flag
        with transaction.atomic():
            for student in students:
                student.years_in_current_grade += 1
                student.is_repeating = False  # Reset for next cycle
                student.save()
                self.stdout.write(f"Student {student} will repeat grade, years in grade: {student.years_in_current_grade}")
    
    def _process_promotion(self, students, max_grade_level, target_academic_year, dry_run):
        """Process students eligible for promotion."""
        promoted_count = 0
        graduated_count = 0
        no_grade_count = 0
        
        # Get current academic year from settings if not defined
        current_academic_year = SchoolSettings.objects.first().academic_year if SchoolSettings.objects.exists() else None
        if not current_academic_year:
            self.stdout.write(self.style.ERROR("Current academic year not found in SchoolSettings. Student report cards cannot be archived."))
        
        for student in students:
            if not student.grade:
                no_grade_count += 1
                self.stdout.write(self.style.WARNING(
                    f"Student {student} has no grade assignment. Skipping."
                ))
                continue
            
            # Get current grade level
            try:
                current_grade_level = student.grade.grade_level
            except AttributeError:
                self.stdout.write(self.style.WARNING(
                    f"Student {student} has invalid grade assignment. Skipping."
                ))
                no_grade_count += 1
                continue
            
            # Check if student should graduate
            if current_grade_level >= max_grade_level:
                if not dry_run:
                    student.status = Student.Status.GRADUATED
                    student.save()
                graduated_count += 1
                self.stdout.write(f"Student {student} graduated from grade level {current_grade_level}")
                continue
            
            # Find or create next grade classroom
            next_grade_level = current_grade_level + 1
            current_section = student.section or student.grade.section
            
            # Create a projected class name for the next grade level
            next_grade_name = f"Grade {next_grade_level}"
            
            # Try to find an existing classroom for next grade with same section
            next_classroom = self._find_or_create_classroom(
                next_grade_level, current_section, target_academic_year, dry_run
            )
            
            if next_classroom and not dry_run:
                # Update student's grade and manage classroom relationships
                old_grade = student.grade
                
                # First remove student from old classroom's students collection
                if old_grade:
                    old_grade.students.remove(student)
                    self.stdout.write(f"Removed {student} from {old_grade}'s students collection")
                
                # Archive student's report cards for the current grade level
                archived_count = self._archive_student_report_cards(student, current_academic_year)
                if archived_count > 0:
                    self.stdout.write(f"Archived {archived_count} report cards for {student}")
                
                # Update student grade
                student.grade = next_classroom
                student.years_in_current_grade = 1
                student.last_promoted_date = datetime.date.today()
                student.save()
                
                # Add student to new classroom's students collection
                next_classroom.students.add(student)
                self.stdout.write(f"Added {student} to {next_classroom}'s students collection")
                
                promoted_count += 1
                self.stdout.write(f"Promoted {student} from {old_grade} to {next_classroom}")
            elif dry_run:
                promoted_count += 1
                self.stdout.write(f"Would promote {student} from grade level {current_grade_level} to {next_grade_level}")
        
        return promoted_count, graduated_count, no_grade_count
    
    def _archive_student_report_cards(self, student, academic_year):
        """Archive a student's report cards from the current academic year.
        
        This marks the report cards as belonging to a previous grade level,
        ensuring they're preserved when the student is promoted.
        
        Args:
            student (Student): The student whose report cards to archive
            academic_year (str): The academic year to archive (e.g., "2023-2024")
            
        Returns:
            int: Number of report cards archived
        """
        try:
            # Find all report cards for this student in the current academic year
            report_cards = ReportCard.objects.filter(
                student=student,
                academic_year=academic_year,
                # Only archive cards that haven't been archived already
                promotion_status__isnull=True
            )
            
            count = report_cards.count()
            if count == 0:
                return 0
                
            # Update all matching report cards
            for report_card in report_cards:
                # Mark as archived from previous grade level
                report_card.promotion_status = "archived"
                # Store the grade level at the time of archiving
                report_card.grade_level = student.grade.grade_level
                report_card.save()
                
            return count
        except Exception as e:
            logger.error(f"Error archiving report cards for student {student}: {str(e)}")
            return 0
    
    def _find_or_create_classroom(self, grade_level, section, academic_year, dry_run):
        """Find an existing classroom or create a new one for the next grade level."""
        # Try to find an existing classroom
        grade_name = f"Grade {grade_level}"
        existing = ClassRoom.objects.filter(
            grade_level=grade_level,
            section=section
        ).first()
        
        if existing:
            return existing
        
        if dry_run:
            self.stdout.write(f"Would create new classroom: {grade_name} {section} for {academic_year}")
            return None
        
        # Create a new classroom
        try:
            new_classroom = ClassRoom.objects.create(
                name=f"{grade_name} {section}",
                section=section,
                grade_level=grade_level
            )
            self.stdout.write(self.style.SUCCESS(f"Created new classroom: {new_classroom}"))
            return new_classroom
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating classroom: {str(e)}"))
            return None
