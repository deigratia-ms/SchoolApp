from django.contrib import admin
from .models import DashboardPreference, Widget, UserWidget, SidebarMenu

@admin.register(DashboardPreference)
class DashboardPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'color_scheme', 'sidebar_collapsed', 'created_at')
    list_filter = ('theme', 'color_scheme', 'sidebar_collapsed')
    search_fields = ('user__username',)


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ('name', 'widget_type', 'default_position', 'default_size', 'is_active')
    list_filter = ('widget_type', 'is_active', 'visible_to_admin', 'visible_to_teacher', 'visible_to_student', 'visible_to_parent')
    search_fields = ('name', 'description')


@admin.register(UserWidget)
class UserWidgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'widget', 'position', 'size', 'is_visible')
    list_filter = ('size', 'is_visible', 'widget__widget_type')
    search_fields = ('user__username', 'widget__name')


@admin.register(SidebarMenu)
class SidebarMenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'icon', 'user_role', 'parent', 'order', 'is_active')
    list_filter = ('user_role', 'is_active')
    search_fields = ('name', 'url')
    list_editable = ('order', 'is_active')