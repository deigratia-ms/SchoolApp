from django import template

register = template.Library()

@register.filter
def percentage(value, total):
    """Calculate percentage of value to total"""
    if total == 0:
        return 0
    return (value / total) * 100

@register.filter
def add(value, arg):
    """Add the arg to the value."""
    return value + arg

@register.filter
def subtract(value, arg):
    """Subtract the arg from the value."""
    return value - arg

@register.filter
def multiply(value, arg):
    """Multiply the value by the arg."""
    return value * arg

@register.filter
def divide(value, arg):
    """Divide the value by the arg."""
    if arg == 0:
        return 0
    return value / arg

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using the key."""
    return dictionary.get(key)

@register.filter
def get_attribute(obj, attr):
    """Get an attribute of an object."""
    return getattr(obj, attr, '')

@register.filter
def format_currency(value):
    """Format a number as currency."""
    return f"GHS {value:.2f}"

@register.filter
def less_than(value, arg):
    """Check if a value is less than the argument."""
    try:
        return float(value) < float(arg)
    except (ValueError, TypeError):
        return False
