from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import Student
import re

UserModel = get_user_model()

class FlexibleStudentBackend(ModelBackend):
    """
    Custom authentication backend for students that allows for flexible student ID formats.
    
    This backend will try to match student IDs in various formats:
    - Exact match (e.g., "STU1234")
    - Case-insensitive match (e.g., "stu1234")
    - Numeric part only (e.g., "1234")
    - With or without leading zeros (e.g., "STU0123" can be entered as "STU123")
    
    As long as the PIN matches, the student will be authenticated.
    """
    
    def authenticate(self, request, student_id=None, pin=None, **kwargs):
        """
        Authenticate a student using a flexible student ID format and PIN.
        """
        if student_id is None or pin is None:
            return None
            
        # Try exact match first
        try:
            student = Student.objects.get(student_id=student_id, pin=pin)
            return student.user if student.user.is_verified else None
        except Student.DoesNotExist:
            pass
            
        # Try case-insensitive match
        try:
            students = Student.objects.filter(pin=pin)
            for student in students:
                if student.student_id.lower() == student_id.lower():
                    return student.user if student.user.is_verified else None
        except Exception:
            pass
            
        # Try to match only the numeric part
        numeric_part = re.sub(r'[^0-9]', '', student_id)
        if numeric_part:
            try:
                students = Student.objects.filter(pin=pin)
                for student in students:
                    # Extract numeric part from the stored student ID
                    stored_numeric_part = re.sub(r'[^0-9]', '', student.student_id)
                    
                    # Check if numeric parts match (ignoring leading zeros)
                    if stored_numeric_part.lstrip('0') == numeric_part.lstrip('0'):
                        return student.user if student.user.is_verified else None
            except Exception:
                pass
                
        # Try to match with prefix + numeric part
        # This handles cases where the prefix is entered correctly but the numeric part has different formatting
        if not student_id.isdigit():
            # Extract prefix (letters) and numeric part
            prefix_match = re.match(r'^([a-zA-Z]+)(\d+)$', student_id)
            if prefix_match:
                prefix, entered_numeric_part = prefix_match.groups()
                try:
                    students = Student.objects.filter(pin=pin)
                    for student in students:
                        # Check if the student ID starts with the same prefix
                        stored_prefix_match = re.match(r'^([a-zA-Z]+)(\d+)$', student.student_id)
                        if stored_prefix_match:
                            stored_prefix, stored_numeric_part = stored_prefix_match.groups()
                            if (stored_prefix.lower() == prefix.lower() and 
                                stored_numeric_part.lstrip('0') == entered_numeric_part.lstrip('0')):
                                return student.user if student.user.is_verified else None
                except Exception:
                    pass
        
        return None
