from django.db.models import Q
from django.utils import timezone
from django.urls import reverse

from communications.models import Notification
from users.models import Student, Teacher, Parent

def create_assignment_notification(assignment, created_by):
    """
    Create notifications for all relevant users when a new assignment is created.
    
    Args:
        assignment: The Assignment object
        created_by: The user who created the assignment
    """
    # Get the class and subject
    class_subject = assignment.class_subject
    classroom = class_subject.classroom
    subject = class_subject.subject
    
    # Create notification title and message
    title = f"New {assignment.get_assignment_type_display()}: {assignment.title}"
    message = f"A new {assignment.get_assignment_type_display().lower()} has been posted for {subject.name}"
    
    # Add due date to message if available
    if assignment.due_date:
        due_date_str = assignment.due_date.strftime("%B %d, %Y at %I:%M %p")
        message += f". Due date: {due_date_str}"
    
    # Get the URL for the assignment detail page
    link = reverse('assignments:assignment_detail', args=[assignment.id])
    
    # Get all students enrolled in this class subject
    students = Student.objects.filter(enrolled_subjects=class_subject)
    
    # Create notifications for all students
    for student in students:
        Notification.objects.create(
            user=student.user,
            notification_type='ASSIGNMENT',
            title=title,
            message=message,
            related_assignment=assignment,
            link=link
        )
    
    # Get all parents of students in this class
    for student in students:
        parents = Parent.objects.filter(children=student)
        for parent in parents:
            # Create notification for parent
            Notification.objects.create(
                user=parent.user,
                notification_type='ASSIGNMENT',
                title=f"New {assignment.get_assignment_type_display()} for {student.user.get_full_name()}",
                message=f"A new {assignment.get_assignment_type_display().lower()} has been posted for {student.user.get_full_name()} in {subject.name}",
                related_assignment=assignment,
                link=link
            )
    
    # Only notify the class teacher if they didn't create the assignment
    if classroom.class_teacher and classroom.class_teacher.user != created_by:
        Notification.objects.create(
            user=classroom.class_teacher.user,
            notification_type='ASSIGNMENT',
            title=f"New {assignment.get_assignment_type_display()} in {subject.name}",
            message=f"{created_by.get_full_name()} posted a new {assignment.get_assignment_type_display().lower()} for {classroom.name} {subject.name}",
            related_assignment=assignment,
            link=link
        )

def create_material_notification(material, created_by):
    """
    Create notifications for all relevant users when a new course material is uploaded.
    
    Args:
        material: The CourseMaterial object
        created_by: The user who created the material
    """
    # Get the class and subject
    class_subject = material.class_subject
    classroom = class_subject.classroom
    subject = class_subject.subject
    
    # Create notification title and message
    title = f"New Material: {material.title}"
    message = f"New course material has been uploaded for {subject.name}: {material.title}"
    
    # Get the URL for the material detail page
    link = reverse('courses:material_detail', args=[material.id])
    
    # Get all students enrolled in this class subject
    students = Student.objects.filter(enrolled_subjects=class_subject)
    
    # Create notifications for all students
    for student in students:
        Notification.objects.create(
            user=student.user,
            notification_type='ANNOUNCEMENT',
            title=title,
            message=message,
            link=link
        )
    
     # Get all parents of students in this class
    for student in students:
        parents = Parent.objects.filter(children=student)
        for parent in parents:
            # Create notification for parent
            Notification.objects.create(
                user=parent.user,
                notification_type='ANNOUNCEMENT',
                title=f"New Material for {student.user.get_full_name()}",
                message=f"A new material has been posted for {student.user.get_full_name()} in {subject.name}",
                link=link
            )
    
    # Only notify the class teacher if they didn't create the material
    if classroom.class_teacher and classroom.class_teacher.user != created_by:
        Notification.objects.create(
            user=classroom.class_teacher.user,
            notification_type='ANNOUNCEMENT',
            title=f"New Material in {subject.name}",
            message=f"{created_by.get_full_name()} uploaded new course material for {classroom.name} {subject.name}: {material.title}",
            link=link
        )

def create_video_notification(video, created_by):
    """
    Create notifications for all relevant users when a new video is uploaded.
    
    Args:
        video: The CourseVideo object
        created_by: The user who created the video
    """
    # Get the class and subject
    class_subject = video.class_subject
    classroom = class_subject.classroom
    subject = class_subject.subject
    
    # Create notification title and message
    title = f"New Video: {video.title}"
    message = f"New video has been uploaded for {subject.name}: {video.title}"
    
    # Get the URL for the video detail page
    link = reverse('courses:video_detail', args=[video.id])
    
    # Get all students enrolled in this class subject
    students = Student.objects.filter(enrolled_subjects=class_subject)
    
    # Create notifications for all students
    for student in students:
        Notification.objects.create(
            user=student.user,
            notification_type='ANNOUNCEMENT',
            title=title,
            message=message,
            link=link
        )
    
    # Get all parents of students in this class
    for student in students:
        parents = Parent.objects.filter(children=student)
        for parent in parents:
            # Create notification for parent
            Notification.objects.create(
                user=parent.user,
                notification_type='ANNOUNCEMENT',
                title=f"New Video for {student.user.get_full_name()}",
                message=f"A new video has been posted for {student.user.get_full_name()} in {subject.name}",
                link=link
            )
    
    # Only notify the class teacher if they didn't create the video
    if classroom.class_teacher and classroom.class_teacher.user != created_by:
        Notification.objects.create(
            user=classroom.class_teacher.user,
            notification_type='ANNOUNCEMENT',
            title=f"New Video in {subject.name}",
            message=f"{created_by.get_full_name()} uploaded a new video for {classroom.name} {subject.name}: {video.title}",
            link=link
        )

def get_unread_notifications_count(user):
    """
    Get the count of unread notifications for a user.
    
    Args:
        user: The user to get notifications for
        
    Returns:
        int: The count of unread notifications
    """
    return Notification.objects.filter(user=user, is_read=False).count()

def get_unread_messages_count(user):
    """
    Get the count of unread messages for a user.
    
    Args:
        user: The user to get messages for
        
    Returns:
        int: The count of unread messages
    """
    from communications.models import Message
    return Message.objects.filter(recipient=user, is_read=False).count()

def create_message_notification(message):
    """
    Create a notification for the recipient when a new message is sent.
    
    Args:
        message: The Message object
    """
    # Get the message details
    sender = message.sender
    recipient = message.recipient
    
    # Create notification title and message
    title = f"New Message from {sender.get_full_name()}"
    notification_message = f"You have received a new message: {message.subject}"
    
    # Get the URL for the message detail page
    link = reverse('communications:message_detail', args=[message.id])
    
    # Create notification for the recipient
    Notification.objects.create(
        user=recipient,
        notification_type='MESSAGE',
        title=title,
        message=notification_message,
        related_message=message,
        link=link
    )