from django import template
from datetime import datetime, timedelta
import re

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide the value by the argument."""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def format_duration(seconds):
    if not seconds:
        return "0 min"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if remaining_minutes == 0:
        return f"{hours} hr"
    else:
        return f"{hours} hr {remaining_minutes} min"

@register.filter
def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

@register.filter
def extract_youtube_id(url):
    """Extract YouTube video ID from a URL."""
    if not url:
        return ""
    
    # Handle youtu.be format
    if 'youtu.be' in url:
        return url.split('/')[-1].split('?')[0]
    
    # Handle youtube.com format
    if 'youtube.com' in url:
        if 'v=' in url:
            return url.split('v=')[1].split('&')[0]
    
    # Return the original URL if no ID found
    return url

@register.filter
def contains(value, arg):
    """Check if a string contains another string."""
    if not value:
        return False
    return arg in value

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary."""
    if not dictionary:
        return None
    return dictionary.get(key)

@register.filter
def getattr(obj, attr):
    """Get an attribute of an object by name."""
    if not obj:
        return None
    try:
        return getattr(obj, attr, '')
    except (AttributeError, TypeError):
        return ''

@register.filter
def endswith(value, arg):
    """Check if a string ends with another string."""
    if not value:
        return False
    return str(value).endswith(arg)

@register.filter
def percentage_of(value, total):
    """Calculate what percentage the value is of the total."""
    try:
        if not total:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def less_than(value, arg):
    """Check if a value is less than the argument."""
    try:
        return float(value) < float(arg)
    except (ValueError, TypeError):
        return False

@register.filter
def get_assessment_grade(grades_dict, assessment_id):
    """Get a grade for a specific assessment by ID from a grades dictionary.
    
    This filter is used in the bulk grade entry template to retrieve grades
    for dynamic assessment columns.
    
    Args:
        grades_dict: Dictionary containing assessment grades keyed by assessment ID
        assessment_id: The ID of the assessment to retrieve the grade for
    
    Returns:
        The grade value if found, or empty string if not found
    """
    if not grades_dict or not assessment_id:
        return ""
    
    # Convert assessment_id to string since dictionary keys from template 
    # are often strings even if the original IDs are integers
    assessment_id_str = str(assessment_id)
    
    # Try to get the grade from the dictionary
    return grades_dict.get(assessment_id_str, "")

@register.filter
def get_assessment_grades_by_type(grades_dict, assessment_type):
    """Get all grades for assessments of a specific type.
    
    Used for calculating component totals in gradebook and report cards.
    
    Args:
        grades_dict: Dictionary containing all student grades
        assessment_type: The type of assessment to filter by (e.g., 'classwork', 'exam')
    
    Returns:
        Dictionary containing only grades for the specified assessment type
    """
    if not grades_dict or not assessment_type:
        return {}
    
    filtered_grades = {}
    for key, value in grades_dict.items():
        # Check if this is an assessment grade entry with the specified type
        if isinstance(key, str) and key.startswith(assessment_type + "_"):
            filtered_grades[key] = value
            
    return filtered_grades
