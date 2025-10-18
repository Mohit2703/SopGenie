from rest_framework import serializers
from .models import VectorDBTask, ModuleVectorStore, QueryLog, Question, Answer, Rating

class VectorDBTaskSerializer(serializers.ModelSerializer):
    # Access module through module_vector_store relationship
    module_id = serializers.IntegerField(source='module_vector_store.module.id', read_only=True)
    module_name = serializers.CharField(source='module_vector_store.module.name', read_only=True)
    project_name = serializers.CharField(source='module_vector_store.module.project.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    duration = serializers.ReadOnlyField()
    is_running = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    
    class Meta:
        model = VectorDBTask
        fields = [
            'id', 'task_id', 'module_vector_store', 'module_id', 'module_name', 
            'project_name', 'status', 'progress_percentage', 'current_step',
            'current_document', 'total_documents', 'processed_documents',
            'successful_documents', 'failed_documents', 'result', 'error_message',
            'created_at', 'started_at', 'completed_at', 'duration', 'is_running',
            'is_completed', 'chunk_size', 'chunk_overlap', 'embedding_model', 
            'created_by_username'
        ]
        read_only_fields = [
            'id', 'task_id', 'status', 'progress_percentage', 'current_step',
            'current_document', 'total_documents', 'processed_documents',
            'successful_documents', 'failed_documents', 'result', 'error_message',
            'created_at', 'started_at', 'completed_at'
        ]

class ModuleVectorStoreSerializer(serializers.ModelSerializer):
    module_id = serializers.IntegerField(source='module.id', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)
    project_name = serializers.CharField(source='module.project.name', read_only=True)
    recent_tasks = VectorDBTaskSerializer(many=True, read_only=True, source='tasks')
    
    class Meta:
        model = ModuleVectorStore
        fields = [
            'id', 'module', 'module_id', 'module_name', 'project_name',
            'collection_name', 'persistence_directory', 'status',
            'embedding_model', 'embedding_dimension', 'chunk_size',
            'chunk_overlap', 'document_count', 'total_chunks', 'total_tokens',
            'created_at', 'updated_at', 'last_indexed_at', 'config',
            'recent_tasks'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_indexed_at',
            'document_count', 'total_chunks', 'total_tokens'
        ]

class QueryLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    module_name = serializers.CharField(source='module.name', read_only=True)
    project_name = serializers.CharField(source='module.project.name', read_only=True)
    
    class Meta:
        model = QueryLog
        fields = [
            'id', 'user', 'module', 'user_username', 'module_name', 'project_name',
            'query_text', 'query_hash', 'response_text', 'retrieved_chunks',
            'similarity_scores', 'retrieval_time_ms', 'generation_time_ms',
            'total_time_ms', 'user_rating', 'user_feedback', 'metadata',
            'created_at'
        ]
        read_only_fields = ['id', 'query_hash', 'created_at']

class VectorDBCreateSerializer(serializers.Serializer):
    """Serializer for creating module vector database"""
    module_id = serializers.IntegerField()
    force_recreate = serializers.BooleanField(default=False, required=False)
    chunk_size = serializers.IntegerField(default=1000, min_value=100, max_value=5000, required=False)
    chunk_overlap = serializers.IntegerField(default=200, min_value=0, max_value=1000, required=False)
    embedding_model = serializers.CharField(
        default='all-MiniLM-L6-v2',
        max_length=255,
        required=False
    )
    
    def validate(self, data):
        """Validate chunk_overlap is less than chunk_size"""
        chunk_size = data.get('chunk_size', 1000)
        chunk_overlap = data.get('chunk_overlap', 200)
        
        if chunk_overlap >= chunk_size:
            raise serializers.ValidationError({
                'chunk_overlap': 'chunk_overlap must be less than chunk_size'
            })
        return data

class RAGQuerySerializer(serializers.Serializer):
    """Serializer for RAG queries"""
    query = serializers.CharField(max_length=2000)
    module_id = serializers.IntegerField()
    max_results = serializers.IntegerField(default=5, min_value=1, max_value=20, required=False)
    similarity_threshold = serializers.FloatField(
        default=0.7, 
        min_value=0.0, 
        max_value=1.0,
        required=False
    )
    include_metadata = serializers.BooleanField(default=True, required=False)
    
    def validate_query(self, value):
        """Validate query is not empty after stripping"""
        if not value or not value.strip():
            raise serializers.ValidationError("Query cannot be empty")
        return value.strip()
    
    def validate_module_id(self, value):
        """Validate module exists"""
        from rag_app.models import Module
        if not Module.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Module does not exist or is not active")
        return value

class RAGResponseSerializer(serializers.Serializer):
    """Serializer for RAG response"""
    query = serializers.CharField()
    answer = serializers.CharField()
    sources = serializers.ListField(child=serializers.DictField())
    retrieval_time_ms = serializers.IntegerField()
    generation_time_ms = serializers.IntegerField()
    total_time_ms = serializers.IntegerField()
    metadata = serializers.DictField()

class QueryFeedbackSerializer(serializers.Serializer):
    """Serializer for query feedback"""
    query_log_id = serializers.UUIDField()
    user_rating = serializers.IntegerField(min_value=1, max_value=5)
    user_feedback = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_query_log_id(self, value):
        """Validate query log exists"""
        if not QueryLog.objects.filter(id=value).exists():
            raise serializers.ValidationError("Query log does not exist")
        return value


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = "__all__"

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = "__all__"
        read_only_fields = ['id', 'created_at']
        

