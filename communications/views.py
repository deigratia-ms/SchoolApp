from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
from .models import Message, Announcement, Event, Notification
from courses.models import ClassRoom, ClassSubject
from users.models import SchoolSettings, Student, CustomUser, Teacher, Parent
from .utils import create_message_notification

# Helper function for admin check
def is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'

# Helper function for teacher check
def is_teacher(user):
    return user.is_authenticated and user.role == 'TEACHER'

# Message views
@login_required
def message_list(request):
    """
    Display a list of messages (inbox and sent) for the current user.
    """
    # Get received and sent messages
    received_messages = Message.objects.filter(recipient=request.user).order_by('-created_at')
    sent_messages = Message.objects.filter(sender=request.user).order_by('-created_at')

    # Count unread messages
    unread_count = received_messages.filter(is_read=False).count()

    context = {
        'received_messages': received_messages,
        'sent_messages': sent_messages,
        'unread_count': unread_count
    }

    return render(request, 'communications/message_list.html', context)

@login_required
def inbox(request):
    """
    Redirect to message_list view.
    """
    return redirect('communications:message_list')

@login_required
def sent_messages(request):
    """
    Redirect to message_list view.
    """
    return redirect('communications:message_list')

@login_required
def chat(request):
    """
    WhatsApp-style chat interface for messaging.
    Lists contacts on the left and messages on the right.
    """
    from django.utils import timezone
    from django.db.models import Q
    from users.models import CustomUser, Teacher, Student, Parent

    # Check if messaging is enabled in system settings
    try:
        school_settings = SchoolSettings.objects.first()
        if not school_settings.enable_messaging:
            messages.error(request, "Messaging is currently disabled by the administrator.")
            if request.user.is_student:
                return redirect('dashboard:student_dashboard')
            elif request.user.is_parent:
                return redirect('dashboard:parent_dashboard')
            elif request.user.is_teacher:
                return redirect('dashboard:teacher_dashboard')
            else:
                return redirect('dashboard:admin_dashboard')
    except:
        # If settings don't exist, allow messaging as default
        pass

    # Check if the user is a student with disabled chat
    if request.user.is_student:
        try:
            student = Student.objects.get(user=request.user)
            if not student.chat_enabled:
                messages.error(request, "Your messaging access has been restricted by a parent or administrator.")
                return redirect('dashboard:student_dashboard')
        except Student.DoesNotExist:
            pass

    # Get potential contacts - Include all users the user could message with
    # This approach ensures new users can be found in search and chat can be started
    all_potential_contacts = get_potential_chat_contacts(request.user)

    # Get all contacts the user has messaged with in the past
    sent_to = Message.objects.filter(sender=request.user).values_list('recipient_id', flat=True).distinct()
    received_from = Message.objects.filter(recipient=request.user).values_list('sender_id', flat=True).distinct()

    # Combine and get unique contact IDs from actual message exchanges
    message_contact_ids = set(sent_to) | set(received_from)

    # Get the latest message with each contact and unread counts
    contacts = []

    # First add contacts with message history
    for contact_id in message_contact_ids:
        try:
            contact = CustomUser.objects.get(id=contact_id)

            # Get the latest message between the user and this contact
            latest_message = Message.objects.filter(
                (Q(sender=request.user) & Q(recipient=contact)) |
                (Q(sender=contact) & Q(recipient=request.user))
            ).order_by('-created_at').first()

            # Count unread messages from this contact
            unread_count = Message.objects.filter(
                sender=contact,
                recipient=request.user,
                is_read=False
            ).count()

            # Format for display - using properties that match the template expectations
            contact_data = {
                'id': contact.id,
                'get_full_name': contact.get_full_name(),
                'email': contact.email,
                'get_role_display': contact.get_role_display(),
                'last_message': latest_message,
                'unread_count': unread_count,
                # Generate a consistent color for the avatar based on email
                'get_avatar_color': f"hsl({abs(hash(contact.email)) % 360}, 70%, 50%)"
            }

            contacts.append(contact_data)
        except CustomUser.DoesNotExist:
            continue

    # Add potential contacts that don't have message history yet
    # This ensures "New Chat" can find contacts we haven't messaged yet
    potential_contact_ids = set([user.id for user in all_potential_contacts])
    # Remove contacts already in the message history
    potential_contact_ids = potential_contact_ids - message_contact_ids

    # Directly include potential contacts for the "New Chat" feature
    potential_contacts = []
    for contact_id in potential_contact_ids:
        try:
            contact = CustomUser.objects.get(id=contact_id)
            potential_contacts.append({
                'id': contact.id,
                'get_full_name': contact.get_full_name(),
                'email': contact.email,
                'get_role_display': contact.get_role_display(),
                'get_avatar_color': f"hsl({abs(hash(contact.email)) % 360}, 70%, 50%)"
            })
        except CustomUser.DoesNotExist:
            continue

    # Sort contacts by most recent message (contacts with no messages will be at the bottom)
    contacts.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else timezone.make_aware(timezone.datetime.min), reverse=True)

    # Combine contacts with message history and potential contacts
    combined_contacts = contacts + potential_contacts

    # Remove duplicates based on user ID
    seen_ids = set()
    unique_combined_contacts = []
    for contact in combined_contacts:
        if contact['id'] not in seen_ids:
            unique_combined_contacts.append(contact)
            seen_ids.add(contact['id'])

    # Render the chat template with all contacts
    context = {
        'all_contacts': unique_combined_contacts,
        'potential_contacts': potential_contacts  # Still pass for "New Chat" modal
    }

    return render(request, 'communications/chat.html', context)

# Helper function to get all potential chat contacts for a user
def get_potential_chat_contacts(user):
    """
    Returns a list of users that the current user can message based on their role.
    Used for the new chat feature and contact search.
    """
    from users.models import CustomUser, Student, Teacher, Parent
    from courses.models import ClassSubject, ClassRoom
    from django.db.models import Q

    all_users = CustomUser.objects.none()

    # Get school settings to check student-to-student messaging permission
    try:
        school_settings = SchoolSettings.objects.first()
        student_to_student_allowed = school_settings.enable_student_to_student_chat
    except:
        student_to_student_allowed = True  # Default to allowed if settings don't exist

    if user.role == 'STUDENT':
        try:
            student = Student.objects.get(user=user)
            # Get teachers of the student's subjects
            teachers = Teacher.objects.filter(
                Q(teaching_subjects__students=student) |  # Subject teachers
                Q(class_teacher_of__subjects__students=student)  # Class teachers
            ).distinct()

            # Start with teachers
            all_users = CustomUser.objects.filter(teacher_profile__in=teachers)

            # Add student-to-student messaging if enabled
            if student_to_student_allowed:
                # Get classmates from the student's grade
                if student.grade:
                    classmates = Student.objects.filter(grade=student.grade).exclude(id=student.id)
                    # Only include students with chat enabled
                    classmates = classmates.filter(chat_enabled=True)
                    classmate_users = CustomUser.objects.filter(student_profile__in=classmates)
                    all_users = all_users | classmate_users
        except Student.DoesNotExist:
            all_users = CustomUser.objects.none()

    elif user.role == 'PARENT':
        try:
            parent = Parent.objects.get(user=user)
            children = parent.children.all()
            # Get teachers of all children
            teachers = Teacher.objects.filter(
                Q(teaching_subjects__students__in=children) |  # Subject teachers
                Q(class_teacher_of__subjects__students__in=children)  # Class teachers
            ).distinct()
            all_users = CustomUser.objects.filter(teacher_profile__in=teachers)
        except Parent.DoesNotExist:
            all_users = CustomUser.objects.none()

    elif user.role == 'TEACHER':
        teacher = Teacher.objects.get(user=user)
        # Get students from teacher's subjects and their parents
        students = Student.objects.filter(
            Q(enrolled_subjects__in=teacher.teaching_subjects.all()) |  # Students in taught subjects
            Q(enrolled_subjects__classroom__class_teacher=teacher)  # Students in class teacher's class
        ).distinct()

        # Get parents of these students
        parents = Parent.objects.filter(children__in=students).distinct()

        # Combine student and parent users
        student_users = CustomUser.objects.filter(student_profile__in=students)
        parent_users = CustomUser.objects.filter(parent_profile__in=parents)
        all_users = (student_users | parent_users).distinct()

    elif user.role == 'ADMIN':
        # Admin can message everyone
        all_users = CustomUser.objects.exclude(id=user.id)

    return all_users

@login_required
def compose_message(request):
    """
    Allow users to compose and send new messages to other users.
    Handles recipient selection, subject, content, and attachments.
    """
    from django.utils import timezone
    from users.models import CustomUser, Student, Teacher, Parent
    from courses.models import ClassSubject, ClassRoom
    from django.db.models import Q

    # Check if messaging is enabled in system settings
    try:
        school_settings = SchoolSettings.objects.first()
        if not school_settings.enable_messaging:
            messages.error(request, "Messaging is currently disabled by the administrator.")
            return redirect('dashboard:student_dashboard' if request.user.is_student else
                           'dashboard:parent_dashboard' if request.user.is_parent else
                           'dashboard:teacher_dashboard' if request.user.is_teacher else
                           'dashboard:admin_dashboard')
    except:
        # If settings don't exist, allow messaging as default
        pass

    # Check if the user is a student with disabled chat
    if request.user.is_student:
        try:
            student = Student.objects.get(user=request.user)
            if not student.chat_enabled:
                messages.error(request, "Your messaging access has been restricted by a parent or administrator.")
                return redirect('dashboard:student_dashboard')
        except Student.DoesNotExist:
            pass

    # Get search and sort parameters
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'name')  # Default sort by name

    # Base queryset
    all_users = CustomUser.objects.none()

    user = request.user
    # Get school settings to check student-to-student messaging permission
    try:
        school_settings = SchoolSettings.objects.first()
        student_to_student_allowed = school_settings.enable_student_to_student_chat
    except:
        student_to_student_allowed = True  # Default to allowed if settings don't exist

    if user.role == 'STUDENT':
        try:
            student = Student.objects.get(user=user)
            # Get teachers of the student's subjects
            teachers = Teacher.objects.filter(
                Q(teaching_subjects__students=student) |  # Subject teachers
                Q(class_teacher_of__subjects__students=student)  # Class teachers
            ).distinct()

            # Start with teachers
            all_users = CustomUser.objects.filter(teacher_profile__in=teachers)

            # Add student-to-student messaging if enabled
            if student_to_student_allowed:
                # Get classmates from the student's grade
                if student.grade:
                    classmates = Student.objects.filter(grade=student.grade).exclude(id=student.id)
                    # Only include students with chat enabled
                    classmates = classmates.filter(chat_enabled=True)
                    classmate_users = CustomUser.objects.filter(student_profile__in=classmates)
                    all_users = all_users | classmate_users
        except Student.DoesNotExist:
            all_users = CustomUser.objects.none()

    elif user.role == 'PARENT':
        try:
            parent = Parent.objects.get(user=user)
            children = parent.children.all()
            # Get teachers of all children
            teachers = Teacher.objects.filter(
                Q(teaching_subjects__students__in=children) |  # Subject teachers
                Q(class_teacher_of__subjects__students__in=children)  # Class teachers
            ).distinct()
            all_users = CustomUser.objects.filter(teacher_profile__in=teachers)
        except Parent.DoesNotExist:
            all_users = CustomUser.objects.none()

    elif user.role == 'TEACHER':
        teacher = Teacher.objects.get(user=user)
        # Get students from teacher's subjects and their parents
        students = Student.objects.filter(
            Q(enrolled_subjects__in=teacher.teaching_subjects.all()) |  # Students in taught subjects
            Q(enrolled_subjects__classroom__class_teacher=teacher)  # Students in class teacher's class
        ).distinct()

        # Get parents of these students
        parents = Parent.objects.filter(children__in=students).distinct()

        # Combine student and parent users
        student_users = CustomUser.objects.filter(student_profile__in=students)
        parent_users = CustomUser.objects.filter(parent_profile__in=parents)
        all_users = (student_users | parent_users).distinct()

    elif user.role == 'ADMIN':
        # Admin can message everyone
        all_users = CustomUser.objects.exclude(id=request.user.id)

    # Apply search filter if provided
    if search_query:
        all_users = all_users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Apply sorting
    if sort_by == 'name':
        all_users = all_users.order_by('first_name', 'last_name')
    elif sort_by == 'name_desc':
        all_users = all_users.order_by('-first_name', '-last_name')
    elif sort_by == 'role':
        all_users = all_users.order_by('role', 'first_name')
    elif sort_by == 'recent':
        # Sort by most recently messaged
        from django.db.models import Max
        all_users = all_users.annotate(
            last_message=Max('received_messages__created_at')
        ).order_by('-last_message', 'first_name')

    if request.method == 'POST':
        recipient_id = request.POST.get('recipient')
        subject = request.POST.get('subject')
        content = request.POST.get('content')

        # Validate required fields
        if not (recipient_id and subject and content):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'communications/compose_message.html', {
                'all_users': all_users,
                'recipients': all_users
            })

        try:
            # Get recipient user
            recipient = CustomUser.objects.get(id=recipient_id)

            # Create message
            new_message = Message(
                sender=request.user,
                recipient=recipient,
                subject=subject,
                content=content
            )

            # Handle attachment if provided
            if 'attachment' in request.FILES:
                new_message.attachment = request.FILES['attachment']

            new_message.save()

            # Create notification for recipient
            create_message_notification(new_message)

            messages.success(request, f"Message sent to {recipient.get_full_name()}.")
            return redirect('communications:message_list')

        except CustomUser.DoesNotExist:
            messages.error(request, "Invalid recipient selected.")

    # GET request - show compose form with all potential recipients
    context = {
        'all_users': all_users,
        'recipients': all_users,
        'search_query': search_query,
        'sort_by': sort_by
    }

    return render(request, 'communications/compose_message.html', context)

# AJAX search endpoint
@login_required
def search_recipients(request):
    """
    AJAX endpoint for searching recipients while composing a message.
    Returns formatted results for Select2 including user icons and role information.
    """
    from users.models import CustomUser, Student, Teacher, Parent
    from django.db.models import Q

    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'name')

    # Get the base queryset based on user role
    user = request.user
    all_users = CustomUser.objects.none()

    # Get school settings to check student-to-student messaging permission
    try:
        school_settings = SchoolSettings.objects.first()
        student_to_student_allowed = school_settings.enable_student_to_student_chat
    except:
        student_to_student_allowed = True  # Default to allowed if settings don't exist

    if user.role == 'STUDENT':
        try:
            student = Student.objects.get(user=user)
            # Get teachers of the student's subjects
            teachers = Teacher.objects.filter(
                Q(teaching_subjects__students=student) |  # Subject teachers
                Q(class_teacher_of__subjects__students=student)  # Class teachers
            ).distinct()

            # Start with teachers
            all_users = CustomUser.objects.filter(teacher_profile__in=teachers)

            # Add student-to-student messaging if enabled
            if student_to_student_allowed:
                # Get classmates from the student's grade
                if student.grade:
                    classmates = Student.objects.filter(grade=student.grade).exclude(id=student.id)
                    # Only include students with chat enabled
                    classmates = classmates.filter(chat_enabled=True)
                    classmate_users = CustomUser.objects.filter(student_profile__in=classmates)
                    all_users = all_users | classmate_users
        except Student.DoesNotExist:
            all_users = CustomUser.objects.none()

    elif user.role == 'PARENT':
        try:
            parent = Parent.objects.get(user=user)
            children = parent.children.all()
            # Get teachers of all children
            teachers = Teacher.objects.filter(
                Q(teaching_subjects__students__in=children) |  # Subject teachers
                Q(class_teacher_of__subjects__students__in=children)  # Class teachers
            ).distinct()
            all_users = CustomUser.objects.filter(teacher_profile__in=teachers)
        except Parent.DoesNotExist:
            all_users = CustomUser.objects.none()

    elif user.role == 'TEACHER':
        teacher = Teacher.objects.get(user=user)
        # Get students from teacher's subjects and their parents
        students = Student.objects.filter(
            Q(enrolled_subjects__in=teacher.teaching_subjects.all()) |  # Students in taught subjects
            Q(enrolled_subjects__classroom__class_teacher=teacher)  # Students in class teacher's class
        ).distinct()

        # Get parents of these students
        parents = Parent.objects.filter(children__in=students).distinct()

        # Combine student and parent users
        student_users = CustomUser.objects.filter(student_profile__in=students)
        parent_users = CustomUser.objects.filter(parent_profile__in=parents)
        all_users = (student_users | parent_users).distinct()

    elif user.role == 'ADMIN':
        # Admin can message everyone
        all_users = CustomUser.objects.exclude(id=request.user.id)

    # Apply search filter
    if search_query:
        all_users = all_users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Apply sorting
    if sort_by == 'name':
        all_users = all_users.order_by('first_name', 'last_name')
    elif sort_by == 'name_desc':
        all_users = all_users.order_by('-first_name', '-last_name')
    elif sort_by == 'role':
        all_users = all_users.order_by('role', 'first_name')
    elif sort_by == 'recent':
        # Sort by most recently messaged
        from django.db.models import Max
        all_users = all_users.annotate(
            last_message=Max('received_messages__created_at')
        ).order_by('-last_message', 'first_name')

    # Format results for Select2 - Enhanced for WhatsApp chat with more user info
    results = [{
        'id': user.id,
        'text': f"{user.get_full_name()} ({user.email})",
        'role': user.get_role_display(),
        'full_name': user.get_full_name(),
        'email': user.email,
        'avatar_color': f"hsl({abs(hash(user.email)) % 360}, 70%, 50%)",
        'avatar_letter': user.get_full_name()[0] if user.get_full_name() else user.email[0]
    } for user in all_users[:20]]  # Increase limit to 20 for better UX

    return JsonResponse({'results': results})

@login_required
def message_detail(request, message_id):
    """
    Display detailed view of a message and mark it as read if the viewer is the recipient.
    Only the sender and recipient can view the message.
    """
    from django.utils import timezone

    # Get the message by ID
    message = get_object_or_404(Message, id=message_id)

    # Security check - only sender and recipient can view the message
    if request.user != message.sender and request.user != message.recipient:
        messages.error(request, "You don't have permission to view this message.")
        return redirect('communications:message_list')

    # Mark message as read if viewer is the recipient and it's unread
    if request.user == message.recipient and not message.is_read:
        message.is_read = True
        message.read_at = timezone.now()
        message.save()

    context = {
        'message': message
    }

    return render(request, 'communications/message_detail.html', context)

@login_required
def view_message(request, message_id):
    """
    Redirect to message_detail view for backward compatibility.
    """
    return redirect('communications:message_detail', message_id=message_id)

# We already defined these AJAX endpoints above

@login_required
def reply_message(request, message_id):
    """
    Reply to an existing message.
    Pre-fills the form with the recipient (original sender) and a quote of the original message.
    """
    from django.utils import timezone

    # Get the original message
    original_message = get_object_or_404(Message, id=message_id)

    # Security check - only the recipient of the original message can reply to it
    if request.user != original_message.recipient:
        messages.error(request, "You don't have permission to reply to this message.")
        return redirect('communications:message_list')

    # Prepare default subject and content with quote
    subject = f"Re: {original_message.subject}"
    content_with_quote = f"\n\n\n----- Original message from {original_message.sender.get_full_name} on {original_message.created_at.strftime('%Y-%m-%d %H:%M')} -----\n\n{original_message.content}"

    if request.method == 'POST':
        # Get form data
        content = request.POST.get('content')
        subject = request.POST.get('subject')

        # Create reply message
        reply = Message(
            sender=request.user,
            recipient=original_message.sender,
            subject=subject,
            content=content
        )

        # Handle attachment if provided
        if 'attachment' in request.FILES:
            reply.attachment = request.FILES['attachment']

        reply.save()

        # Create notification for recipient
        create_message_notification(reply)

        messages.success(request, f"Reply sent to {original_message.sender.get_full_name()}.")
        return redirect('communications:message_list')

    # Pass context to template
    context = {
        'original_message': original_message,
        'subject': subject,
        'content_with_quote': content_with_quote
    }

    return render(request, 'communications/reply_message.html', context)

@login_required
def delete_message(request, message_id):
    """
    Delete a message.
    Only the sender or recipient can delete a message.
    """
    # Get the message
    message = get_object_or_404(Message, id=message_id)

    # Security check - only sender and recipient can delete the message
    if request.user != message.sender and request.user != message.recipient:
        messages.error(request, "You don't have permission to delete this message.")
        return redirect('communications:message_list')

    # Delete the message
    message.delete()

    messages.success(request, "Message deleted successfully.")
    return redirect('communications:message_list')


@login_required
def mark_message_read(request, message_id):
    """
    Mark a message as read via AJAX.
    """
    from django.utils import timezone
    from django.http import JsonResponse

    # Get the message
    message = get_object_or_404(Message, id=message_id)

    # Security check - only recipient can mark message as read
    if request.user != message.recipient:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'})

    # Mark as read if not already
    if not message.is_read:
        message.is_read = True
        message.read_at = timezone.now()
        message.save()

    return JsonResponse({'status': 'success'})

# AJAX endpoints for the WhatsApp-style chat interface
@login_required
def send_message_ajax(request):
    """
    AJAX endpoint to send a message and return the result.
    Used by the WhatsApp-style chat interface.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'})

    recipient_id = request.POST.get('recipient')
    subject = request.POST.get('subject', 'Chat Message')
    content = request.POST.get('content', '').strip()

    # Validate required fields
    if not recipient_id:
        return JsonResponse({'status': 'error', 'message': 'Recipient is required'})

    if not content and 'attachment' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'Message content or attachment is required'})

    try:
        # Get recipient user
        from users.models import CustomUser
        recipient = CustomUser.objects.get(id=recipient_id)

        # Create message
        new_message = Message(
            sender=request.user,
            recipient=recipient,
            subject=subject,
            content=content
        )

        # Handle attachment if provided
        if 'attachment' in request.FILES:
            new_message.attachment = request.FILES['attachment']

        new_message.save()

        # Create notification for recipient
        create_message_notification(new_message)

        # Format the message for JSON response
        message_data = {
            'id': new_message.id,
            'sender': new_message.sender.id,
            'sender_name': new_message.sender.get_full_name(),
            'recipient': new_message.recipient.id,
            'subject': new_message.subject,
            'content': new_message.content,
            'is_read': new_message.is_read,
            'created_at': new_message.created_at.isoformat(),
        }

        if new_message.attachment:
            message_data['attachment'] = new_message.attachment.name
            message_data['attachment_url'] = new_message.attachment.url

        return JsonResponse({
            'status': 'success',
            'message': message_data
        })

    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid recipient'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def get_messages_ajax(request):
    """
    AJAX endpoint to get all messages between the current user and another user.
    Used by the WhatsApp-style chat interface.
    """
    from django.utils import timezone
    from django.db.models import Q

    user_id = request.GET.get('user_id')

    if not user_id:
        return JsonResponse({'status': 'error', 'message': 'User ID is required'})

    try:
        from users.models import CustomUser
        other_user = CustomUser.objects.get(id=user_id)

        # Get all messages between the two users
        messages_query = Message.objects.filter(
            (Q(sender=request.user) & Q(recipient=other_user)) |
            (Q(sender=other_user) & Q(recipient=request.user))
        ).order_by('created_at')

        # Mark messages from other user as read
        unread_messages = messages_query.filter(sender=other_user, recipient=request.user, is_read=False)

        if unread_messages.exists():
            now = timezone.now()
            unread_messages.update(is_read=True, read_at=now)

        # Format messages for JSON response
        messages_data = []
        for msg in messages_query:
            message_dict = {
                'id': msg.id,
                'sender': msg.sender.id,
                'sender_name': msg.sender.get_full_name(),
                'recipient': msg.recipient.id,
                'subject': msg.subject,
                'content': msg.content,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat(),
            }

            if msg.attachment:
                message_dict['attachment'] = msg.attachment.name
                message_dict['attachment_url'] = msg.attachment.url

            messages_data.append(message_dict)

        return JsonResponse({
            'status': 'success',
            'messages': messages_data
        })

    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def get_new_messages_ajax(request):
    """
    AJAX endpoint to get new messages since a specific timestamp.
    Used for real-time chat updates.
    """
    from django.utils import timezone
    from django.db.models import Q

    user_id = request.GET.get('user_id')
    since_timestamp = request.GET.get('since')

    if not user_id or not since_timestamp:
        return JsonResponse({'status': 'error', 'message': 'User ID and timestamp are required'})

    try:
        from users.models import CustomUser
        other_user = CustomUser.objects.get(id=user_id)
        since_datetime = timezone.datetime.fromtimestamp(int(since_timestamp)/1000, tz=timezone.get_current_timezone())

        # Get new messages since the timestamp
        new_messages = Message.objects.filter(
            (Q(sender=request.user) & Q(recipient=other_user)) |
            (Q(sender=other_user) & Q(recipient=request.user)),
            created_at__gt=since_datetime
        ).order_by('created_at')

        # Mark messages from other user as read
        unread_messages = new_messages.filter(sender=other_user, recipient=request.user, is_read=False)

        if unread_messages.exists():
            now = timezone.now()
            unread_messages.update(is_read=True, read_at=now)

        # Format messages for JSON response
        messages_data = []
        for msg in new_messages:
            message_dict = {
                'id': msg.id,
                'sender': msg.sender.id,
                'sender_name': msg.sender.get_full_name(),
                'recipient': msg.recipient.id,
                'subject': msg.subject,
                'content': msg.content,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat(),
            }

            if msg.attachment:
                message_dict['attachment'] = msg.attachment.name
                message_dict['attachment_url'] = msg.attachment.url

            messages_data.append(message_dict)

        return JsonResponse({
            'status': 'success',
            'messages': messages_data
        })

    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'})
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid timestamp'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def delete_message_ajax(request):
    """
    AJAX endpoint to delete a message.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'})

    message_id = request.POST.get('message_id')

    if not message_id:
        return JsonResponse({'status': 'error', 'message': 'Message ID is required'})

    try:
        message = Message.objects.get(id=message_id)

        # Security check - only sender and recipient can delete
        if request.user != message.sender and request.user != message.recipient:
            return JsonResponse({'status': 'error', 'message': 'You don\'t have permission to delete this message'})

        message.delete()

        return JsonResponse({'status': 'success'})

    except Message.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Message not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# Announcement views
@login_required
def announcement_list(request):
    """
    Display a list of announcements relevant to the current user.
    """
    from users.models import Student, Teacher, Parent

    # Get user role
    user = request.user
    role = user.role.lower()

    # All users can see general announcements
    announcements = Announcement.objects.filter(
        Q(target_type='ALL') |
        Q(target_type=role.upper()) |
        Q(target_type='SPECIFIC_USER', target_user=user)
    ).order_by('-created_at')

    # Add class-specific announcements
    if role == 'student':
        try:
            student = Student.objects.get(user=user)
            class_rooms = ClassRoom.objects.filter(
                subjects__students=student
            ).distinct()

            class_announcements = Announcement.objects.filter(
                target_type='SPECIFIC_CLASS',
                target_class__in=class_rooms
            )

            # Combine querysets
            announcements = (announcements | class_announcements).distinct()

        except Student.DoesNotExist:
            pass

    elif role == 'teacher':
        try:
            teacher = Teacher.objects.get(user=user)
            class_rooms = ClassRoom.objects.filter(
                subjects__teacher=teacher
            ).distinct()

            class_announcements = Announcement.objects.filter(
                target_type='SPECIFIC_CLASS',
                target_class__in=class_rooms
            )

            # Combine querysets
            announcements = (announcements | class_announcements).distinct()

        except Teacher.DoesNotExist:
            pass

    elif role == 'parent':
        try:
            parent = Parent.objects.get(user=user)
            children = parent.children.all()

            # Get classes of all children
            all_class_rooms = set()
            for child in children:
                class_rooms = ClassRoom.objects.filter(
                    subjects__students=child
                ).distinct()
                all_class_rooms.update(class_rooms)

            class_announcements = Announcement.objects.filter(
                target_type='SPECIFIC_CLASS',
                target_class__in=all_class_rooms
            )

            # Combine querysets
            announcements = (announcements | class_announcements).distinct()

        except Parent.DoesNotExist:
            pass

    # Order by created date
    announcements = announcements.order_by('-created_at')

    context = {
        'announcements': announcements
    }

    return render(request, 'communications/announcement_list.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def create_announcement(request):
    """
    Create a new announcement targeting specific users or groups.
    Only administrators and teachers can create announcements.
    """
    from django.utils import timezone
    from users.models import CustomUser
    from courses.models import ClassRoom

    # Get available target classes
    class_rooms = ClassRoom.objects.all().order_by('name')

    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        content = request.POST.get('content')
        target_type = request.POST.get('target_type')
        target_class_id = request.POST.get('target_class')
        target_user_id = request.POST.get('target_user')
        expiry_date = request.POST.get('expiry_date')

        # Validate required fields
        if not (title and content and target_type):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'communications/create_announcement.html', {
                'class_rooms': class_rooms
            })

        # Create announcement
        announcement = Announcement(
            title=title,
            content=content,
            target_type=target_type,
            created_by=request.user
        )

        # Set optional fields based on target type
        if target_type == 'SPECIFIC_CLASS' and target_class_id:
            try:
                announcement.target_class = ClassRoom.objects.get(id=target_class_id)
            except ClassRoom.DoesNotExist:
                messages.error(request, "Selected class does not exist.")
                return render(request, 'communications/create_announcement.html', {
                    'class_rooms': class_rooms
                })

        elif target_type == 'SPECIFIC_USER' and target_user_id:
            try:
                announcement.target_user = CustomUser.objects.get(id=target_user_id)
            except CustomUser.DoesNotExist:
                messages.error(request, "Selected user does not exist.")
                return render(request, 'communications/create_announcement.html', {
                    'class_rooms': class_rooms
                })

        # Set expiry date if provided
        if expiry_date:
            from datetime import datetime
            try:
                expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%d')
                announcement.expires_at = expiry_datetime
            except ValueError:
                # Invalid date format, ignore expiry
                pass

        # Handle attachment if provided
        if 'attachment' in request.FILES:
            announcement.attachment = request.FILES['attachment']

        # Save announcement
        announcement.save()

        messages.success(request, "Announcement created successfully.")
        return redirect('communications:announcement_list')

    # GET request
    context = {
        'class_rooms': class_rooms,
        'all_users': CustomUser.objects.all().order_by('last_name', 'first_name')
    }

    return render(request, 'communications/create_announcement.html', context)

@login_required
def announcement_detail(request, announcement_id):
    """
    Display detailed view of an announcement.
    """
    # Get the announcement
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Check if user has permission to view this announcement
    user = request.user
    can_view = False

    # Check various conditions based on announcement target
    if (announcement.target_type == 'ALL' or
        announcement.target_type == user.role or
        (announcement.target_type == 'SPECIFIC_USER' and announcement.target_user == user)):
        can_view = True

    elif announcement.target_type == 'SPECIFIC_CLASS':
        # Check if user is related to this class
        from users.models import Student, Teacher, Parent

        if user.role == 'STUDENT':
            try:
                student = Student.objects.get(user=user)
                if student.enrolled_subjects.filter(class_room=announcement.target_class).exists():
                    can_view = True
            except Student.DoesNotExist:
                pass

        elif user.role == 'TEACHER':
            try:
                teacher = Teacher.objects.get(user=user)
                if teacher.class_subjects.filter(class_room=announcement.target_class).exists():
                    can_view = True
            except Teacher.DoesNotExist:
                pass

        elif user.role == 'PARENT':
            try:
                parent = Parent.objects.get(user=user)
                # Check if any of the parent's children are in this class
                for child in parent.children.all():
                    if child.enrolled_subjects.filter(class_room=announcement.target_class).exists():
                        can_view = True
                        break
            except Parent.DoesNotExist:
                pass

    # Administrators can view all announcements
    if user.role == 'ADMIN':
        can_view = True

    # The creator can always view their own announcements
    if announcement.created_by == user:
        can_view = True

    if not can_view:
        messages.error(request, "You don't have permission to view this announcement.")
        return redirect('communications:announcement_list')

    context = {
        'announcement': announcement
    }

    return render(request, 'communications/announcement_detail.html', context)

@login_required
def view_announcement(request, announcement_id):
    """
    Redirect to announcement_detail for consistency.
    """
    return redirect('communications:announcement_detail', announcement_id=announcement_id)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def edit_announcement(request, announcement_id):
    """
    Edit an existing announcement.
    Only administrators and the creator can edit announcements.
    """
    # Get the announcement
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Security check - only admins and the creator can edit
    if not is_admin(request.user) and request.user != announcement.created_by:
        messages.error(request, "You don't have permission to edit this announcement.")
        return redirect('communications:announcement_list')

    # Get available target classes
    class_rooms = ClassRoom.objects.all().order_by('name')

    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        content = request.POST.get('content')
        target_type = request.POST.get('target_type')
        target_class_id = request.POST.get('target_class')
        target_user_id = request.POST.get('target_user')
        expiry_date = request.POST.get('expiry_date')
        is_active = 'is_active' in request.POST

        # Validate required fields
        if not (title and content and target_type):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'communications/edit_announcement.html', {
                'announcement': announcement,
                'class_rooms': class_rooms
            })

        # Update announcement fields
        announcement.title = title
        announcement.content = content
        announcement.target_type = target_type
        announcement.is_active = is_active

        # Reset optional target fields
        announcement.target_class = None
        announcement.target_user = None

        # Set optional fields based on target type
        if target_type == 'SPECIFIC_CLASS' and target_class_id:
            try:
                announcement.target_class = ClassRoom.objects.get(id=target_class_id)
            except ClassRoom.DoesNotExist:
                messages.error(request, "Selected class does not exist.")
                return render(request, 'communications/edit_announcement.html', {
                    'announcement': announcement,
                    'class_rooms': class_rooms
                })

        elif target_type == 'SPECIFIC_USER' and target_user_id:
            try:
                announcement.target_user = CustomUser.objects.get(id=target_user_id)
            except CustomUser.DoesNotExist:
                messages.error(request, "Selected user does not exist.")
                return render(request, 'communications/edit_announcement.html', {
                    'announcement': announcement,
                    'class_rooms': class_rooms
                })

        # Set expiry date if provided
        if expiry_date:
            from datetime import datetime
            try:
                expiry_datetime = datetime.strptime(expiry_date, '%Y-%m-%d')
                announcement.expires_at = expiry_datetime
            except ValueError:
                # Invalid date format, ignore expiry
                pass
        else:
            announcement.expires_at = None

        # Handle attachment if provided
        if 'attachment' in request.FILES:
            # Delete old attachment if exists
            if announcement.attachment:
                announcement.attachment.delete()

            announcement.attachment = request.FILES['attachment']

        # Save announcement
        announcement.save()

        messages.success(request, "Announcement updated successfully.")
        return redirect('communications:announcement_detail', announcement_id=announcement.id)

    # GET request - prepare context for edit form
    context = {
        'announcement': announcement,
        'class_rooms': class_rooms,
        'all_users': CustomUser.objects.all().order_by('last_name', 'first_name')
    }

    return render(request, 'communications/edit_announcement.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def delete_announcement(request, announcement_id):
    """
    Delete an announcement.
    Only administrators and the creator can delete announcements.
    """
    # Get the announcement
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Security check - only admins and the creator can delete
    if not is_admin(request.user) and request.user != announcement.created_by:
        messages.error(request, "You don't have permission to delete this announcement.")
        return redirect('communications:announcement_list')

    # Delete the announcement
    announcement.delete()

    messages.success(request, "Announcement deleted successfully.")
    return redirect('communications:announcement_list')

# Event views
@login_required
def event_list(request):
    """
    Display a list of events relevant to the current user.
    """
    from users.models import Student, Teacher, Parent
    from django.db.models import Q
    from django.utils import timezone

    # Get current date
    today = timezone.now().date()

    # Get user role
    user = request.user
    role = user.role.lower()

    # All users can see school-wide events
    events = Event.objects.filter(is_school_wide=True)

    # Add class-specific and subject-specific events based on user role
    if role == 'student':
        try:
            student = Student.objects.get(user=user)
            # Get classes the student is in through enrolled subjects
            class_rooms = ClassRoom.objects.filter(subjects__in=student.enrolled_subjects.all()).distinct()
            # Get subjects the student is enrolled in
            subjects = student.enrolled_subjects.all()

            # Get events for these classes and subjects
            specific_events = Event.objects.filter(
                Q(specific_class__in=class_rooms) |
                Q(specific_subject__in=subjects)
            )

            # Combine querysets
            events = (events | specific_events).distinct()

        except Student.DoesNotExist:
            pass

    elif role == 'teacher':
        try:
            teacher = Teacher.objects.get(user=user)
            # Get classes where teacher teaches any subject
            class_rooms = ClassRoom.objects.filter(subjects__teacher=teacher).distinct()
            # Get subjects taught by teacher
            subjects = teacher.teaching_subjects.all()

            # Get events for these classes and subjects
            specific_events = Event.objects.filter(
                Q(specific_class__in=class_rooms) |
                Q(specific_subject__in=subjects)
            )

            # Combine querysets
            events = (events | specific_events).distinct()

        except Teacher.DoesNotExist:
            pass

    elif role == 'parent':
        try:
            parent = Parent.objects.get(user=user)
            children = parent.children.all()

            # Get all subjects and classes for all children
            all_subjects = set()
            all_class_rooms = set()

            for child in children:
                # Get classes child is in through subjects
                class_rooms = ClassRoom.objects.filter(subjects__students=child).distinct()
                all_class_rooms.update(class_rooms)

                # Get child's subjects
                subjects = child.enrolled_subjects.all()
                all_subjects.update(subjects)

            # Get events for these classes and subjects
            specific_events = Event.objects.filter(
                Q(specific_class__in=all_class_rooms) |
                Q(specific_subject__in=all_subjects)
            )

            # Combine querysets
            events = (events | specific_events).distinct()

        except Parent.DoesNotExist:
            pass

    # Filter events by date if specified
    date_filter = request.GET.get('date_filter', 'all')

    if date_filter == 'upcoming':
        events = events.filter(end_date__gte=today)
    elif date_filter == 'past':
        events = events.filter(end_date__lt=today)
    elif date_filter == 'today':
        events = events.filter(start_date__lte=today, end_date__gte=today)
    elif date_filter == 'this_week':
        from datetime import timedelta
        week_end = today + timedelta(days=7)
        events = events.filter(start_date__lte=week_end, end_date__gte=today)
    elif date_filter == 'this_month':
        from datetime import timedelta
        month_end = today + timedelta(days=30)
        events = events.filter(start_date__lte=month_end, end_date__gte=today)
    # If date_filter is 'all' or any other value, don't apply date filtering

    # Filter events by type if specified
    event_type = request.GET.get('type', '')
    if event_type:
        events = events.filter(event_type=event_type)

    # Order by start date
    events = events.order_by('start_date', 'start_time')

    # Prepare event types for filtering
    event_types = Event.EventType.choices

    context = {
        'events': events,
        'date_filter': date_filter,
        'event_type': event_type,
        'event_types': event_types,
        'today': today
    }

    return render(request, 'communications/event_list.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def create_event(request):
    """
    Create a new event.
    Only administrators and teachers can create events.
    """
    from django.utils import timezone
    from courses.models import ClassRoom, ClassSubject

    # Get available classes and subjects
    class_rooms = ClassRoom.objects.all().order_by('name')
    subjects = ClassSubject.objects.all().order_by('subject__name')

    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_type = request.POST.get('event_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date') or start_date  # Default to start_date if not provided
        all_day = 'all_day' in request.POST or 'is_all_day' in request.POST  # Accept both field names
        start_time = request.POST.get('start_time') if not all_day else None
        end_time = request.POST.get('end_time') if not all_day else None
        location = request.POST.get('location')

        # Virtual event settings
        is_virtual = 'is_virtual' in request.POST
        virtual_link = request.POST.get('virtual_link') or request.POST.get('meeting_link')  # Accept both field names

        is_school_wide = 'is_school_wide' in request.POST or 'target_type' in request.POST and request.POST.get('target_type') in ['ALL', 'TEACHERS', 'STUDENTS', 'PARENTS']  # Accept both field names
        specific_class_id = request.POST.get('specific_class') or request.POST.get('target_class') if not is_school_wide else None
        specific_subject_id = request.POST.get('specific_subject') if not is_school_wide else None

        # Get attachment if provided
        attachment = request.FILES.get('attachment')

        # Validate required fields
        if not (title and event_type and start_date):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'communications/create_event.html', {
                'class_rooms': class_rooms,
                'subjects': subjects,
                'event_types': Event.EventType.choices
            })

        # Parse dates
        from datetime import datetime
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

            # Validate date range
            if end_date_obj < start_date_obj:
                messages.error(request, "End date cannot be before start date.")
                return render(request, 'communications/create_event.html', {
                    'class_rooms': class_rooms,
                    'subjects': subjects
                })
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, 'communications/create_event.html', {
                'class_rooms': class_rooms,
                'subjects': subjects
            })

        # Get website integration setting
        show_on_website = 'show_on_website' in request.POST

        # Create event
        event = Event(
            title=title,
            description=description,
            event_type=event_type,
            start_date=start_date_obj,
            end_date=end_date_obj,
            all_day=all_day,
            location=location,
            is_school_wide=is_school_wide,
            is_virtual=is_virtual,
            virtual_link=virtual_link,
            show_on_website=show_on_website
        )

        # Set created_by field explicitly
        if request.user.is_authenticated:
            event.created_by = request.user

        # Set times if not all-day event
        if not all_day and start_time and end_time:
            try:
                event.start_time = datetime.strptime(start_time, '%H:%M').time()
                event.end_time = datetime.strptime(end_time, '%H:%M').time()
            except ValueError:
                # Invalid time format, ignore times
                pass

        # Set specific class or subject if not school-wide
        if not is_school_wide:
            if specific_class_id:
                try:
                    event.specific_class = ClassRoom.objects.get(id=specific_class_id)
                except ClassRoom.DoesNotExist:
                    pass

            if specific_subject_id:
                try:
                    event.specific_subject = ClassSubject.objects.get(id=specific_subject_id)
                except ClassSubject.DoesNotExist:
                    pass

        # Save event
        event.save()

        # Handle attachment if provided
        if attachment:
            event.attachment = attachment
            event.save()

        # Create notifications for relevant users

        # Create notification title and message
        notification_title = f"New Event: {title}"
        notification_message = f"A new event has been scheduled: {title}"

        if location:
            notification_message += f" at {location}"

        notification_message += f" on {start_date_obj.strftime('%B %d, %Y')}"

        # Get the URL for the event detail page
        event_link = reverse('communications:event_detail', args=[event.id])

        # Determine target users based on event settings
        target_users = []

        if is_school_wide:
            # All users should be notified
            target_users = list(CustomUser.objects.all())
        else:
            if event.specific_class:
                # Get all students in this class
                students = Student.objects.filter(enrolled_subjects__class_room=event.specific_class)
                for student in students:
                    target_users.append(student.user)

                    # Also notify parents of these students
                    parents = Parent.objects.filter(children=student)
                    for parent in parents:
                        if parent.user not in target_users:
                            target_users.append(parent.user)

                # Notify the class teacher
                if event.specific_class.class_teacher and event.specific_class.class_teacher.user != request.user:
                    target_users.append(event.specific_class.class_teacher.user)

            if event.specific_subject:
                # Get all students enrolled in this subject
                students = Student.objects.filter(enrolled_subjects=event.specific_subject)
                for student in students:
                    if student.user not in target_users:
                        target_users.append(student.user)

                        # Also notify parents of these students
                        parents = Parent.objects.filter(children=student)
                        for parent in parents:
                            if parent.user not in target_users:
                                target_users.append(parent.user)

                # Notify the subject teacher
                if event.specific_subject.teacher and event.specific_subject.teacher.user != request.user:
                    target_users.append(event.specific_subject.teacher.user)

        # Create notifications for all target users
        for user in target_users:
            if user != request.user:  # Don't notify the creator
                Notification.objects.create(
                    user=user,
                    notification_type='EVENT',
                    title=notification_title,
                    message=notification_message,
                    related_event=event,
                    link=event_link
                )

        messages.success(request, "Event created successfully.")
        return redirect('communications:event_list')

    # GET request
    context = {
        'class_rooms': class_rooms,
        'subjects': subjects,
        'event_types': Event.EventType.choices
    }

    return render(request, 'communications/create_event.html', context)

@login_required
def event_detail(request, event_id):
    """
    Display detailed view of an event.
    """
    # Get the event
    event = get_object_or_404(Event, id=event_id)

    # Check if user has permission to view this event
    user = request.user
    can_view = False

    # Anyone can view school-wide events
    if event.is_school_wide:
        can_view = True
    else:
        # Check if user is related to this class or subject
        from users.models import Student, Teacher, Parent

        if user.role == 'STUDENT':
            try:
                student = Student.objects.get(user=user)
                if ((event.specific_class and student.enrolled_subjects.filter(class_room=event.specific_class).exists()) or
                    (event.specific_subject and student.enrolled_subjects.filter(id=event.specific_subject.id).exists())):
                    can_view = True
            except Student.DoesNotExist:
                pass

        elif user.role == 'TEACHER':
            try:
                teacher = Teacher.objects.get(user=user)
                if ((event.specific_class and teacher.class_subjects.filter(class_room=event.specific_class).exists()) or
                    (event.specific_subject and teacher.class_subjects.filter(id=event.specific_subject.id).exists())):
                    can_view = True
            except Teacher.DoesNotExist:
                pass

        elif user.role == 'PARENT':
            try:
                parent = Parent.objects.get(user=user)
                # Check if any of the parent's children are in this class or subject
                for child in parent.children.all():
                    if ((event.specific_class and child.enrolled_subjects.filter(class_room=event.specific_class).exists()) or
                        (event.specific_subject and child.enrolled_subjects.filter(id=event.specific_subject.id).exists())):
                        can_view = True
                        break
            except Parent.DoesNotExist:
                pass

    # Administrators can view all events
    if user.role == 'ADMIN':
        can_view = True

    # The creator can always view their own events
    if event.created_by == user:
        can_view = True

    if not can_view:
        messages.error(request, "You don't have permission to view this event.")
        return redirect('communications:event_list')

    context = {
        'event': event
    }

    return render(request, 'communications/event_detail.html', context)

@login_required
def view_event(request, event_id):
    """
    Redirect to event_detail for consistency.
    """
    return redirect('communications:event_detail', event_id=event_id)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def edit_event(request, event_id):
    """
    Edit an existing event.
    Only administrators and the creator can edit events.
    """
    # Get the event
    event = get_object_or_404(Event, id=event_id)

    # Security check - only admins and the creator can edit
    if not is_admin(request.user) and request.user != event.created_by:
        messages.error(request, "You don't have permission to edit this event.")
        return redirect('communications:event_list')

    # Get available classes and subjects
    class_rooms = ClassRoom.objects.all().order_by('name')
    subjects = ClassSubject.objects.all().order_by('subject__name')

    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_type = request.POST.get('event_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        all_day = 'all_day' in request.POST
        start_time = request.POST.get('start_time') if not all_day else None
        end_time = request.POST.get('end_time') if not all_day else None
        location = request.POST.get('location')

        # Virtual event settings
        is_virtual = 'is_virtual' in request.POST
        virtual_link = request.POST.get('meeting_link') or request.POST.get('virtual_link')
        virtual_link = virtual_link if is_virtual else None

        # Determine if school-wide based on target_type
        target_type = request.POST.get('target_type')
        is_school_wide = (target_type == 'ALL')
        specific_class_id = request.POST.get('specific_class') if not is_school_wide else None
        specific_subject_id = request.POST.get('specific_subject') if not is_school_wide else None

        # Validate required fields
        if not (title and event_type and start_date and end_date):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'communications/edit_event.html', {
                'event': event,
                'class_rooms': class_rooms,
                'subjects': subjects
            })

        # Parse dates
        from datetime import datetime
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

            # Validate date range
            if end_date_obj < start_date_obj:
                messages.error(request, "End date cannot be before start date.")
                return render(request, 'communications/edit_event.html', {
                    'event': event,
                    'class_rooms': class_rooms,
                    'subjects': subjects
                })
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, 'communications/edit_event.html', {
                'event': event,
                'class_rooms': class_rooms,
                'subjects': subjects
            })

        # Get website integration setting
        show_on_website = 'show_on_website' in request.POST

        # Update event fields
        event.title = title
        event.description = description
        event.event_type = event_type
        event.start_date = start_date_obj
        event.end_date = end_date_obj
        event.all_day = all_day
        event.location = location
        event.is_school_wide = is_school_wide
        event.is_virtual = is_virtual
        event.virtual_link = virtual_link
        event.show_on_website = show_on_website

        # Set times if not all-day event
        if not all_day and start_time and end_time:
            try:
                event.start_time = datetime.strptime(start_time, '%H:%M').time()
                event.end_time = datetime.strptime(end_time, '%H:%M').time()
            except ValueError:
                # Invalid time format, ignore times
                pass
        else:
            event.start_time = None
            event.end_time = None

        # Reset specific class and subject
        event.specific_class = None
        event.specific_subject = None

        # Set specific class or subject if not school-wide
        if not is_school_wide:
            if specific_class_id:
                try:
                    event.specific_class = ClassRoom.objects.get(id=specific_class_id)
                except ClassRoom.DoesNotExist:
                    pass

            if specific_subject_id:
                try:
                    event.specific_subject = ClassSubject.objects.get(id=specific_subject_id)
                except ClassSubject.DoesNotExist:
                    pass

        # Handle attachment if provided
        if 'attachment' in request.FILES:
            # Delete old attachment if exists
            if event.attachment:
                event.attachment.delete(save=False)

            # Set new attachment
            event.attachment = request.FILES['attachment']

        # Save event
        event.save()

        messages.success(request, "Event updated successfully.")
        return redirect('communications:event_detail', event_id=event.id)

    # GET request - prepare context for edit form
    context = {
        'event': event,
        'class_rooms': class_rooms,
        'subjects': subjects,
        'event_types': Event.EventType.choices
    }

    return render(request, 'communications/edit_event.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def delete_event(request, event_id):
    """
    Delete an event.
    Only administrators and the creator can delete events.
    """
    # Get the event
    event = get_object_or_404(Event, id=event_id)

    # Security check - only admins and the creator can delete
    if not is_admin(request.user) and request.user != event.created_by:
        messages.error(request, "You don't have permission to delete this event.")
        return redirect('communications:event_list')

    # Delete the event
    event.delete()

    messages.success(request, "Event deleted successfully.")
    return redirect('communications:event_list')

@login_required
def event_calendar(request):
    """
    Display a calendar view of events.
    """
    # This view will be similar to event_list but formatted for a calendar
    return render(request, 'communications/event_calendar.html')

@login_required
def calendar_view(request):
    """
    Redirect to event_calendar for consistency.
    """
    return redirect('communications:event_calendar')

# Notification views
@login_required
def notification_list(request):
    """
    Display a list of notifications for the current user.
    """
    # Get notifications for the current user
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Count unread notifications
    unread_count = notifications.filter(is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }

    return render(request, 'communications/notification_list.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def create_notification(request):
    """
    Create a new notification for a user or group of users.
    Only administrators and teachers can create notifications.
    """
    from django.utils import timezone
    from users.models import CustomUser, Student, Teacher, Parent

    if request.method == 'POST':
        # Get form data
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type')
        target_type = request.POST.get('target_type')

        # Get target users
        target_users = []

        if target_type == 'all':
            target_users = CustomUser.objects.all()
        elif target_type == 'teachers':
            target_users = CustomUser.objects.filter(role='TEACHER')
        elif target_type == 'students':
            target_users = CustomUser.objects.filter(role='STUDENT')
        elif target_type == 'parents':
            target_users = CustomUser.objects.filter(role='PARENT')
        elif target_type == 'specific_user':
            user_id = request.POST.get('user_id')
            if user_id:
                try:
                    user = CustomUser.objects.get(id=user_id)
                    target_users = [user]
                except CustomUser.DoesNotExist:
                    messages.error(request, "Selected user does not exist.")
                    return redirect('communications:create_notification')
        elif target_type == 'specific_class':
            class_id = request.POST.get('class_id')
            if class_id:
                try:
                    class_room = ClassRoom.objects.get(id=class_id)

                    # Get students in this class
                    students = Student.objects.filter(enrolled_subjects__class_room=class_room)
                    student_users = [student.user for student in students]

                    # Get teachers of this class
                    teachers = Teacher.objects.filter(class_subjects__class_room=class_room)
                    teacher_users = [teacher.user for teacher in teachers]

                    # Get parents of students in this class
                    parent_users = []
                    for student in students:
                        parents = Parent.objects.filter(children=student)
                        for parent in parents:
                            if parent.user not in parent_users:
                                parent_users.append(parent.user)

                    # Combine all users
                    target_users = student_users + teacher_users + parent_users
                except ClassRoom.DoesNotExist:
                    messages.error(request, "Selected class does not exist.")
                    return redirect('communications:create_notification')

        # Validate inputs
        if not (title and message and notification_type and target_users):
            messages.error(request, "Please fill in all required fields.")
            return redirect('communications:create_notification')

        # Create notifications for all target users
        for user in target_users:
            Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message
            )

        messages.success(request, f"Notification sent to {len(target_users)} users.")
        return redirect('communications:notification_list')

    # GET request
    context = {
        'users': CustomUser.objects.all().order_by('last_name', 'first_name'),
        'classes': ClassRoom.objects.all().order_by('name'),
        'notification_types': Notification.NotificationType.choices
    }

    return render(request, 'communications/create_notification.html', context)

@login_required
def view_notification(request, notification_id):
    """
    View a notification and mark it as read.
    """
    from django.utils import timezone

    # Get the notification
    notification = get_object_or_404(Notification, id=notification_id)

    # Security check - only the recipient can view their notification
    if request.user != notification.user:
        messages.error(request, "You don't have permission to view this notification.")
        return redirect('communications:notification_list')

    # Mark notification as read if not already
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

    # Determine redirect URL based on notification type
    if notification.notification_type == 'ASSIGNMENT' and notification.related_assignment:
        return redirect('assignments:assignment_detail', assignment_id=notification.related_assignment.id)
    elif notification.notification_type == 'ANNOUNCEMENT' and notification.related_announcement:
        return redirect('communications:announcement_detail', announcement_id=notification.related_announcement.id)
    elif notification.notification_type == 'EVENT' and notification.related_event:
        return redirect('communications:event_detail', event_id=notification.related_event.id)
    elif notification.notification_type == 'MESSAGE' and notification.related_message:
        return redirect('communications:message_detail', message_id=notification.related_message.id)
    else:
        # No specific redirect, show notification details
        context = {
            'notification': notification
        }
        return render(request, 'communications/view_notification.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a notification as read and redirect to the appropriate page.
    """
    from django.utils import timezone
    from django.http import HttpResponseRedirect

    # Get the notification
    notification = get_object_or_404(Notification, id=notification_id)

    # Security check - only the recipient can mark their notification as read
    if request.user != notification.user:
        messages.error(request, "You don't have permission to view this notification.")
        return redirect('communications:notification_list')

    # Mark as read if not already
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

    # Determine where to redirect based on notification type and related objects
    if notification.link:
        # If the notification has a specific link, redirect there
        return HttpResponseRedirect(notification.link)
    elif notification.notification_type == 'ASSIGNMENT' and notification.related_assignment:
        return redirect('assignments:assignment_detail', assignment_id=notification.related_assignment.id)
    elif notification.notification_type == 'ANNOUNCEMENT' and notification.related_announcement:
        return redirect('communications:announcement_detail', announcement_id=notification.related_announcement.id)
    elif notification.notification_type == 'EVENT' and notification.related_event:
        return redirect('communications:event_detail', event_id=notification.related_event.id)
    elif notification.notification_type == 'MESSAGE' and notification.related_message:
        return redirect('communications:message_detail', message_id=notification.related_message.id)
    else:
        # If no specific redirect, go to the notification list
        return redirect('communications:notification_list')

@login_required
def mark_all_notifications_read(request):
    """
    Mark all notifications for the current user as read.
    """
    from django.utils import timezone

    # Get unread notifications for the current user
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False)

    # Mark all as read
    for notification in unread_notifications:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

    messages.success(request, f"{unread_notifications.count()} notifications marked as read.")
    return redirect('communications:notification_list')

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def delete_notification(request, notification_id):
    """
    Delete a notification.
    Only the recipient can delete their notification.
    """
    # Get the notification
    notification = get_object_or_404(Notification, id=notification_id)

    # Security check - only the recipient can delete their notification
    if request.user != notification.user:
        messages.error(request, "You don't have permission to delete this notification.")
        return redirect('communications:notification_list')

    # Delete the notification
    notification.delete()

    messages.success(request, "Notification deleted successfully.")
    return redirect('communications:notification_list')

# Broadcast views
# Import the custom decorator
from users.decorators import admin_or_teacher_required

@login_required
@admin_or_teacher_required
def broadcast_message(request):
    """
    Broadcast a message to multiple users at once.
    Creates Message objects for multiple recipients.

    Security checks:
    - Only admins and teachers can broadcast messages
    - Teachers can only broadcast to their own classes
    - Target type is validated using a whitelist approach
    - Input validation to prevent security vulnerabilities
    """
    from django.utils import timezone
    from users.models import CustomUser, Student, Teacher, Parent
    from django.db.models import Q
    import bleach  # For sanitizing user input

    # Valid target types whitelist with explicit enumeration
    VALID_TARGET_TYPES = ['all', 'teachers', 'students', 'parents', 'specific_class']

    if request.method == 'POST':
        # Get form data and sanitize inputs
        subject = bleach.clean(request.POST.get('subject', '').strip())
        content = bleach.clean(request.POST.get('content', '').strip())
        target_type = request.POST.get('target_type', '').strip()

        # Validate required fields
        if not subject or not content or not target_type:
            messages.error(request, "Subject, content, and target type are required.")
            return redirect('communications:broadcast_message')

        # Validate target_type using whitelist approach
        if target_type not in VALID_TARGET_TYPES:
            messages.error(request, "Invalid target type selected.")
            return redirect('communications:broadcast_message')

        # Enforce reasonable length limits
        if len(subject) > 200:  # Arbitrary reasonable limit
            messages.error(request, "Subject is too long. Maximum 200 characters allowed.")
            return redirect('communications:broadcast_message')

        if len(content) > 10000:  # Arbitrary reasonable limit
            messages.error(request, "Message content is too long. Maximum 10000 characters allowed.")
            return redirect('communications:broadcast_message')

        # Get target users
        target_users = []

        if target_type == 'all':
            # Only admins can message everyone
            if request.user.role != 'ADMIN':
                messages.error(request, "Only administrators can broadcast to all users.")
                return redirect('communications:broadcast_message')
            target_users = CustomUser.objects.exclude(id=request.user.id)
        elif target_type == 'teachers':
            # Only admins can message all teachers
            if request.user.role != 'ADMIN':
                messages.error(request, "Only administrators can broadcast to all teachers.")
                return redirect('communications:broadcast_message')
            target_users = CustomUser.objects.filter(role='TEACHER').exclude(id=request.user.id)
        elif target_type == 'students':
            # Teachers can only message students they teach
            if request.user.role == 'TEACHER':
                try:
                    teacher = Teacher.objects.get(user=request.user)
                    student_ids = Student.objects.filter(
                        Q(enrolled_subjects__teacher=teacher) |  # Students in subjects taught by teacher
                        Q(enrolled_subjects__classroom__class_teacher=teacher)  # Students in classes where teacher is class teacher
                    ).distinct().values_list('user_id', flat=True)
                    target_users = CustomUser.objects.filter(id__in=student_ids)
                except Teacher.DoesNotExist:
                    messages.error(request, "Teacher profile not found.")
                    return redirect('communications:broadcast_message')
            else:
                target_users = CustomUser.objects.filter(role='STUDENT')
        elif target_type == 'parents':
            # Teachers can only message parents of students they teach
            if request.user.role == 'TEACHER':
                try:
                    teacher = Teacher.objects.get(user=request.user)
                    # Get students taught by this teacher
                    students = Student.objects.filter(
                        Q(enrolled_subjects__teacher=teacher) |  # Students in subjects taught by teacher
                        Q(enrolled_subjects__classroom__class_teacher=teacher)  # Students in classes where teacher is class teacher
                    ).distinct()

                    # Get parents of these students
                    parent_ids = []
                    for student in students:
                        parent_ids.extend(Parent.objects.filter(children=student).values_list('user_id', flat=True))

                    target_users = CustomUser.objects.filter(id__in=parent_ids)
                except Teacher.DoesNotExist:
                    messages.error(request, "Teacher profile not found.")
                    return redirect('communications:broadcast_message')
            else:
                target_users = CustomUser.objects.filter(role='PARENT')
        elif target_type == 'specific_class':
            class_id = request.POST.get('class_id')
            if not class_id:
                messages.error(request, "Class ID is required for class-specific broadcasts.")
                return redirect('communications:broadcast_message')

            try:
                class_room = ClassRoom.objects.get(id=class_id)

                # Security check: Teachers can only broadcast to their own classes
                if request.user.role == 'TEACHER':
                    try:
                        teacher = Teacher.objects.get(user=request.user)

                        # Check if teacher teaches this class
                        teacher_has_access = (
                            class_room.class_teacher == teacher or
                            ClassSubject.objects.filter(classroom=class_room, teacher=teacher).exists()
                        )

                        if not teacher_has_access:
                            messages.error(request, "You can only broadcast messages to classes you teach.")
                            return redirect('communications:broadcast_message')
                    except Teacher.DoesNotExist:
                        messages.error(request, "Teacher profile not found.")
                        return redirect('communications:broadcast_message')

                # Get students in this class
                students = Student.objects.filter(enrolled_subjects__classroom=class_room)
                student_users = CustomUser.objects.filter(student_profile__in=students)

                # Get parents of students in this class
                parent_users = CustomUser.objects.filter(
                    parent_profile__children__in=students
                ).distinct()

                # Combine all users
                target_users = (student_users | parent_users).distinct()
            except ClassRoom.DoesNotExist:
                messages.error(request, "Selected class does not exist.")
                return redirect('communications:broadcast_message')

        # Validate we have recipients and content
        if not target_users:
            messages.error(request, "No recipients match the selected criteria.")
            return redirect('communications:broadcast_message')

        if not (subject and content):
            messages.error(request, "Please fill in all required fields.")
            return redirect('communications:broadcast_message')

        # Limit the number of recipients to prevent abuse
        MAX_RECIPIENTS = 500  # Arbitrary reasonable limit
        if len(target_users) > MAX_RECIPIENTS:
            messages.error(request, f"Too many recipients ({len(target_users)}). Maximum {MAX_RECIPIENTS} allowed.")
            return redirect('communications:broadcast_message')

        # Create messages for all target users with rate limiting
        message_count = 0
        for user in target_users:
            # Create message
            message = Message(
                sender=request.user,
                recipient=user,
                subject=subject,
                content=content
            )

            # Handle attachment if provided
            if 'attachment' in request.FILES:
                # Check file size to prevent abuse
                attachment = request.FILES['attachment']
                if attachment.size > 5 * 1024 * 1024:  # 5MB limit
                    messages.error(request, "Attachment is too large. Maximum 5MB allowed.")
                    return redirect('communications:broadcast_message')

                message.attachment = attachment

            message.save()

            # Create notification for recipient
            create_message_notification(message)
            message_count += 1

            # Rate limiting - break into batches if needed
            if message_count >= 100:  # Send in batches of 100
                messages.success(request, f"Sending messages in batches: {message_count} sent so far...")

        messages.success(request, f"Message broadcasted to {message_count} users.")
        return redirect('communications:message_list')

    # GET request
    # Get classes based on user role
    if request.user.role == 'TEACHER':
        try:
            teacher = Teacher.objects.get(user=request.user)
            classes = ClassRoom.objects.filter(
                Q(class_teacher=teacher) |
                Q(subjects__teacher=teacher)
            ).distinct().order_by('name')
        except Teacher.DoesNotExist:
            classes = ClassRoom.objects.none()
    else:
        classes = ClassRoom.objects.all().order_by('name')

    context = {
        'classes': classes,
        'target_types': VALID_TARGET_TYPES
    }

    return render(request, 'communications/broadcast_message.html', context)

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def broadcast_to_class(request, classroom_id):
    """
    Redirect to broadcast_message with pre-selected class.
    """
    return redirect('communications:broadcast_message')

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def broadcast_to_teachers(request):
    """
    Redirect to broadcast_message with pre-selected teacher target.
    """
    return redirect('communications:broadcast_message')

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def broadcast_to_students(request):
    """
    Redirect to broadcast_message with pre-selected student target.
    """
    return redirect('communications:broadcast_message')

@login_required
@user_passes_test(lambda u: is_admin(u) or is_teacher(u))
def broadcast_to_parents(request):
    """
    Redirect to broadcast_message with pre-selected parent target.
    """
    return redirect('communications:broadcast_message')

# API views for notifications
@login_required
def notification_count(request):
    """
    Return the count of unread notifications for the current user.
    Used for AJAX updates in the UI.
    """
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': unread_count})

@login_required
def message_count(request):
    """
    Return the count of unread messages for the current user.
    Used for AJAX updates in the UI.
    """
    unread_count = Message.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': unread_count})

@login_required
def material_notification_count(request):
    """
    Return the count of unread material notifications for the current user.
    Used for AJAX updates in the UI.
    """
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False,
        notification_type='ASSIGNMENT',
        title__contains='material'  # Simple heuristic to identify material notifications
    ).count()
    return JsonResponse({'count': unread_count})

@login_required
def assignment_notification_count(request):
    """
    Return the count of unread assignment notifications for the current user.
    Used for AJAX updates in the UI.
    """
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False,
        notification_type='ASSIGNMENT'
    ).exclude(
        title__contains='material'  # Exclude material notifications
    ).count()
    return JsonResponse({'count': unread_count})

@login_required
def quiz_notification_count(request):
    """
    Return the count of unread quiz notifications for the current user.
    Used for AJAX updates in the UI.
    """
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False,
        notification_type='QUIZ'
    ).count()
    return JsonResponse({'count': unread_count})

@login_required
def notification_api_list(request):
    """
    Return a list of recent notifications for the current user.
    Used for AJAX updates in the UI.
    """
    # Get recent notifications (limit to 5)
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]

    # Format notifications for JSON response
    notification_list = []
    for notification in notifications:
        notification_data = {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.get_notification_type_display(),
            'is_read': notification.is_read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M')
        }
        notification_list.append(notification_data)

    return JsonResponse({'notifications': notification_list})

# Other API views for AJAX functionality
@login_required
def api_get_messages(request):
    """
    Return a list of recent messages for the current user.
    Used for AJAX updates in the UI.
    """
    # Get recent messages (limit to 5)
    received_messages = Message.objects.filter(recipient=request.user).order_by('-created_at')[:5]

    # Format messages for JSON response
    message_list = []
    for message in received_messages:
        message_data = {
            'id': message.id,
            'sender': message.sender.get_full_name(),
            'subject': message.subject,
            'is_read': message.is_read,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M')
        }
        message_list.append(message_data)

    return JsonResponse({'messages': message_list})

@login_required
def api_get_announcements(request):
    """
    Return a list of recent announcements for the current user.
    Used for AJAX updates in the UI.
    """
    # Logic to get relevant announcements (similar to announcement_list view)
    # Simplified version for AJAX
    from django.db.models import Q

    # Get user role
    user = request.user
    role = user.role.upper()

    # All users can see general announcements
    announcements = Announcement.objects.filter(
        Q(target_type='ALL') |
        Q(target_type=role) |
        Q(target_type='SPECIFIC_USER', target_user=user),
        is_active=True
    ).order_by('-created_at')[:5]

    # Format announcements for JSON response
    announcement_list = []
    for announcement in announcements:
        announcement_data = {
            'id': announcement.id,
            'title': announcement.title,
            'created_by': announcement.created_by.get_full_name(),
            'created_at': announcement.created_at.strftime('%Y-%m-%d %H:%M')
        }
        announcement_list.append(announcement_data)

    return JsonResponse({'announcements': announcement_list})

@login_required
def api_get_events(request):
    """
    Return a list of upcoming events for the current user.
    Used for AJAX updates in the UI.
    """
    from django.utils import timezone

    # Get current date
    today = timezone.now().date()

    # Get upcoming events (limit to 5)
    events = Event.objects.filter(
        is_school_wide=True,
        end_date__gte=today
    ).order_by('start_date')[:5]

    # Format events for JSON response
    event_list = []
    for event in events:
        event_data = {
            'id': event.id,
            'title': event.title,
            'event_type': event.get_event_type_display(),
            'start_date': event.start_date.strftime('%Y-%m-%d'),
            'location': event.location
        }
        event_list.append(event_data)

    return JsonResponse({'events': event_list})

@login_required
def api_get_notifications(request):
    """
    Alias for notification_api_list for consistency.
    """
    return notification_api_list(request)