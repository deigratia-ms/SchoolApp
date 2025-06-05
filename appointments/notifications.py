from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from communications.models import Notification

def send_appointment_confirmation(appointment):
    """
    Send a confirmation email to the parent when an appointment is booked
    """
    parent = appointment.parent
    user = parent.user
    
    # Create a notification in the system
    Notification.objects.create(
        user=user,
        title="Appointment Confirmation",
        message=f"Your appointment on {appointment.time_slot.date} at {appointment.time_slot.start_time} has been confirmed.",
        notification_type="APPOINTMENT",
        link=f"/appointments/appointment/{appointment.id}/"
    )
    
    # Send email notification
    subject = f"Appointment Confirmation - {settings.DEFAULT_SCHOOL_NAME}"
    context = {
        'parent': parent,
        'appointment': appointment,
        'school_name': settings.DEFAULT_SCHOOL_NAME,
    }
    
    html_message = render_to_string('appointments/email/appointment_confirmation.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send appointment confirmation email: {e}")
        return False

def send_appointment_reminder(appointment):
    """
    Send a reminder email to the parent before an appointment
    """
    parent = appointment.parent
    user = parent.user
    
    # Create a notification in the system
    Notification.objects.create(
        user=user,
        title="Appointment Reminder",
        message=f"Reminder: You have an appointment tomorrow at {appointment.time_slot.start_time}.",
        notification_type="APPOINTMENT",
        link=f"/appointments/appointment/{appointment.id}/"
    )
    
    # Send email notification
    subject = f"Appointment Reminder - {settings.DEFAULT_SCHOOL_NAME}"
    context = {
        'parent': parent,
        'appointment': appointment,
        'school_name': settings.DEFAULT_SCHOOL_NAME,
    }
    
    html_message = render_to_string('appointments/email/appointment_reminder.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send appointment reminder email: {e}")
        return False

def send_appointment_update(appointment, changes):
    """
    Send an update email to the parent when an appointment is updated
    """
    parent = appointment.parent
    user = parent.user
    
    # Create a notification in the system
    Notification.objects.create(
        user=user,
        title="Appointment Updated",
        message=f"Your appointment on {appointment.time_slot.date} at {appointment.time_slot.start_time} has been updated.",
        notification_type="APPOINTMENT",
        link=f"/appointments/appointment/{appointment.id}/"
    )
    
    # Send email notification
    subject = f"Appointment Update - {settings.DEFAULT_SCHOOL_NAME}"
    context = {
        'parent': parent,
        'appointment': appointment,
        'changes': changes,
        'school_name': settings.DEFAULT_SCHOOL_NAME,
    }
    
    html_message = render_to_string('appointments/email/appointment_update.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send appointment update email: {e}")
        return False

def send_appointment_cancellation(appointment):
    """
    Send a cancellation email to the parent when an appointment is cancelled
    """
    parent = appointment.parent
    user = parent.user
    
    # Create a notification in the system
    Notification.objects.create(
        user=user,
        title="Appointment Cancelled",
        message=f"Your appointment on {appointment.time_slot.date} at {appointment.time_slot.start_time} has been cancelled.",
        notification_type="APPOINTMENT",
        link=f"/appointments/appointment/{appointment.id}/"
    )
    
    # Send email notification
    subject = f"Appointment Cancellation - {settings.DEFAULT_SCHOOL_NAME}"
    context = {
        'parent': parent,
        'appointment': appointment,
        'school_name': settings.DEFAULT_SCHOOL_NAME,
    }
    
    html_message = render_to_string('appointments/email/appointment_cancellation.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send appointment cancellation email: {e}")
        return False
