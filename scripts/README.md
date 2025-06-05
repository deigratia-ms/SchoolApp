# Database Population Script

This script populates the database with comprehensive sample data for testing all functionalities of the Ricas School Management System.

## What the Script Creates

The script creates sample data for:

1. **School Settings**
   - Basic school information

2. **Users**
   - Admin user
   - Teachers
   - Students
   - Parents

3. **GES Curriculum**
   - Subjects for all levels (KG, Primary, JHS)
   - Classes and grade levels
   - Class-subject assignments
   - Class schedules

4. **Academic Content**
   - Assignments and quizzes
   - Questions and answer choices
   - Student submissions
   - Grades

5. **Attendance**
   - Daily attendance records
   - Student attendance status

6. **Communications**
   - Messages between users
   - Notifications
   - School events

7. **Financial Records**
   - Academic terms
   - Student fees
   - Payments and receipts

## How to Run the Script

Make sure you have already:
1. Applied all migrations
2. Activated your virtual environment

### Method 1: Using Django Shell

```bash
# Navigate to the project directory
cd ricas_school_manager

# Activate your virtual environment (if not already activated)
# On Windows:
.\venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Run the script using Django shell
python manage.py shell < scripts/populate_sample_data.py
```

### Method 2: Using Python

```bash
# Navigate to the project directory
cd ricas_school_manager

# Activate your virtual environment (if not already activated)
# On Windows:
.\venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Run the script directly
python scripts/populate_sample_data.py
```

## Login Credentials

After running the script, you can log in with the following credentials:

### Admin
- Email: admin@deigratia.edu.gh
- Password: admin123

### Teachers
- Email: [firstname].[lastname]@deigratia.edu.gh (e.g., john.smith@deigratia.edu.gh)
- Password: teacher123

### Students (JHS only)
- Email: [firstname].[lastname]@student.deigratia.edu.gh (e.g., nana.yeboah@student.deigratia.edu.gh)
- Password: student123
- Student ID: STU1001 through STU1050
- PIN: 12345

### Parents
- Email: [firstname].[lastname]@parent.deigratia.edu.gh (e.g., daniel.adu@parent.deigratia.edu.gh)
- Password: parent123

## Notes

- The script uses random data generation for many fields, so each run will produce slightly different results.
- The script is designed to be idempotent - it checks for existing data before creating new entries.
- If you encounter any errors, make sure all required models and dependencies are properly set up.
- The script may take a few minutes to run as it creates a comprehensive dataset.

## Customization

You can modify the script to add more data or change existing data patterns:

- Adjust the number of users by modifying the data arrays
- Change the academic terms or fee structure
- Add more subjects or classrooms
- Modify the random data generation parameters

## Troubleshooting

If you encounter any issues:

1. Check that all required models are imported
2. Verify that your database migrations are up to date
3. Make sure your virtual environment has all required packages installed
4. Check for any model constraints that might be violated
