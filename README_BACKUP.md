# 🔄 Deigratia Montessori School - Backup & Restore

## Overview

The School Management System includes a comprehensive backup and restore functionality that allows you to:

- **Create full system backups** including database, media files, and configurations
- **Restore backups** through web interface or command line
- **Migrate between databases** (SQLite ↔ PostgreSQL ↔ MySQL)
- **Download backups** for local storage
- **Upload and restore** backups through the web interface

## 🚀 Quick Start

### Creating Backups

#### Via Web Interface (Recommended)
1. Login as admin
2. Go to **Dashboard** → **Quick Administrative Links** → **System Backup**
3. Click **"Create New Backup"**
4. Wait for the progress to complete
5. Download the backup file

#### Via Command Line
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Create backup
python manage.py backup_system --output-dir backups --compress

# Create backup without media files
python manage.py backup_system --output-dir backups --no-include-media
```

### Restoring Backups

#### Via Web Interface (Easiest)
1. Go to **System Backup** page
2. Use the **"Restore from Backup"** form on the right
3. Select your backup ZIP file
4. Choose restore options:
   - ✅ **Clear existing data first** (recommended for clean restore)
   - ✅ **Restore media files** (includes uploaded files)
5. Click **"Upload & Restore"**
6. Wait for the progress to complete

#### Via Command Line
```bash
# Restore from backup file
python manage.py restore_system path/to/backup.zip

# Restore with options
python manage.py restore_system backup.zip --flush-database --restore-media

# Restore without flushing existing data
python manage.py restore_system backup.zip --no-flush-database
```

#### Using the Restore Script (Cross-platform)
```bash
# Extract backup file
unzip school_backup_20231201_143022.zip
cd school_backup_20231201_143022

# Run restore script
python restore_backup.py
# Follow the interactive prompts
```

## 📁 What's Included in Backups

### Database Backup
- **Complete database dump** (all tables and data)
- **Individual app dumps** for granular restoration
- **Database-agnostic format** (works with SQLite, PostgreSQL, MySQL)

### Media Files
- All uploaded files (student photos, documents, assignments)
- Preserves directory structure and file permissions
- Includes all media directories

### System Information
- Django version and settings
- Database configuration
- Installed apps list
- Backup timestamp and metadata

### Restore Script
- Cross-platform Python script
- Interactive restoration process
- Automatic database migration support
- Error handling and validation

## 🔄 Database Migration

The backup system supports seamless migration between different database systems:

### SQLite to PostgreSQL
```bash
# 1. Create backup from SQLite system
python manage.py backup_system --output-dir backups

# 2. Set up PostgreSQL database
# Update DATABASE_URL in .env file

# 3. Restore to PostgreSQL
python manage.py restore_system backups/school_backup_*.zip --migrate-first
```

### PostgreSQL to MySQL
```bash
# Same process - the backup format is database-agnostic
python manage.py restore_system backup.zip --migrate-first
```

## 🛡️ Security & Best Practices

### Backup Security
- Store backups in secure locations
- Consider encrypting sensitive backups
- Regular backup rotation (keep last 10 backups)
- Test restore procedures regularly

### Production Recommendations
- **Schedule automated backups** (daily/weekly)
- **Store backups off-site** (cloud storage)
- **Test restore procedures** in staging environment
- **Monitor backup success/failure**

### File Permissions
- Backup files contain sensitive data
- Restrict access to backup directories
- Use secure transfer methods (SFTP, encrypted storage)

## 🔧 Advanced Usage

### Custom Backup Locations
```bash
# Backup to specific directory
python manage.py backup_system --output-dir /path/to/backups

# Backup without compression
python manage.py backup_system --no-compress
```

### Selective Restore
```bash
# Restore only database (no media files)
python manage.py restore_system backup.zip --no-restore-media

# Restore specific apps only
python manage.py loaddata backup/users.json
python manage.py loaddata backup/courses.json
```

### Backup Automation
```bash
# Add to crontab for daily backups at 2 AM
0 2 * * * cd /path/to/project && python manage.py backup_system --output-dir /backups/daily
```

## 🚨 Troubleshooting

### Common Issues

#### Unicode Encoding Errors
- **Solution**: Backups now use UTF-8 encoding by default
- **Manual fix**: Ensure all text data uses proper encoding

#### Large File Uploads
- **Issue**: Web upload fails for large backups
- **Solution**: Use command line restore or increase upload limits

#### Database Connection Errors
- **Check**: DATABASE_URL environment variable
- **Verify**: Database server is running and accessible

#### Permission Errors
- **Ensure**: Proper file permissions for backup directories
- **Check**: Django has write access to backup location

### Recovery Scenarios

#### Corrupted Database
```bash
# 1. Stop the application
# 2. Restore from latest backup
python manage.py restore_system latest_backup.zip --flush-database

# 3. Restart application
```

#### Lost Media Files
```bash
# Restore only media files from backup
python manage.py restore_system backup.zip --restore-media --no-flush-database
```

## 📞 Support

For backup-related issues:
1. Check the backup logs in Django admin
2. Verify file permissions and disk space
3. Test with a small backup first
4. Contact system administrator with specific error messages

---

**⚠️ Important**: Always test backup and restore procedures in a development environment before using in production.
