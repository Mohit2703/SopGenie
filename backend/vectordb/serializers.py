from rest_framework import serializers
from .models import VectorDBTask, ModuleVectorStore, QueryLog


class VectorDBTaskSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='module.name', read_only=True)
    project_name = serializers.CharField(source='module.project.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    duration = serializers.ReadOnlyField()
    is_running = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    
    class Meta:
        model = VectorDBTask
        fields = [
            'id', 'task_id', 'status', 'progress_percentage', 'current_step',
            'current_document', 'total_documents', 'processed_documents',
            'successful_documents', 'failed_documents', 'result', 'error_message',
            'created_at', 'started_at', 'completed_at', 'duration', 'is_running',
            'is_completed', 'force_recreate', 'chunk_size', 'chunk_overlap',
            'embedding_model', 'module_name', 'project_name', 'created_by_username'
        ]
        read_only_fields = [
            'id', 'task_id', 'status', 'progress_percentage', 'current_step',
            'current_document', 'total_documents', 'processed_documents',
            'successful_documents', 'failed_documents', 'result', 'error_message',
            'created_at', 'started_at', 'completed_at'
        ]


class ModuleVectorStoreSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='module.name', read_only=True)
    project_name = serializers.CharField(source='module.project.name', read_only=True)
    
    class Meta:
        model = ModuleVectorStore
        fields = [
            'id', 'collection_name', 'vector_store_type', 'status',
            'embedding_model', 'embedding_dimension', 'chunk_size',
            'chunk_overlap', 'document_count', 'total_chunks', 'total_tokens',
            'created_at', 'updated_at', 'last_indexed_at', 'config',
            'module_name', 'project_name'
        ]


class QueryLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)
    
    class Meta:
        model = QueryLog
        fields = [
            'id', 'query_text', 'response_text', 'retrieved_chunks',
            'similarity_scores', 'retrieval_time_ms', 'generation_time_ms',
            'total_time_ms', 'user_rating', 'user_feedback', 'metadata',
            'created_at', 'user_username', 'module_name'
        ]


class VectorDBCreateSerializer(serializers.Serializer):
    """Serializer for creating module vector database"""
    module_id = serializers.IntegerField()
    force_recreate = serializers.BooleanField(default=False)
    chunk_size = serializers.IntegerField(default=1000, min_value=100, max_value=5000)
    chunk_overlap = serializers.IntegerField(default=200, min_value=0, max_value=1000)
    embedding_model = serializers.CharField(required=False)
    
    def validate(self, data):
        """Validate chunk_overlap is less than chunk_size"""
        if data.get('chunk_overlap', 0) >= data.get('chunk_size', 1000):
            raise serializers.ValidationError(
                "chunk_overlap must be less than chunk_size"
            )
        return data


class RAGQuerySerializer(serializers.Serializer):
    """Serializer for RAG queries"""
    query = serializers.CharField(max_length=2000)
    module_id = serializers.IntegerField()
    max_results = serializers.IntegerField(default=5, min_value=1, max_value=20)
    similarity_threshold = serializers.FloatField(default=0.7, min_value=0.0, max_value=1.0)
    include_metadata = serializers.BooleanField(default=True)
    
    def validate_query(self, value):
        """Validate query is not empty after stripping"""
        if not value.strip():
            raise serializers.ValidationError("Query cannot be empty")
        return value.strip()


class RAGResponseSerializer(serializers.Serializer):
    """Serializer for RAG response"""
    query = serializers.CharField()
    answer = serializers.CharField()
    sources = serializers.ListField()
    retrieval_time_ms = serializers.IntegerField()
    generation_time_ms = serializers.IntegerField()
    total_time_ms = serializers.IntegerField()
    metadata = serializers.DictField()
