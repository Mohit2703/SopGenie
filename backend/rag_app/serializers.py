from rest_framework import serializers
from .models import User, Project, Module, Document

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]  # adjust fields as needed

class ProjectSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True, read_only=True)   # nested users
    admin = UserSerializer(read_only=True)              # nested admin

    class Meta:
        model = Project
        fields = [
            "id", "name", "description", "persist_directory",
            "created_at", "updated_at", "users", "admin"
        ]

class ModuleSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)  # nested created_by
    project = ProjectSerializer(read_only=True)  # nested project
    class Meta:
        model = Module
        fields = "__all__"
class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.ReadOnlyField()
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'file', 'file_url', 'file_size', 'file_size_mb', 
            'file_type', 'uploaded_by', 'uploaded_by_username', 
            'uploaded_at', 'updated_at', 'active'
        ]
        read_only_fields = ['uploaded_by', 'file_size', 'file_type']
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
