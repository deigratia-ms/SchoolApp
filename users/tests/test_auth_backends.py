from django.test import TestCase
from django.contrib.auth import authenticate
from users.models import CustomUser, Student
from users.auth_backends import FlexibleStudentBackend

class FlexibleStudentBackendTest(TestCase):
    """Test the flexible student authentication backend"""
    
    def setUp(self):
        """Set up test data"""
        # Create a student user
        self.user = CustomUser.objects.create_user(
            email='stu1234@school.internal',
            password='12345',
            first_name='Test',
            last_name='Student',
            role=CustomUser.Role.STUDENT,
            is_verified=True
        )
        
        # Create a student profile
        self.student = Student.objects.create(
            user=self.user,
            student_id='STU1234',
            pin='12345'
        )
        
        # Create another student with a different ID format
        self.user2 = CustomUser.objects.create_user(
            email='stu0056@school.internal',
            password='54321',
            first_name='Another',
            last_name='Student',
            role=CustomUser.Role.STUDENT,
            is_verified=True
        )
        
        self.student2 = Student.objects.create(
            user=self.user2,
            student_id='STU0056',
            pin='54321'
        )
        
    def test_exact_match(self):
        """Test authentication with exact student ID match"""
        user = authenticate(None, student_id='STU1234', pin='12345')
        self.assertEqual(user, self.user)
        
    def test_case_insensitive_match(self):
        """Test authentication with case-insensitive student ID match"""
        user = authenticate(None, student_id='stu1234', pin='12345')
        self.assertEqual(user, self.user)
        
    def test_numeric_only_match(self):
        """Test authentication with only the numeric part of the student ID"""
        user = authenticate(None, student_id='1234', pin='12345')
        self.assertEqual(user, self.user)
        
    def test_leading_zeros(self):
        """Test authentication with leading zeros in the numeric part"""
        # Student ID is STU0056, test with just 56
        user = authenticate(None, student_id='56', pin='54321')
        self.assertEqual(user, self.user2)
        
    def test_prefix_with_different_case(self):
        """Test authentication with prefix in different case"""
        user = authenticate(None, student_id='Stu1234', pin='12345')
        self.assertEqual(user, self.user)
        
    def test_wrong_pin(self):
        """Test authentication with correct ID but wrong PIN"""
        user = authenticate(None, student_id='STU1234', pin='wrong')
        self.assertIsNone(user)
        
    def test_nonexistent_id(self):
        """Test authentication with non-existent student ID"""
        user = authenticate(None, student_id='STU9999', pin='12345')
        self.assertIsNone(user)
