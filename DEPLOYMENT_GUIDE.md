# School Management System - Deployment Guide

This guide covers deploying the School Management System to various platforms with comprehensive backup and restore functionality.

## 🚀 Quick Deploy to Fly.io (Recommended)

### Prerequisites
1. Install [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/)
2. Create a Fly.io account: `flyctl auth signup`

### Step 1: Deploy the Application

```bash
# Clone your repository
git clone https://github.com/deigratia-ms/SchoolApp.git
cd SchoolApp

# Login to Fly.io
flyctl auth login

# Launch the app (this will create fly.toml)
flyctl launch --name school-management-system

# Set environment variables
flyctl secrets set SECRET_KEY="your-super-secret-key-here"
flyctl secrets set DEBUG=False
flyctl secrets set ALLOWED_HOSTS="school-management-system.fly.dev,.fly.dev"

# Deploy
flyctl deploy
```

### Step 2: Set up PostgreSQL Database

```bash
# Create a PostgreSQL database
flyctl postgres create --name school-db

# Attach database to your app
flyctl postgres attach school-db

# This automatically sets DATABASE_URL secret
```

### Step 3: Run Migrations

```bash
# Connect to your app and run migrations
flyctl ssh console
python manage.py migrate
python manage.py createsuperuser
exit
```

### Step 4: Access Your Application

Your app will be available at: `https://school-management-system.fly.dev`

## 🔄 Backup and Restore System

### Creating Backups

#### Via Web Interface (Recommended)
1. Login as admin
2. Go to Dashboard → Quick Actions → System Backup
3. Click "Create New Backup"
4. Download the backup file when ready

#### Via Command Line
```bash
# SSH into your deployed app
flyctl ssh console

# Create backup
python manage.py backup_system --output-dir /tmp/backups --compress

# Download backup to local machine
exit
flyctl sftp get /tmp/backups/school_backup_YYYYMMDD_HHMMSS.zip ./
```

### Restoring Backups

#### Method 1: Using the Restore Script (Easiest)
```bash
# Extract the backup file
unzip school_backup_YYYYMMDD_HHMMSS.zip
cd school_backup_YYYYMMDD_HHMMSS

# Run the restore script
python restore_backup.py
# Follow the prompts
```

#### Method 2: Manual Restore
```bash
# Upload backup to server
flyctl sftp put school_backup_YYYYMMDD_HHMMSS.zip /tmp/

# SSH into server
flyctl ssh console

# Extract backup
cd /tmp
unzip school_backup_YYYYMMDD_HHMMSS.zip
cd school_backup_*

# Restore database
python /app/manage.py flush --noinput
python /app/manage.py migrate
python /app/manage.py loaddata database/full_database.json

# Restore media files
cp -r media/* /app/media/
```

### Database Migration Support

The backup system supports migrating between different database systems:

#### SQLite to PostgreSQL
```bash
# 1. Create backup from SQLite system
python manage.py backup_system

# 2. Set up new PostgreSQL system
# 3. Run migrations on new system
python manage.py migrate

# 4. Restore data
python manage.py restore_system backup_file.zip --migrate-first
```

#### PostgreSQL to MySQL
```bash
# Same process - the backup format is database-agnostic
# Django's loaddata command handles the database differences
```

## 🌐 Alternative Deployment Options

### Deploy to Railway

1. Connect your GitHub repository to Railway
2. Set environment variables:
   ```
   SECRET_KEY=your-secret-key
   DEBUG=False
   DATABASE_URL=postgresql://... (Railway provides this)
   ```
3. Deploy automatically on git push

### Deploy to Heroku

```bash
# Install Heroku CLI
# Login: heroku login

# Create app
heroku create school-management-system

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DEBUG=False

# Deploy
git push heroku main

# Run migrations
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### Deploy to DigitalOcean App Platform

1. Connect your GitHub repository
2. Set environment variables in the dashboard
3. Deploy automatically

## 🔧 Environment Variables

Required environment variables for production:

```bash
SECRET_KEY=your-super-secret-django-key
DEBUG=False
DATABASE_URL=postgresql://user:password@host:port/database
ALLOWED_HOSTS=yourdomain.com,.yourdomain.com

# Optional
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 📁 Backup Contents

Each backup includes:

### Database Backup
- Complete database dump (all tables and data)
- Individual app dumps for granular restoration
- Database-agnostic format (works with SQLite, PostgreSQL, MySQL)

### Media Files
- All uploaded files (student photos, documents)
- Preserves directory structure
- Maintains file permissions

### System Information
- Django version and settings
- Database configuration
- Installed apps list
- Backup timestamp and metadata

### Restore Script
- Automated restoration process
- Cross-platform compatibility (Windows, Linux, macOS)
- Database migration support
- Error handling and validation

## 🔒 Security Considerations

### Production Settings
- DEBUG=False in production
- Strong SECRET_KEY (50+ characters)
- HTTPS enforcement
- Secure cookie settings
- CSRF protection enabled

### Database Security
- Use environment variables for credentials
- Enable SSL for database connections
- Regular security updates
- Backup encryption (recommended)

### File Security
- Secure media file serving
- Input validation for uploads
- File type restrictions
- Size limits

## 🚨 Troubleshooting

### Common Issues

#### Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --noinput
```

#### Database Connection Errors
```bash
# Check DATABASE_URL format
echo $DATABASE_URL

# Test connection
python manage.py dbshell
```

#### Migration Issues
```bash
# Reset migrations (DANGER: Data loss)
python manage.py migrate --fake-initial

# Or restore from backup
python manage.py restore_system backup_file.zip
```

### Backup Issues

#### Large Backup Files
- Use compression (enabled by default)
- Consider excluding large media files temporarily
- Use incremental backups for large datasets

#### Restore Failures
- Check database permissions
- Verify Django version compatibility
- Use individual app dumps if full restore fails

## 📞 Support

For deployment issues:
1. Check the application logs
2. Verify environment variables
3. Test backup/restore locally first
4. Contact support with specific error messages

## 🔄 Maintenance

### Regular Tasks
- Weekly backups (automated recommended)
- Monthly security updates
- Quarterly dependency updates
- Annual security audits

### Monitoring
- Set up health checks
- Monitor disk space
- Track backup success/failure
- Monitor application performance

---

**Note**: Always test backup and restore procedures in a development environment before using in production.
