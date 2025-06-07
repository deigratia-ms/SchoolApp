from django.core.cache import cache
from courses.models import ClassRoom, ClassSubject
from .models import DashboardPreference
from communications.utils import get_unread_notifications_count, get_unread_messages_count

def notifications_context(request):
    """
    Context processor to add notification and message counts to all templates.
    This enables notification counters in the navigation menus.
    Uses caching for performance.
    """
    context = {
        'unread_notifications_count': 0,
        'unread_messages_count': 0
    }

    # Only process for authenticated users
    if request.user.is_authenticated:
        try:
            # Use cache key based on user ID
            cache_key = f'notifications_context_{request.user.id}'
            cached_context = cache.get(cache_key)

            if cached_context is not None:
                return cached_context

            # Get unread notification count
            context['unread_notifications_count'] = get_unread_notifications_count(request.user)

            # Get unread message count
            context['unread_messages_count'] = get_unread_messages_count(request.user)

            # Cache for 1 minute (notifications change frequently)
            cache.set(cache_key, context, 60)

        except Exception as e:
            # If there's any error, just return the default context
            pass

    return context
def sidebar_context(request):
    """
    Context processor to add teacher class information to all templates.
    This ensures the teacher sidebar always has access to class information
    regardless of which view is being rendered.
    Uses caching for performance.
    """
    context = {
        'class_teacher_of': [],
        'assigned_classes': [],
        'unique_classrooms': []
    }

    # Only process for authenticated users who are teachers
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'TEACHER':
        try:
            # Use cache key based on user ID
            cache_key = f'sidebar_context_{request.user.id}'
            cached_context = cache.get(cache_key)

            if cached_context is not None:
                return cached_context

            teacher = request.user.teacher_profile

            # Get classes where the user is the class teacher
            class_teacher_of = list(ClassRoom.objects.filter(class_teacher=teacher).select_related())
            context['class_teacher_of'] = class_teacher_of

            # Get classes where the user teaches subjects
            assigned_classes = list(ClassSubject.objects.filter(teacher=teacher).select_related('classroom'))
            context['assigned_classes'] = assigned_classes

            # Create a list of unique classrooms
            unique_classrooms = []
            classroom_set = set()

            # First add classrooms where teacher is class teacher
            for classroom in class_teacher_of:
                classroom_set.add(classroom.id)
                unique_classrooms.append(classroom)

            # Then add classrooms from subjects taught by teacher (if not already added)
            for class_subject in assigned_classes:
                if class_subject.classroom.id not in classroom_set:
                    classroom_set.add(class_subject.classroom.id)
                    unique_classrooms.append(class_subject.classroom)

            context['unique_classrooms'] = unique_classrooms

            # Cache for 5 minutes (class assignments don't change frequently)
            cache.set(cache_key, context, 300)

        except Exception as e:
            # If there's any error, just return the empty context
            pass

    return context

def user_preferences(request):
    """
    Context processor to add user dashboard preferences to all templates.
    This ensures preferences like sidebar_collapsed are available globally.
    Uses caching for performance.
    """
    context = {
        'preferences': None
    }

    # Only process for authenticated users
    if request.user.is_authenticated:
        try:
            # Use cache key based on user ID
            cache_key = f'user_preferences_{request.user.id}'
            cached_preferences = cache.get(cache_key)

            if cached_preferences is not None:
                context['preferences'] = cached_preferences
                return context

            # Get or create user preferences
            preferences, created = DashboardPreference.objects.get_or_create(user=request.user)
            context['preferences'] = preferences

            # Cache for 10 minutes (preferences don't change frequently)
            cache.set(cache_key, preferences, 600)

        except Exception as e:
            # If there's any error, just return the empty context
            pass

    return context