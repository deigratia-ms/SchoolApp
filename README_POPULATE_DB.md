# Database Population Script

This script populates the database with comprehensive sample data for testing all functionalities of the Ricas School Management System.

## How to Run the Script

The script is designed to be run directly with Python, without needing to use the Django shell.

### Basic Run (School Settings, Subjects, Classrooms, and Teachers)

```bash
# Navigate to the project directory
cd C:\Users\RICAS\Desktop\SMS_V0\ricas_school_manager

# Run the script
python populate_db.py
```

This will create:
- School settings
- GES curriculum subjects
- Classrooms for KG, Primary, and JHS
- Teachers with specialties

### Full Run (All Data)

```bash
# Navigate to the project directory
cd C:\Users\RICAS\Desktop\SMS_V0\ricas_school_manager

# Run the script with the --full flag
python populate_db.py --full
```

This will create everything in the basic run, plus:
- Students
- Parents with children
- Class subjects
- Assignments and quizzes
- Attendance records

## What the Script Creates

### School Settings
- School name, contact information, and configuration

### Users
- Admin user
- Teachers with specialties
- Students in different grade levels
- Parents linked to their children

### GES Curriculum
- Subjects for all levels (KG, Primary, JHS, SHS)
- Classes and grade levels
- Class-subject assignments

### Academic Content
- Assignments and quizzes
- Questions and answer choices

### Attendance
- Daily attendance records
- Student attendance status

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
- Student ID: STU1001 through STU1020
- PIN: 12345

### Parents
- Email: [firstname].[lastname]@parent.deigratia.edu.gh (e.g., daniel.adu@parent.deigratia.edu.gh)
- Password: parent123

## Notes

- The script uses random data generation for many fields, so each run will produce slightly different results.
- The script is designed to be idempotent - it checks for existing data before creating new entries.
- If you encounter any errors, make sure all required models and dependencies are properly set up.
- The script may take a few minutes to run as it creates a comprehensive dataset.

## Troubleshooting

If you encounter any issues:

1. Check that all required models are imported
2. Verify that your database migrations are up to date
3. Make sure your virtual environment has all required packages installed
4. Check for any model constraints that might be violated

If you get errors about missing fields or models, you may need to adjust the script to match your current database schema.
