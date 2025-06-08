# Production Deployment Checklist

## 🚀 Pre-Deployment Checklist

### Environment Configuration
- [ ] Set `DEBUG=False` in production environment
- [ ] Generate strong `SECRET_KEY` (50+ characters)
- [ ] Configure `DATABASE_URL` for PostgreSQL
- [ ] Set proper `ALLOWED_HOSTS` (remove wildcards)
- [ ] Configure email settings (`EMAIL_HOST`, `EMAIL_HOST_USER`, etc.)
- [ ] Set `ENVIRONMENT=production`

### Security Settings
- [ ] HTTPS enforcement enabled (`SECURE_SSL_REDIRECT=True`)
- [ ] HSTS headers configured
- [ ] Secure cookies enabled
- [ ] CSRF protection verified
- [ ] Remove any test/debug credentials

### Database Setup
- [ ] PostgreSQL database created on fly.io
- [ ] Database attached to application
- [ ] Connection pooling configured
- [ ] Backup strategy in place

### Static Files & Media
- [ ] WhiteNoise configured for static files
- [ ] Static files collected (`collectstatic`)
- [ ] Media files directory created
- [ ] File upload limits configured

## 🔧 Deployment Commands

### 1. Initial Setup
```bash
# Login to fly.io
flyctl auth login

# Launch application (if not done already)
flyctl launch --name school-management-system

# Create PostgreSQL database
flyctl postgres create --name school-db
flyctl postgres attach school-db
```

### 2. Set Environment Variables
```bash
# Required secrets
flyctl secrets set SECRET_KEY="your-super-secret-key-here"
flyctl secrets set DEBUG=False
flyctl secrets set ENVIRONMENT=production
flyctl secrets set ALLOWED_HOSTS="school-management-system.fly.dev,.fly.dev"

# Email configuration
flyctl secrets set EMAIL_HOST="smtp.gmail.com"
flyctl secrets set EMAIL_HOST_USER="your-email@gmail.com"
flyctl secrets set EMAIL_HOST_PASSWORD="your-app-password"
flyctl secrets set DEFAULT_FROM_EMAIL="noreply@yourschool.com"

# Optional settings
flyctl secrets set DEFAULT_SCHOOL_NAME="Your School Name"
flyctl secrets set TIME_ZONE="Africa/Accra"
```

### 3. Deploy Application
```bash
# Deploy the application
flyctl deploy

# SSH into the application for setup
flyctl ssh console

# Run production setup
python manage.py setup_production

# Create superuser
python manage.py createsuperuser

# Exit SSH
exit
```

### 4. Verify Deployment
```bash
# Check application status
flyctl status

# View logs
flyctl logs

# Check health endpoint
curl https://school-management-system.fly.dev/health/
```

## 📊 Post-Deployment Verification

### Application Health
- [ ] Health check endpoint responding (`/health/`)
- [ ] Homepage loads correctly
- [ ] Admin interface accessible
- [ ] User authentication working
- [ ] Database queries executing

### Functionality Tests
- [ ] User registration/login
- [ ] Student management
- [ ] Teacher management
- [ ] Course creation
- [ ] Assignment creation
- [ ] Attendance marking
- [ ] Fee management
- [ ] Communication system
- [ ] Backup system

### Performance & Security
- [ ] HTTPS working correctly
- [ ] Static files loading
- [ ] Media files uploading
- [ ] Database performance acceptable
- [ ] No debug information exposed
- [ ] Error pages working (404, 500)

## 🔄 Maintenance Tasks

### Regular Monitoring
- [ ] Set up log monitoring
- [ ] Monitor database performance
- [ ] Check disk space usage
- [ ] Monitor application errors

### Backup Strategy
- [ ] Schedule automated backups
- [ ] Test backup restoration
- [ ] Store backups securely off-site
- [ ] Document recovery procedures

### Updates & Security
- [ ] Plan for dependency updates
- [ ] Security patch schedule
- [ ] Database maintenance windows
- [ ] Performance optimization reviews

## 🚨 Troubleshooting

### Common Issues

#### Static Files Not Loading
```bash
flyctl ssh console
python manage.py collectstatic --noinput --clear
exit
```

#### Database Connection Issues
```bash
# Check database status
flyctl postgres list
flyctl postgres status school-db

# Verify connection
flyctl ssh console
python manage.py dbshell
```

#### Application Errors
```bash
# View recent logs
flyctl logs --app school-management-system

# Check specific errors
flyctl logs --app school-management-system | grep ERROR
```

#### Cache Issues
```bash
flyctl ssh console
python manage.py createcachetable
exit
```

## 📞 Support Contacts

- **Fly.io Support**: https://fly.io/docs/
- **Django Documentation**: https://docs.djangoproject.com/
- **Application Issues**: Check logs and error messages

## 🔐 Security Notes

- Never commit secrets to version control
- Use environment variables for all sensitive data
- Regularly update dependencies
- Monitor for security vulnerabilities
- Implement proper backup encryption
- Use strong passwords for all accounts
- Enable two-factor authentication where possible

---

**Last Updated**: [Date]
**Deployment Version**: [Version]
**Environment**: Production
