from rest_framework import serializers
from .models import User, Project, Module, Document

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'name', 
            'role', 'organization', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']

class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer with statistics"""
    projects_count = serializers.SerializerMethodField()
    modules_count = serializers.SerializerMethodField()
    documents_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'name', 'role', 
            'organization', 'date_joined', 'last_login',
            'projects_count', 'modules_count', 'documents_count'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_projects_count(self, obj):
        """Count admin projects"""
        return obj.admin_projects.count()
    
    def get_modules_count(self, obj):
        """Count created modules"""
        return obj.created_modules.count()
    
    def get_documents_count(self, obj):
        """Count uploaded documents"""
        return obj.uploaded_documents.count()

class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model"""
    users = UserSerializer(many=True, read_only=True)
    admin = UserSerializer(read_only=True)
    admin_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='admin',
        required=False,
        write_only=True
    )
    modules_count = serializers.SerializerMethodField()
    total_documents = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'created_at', 'updated_at',
            'users', 'admin', 'admin_id', 'modules_count', 'total_documents'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_modules_count(self, obj):
        """Count active modules"""
        return obj.modules.filter(is_active=True).count()
    
    def get_total_documents(self, obj):
        """Count total documents across all modules"""
        return Document.objects.filter(
            module__project=obj,
            active=True
        ).count()

class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project lists"""
    admin_username = serializers.CharField(source='admin.username', read_only=True)
    modules_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'admin_username',
            'modules_count', 'created_at', 'updated_at'
        ]
    
    def get_modules_count(self, obj):
        return obj.modules.filter(is_active=True).count()

class ModuleSerializer(serializers.ModelSerializer):
    """Serializer for Module model"""
    created_by = UserSerializer(read_only=True)
    project = ProjectListSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        source='project',
        write_only=True
    )
    documents_count = serializers.SerializerMethodField()
    has_vector_store = serializers.SerializerMethodField()
    vector_store_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Module
        fields = [
            'id', 'name', 'description', 'is_active', 'folder_path',
            'created_at', 'updated_at', 'project', 'project_id',
            'created_by', 'documents_count', 'has_vector_store',
            'vector_store_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_documents_count(self, obj):
        """Count active documents in module"""
        return obj.documents.filter(active=True).count()
    
    def get_has_vector_store(self, obj):
        """Check if module has a vector store"""
        return hasattr(obj, 'vector_store')
    
    def get_vector_store_status(self, obj):
        """Get vector store status if exists"""
        if hasattr(obj, 'vector_store'):
            return obj.vector_store.status
        return None

class ModuleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for module lists"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    documents_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Module
        fields = [
            'id', 'name', 'description', 'is_active',
            'project_name', 'created_by_username',
            'documents_count', 'created_at'
        ]
    
    def get_documents_count(self, obj):
        return obj.documents.filter(active=True).count()

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    uploaded_by = UserSerializer(read_only=True)
    uploaded_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='uploaded_by',
        write_only=True,
        required=False
    )
    module_name = serializers.CharField(source='module.name', read_only=True)
    project_name = serializers.CharField(source='module.project.name', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.ReadOnlyField()
    file_extension = serializers.ReadOnlyField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'file', 'file_path', 'file_url',
            'file_size', 'file_size_display', 'file_type', 'file_extension',
            'module', 'module_name', 'project_name',
            'uploaded_by', 'uploaded_by_id',
            'active', 'uploaded_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'file_type', 
            'uploaded_at', 'updated_at'
        ]
    
    def get_file_url(self, obj):
        """Get file URL"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def validate_file(self, value):
        """Validate file upload"""
        if value:
            # Check file size (e.g., max 50MB)
            max_size = 50 * 1024 * 1024  # 50MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"File size cannot exceed 50MB. Your file is {value.size / (1024 * 1024):.2f}MB"
                )
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx']
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in allowed_extensions:
                raise serializers.ValidationError(
                    f"File type {ext} is not allowed. Allowed types: {', '.join(allowed_extensions)}"
                )
        
        return value

class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document lists"""
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    file_size_display = serializers.ReadOnlyField()
    file_extension = serializers.ReadOnlyField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'file_size_display', 'file_extension',
            'uploaded_by_username', 'uploaded_at', 'active'
        ]

class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer specifically for document upload"""
    module_id = serializers.PrimaryKeyRelatedField(
        queryset=Module.objects.filter(is_active=True),
        source='module',
        write_only=True
    )
    
    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'module_id']
    
    def validate_file(self, value):
        """Validate file upload"""
        if not value:
            raise serializers.ValidationError("File is required")
        
        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size cannot exceed 50MB"
            )
        
        # Check file extension
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx', '.pptx']
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type {ext} is not supported"
            )
        
        return value
    
    def create(self, validated_data):
        """Create document with auto-generated title if not provided"""
        if not validated_data.get('title'):
            # Use filename as title
            file = validated_data.get('file')
            if file:
                validated_data['title'] = os.path.splitext(file.name)[0]
        
        # Set uploaded_by from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['uploaded_by'] = request.user
        
        return super().create(validated_data)

class DocumentBulkUploadSerializer(serializers.Serializer):
    """Serializer for bulk document upload"""
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False
    )
    module_id = serializers.IntegerField()
    
    def validate_module_id(self, value):
        """Validate module exists and is active"""
        if not Module.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError
