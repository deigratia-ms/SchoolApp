"""
Django settings for ricas_school_manager project.
This file integrates settings from both the DGMS website and School Management System.
"""

import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
SECRET_KEY = config('SECRET_KEY', default='django-insecure-integration-key-replace-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)

# Parse ALLOWED_HOSTS from comma-separated string
allowed_hosts_str = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,testserver,*')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',')]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party apps
    'crispy_forms',
    'crispy_bootstrap4',
    'mathfilters',
    'widget_tweaks',
    'tinymce',
    'django_apscheduler',
    'cloudinary_storage',
    'cloudinary',

    # Website (DGMS) app
    'website',

    # SMS apps
    'users',
    'courses',
    'assignments',
    'attendance',
    'communications',
    'dashboard',
    'fees',
    'payroll',
    'appointments',  # Appointment booking system
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Compress responses
]

ROOT_URLCONF = 'ricas_school_manager.urls'

# URL configuration
APPEND_SLASH = True  # Django default, but explicit for clarity

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,  # Enable app directories for Django admin templates
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'website.context_processors.site_settings',
                'dashboard.context_processors.sidebar_context',
                'dashboard.context_processors.user_preferences',
                'dashboard.context_processors.notifications_context',
                'appointments.context_processors.appointment_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'ricas_school_manager.wsgi.application'


# Database - SINGLE DATABASE FOR BOTH SYSTEMS
# Use PostgreSQL for both local development and production
DATABASE_URL = config('DATABASE_URL', default='postgresql://neondb_owner:npg_UgOjXAbZ49Gn@ep-little-recipe-a23uiq8a-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require')

# Always use PostgreSQL (both local and production)
DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL)
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# WhiteNoise configuration for static files with optimization
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise optimization settings
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MAX_AGE = 31536000  # 1 year cache for static files

# Cloudinary Configuration for Image Optimization
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False

# Cloudinary settings - Free tier provides 25GB storage + 25GB bandwidth
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# Use Cloudinary for media files in production, local storage in development
if not DEBUG and CLOUDINARY_AVAILABLE and CLOUDINARY_STORAGE['CLOUD_NAME']:
    # Production: Use Cloudinary for optimized image delivery
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_STORAGE['CLOUD_NAME']}/"
else:
    # Development or fallback: Use local storage
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms settings
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Default system name
DEFAULT_SCHOOL_NAME = config('DEFAULT_SCHOOL_NAME', default='Ricas School Manager')

# Use custom user model from SMS
AUTH_USER_MODEL = 'users.CustomUser'

# Authentication settings
LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'website:home'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'users.auth_backends.FlexibleStudentBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Password reset settings
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour
PASSWORD_RESET_DONE_REDIRECT_URL = 'users:password_reset_done'
PASSWORD_RESET_CONFIRM_TEMPLATE_NAME = 'users/password_reset_confirm.html'

# TinyMCE Configuration
TINYMCE_DEFAULT_CONFIG = {
    'height': 360,
    'width': '100%',
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 20,
    'selector': 'textarea',
    'theme': 'silver',
    'plugins': '''
        textcolor save link image media preview codesample contextmenu
        table code lists fullscreen insertdatetime nonbreaking
        contextmenu directionality searchreplace wordcount visualblocks
        visualchars code fullscreen autolink lists charmap print hr
        anchor pagebreak
        ''',
    'toolbar1': '''
        fullscreen preview bold italic underline | fontselect,
        fontsizeselect | forecolor backcolor | alignleft alignright |
        aligncenter alignjustify | indent outdent | bullist numlist table |
        | link image media | codesample |
        ''',
    'toolbar2': '''
        visualblocks visualchars |
        charmap hr pagebreak nonbreaking anchor | code |
        ''',
    'contextmenu': 'formats | link image',
    'menubar': True,
    'statusbar': True,
}

# Academic years and terms (from SMS)
from datetime import datetime
CURRENT_YEAR = datetime.now().year
ACADEMIC_YEARS = [str(year) for year in range(CURRENT_YEAR - 1, CURRENT_YEAR + 5)]
ACADEMIC_TERMS = ["First Term", "Second Term", "Third Term"]

# Email settings
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='skillnetservices@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='skillnetservices@gmail.com')

# --- PERFORMANCE & CONCURRENCY OPTIMIZATIONS ---

# Use database-backed cache for low RAM, or file-based if disk is available
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
        'TIMEOUT': 300,  # 5 minutes
        'OPTIONS': {
            'MAX_ENTRIES': 1000,  # Limit cache size
        }
    }
}
# To create cache table: python manage.py createcachetable

# Additional performance settings for development
if DEBUG:
    # Reduce database connection timeout in development
    DATABASES['default']['CONN_MAX_AGE'] = 30

    # Disable some middleware in development for speed
    # Keep essential middleware only
    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'whitenoise.middleware.WhiteNoiseMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]

# Use cached sessions for less DB load
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Template caching (only for production)
if not DEBUG:
    # Disable APP_DIRS when using custom loaders
    TEMPLATES[0]['APP_DIRS'] = False
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

# WhiteNoise is already included in MIDDLEWARE above

# Gunicorn settings (for deployment):
# Use --workers=2 --threads=2 for low RAM, scale up as needed

# Database connection pooling (if using Postgres)
# Use pgbouncer or set CONN_MAX_AGE for persistent connections
DATABASES['default']['CONN_MAX_AGE'] = 60

# Pagination defaults (limit per page to reduce memory usage)
PAGINATION_PER_PAGE = 20

# Disable debug toolbar and other dev-only middleware in production

# --- END PERFORMANCE ---

# Try to import local settings if they exist
try:
    from .local_settings import *
except ImportError:
    pass

# Scheduler settings
RUN_SCHEDULER_IN_DEBUG = config('RUN_SCHEDULER_IN_DEBUG', default=True, cast=bool)

# Production Environment Detection
IS_PRODUCTION = not DEBUG and (
    'fly.dev' in config('ALLOWED_HOSTS', default='') or
    config('ENVIRONMENT', default='development').lower() == 'production'
)

# Security settings - only enforce HTTPS in production environments
# This ensures development works with HTTP while production is secure
if not DEBUG:
    # Only apply security settings in production
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

    # HTTPS/SSL security settings from environment variables
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)

    # Additional HSTS settings if HSTS is enabled
    if SECURE_HSTS_SECONDS > 0:
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True

    # Allowed hosts for production - use environment variable
    env_allowed_hosts = config('ALLOWED_HOSTS', default='localhost,127.0.0.1')
    ALLOWED_HOSTS = [host.strip() for host in env_allowed_hosts.split(',')]

    # Add default production hosts if not already included
    default_hosts = ['school-management-system.fly.dev', '.fly.dev']
    for host in default_hosts:
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

# Health check endpoint
HEALTH_CHECK_URL = '/health/'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'users': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'dashboard': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
logs_dir = BASE_DIR / 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Production-specific optimizations
if IS_PRODUCTION:
    # Enhanced security settings for production
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Additional security headers
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

    # Optimize database connections for production (optional)
    # Only apply if not already set
    if DATABASES['default'].get('CONN_MAX_AGE', 0) < 300:
        DATABASES['default']['CONN_MAX_AGE'] = 300  # 5 minutes

    # Optional: Advanced connection pooling (uncomment if needed)
    # DATABASES['default']['OPTIONS'] = {
    #     'MAX_CONNS': 20,
    #     'MIN_CONNS': 5,
    # }

    # Production logging - log to stdout for fly.io
    LOGGING['handlers']['console']['level'] = 'WARNING'
    LOGGING['handlers']['file']['level'] = 'ERROR'

    # Disable debug toolbar and other dev tools
    INSTALLED_APPS = [app for app in INSTALLED_APPS if 'debug_toolbar' not in app]

    # Cache optimization for production
    CACHES['default']['TIMEOUT'] = 600  # 10 minutes
    CACHES['default']['OPTIONS']['MAX_ENTRIES'] = 5000
