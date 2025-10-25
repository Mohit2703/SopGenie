from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from .models import User, Project, Module, Document, ProjectMember
import os

@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    """Admin for Project Members"""
    list_display = ['project_link', 'user_link', 'role', 'joined_at', 'updated_at']
    list_filter = ['role', 'joined_at', 'updated_at']
    search_fields = ['project__name', 'user__username', 'role']
    ordering = ['-joined_at']
    
    def project_link(self, obj):
        """Display project with link"""
        url = reverse('admin:rag_app_project_change', args=[obj.project.id])
        return format_html('<a href="{}">{}</a>', url, obj.project.name)
    project_link.short_description = 'Project'
    
    def user_link(self, obj):
        """Display user with link"""
        url = reverse('admin:rag_app_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Enhanced User Admin"""
    list_display = [
        'username', 'email', 'name', 'role', 
        'organization', 'projects_count', 'modules_count',
        'is_active', 'date_joined'
    ]
    list_filter = ['role', 'organization', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'name', 'organization']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('name', 'email', 'role', 'organization')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'name', 'role', 'organization', 'password1', 'password2'),
        }),
    )
    
    def projects_count(self, obj):
        """Count admin projects"""
        count = obj.admin_projects.count()
        if count > 0:
            url = f"{reverse('admin:rag_app_project_changelist')}?admin__id__exact={obj.id}"
            return format_html('<a href="{}">{} projects</a>', url, count)
        return '0 projects'
    projects_count.short_description = 'Projects'
    
    def modules_count(self, obj):
        """Count created modules"""
        count = obj.created_modules.count()
        if count > 0:
            url = f"{reverse('admin:rag_app_module_changelist')}?created_by__id__exact={obj.id}"
            return format_html('<a href="{}">{} modules</a>', url, count)
        return '0 modules'
    modules_count.short_description = 'Modules'

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Enhanced Project Admin"""
    list_display = [
        'name', 'admin_link', 'modules_count', 
        'documents_count', 'users_display', 'created_at'
    ]
    list_filter = ['created_at', 'updated_at', 'admin']
    search_fields = ['name', 'description', 'admin__username']
    ordering = ['-created_at']
    filter_horizontal = ['users']
    readonly_fields = [
        'created_at', 'updated_at', 'modules_count', 
        'documents_count', 'total_file_size'
    ]
    
    fieldsets = (
        ('Project Information', {
            'fields': ('name', 'description', 'admin')
        }),
        ('Access Control', {
            'fields': ('users',)
        }),
        ('Statistics', {
            'fields': ('modules_count', 'documents_count', 'total_file_size'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries with prefetch"""
        qs = super().get_queryset(request)
        return qs.select_related('admin').prefetch_related('users', 'modules')
    
    def admin_link(self, obj):
        """Display admin with link"""
        url = reverse('admin:rag_app_user_change', args=[obj.admin.id])
        return format_html('<a href="{}">{}</a>', url, obj.admin.username)
    admin_link.short_description = 'Admin'
    
    def modules_count(self, obj):
        """Count modules in project"""
        count = obj.modules.filter(is_active=True).count()
        if count > 0:
            url = f"{reverse('admin:rag_app_module_changelist')}?project__id__exact={obj.id}"
            return format_html('<a href="{}">{} modules</a>', url, count)
        return '0 modules'
    modules_count.short_description = 'Modules'
    
    def documents_count(self, obj):
        """Count total documents"""
        count = Document.objects.filter(
            module__project=obj, 
            active=True
        ).count()
        return f"{count} documents"
    documents_count.short_description = 'Documents'
    
    def users_display(self, obj):
        """Display user count"""
        count = obj.users.count()
        return format_html(
            '<span title="{}">{} users</span>',
            ', '.join([u.username for u in obj.users.all()[:5]]),
            count
        )
    users_display.short_description = 'Users'
    
    def total_file_size(self, obj):
        """Calculate total file size"""
        from django.db.models import Sum
        total = Document.objects.filter(
            module__project=obj,
            active=True
        ).aggregate(total=Sum('file_size'))['total'] or 0
        
        if total < 1024:
            return f"{total} bytes"
        elif total < 1024*1024:
            return f"{total/1024:.1f} KB"
        elif total < 1024*1024*1024:
            return f"{total/(1024*1024):.1f} MB"
        else:
            return f"{total/(1024*1024*1024):.2f} GB"
    total_file_size.short_description = 'Total File Size'

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    """Enhanced Module Admin"""
    list_display = [
        'name', 'project_link', 'is_active_badge',
        'documents_count', 'vector_store_status',
        'created_by_link', 'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'project']
    search_fields = [
        'name', 'description', 
        'project__name', 'created_by__username'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'documents_count',
        'vector_store_info', 'folder_path'
    ]
    
    fieldsets = (
        ('Module Information', {
            'fields': ('name', 'description', 'project', 'is_active')
        }),
        ('Creator', {
            'fields': ('created_by',)
        }),
        ('Vector Store', {
            'fields': ('vector_store_info',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('documents_count', 'folder_path'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('project', 'created_by').prefetch_related('documents')
    
    def project_link(self, obj):
        """Display project with link"""
        url = reverse('admin:rag_app_project_change', args=[obj.project.id])
        return format_html('<a href="{}">{}</a>', url, obj.project.name)
    project_link.short_description = 'Project'
    
    def is_active_badge(self, obj):
        """Display active status as badge"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    
    def documents_count(self, obj):
        """Count documents in module"""
        count = obj.documents.filter(active=True).count()
        if count > 0:
            url = f"{reverse('admin:rag_app_document_changelist')}?module__id__exact={obj.id}"
            return format_html('<a href="{}">{} documents</a>', url, count)
        return '0 documents'
    documents_count.short_description = 'Documents'
    
    def vector_store_status(self, obj):
        """Display vector store status"""
        if hasattr(obj, 'vector_store'):
            vs = obj.vector_store
            colors = {
                'empty': '#6c757d',
                'indexing': '#ffc107',
                'ready': '#28a745',
                'error': '#dc3545'
            }
            color = colors.get(vs.status, '#6c757d')
            url = reverse('admin:vectordb_modulevectorstore_change', args=[vs.id])
            return format_html(
                '<a href="{}" style="background-color: {}; color: white; '
                'padding: 3px 8px; border-radius: 3px; text-decoration: none;">{}</a>',
                url, color, vs.status.upper()
            )
        return format_html('<span style="color: #999;">No vector store</span>')
    vector_store_status.short_description = 'Vector Store'
    
    def created_by_link(self, obj):
        """Display creator with link"""
        url = reverse('admin:rag_app_user_change', args=[obj.created_by.id])
        return format_html('<a href="{}">{}</a>', url, obj.created_by.username)
    created_by_link.short_description = 'Created By'
    
    def vector_store_info(self, obj):
        """Display detailed vector store information"""
        if hasattr(obj, 'vector_store'):
            vs = obj.vector_store
            url = reverse('admin:vectordb_modulevectorstore_change', args=[vs.id])
            return format_html(
                '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">'
                '<p><strong>Status:</strong> {}</p>'
                '<p><strong>Documents:</strong> {}</p>'
                '<p><strong>Chunks:</strong> {:,}</p>'
                '<p><strong>Collection:</strong> {}</p>'
                '<p><a href="{}">View Vector Store →</a></p>'
                '</div>',
                vs.status, vs.document_count, vs.total_chunks,
                vs.collection_name, url
            )
        return 'No vector store created yet'
    vector_store_info.short_description = 'Vector Store Details'
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by to current user if not set"""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Enhanced Document Admin"""
    list_display = [
        'title', 'module_link', 'file_preview',
        'file_size_badge', 'file_type_badge',
        'active_badge', 'uploaded_by_link', 'uploaded_at'
    ]
    list_filter = [
        'active', 'file_type', 'uploaded_at', 
        'module', 'uploaded_by'
    ]
    search_fields = [
        'title', 'module__name', 
        'uploaded_by__username', 'file'
    ]
    readonly_fields = [
        'uploaded_at', 'updated_at', 'file_size',
        'file_type', 'file_size_display', 'file_preview_large',
        'file_path_display', 'project_name'
    ]
    ordering = ['-uploaded_at']
    
    fieldsets = (
        ('Document Information', {
            'fields': ('title', 'file', 'module', 'active')
        }),
        ('File Details', {
            'fields': (
                'file_size_display', 'file_type', 
                'file_preview_large', 'file_path_display'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'project_name', 'uploaded_by', 
                'uploaded_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('module', 'module__project', 'uploaded_by')
    
    def module_link(self, obj):
        """Display module with link"""
        url = reverse('admin:rag_app_module_change', args=[obj.module.id])
        return format_html(
            '<a href="{}">{}</a><br>'
            '<small style="color: #666;">{}</small>',
            url, obj.module.name, obj.module.project.name
        )
    module_link.short_description = 'Module'
    
    def file_preview(self, obj):
        """Display file with icon and download link"""
        if obj.file:
            icons = {
                '.pdf': '📄',
                '.doc': '📝',
                '.docx': '📝',
                '.txt': '📃',
                '.csv': '📊',
                '.xlsx': '📊',
                '.pptx': '📊'
            }
            ext = os.path.splitext(obj.file.name)[1].lower()
            icon = icons.get(ext, '📎')
            
            return format_html(
                '{} <a href="{}" target="_blank" download>{}</a>',
                icon, obj.file.url, os.path.basename(obj.file.name)
            )
        return "No file"
    file_preview.short_description = "File"
    
    def file_preview_large(self, obj):
        """Large file preview for detail page"""
        if obj.file:
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">'
                '<p><strong>File:</strong> {}</p>'
                '<p><strong>URL:</strong> <a href="{}" target="_blank">{}</a></p>'
                '<p><a href="{}" class="button" download>Download File</a></p>'
                '</div>',
                obj.file.name, obj.file.url, obj.file.url, obj.file.url
            )
        return "No file"
    file_preview_large.short_description = "File Preview"
    
    def file_size_badge(self, obj):
        """Display file size as badge"""
        if obj.file_size:
            size_display = obj.file_size_display
            if 'MB' in size_display:
                color = '#007bff'
            elif 'KB' in size_display:
                color = '#28a745'
            else:
                color = '#6c757d'
            
            return format_html(
                '<span style="background-color: {}; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                color, size_display
            )
        return "N/A"
    file_size_badge.short_description = "Size"
    
    def file_type_badge(self, obj):
        """Display file type as badge"""
        if obj.file_type:
            return format_html(
                '<span style="background-color: #6c757d; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                obj.file_type.upper().replace('.', '')
            )
        return "N/A"
    file_type_badge.short_description = "Type"
    
    def active_badge(self, obj):
        """Display active status as badge"""
        if obj.active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px;">Inactive</span>'
        )
    active_badge.short_description = 'Status'
    
    def uploaded_by_link(self, obj):
        """Display uploader with link"""
        url = reverse('admin:rag_app_user_change', args=[obj.uploaded_by.id])
        return format_html('<a href="{}">{}</a>', url, obj.uploaded_by.username)
    uploaded_by_link.short_description = 'Uploaded By'
    
    def file_path_display(self, obj):
        """Display full file path"""
        if obj.file:
            return obj.file.path
        return "No file"
    file_path_display.short_description = "File Path"
    
    def project_name(self, obj):
        """Display project name"""
        return obj.module.project.name
    project_name.short_description = "Project"
    
    def save_model(self, request, obj, form, change):
        """Auto-set uploaded_by to current user if not set"""
        if not change:  # Only on creation
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def mark_as_active(self, request, queryset):
        """Bulk action to mark documents as active"""
        updated = queryset.update(active=True)
        self.message_user(request, f"{updated} documents marked as active.")
    mark_as_active.short_description = "Mark selected documents as active"
    
    def mark_as_inactive(self, request, queryset):
        """Bulk action to mark documents as inactive"""
        updated = queryset.update(active=False)
        self.message_user(request, f"{updated} documents marked as inactive.")
    mark_as_inactive.short_description = "Mark selected documents as inactive"
