"""
Resource management configuration for the messaging system.
Adjust these settings based on your server capacity.
"""

# === POLLING CONFIGURATION ===
# How often to check for new messages (in milliseconds)
INITIAL_POLL_INTERVAL = 5000  # 5 seconds

# Adaptive polling intervals based on activity
INACTIVE_POLL_INTERVAL = 15000  # 15 seconds after 30s of no activity
IDLE_POLL_INTERVAL = 30000     # 30 seconds after 5 minutes of no activity

# When to consider user inactive/idle
INACTIVITY_THRESHOLD = 6       # 6 polls (30 seconds) before slowing down
IDLE_THRESHOLD = 20           # 20 polls (5 minutes) before going to idle mode
USER_IDLE_TIMEOUT = 300000    # 5 minutes in milliseconds

# === RATE LIMITING ===
# Maximum API requests per user per minute
MAX_POLL_REQUESTS_PER_MINUTE = 20

# Maximum messages a user can send per minute
MAX_MESSAGES_PER_MINUTE = 10

# === FILE ATTACHMENT LIMITS ===
# File size limits (in bytes)
MAX_FILE_SIZE_STUDENT = 2 * 1024 * 1024    # 2MB for students
MAX_FILE_SIZE_TEACHER = 5 * 1024 * 1024    # 5MB for teachers/admins

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS = [
    '.pdf', '.doc', '.docx', '.txt',           # Documents
    '.jpg', '.jpeg', '.png', '.gif', '.webp'   # Images
]

# === CONCURRENT USER LIMITS ===
# Maximum active chat sessions (0 = unlimited)
MAX_CONCURRENT_CHATS = 0  # Set to 50-100 for limited resources

# === CACHE SETTINGS ===
# How long to cache message data (in seconds)
MESSAGE_CACHE_TIMEOUT = 300    # 5 minutes

# How long to cache user contact lists
CONTACT_CACHE_TIMEOUT = 600    # 10 minutes

# === CLEANUP SETTINGS ===
# Auto-delete old messages after X days (0 = never delete)
AUTO_DELETE_MESSAGES_AFTER_DAYS = 0  # Set to 90 for 3 months

# Auto-delete old attachments after X days
AUTO_DELETE_ATTACHMENTS_AFTER_DAYS = 0  # Set to 30 for 1 month

# === PERFORMANCE MONITORING ===
# Log slow queries (in milliseconds)
SLOW_QUERY_THRESHOLD = 1000

# Log high memory usage warnings
MEMORY_WARNING_THRESHOLD_MB = 100

# === FEATURE TOGGLES ===
# Enable/disable features to save resources
ENABLE_TYPING_INDICATORS = False      # Requires more frequent polling
ENABLE_ONLINE_STATUS = True           # Minimal impact
ENABLE_MESSAGE_REACTIONS = False      # Additional database queries
ENABLE_FILE_PREVIEW = True            # Uses client-side processing

# === DEPLOYMENT SPECIFIC ===
# Adjust based on your hosting environment

# For Fly.io or similar (limited resources)
FLY_IO_OPTIMIZED = {
    'MAX_CONCURRENT_CHATS': 50,
    'INITIAL_POLL_INTERVAL': 10000,  # Slower polling
    'MAX_POLL_REQUESTS_PER_MINUTE': 10,
    'MAX_FILE_SIZE_STUDENT': 1 * 1024 * 1024,  # 1MB
    'ENABLE_TYPING_INDICATORS': False,
    'ENABLE_MESSAGE_REACTIONS': False,
}

# For dedicated servers (more resources)
DEDICATED_SERVER_OPTIMIZED = {
    'MAX_CONCURRENT_CHATS': 0,  # Unlimited
    'INITIAL_POLL_INTERVAL': 3000,  # Faster polling
    'MAX_POLL_REQUESTS_PER_MINUTE': 30,
    'MAX_FILE_SIZE_STUDENT': 5 * 1024 * 1024,  # 5MB
    'ENABLE_TYPING_INDICATORS': True,
    'ENABLE_MESSAGE_REACTIONS': True,
}

def get_config_for_environment():
    """
    Return configuration based on environment.
    You can modify this to detect your environment automatically.
    """
    import os
    
    # Check if running on Fly.io or similar limited resource environment
    if os.environ.get('FLY_APP_NAME') or os.environ.get('RAILWAY_PROJECT_ID'):
        return FLY_IO_OPTIMIZED
    
    # Default to conservative settings
    return {
        'MAX_CONCURRENT_CHATS': 100,
        'INITIAL_POLL_INTERVAL': INITIAL_POLL_INTERVAL,
        'MAX_POLL_REQUESTS_PER_MINUTE': MAX_POLL_REQUESTS_PER_MINUTE,
        'MAX_FILE_SIZE_STUDENT': MAX_FILE_SIZE_STUDENT,
        'ENABLE_TYPING_INDICATORS': ENABLE_TYPING_INDICATORS,
        'ENABLE_MESSAGE_REACTIONS': ENABLE_MESSAGE_REACTIONS,
    }
