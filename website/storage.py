"""
Custom storage backends for the website app
"""

from django.conf import settings
import mimetypes


def get_cloudinary_storage():
    """Get Cloudinary storage instance for images and videos"""
    try:
        # Check if Cloudinary is configured
        cloudinary_configured = getattr(settings, 'CLOUDINARY_CONFIGURED', False)
        cloudinary_storage_setting = getattr(settings, 'CLOUDINARY_STORAGE', {})
        cloud_name = cloudinary_storage_setting.get('CLOUD_NAME', '')

        if cloudinary_configured and cloud_name:
            # Import and return Cloudinary storage
            from cloudinary_storage.storage import MediaCloudinaryStorage
            return MediaCloudinaryStorage()
        else:
            # Fallback to default storage
            from django.core.files.storage import default_storage
            return default_storage

    except ImportError as e:
        # If cloudinary_storage is not available, use default storage
        from django.core.files.storage import default_storage
        print(f"⚠️ Cloudinary import failed, using default storage: {e}")
        return default_storage


def get_file_storage():
    """Get appropriate storage based on file type"""
    # For now, return default storage for all files
    # This can be expanded to use different storage backends for different file types
    from django.core.files.storage import default_storage
    return default_storage


def is_image_file(filename):
    """Check if file is an image"""
    if not filename:
        return False

    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type and mime_type.startswith('image/')


def is_video_file(filename):
    """Check if file is a video"""
    if not filename:
        return False

    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type and mime_type.startswith('video/')
