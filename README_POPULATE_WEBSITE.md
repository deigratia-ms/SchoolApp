# Website Content Population Script

This document explains how to use the `populate_website.py` script to populate your Deigratia Montessori School website with sample content.

## Overview

The `populate_website.py` script creates comprehensive website content including:

- **Site Settings**: Contact information, social media links, and basic configuration
- **Staff Members**: Executive, teaching, and support staff with detailed profiles
- **Events**: Upcoming school events with categories
- **Testimonials**: Parent, student, and alumni testimonials
- **Gallery**: School life images organized by category
- **Announcements**: News and updates with categories
- **Hero Slides**: Homepage carousel content

## Features

✅ **Error Prevention**: Comprehensive error handling prevents crashes
✅ **Duplicate Prevention**: Checks for existing content before creating new entries
✅ **Realistic Content**: Uses authentic Ghanaian names and school-appropriate content
✅ **No External Dependencies**: Works without internet connection or additional packages
✅ **Transaction Safety**: Uses database transactions for data integrity

## Usage

### Basic Usage

```bash
python populate_website.py
```

### Prerequisites

1. **Django Environment**: Ensure your Django environment is properly configured
2. **Database**: Make sure your database is set up and migrations are applied
3. **Virtual Environment**: Activate your virtual environment if using one

```bash
# Activate virtual environment (if using one)
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run the population script
python populate_website.py
```

## What Gets Created

### Site Settings
- Contact information (email, phone, address)
- Social media links
- Google Maps coordinates
- Office hours

### Staff Members (9 total)
- **Executive Staff**: Director, Head Teacher, Academic Coordinator
- **Teaching Staff**: Toddler, Primary, Elementary, and Art teachers
- **Support Staff**: School Nurse, ICT Coordinator

Each staff member includes:
- Full name and position
- Professional bio
- Contact information
- Qualifications and achievements
- Professional interests
- Featured status for homepage display

### Events (8 total)
- Parent-Teacher Conference
- Annual Science Fair
- Cultural Day Celebration
- Sports Day
- Montessori Workshop for Parents
- Field Trip to National Museum
- End of Term Celebration
- New Parent Orientation

### Event Categories (7 total)
- Academic Events
- Sports & Recreation
- Cultural Activities
- Parent Meetings
- School Celebrations
- Field Trips
- Workshops & Training

### Testimonials (8 total)
- Parent testimonials
- Former student testimonials
- Detailed feedback about school experience

### Gallery Items (16 total)
Organized by categories:
- **Classroom**: Learning environments and activities
- **Campus**: School buildings and facilities
- **Activities**: Student activities and programs
- **Events**: School events and celebrations

### Announcements (5 total)
- Registration information
- Academic achievements
- Program updates
- Facility improvements

### Hero Slides (3 total)
- Welcome message
- Montessori education focus
- Learning environment highlights

## Running Multiple Times

The script is designed to be run multiple times safely:

- **Existing Content**: Will not create duplicates of existing content
- **New Content**: Will only create content that doesn't already exist
- **Updates**: To update existing content, delete it first, then run the script

## Customization

### Adding Your Own Content

After running the script, you can:

1. **Replace Images**: Add your own images through the Django admin
2. **Edit Content**: Modify text content through the admin interface
3. **Add More Items**: Create additional staff, events, testimonials, etc.

### Modifying the Script

To customize the content before running:

1. Edit the data arrays in `populate_website.py`
2. Modify staff information, event details, testimonials, etc.
3. Add or remove categories as needed

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure Django environment is properly set up
2. **Database Errors**: Check database connection and migrations
3. **Permission Errors**: Ensure proper file permissions

### Error Messages

The script provides detailed error messages:
- ✅ Success messages show what was created
- ⚠️ Warning messages show what already exists
- ❌ Error messages show what failed and why

### Getting Help

If you encounter issues:

1. Check the error messages in the console output
2. Ensure all Django migrations are applied
3. Verify database connectivity
4. Check file permissions

## Example Output

```
============================================================
DEIGRATIA MONTESSORI SCHOOL - WEBSITE CONTENT POPULATION
============================================================

Creating site settings...
✓ Site settings created successfully

Creating event categories...
✓ Created event category: Academic Events
✓ Created event category: Sports & Recreation
...

Creating staff members...
✓ Created staff member: Dr. Grace Mensah
✓ Created staff member: Mr. Kwame Asante
...

============================================================
POPULATION SUMMARY
============================================================
✓ Staff members: 9
✓ Events: 8
✓ Testimonials: 8
✓ Gallery items: 16
✓ Announcements: 5
✓ Hero slides: 3
✓ Event categories: 7
✓ Announcement categories: 5

✓ All website content populated successfully!
============================================================
```

## Next Steps

After running the script:

1. **Access Django Admin**: Log in to add/edit content and images
2. **Review Content**: Check the website to see the populated content
3. **Customize**: Replace placeholder content with your actual content
4. **Add Images**: Upload real images for staff, events, and gallery

## Security Note

The script creates sample content with placeholder information. Remember to:
- Replace sample email addresses with real ones
- Update contact information with actual details
- Replace placeholder images with real photos
- Review all content for accuracy before going live
