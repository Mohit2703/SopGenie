from django.contrib import admin
from .models import User, Project, Module, Document
from django.utils.html import format_html
from django.urls import reverse
# Register your models here.


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'organization', 'name', 'first_name', 'last_name')
    list_filter = ('role', 'organization')
    search_fields = ('username', 'email', 'organization', 'name')
    ordering = ('email','username',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'persist_directory', 'admin', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'admin__username')
    ordering = ('name', '-created_at',)

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'description', 'created_by', 'is_active', 'folder_path', 'collection_name', 'created_at', 'updated_at')
    list_filter = ('is_active', 'project')
    search_fields = ('name', 'project__name', 'created_by__username')
    ordering = ('name', '-created_at',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'module', 
        'file_link',
        'file_size_display', 
        'uploaded_by', 
        'uploaded_at',
        'active'
    ]
    list_filter = [
        'active', 
        'uploaded_at', 
        'module', 
        'uploaded_by'
    ]
    search_fields = [
        'title', 
        'module__name', 
        'uploaded_by__username'
    ]
    readonly_fields = [
        'uploaded_at', 
        'updated_at', 
        'file_size_display',
        'file_url_display'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'file', 'module', 'active')
        }),
        ('File Information', {
            'fields': ('file_size_display', 'file_url_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uploaded_by', 'uploaded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_link(self, obj):
        """Display file as a clickable link"""
        if obj.file:
            url = obj.file.url
            return format_html(
                '<a href="{}" target="_blank">{}</a>', 
                url, 
                obj.file.name.split('/')[-1]
            )
        return "No file"
    file_link.short_description = "File"
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if obj.file:
            size = obj.file.size
            if size < 1024:
                return f"{size} bytes"
            elif size < 1024*1024:
                return f"{size/1024:.1f} KB"
            else:
                return f"{size/(1024*1024):.1f} MB"
        return "N/A"
    file_size_display.short_description = "File Size"
    
    def file_url_display(self, obj):
        """Display full file URL"""
        if obj.file:
            return obj.file.url
        return "No file"
    file_url_display.short_description = "File URL"
    
    def save_model(self, request, obj, form, change):
        """Auto-set uploaded_by to current user if not set"""
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


