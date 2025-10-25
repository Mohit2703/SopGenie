from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, BooleanField, TextField
from django.urls import reverse
from django.db import models
from django.utils import timezone
import uuid
import os

# Create your models here.
class User(AbstractUser):
    ROLE_CHOICES = [
        ("Client", "Client"),
        ("Normal User", "Normal User"),
    ]

    #: First and last name do not cover name patterns around the globe
    name = CharField("Name of User", blank=True, max_length=255)
    role = CharField("Role", max_length=128, default="Normal User", choices=ROLE_CHOICES)
    organization = CharField("Organization", max_length=128, null=True)
    first_name = None  # type: ignore
    last_name = None  # type: ignore

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})
    
class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    users = models.ManyToManyField(User, related_name='project_users', blank=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_projects')
    def _str_(self):
        return self.name
    
class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=50, choices=[('admin', 'Admin'), ('viewer', 'Viewer'), ('editor', 'Editor'), ('owner', 'Owner')], default='viewer')
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('project', 'user')
    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.role})"

class Module(models.Model):
    name = models.CharField(max_length=255)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='modules')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_modules')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    folder_path = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _str_(self):
        return self.name

def upload_to_project_module_folder(instance, filename):
    """
    Generate file path: documents/projects/{project_id}/modules/{module_id}/{uuid}_{filename}
    """
    # Clean filename to prevent issues
    cleaned_filename = filename.replace(' ', '_')
    
    # Generate unique filename to prevent conflicts
    ext = cleaned_filename.split('.')[-1].lower()
    name = '.'.join(cleaned_filename.split('.')[:-1])
    unique_filename = f"{uuid.uuid4().hex[:8]}_{name}.{ext}"
    
    # Create path structure: documents/projects/PROJECT_ID/modules/MODULE_ID/
    project_id = instance.module.project.id
    module_id = instance.module.id

    return f"documents/projects_{project_id}/modules_{module_id}/{unique_filename}"

class Document(models.Model):
    title = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    
    # Updated to use the new upload function
    file = models.FileField(
        upload_to=upload_to_project_module_folder, 
        blank=True, 
        null=True,
        help_text="Upload files to project/module specific folders"
    )
    
    module = models.ForeignKey('Module', on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Make these fields nullable so existing records aren't affected
    file_size = models.BigIntegerField(blank=True, null=True, help_text="File size in bytes")
    file_type = models.CharField(max_length=10, blank=True, null=True, help_text="File extension")
    
    class Meta:
        db_table = 'rag_app_document'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['module', 'active']),
            models.Index(fields=['uploaded_by', '-uploaded_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-populate file_size and file_type if file exists
        if self.file:
            try:
                self.file_size = self.file.size
                self.file_type = os.path.splitext(self.file.name)[1].lower()
            except Exception as e:
                print(f"Error getting file info: {e}")
                pass
        super().save(*args, **kwargs)
    
    @property
    def file_size_display(self):
        """Return file size in human readable format"""
        if self.file_size:
            size = self.file_size
            if size < 1024:
                return f"{size} bytes"
            elif size < 1024*1024:
                return f"{size/1024:.1f} KB"
            else:
                return f"{size/(1024*1024):.1f} MB"
        return "Unknown"
    
    @property
    def file_extension(self):
        """Return file extension"""
        return self.file_type or (os.path.splitext(self.file.name)[1] if self.file else "")
    
    @property
    def project_name(self):
        """Get project name through module"""
        return self.module.project.name if self.module and self.module.project else None
    
    @property
    def folder_path(self):
        """Get the folder path where file is stored"""
        if self.file:
            return os.path.dirname(self.file.path)
        return None

