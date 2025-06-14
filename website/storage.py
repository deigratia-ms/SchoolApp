"""
Custom storage backends for the website app
"""

from django.conf import settings


class CloudinaryMediaStorage:
    """
    A storage class that ensures Cloudinary is used when configured
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = cls._get_storage()
        return cls._instance

    @classmethod
    def _get_storage(cls):
        """Get the appropriate storage backend"""
        try:
            # Check if Cloudinary is configured
            cloudinary_configured = getattr(settings, 'CLOUDINARY_CONFIGURED', False)
            cloudinary_storage_setting = getattr(settings, 'CLOUDINARY_STORAGE', {})
            cloud_name = cloudinary_storage_setting.get('CLOUD_NAME', '')

            if cloudinary_configured and cloud_name:
                # Import and return Cloudinary storage
                from cloudinary_storage.storage import MediaCloudinaryStorage
                print(f"✅ Using Cloudinary storage: {cloud_name}")
                return MediaCloudinaryStorage()
            else:
                # Fallback to default storage
                from django.core.files.storage import default_storage
                print("⚠️ Using default storage (Cloudinary not configured)")
                return default_storage

        except ImportError as e:
            # If cloudinary_storage is not available, use default storage
            from django.core.files.storage import default_storage
            print(f"⚠️ Cloudinary import failed, using default storage: {e}")
            return default_storage


# Create a function that returns the storage instance
def get_cloudinary_storage():
    """Get Cloudinary storage instance"""
    return CloudinaryMediaStorage()


# For backward compatibility
media_storage = get_cloudinary_storage()
