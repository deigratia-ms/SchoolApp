from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    # WhatsApp-style Chat Interface
    path('chat/', views.chat, name='chat'),
    path('chat/send/', views.send_message_ajax, name='send_message_ajax'),
    path('chat/messages/', views.get_messages_ajax, name='get_messages_ajax'),
    path('chat/messages/new/', views.get_new_messages_ajax, name='get_new_messages_ajax'),
    path('chat/messages/delete/', views.delete_message_ajax, name='delete_message_ajax'),
    
    # Legacy Message Routes (for backward compatibility)
    path('messages/', views.message_list, name='message_list'),
    path('messages/compose/', views.compose_message, name='compose_message'),
    path('messages/<int:message_id>/', views.message_detail, name='message_detail'),
    path('messages/<int:message_id>/reply/', views.reply_message, name='reply_message'),
    path('messages/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('messages/sent/', views.sent_messages, name='sent_messages'),
    path('messages/<int:message_id>/mark-read/', views.mark_message_read, name='mark_message_read'),
    path('messages/search-recipients/', views.search_recipients, name='search_recipients'),
    
    # Announcements
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/<int:announcement_id>/', views.announcement_detail, name='announcement_detail'),
    path('announcements/<int:announcement_id>/edit/', views.edit_announcement, name='edit_announcement'),
    path('announcements/<int:announcement_id>/delete/', views.delete_announcement, name='delete_announcement'),
    
    # Events
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('events/calendar/', views.event_calendar, name='event_calendar'),
    
    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/create/', views.create_notification, name='create_notification'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    
    # Admin Broadcasting
    path('broadcast/', views.broadcast_message, name='broadcast_message'),
    path('broadcast/class/<int:classroom_id>/', views.broadcast_to_class, name='broadcast_to_class'),
    path('broadcast/teachers/', views.broadcast_to_teachers, name='broadcast_to_teachers'),
    path('broadcast/students/', views.broadcast_to_students, name='broadcast_to_students'),
    path('broadcast/parents/', views.broadcast_to_parents, name='broadcast_to_parents'),
    
    # API for notifications and messages (AJAX)
    path('api/notifications/count/', views.notification_count, name='notification_count'),
    path('api/notifications/list/', views.notification_api_list, name='notification_api_list'),
    path('api/messages/', views.api_get_messages, name='api_get_messages'),
    path('api/messages/count/', views.message_count, name='message_count'),
    
    # Category-specific notification counts
    path('api/notifications/materials/count/', views.material_notification_count, name='material_notification_count'),
    path('api/notifications/assignments/count/', views.assignment_notification_count, name='assignment_notification_count'),
    path('api/notifications/quizzes/count/', views.quiz_notification_count, name='quiz_notification_count'),
]