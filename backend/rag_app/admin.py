from django.contrib import admin
from .models import User, Project, Module, Document
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
    list_display = ('title', 'file_path', 'module')
    search_fields = ('title', 'module__name', 'uploaded_by__username')
    ordering = ('title',)


