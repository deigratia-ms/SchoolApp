from django import template
from django.template.defaultfilters import filesizeformat

register = template.Library()


@register.filter
def safe_file_size(file_field):
    """
    Safely get file size, handling Cloudinary storage and missing files.
    Returns formatted file size or None if not available.
    """
    if not file_field:
        return None
    
    try:
        # Try to get the size from the file field
        if hasattr(file_field, 'size') and file_field.size:
            return file_field.size
        # For Cloudinary files, size might not be available
        return None
    except (FileNotFoundError, OSError, AttributeError):
        return None


@register.filter
def safe_file_size_formatted(file_field):
    """
    Safely get formatted file size, handling Cloudinary storage and missing files.
    Returns formatted file size string or 'Size not available' if not available.
    """
    size = safe_file_size(file_field)
    if size:
        return filesizeformat(size)
    return "Size not available"


@register.filter
def file_exists(file_field):
    """
    Check if a file exists, handling Cloudinary storage.
    """
    if not file_field:
        return False

    try:
        # For Cloudinary, we can check if the file has a URL
        # If it has a URL, it likely exists
        return bool(file_field.url)
    except:
        return False


@register.filter
def safe_file_url(file_field):
    """
    Safely get file URL, handling Cloudinary storage and missing files.
    Returns the file URL or None if not available.
    """
    if not file_field:
        return None

    try:
        # Try to get the URL from the file field
        return file_field.url
    except (ValueError, AttributeError, FileNotFoundError):
        return None
