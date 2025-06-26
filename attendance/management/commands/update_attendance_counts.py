from django.core.management.base import BaseCommand
from attendance.models import AttendanceRecord


class Command(BaseCommand):
    help = 'Update attendance counts for all attendance records'

    def handle(self, *args, **options):
        self.stdout.write('Updating attendance counts...')
        
        records = AttendanceRecord.objects.all()
        updated_count = 0
        
        for record in records:
            old_present = record.present_count
            old_absent = record.absent_count
            old_late = record.late_count
            old_excused = record.excused_count
            
            # Update counts
            record.update_counts()
            
            # Check if anything changed
            if (record.present_count != old_present or 
                record.absent_count != old_absent or 
                record.late_count != old_late or 
                record.excused_count != old_excused):
                updated_count += 1
                self.stdout.write(
                    f'Updated {record.classroom.name} - {record.date}: '
                    f'P:{old_present}→{record.present_count}, '
                    f'A:{old_absent}→{record.absent_count}, '
                    f'L:{old_late}→{record.late_count}, '
                    f'E:{old_excused}→{record.excused_count}'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} out of {records.count()} attendance records.'
            )
        )
