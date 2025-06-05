from django import template

register = template.Library()

@register.filter
def getattr(obj, attr):
    """Gets an attribute of an object dynamically from a string name"""
    if obj is None:
        return None
    try:
        return getattr(obj, attr)
    except (AttributeError, TypeError):
        return None

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using the key."""
    if dictionary is None:
        return None
    return dictionary.get(key)
