# PythonAnywhere Deployment Guide for Deigratia School Management System

This guide will walk you through deploying the Deigratia School Management System on PythonAnywhere for testing purposes.

## Prerequisites

- A PythonAnywhere account (free tier is sufficient for testing)
- GitHub repository: https://github.com/deigratia-ms/SchoolApp.git
- Basic knowledge of command line operations

## Step 1: Create PythonAnywhere Account

1. Go to [PythonAnywhere](https://www.pythonanywhere.com/)
2. Sign up for a free account
3. Verify your email address

## Step 2: Open a Bash Console

1. Log into your PythonAnywhere dashboard
2. Click on "Tasks" → "Consoles"
3. Click "Bash" to open a new bash console

## Step 3: Clone the Repository

In the bash console, run the following commands:

```bash
# Navigate to your home directory
cd ~

# Clone the repository
git clone https://github.com/deigratia-ms/SchoolApp.git

# Navigate to the project directory
cd SchoolApp
```

## Step 4: Create Virtual Environment

```bash
# Create a virtual environment
python3.10 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

## Step 5: Install Dependencies

```bash
# Install production requirements
pip install -r requirements_production.txt

# If the above fails, install individual packages
pip install Django==5.1.6
pip install psycopg2-binary==2.9.9
pip install gunicorn==21.2.0
pip install whitenoise==6.6.0
pip install dj-database-url==2.1.0
pip install python-decouple==3.8
pip install django-crispy-forms==2.3
pip install crispy-bootstrap4==2024.10
pip install django-tinymce==4.1.0
pip install django-widget-tweaks==1.4.12
pip install django-mathfilters==1.0.0
pip install django-apscheduler==0.6.2
pip install pillow==11.1.0
pip install reportlab==4.3.1
pip install weasyprint==64.1
pip install openpyxl==3.1.5
```

## Step 6: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Create .env file
nano .env
```

Add the following content to the `.env` file:

```env
# Basic Django Settings
SECRET_KEY=your-secret-key-here-change-this-in-production
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com,localhost,127.0.0.1

# Database Configuration (Use PythonAnywhere's MySQL)
DATABASE_URL=mysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$schooldb

# Email Settings (Optional - for testing)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# School Settings
DEFAULT_SCHOOL_NAME=Deigratia Montessori School

# Scheduler Settings
RUN_SCHEDULER_IN_DEBUG=False
```

**Important Notes:**
- Replace `yourusername` with your actual PythonAnywhere username
- Replace `yourpassword` with your MySQL password (set in PythonAnywhere dashboard)
- Generate a new SECRET_KEY for production use

## Step 7: Set Up Database

### 7.1 Create MySQL Database

1. Go to your PythonAnywhere dashboard
2. Click on "Databases"
3. Create a new MySQL database named `schooldb`
4. Note down your database password

### 7.2 Update Database URL

Update the `DATABASE_URL` in your `.env` file with the correct credentials:

```env
DATABASE_URL=mysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$schooldb
```

### 7.3 Run Migrations

```bash
# Make sure you're in the project directory and virtual environment is activated
cd ~/SchoolApp
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create cache table
python manage.py createcachetable

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

## Step 8: Configure Web App

### 8.1 Create Web App

1. Go to your PythonAnywhere dashboard
2. Click on "Web"
3. Click "Add a new web app"
4. Choose "Manual configuration"
5. Select "Python 3.10"

### 8.2 Configure WSGI File

1. In the Web tab, click on the WSGI configuration file link
2. Replace the entire content with:

```python
import os
import sys

# Add your project directory to sys.path
path = '/home/yourusername/SchoolApp'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variable for Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'ricas_school_manager.settings'

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Replace `yourusername` with your actual PythonAnywhere username**

### 8.3 Configure Virtual Environment

1. In the Web tab, find the "Virtualenv" section
2. Enter the path to your virtual environment:
```
/home/yourusername/SchoolApp/venv
```

### 8.4 Configure Static Files

1. In the Web tab, find the "Static files" section
2. Add the following mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/yourusername/SchoolApp/staticfiles/` |
| `/media/` | `/home/yourusername/SchoolApp/media/` |

## Step 9: Configure Settings for Production

Create a production settings file or update the existing settings:

```bash
# Edit settings file
nano ricas_school_manager/settings.py
```

Make sure these settings are configured for production:

```python
# At the top of settings.py, add:
import os
from decouple import config

# Debug should be False in production
DEBUG = config('DEBUG', default=False, cast=bool)

# Allowed hosts
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_HSTS_SECONDS = 31536000
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
```

## Step 10: Test the Deployment

1. Go back to the Web tab in your PythonAnywhere dashboard
2. Click the green "Reload" button
3. Click on the link to your web app (e.g., `yourusername.pythonanywhere.com`)
4. Test the following:
   - Home page loads correctly
   - Admin login at `/my-admin/`
   - Static files (CSS, JS) are loading
   - Database connections work

## Step 11: Create Initial Data (Optional)

If you want to populate the system with sample data:

```bash
# In the bash console, navigate to your project
cd ~/SchoolApp
source venv/bin/activate

# Create some initial data using Django shell
python manage.py shell
```

Then in the Django shell:

```python
from users.models import CustomUser, SchoolSettings
from website.models import SiteSettings

# Create school settings
school_settings = SchoolSettings.objects.create(
    school_name="Deigratia Montessori School",
    address="123 Education Street, Learning City",
    phone="+1234567890",
    email="info@deigratia.edu",
    website="https://deigratia.edu"
)

# Create site settings
site_settings = SiteSettings.objects.create(
    school_name="Deigratia Montessori School",
    tagline="Nurturing Excellence Through Montessori Education",
    address="123 Education Street, Learning City",
    phone="+1234567890",
    email="info@deigratia.edu"
)

exit()
```

## Troubleshooting

### Common Issues and Solutions

1. **Import Errors**: Make sure all dependencies are installed in the virtual environment
2. **Database Connection Errors**: Verify your DATABASE_URL in the .env file
3. **Static Files Not Loading**: Check static files configuration and run `collectstatic`
4. **500 Internal Server Error**: Check the error logs in PythonAnywhere dashboard

### Checking Logs

1. Go to your PythonAnywhere dashboard
2. Click on "Web"
3. Check the "Log files" section for error details

### Updating the Application

To update your application with new changes:

```bash
cd ~/SchoolApp
git pull origin main
source venv/bin/activate
pip install -r requirements_production.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Then reload your web app from the PythonAnywhere dashboard.

## Security Considerations

1. **Change the SECRET_KEY**: Generate a new secret key for production
2. **Use Environment Variables**: Never commit sensitive data to version control
3. **Enable HTTPS**: PythonAnywhere provides HTTPS by default
4. **Regular Updates**: Keep Django and dependencies updated
5. **Database Backups**: Regularly backup your database

## Quick Commands Reference

### Useful Commands for Maintenance

```bash
# Activate virtual environment
cd ~/SchoolApp && source venv/bin/activate

# Update from GitHub
git pull origin main

# Install new dependencies
pip install -r requirements_production.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create cache table (if needed)
python manage.py createcachetable

# Check for issues
python manage.py check

# Access Django shell
python manage.py shell

# Create superuser
python manage.py createsuperuser
```

### Database Management

```bash
# Backup database (MySQL dump)
mysqldump -u yourusername -p yourusername$schooldb > backup.sql

# Import database
mysql -u yourusername -p yourusername$schooldb < backup.sql

# Reset migrations (if needed)
python manage.py migrate --fake-initial
```

## Environment Variables Reference

Create a `.env` file with these variables:

```env
# Required Settings
SECRET_KEY=your-very-long-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com,localhost,127.0.0.1

# Database (MySQL for PythonAnywhere)
DATABASE_URL=mysql://yourusername:password@yourusername.mysql.pythonanywhere-services.com/yourusername$schooldb

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# School Configuration
DEFAULT_SCHOOL_NAME=Deigratia Montessori School

# Performance Settings
RUN_SCHEDULER_IN_DEBUG=False
```

## Testing Checklist

After deployment, test these features:

- [ ] Home page loads correctly
- [ ] Admin login at `/my-admin/` works
- [ ] Student/Teacher/Parent login pages work
- [ ] Dashboard loads for different user types
- [ ] Static files (CSS, JS, images) load properly
- [ ] File uploads work (profile pictures, documents)
- [ ] Email functionality works (if configured)
- [ ] Database operations work (create, read, update, delete)
- [ ] Responsive design works on mobile devices

## Performance Optimization

### For Better Performance on PythonAnywhere:

1. **Enable Caching**:
```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
        'TIMEOUT': 300,
    }
}
```

2. **Optimize Static Files**:
```python
# Use WhiteNoise for static files
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ... other middleware
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

3. **Database Optimization**:
```python
# Connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 60
```

## Monitoring and Maintenance

### Regular Maintenance Tasks:

1. **Weekly**:
   - Check error logs
   - Monitor disk space usage
   - Test critical functionality

2. **Monthly**:
   - Update dependencies
   - Backup database
   - Review security settings

3. **Quarterly**:
   - Update Django version
   - Security audit
   - Performance review

### Log Monitoring:

Check these log files regularly:
- Error log: `/var/log/yourusername.pythonanywhere.com.error.log`
- Access log: `/var/log/yourusername.pythonanywhere.com.access.log`
- Server log: `/var/log/yourusername.pythonanywhere.com.server.log`

## Support

- PythonAnywhere Help: https://help.pythonanywhere.com/
- Django Documentation: https://docs.djangoproject.com/
- Project Repository: https://github.com/deigratia-ms/SchoolApp
- PythonAnywhere Forums: https://www.pythonanywhere.com/forums/

## Appendix: Sample Configuration Files

### Sample .env file:
```env
SECRET_KEY=django-insecure-your-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com,localhost,127.0.0.1
DATABASE_URL=mysql://yourusername:password@yourusername.mysql.pythonanywhere-services.com/yourusername$schooldb
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_SCHOOL_NAME=Deigratia Montessori School
RUN_SCHEDULER_IN_DEBUG=False
```

### Sample WSGI Configuration:
```python
import os
import sys

# Add your project directory to the Python path
path = '/home/yourusername/SchoolApp'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'ricas_school_manager.settings'

# Import Django's WSGI handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

---

**Note**: This guide is for testing purposes. For production deployment, consider additional security measures, monitoring, and backup strategies.

**Last Updated**: June 2025
**Django Version**: 5.1.6
**Python Version**: 3.10+
