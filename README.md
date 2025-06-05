# Deigratia Montessori School Management System

A comprehensive Django-based school management system for Deigratia Montessori School, integrating a public website and internal management for educational excellence in Ghana.

<!-- SEO Meta Tags -->
<meta name="description" content="Deigratia Montessori School Management System - Modern, secure, and feature-rich platform for school administration, parent communication, and student learning in Ghana.">
<meta name="keywords" content="Deigratia Montessori School, Montessori, School Management, Education, Ghana, Django, Parent Portal, Student Portal, School Website, School ERP, School Software">
<meta name="author" content="Deigratia Montessori School">
<meta property="og:title" content="Deigratia Montessori School Management System">
<meta property="og:description" content="Modern, secure, and feature-rich platform for school administration, parent communication, and student learning in Ghana.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://deigratiams.edu.gh/">
<meta property="og:site_name" content="Deigratia Montessori School">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Deigratia Montessori School Management System">
<meta name="twitter:description" content="Modern, secure, and feature-rich platform for school administration, parent communication, and student learning in Ghana.">

## Features

### Public Website (DGMS)
- **Home Page**: Welcoming interface with school information
- **About Us**: School history, mission, and vision
- **Academic Programs**: Detailed program information for different age groups
- **Admissions**: Application process and requirements
- **Contact**: Contact information and inquiry forms

### School Management System (SMS)
- **User Management**: Students, teachers, and administrative staff
- **Course Management**: Subject creation and management
- **Assignment System**: Create, distribute, and grade assignments
- **Attendance Tracking**: Daily attendance monitoring
- **Fee Management**: Fee structure and payment tracking
- **Payroll System**: Staff salary management
- **Communications**: Internal messaging system
- **Dashboard**: Comprehensive overview and analytics
- **Appointment Booking**: Schedule meetings and consultations

## Technology Stack

- **Backend**: Django 5.1.6
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Frontend**: Bootstrap 4, HTML5, CSS3, JavaScript
- **Rich Text Editor**: TinyMCE
- **Task Scheduling**: APScheduler with django-apscheduler
- **Forms**: Django Crispy Forms with Bootstrap 4
- **Environment Management**: python-decouple

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/deigratia-ms/SchoolApp.git
   cd SchoolApp
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   - Copy `.env.example` to `.env` (if available) or create a new `.env` file
   - Update the environment variables in `.env`:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   EMAIL_HOST_PASSWORD=your-email-password
   ```

5. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Public Website: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin/
   - SMS Dashboard: http://127.0.0.1:8000/dashboard/

## Configuration

### Environment Variables

The application uses environment variables for configuration. Key variables include:

- `SECRET_KEY`: Django secret key for security
- `DEBUG`: Enable/disable debug mode
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `EMAIL_HOST_USER`: SMTP email username
- `EMAIL_HOST_PASSWORD`: SMTP email password
- `DEFAULT_SCHOOL_NAME`: School name displayed throughout the system

### Email Configuration

Configure SMTP settings in your `.env` file for email functionality:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## Project Structure

```
DeigratiaMontessori/
├── ricas_school_manager/     # Main Django project
├── website/                  # Public website app
├── users/                    # User management
├── dashboard/                # Main dashboard
├── courses/                  # Course management
├── assignments/              # Assignment system
├── attendance/               # Attendance tracking
├── fees/                     # Fee management
├── payroll/                  # Payroll system
├── communications/           # Internal messaging
├── appointments/             # Appointment booking
├── templates/                # Shared templates
├── static/                   # Static files (CSS, JS, images)
├── media/                    # User uploaded files
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── .gitignore                # Git ignore rules
├── robots.txt                # SEO robots file
├── sitemap.xml               # SEO sitemap file
├── seo.html                  # SEO meta tags snippet
└── manage.py                 # Django management script
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please contact the development team or create an issue in the GitHub repository.

## Recent Updates

- ✅ Resolved Django model registration warnings
- ✅ Fixed template tag naming conflicts
- ✅ Added APScheduler for task scheduling
- ✅ Implemented environment variable configuration
- ✅ Updated requirements and dependencies
- ✅ Improved error handling and logging

## SEO Deployment Checklist
- [x] robots.txt present
- [x] sitemap.xml present
- [x] SEO meta tags in base templates and README
- [x] School name and branding updated to Deigratia Montessori School
- [x] Canonical URL set to https://deigratiams.edu.gh/

## Improving SEO in Django Templates
- Use the `{% block title %}` in every template for unique, descriptive page titles.
- Add meta description and keywords in the `<head>` of your base template.
- Use Open Graph and Twitter Card tags for social sharing.
- Ensure all images have descriptive alt text.
- Use semantic HTML (header, nav, main, footer, article, section, etc.).
- Submit your sitemap.xml to Google Search Console.

## Submitting to Google Search Console
1. Go to https://search.google.com/search-console/
2. Add your site (https://deigratiams.edu.gh/)
3. Verify ownership (using DNS or HTML file)
4. Submit your sitemap.xml

## SEO Best Practices for Django
- Always use HTTPS
- Set canonical URLs
- Avoid duplicate content
- Use robots.txt and sitemap.xml
- Optimize page speed (minify CSS/JS, compress images)
- Use descriptive URLs and slugs
- Add structured data (JSON-LD) if possible
- Monitor with Google Search Console and Analytics

## Favicon and Branding
- Place your favicon.ico in /static/website/img/favicon.ico
- Reference it in your base template and seo.html

## Social Media SEO
- Add Open Graph and Twitter Card meta tags
- Use high-quality images for sharing
- Keep your school’s social profiles up to date

## Local SEO for Ghana
- Add your school to Google Maps
- Use Ghana-specific keywords
- List your school in local directories
- Encourage parents to leave reviews

## Monitoring SEO Performance
- Use Google Analytics and Google Search Console
- Track keyword rankings
- Monitor site speed and mobile usability

## Accessibility and SEO
- Ensure your site is accessible to all users
- Use proper heading structure (h1, h2, h3, ...)
- Provide alt text for all images
- Test with screen readers

## Keeping SEO Up to Date
- Regularly update your content
- Monitor for broken links
- Refresh meta tags as needed
- Stay informed about SEO best practices

## Django SEO Packages
- [django-meta](https://github.com/nephila/django-meta)
- [django-seo2](https://github.com/jazzband/django-seo2)
- [django-sitemap](https://docs.djangoproject.com/en/5.1/ref/contrib/sitemaps/)
