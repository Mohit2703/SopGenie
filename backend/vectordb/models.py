from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class VectorDBTask(models.Model):
    """Track vector database creation tasks at module level"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.CharField(max_length=255, unique=True, db_index=True)

    module_vector_store = models.ForeignKey(
        'ModuleVectorStore', 
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    
    # Task details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    current_step = models.CharField(max_length=255, blank=True)
    current_document = models.CharField(max_length=255, blank=True)  # Currently processing document
    
    # Progress tracking
    total_documents = models.IntegerField(default=0)
    processed_documents = models.IntegerField(default=0)
    successful_documents = models.IntegerField(default=0)
    failed_documents = models.IntegerField(default=0)
    
    # Results and metadata
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Timing information
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # User who initiated the task
    created_by = models.ForeignKey(
        'rag_app.User', 
        on_delete=models.CASCADE,
        related_name='vector_tasks'
    )
    
    # Processing options
    chunk_size = models.IntegerField(default=1000)
    chunk_overlap = models.IntegerField(default=200)
    embedding_model = models.CharField(max_length=255, blank=True)
    class Meta:
        db_table = 'vectordb_task'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['module_vector_store', '-created_at']),  # Fixed
            models.Index(fields=['created_by', '-created_at']),
        ]
    
    def __str__(self):
        # Fixed to use module_vector_store
        return f"VectorDB Task {self.task_id} - Module: {self.module_vector_store.module.name} - {self.status}"
    
    @property
    def duration(self):
        """Calculate task duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None
    
    @property
    def is_running(self):
        """Check if task is currently running"""
        return self.status in ['pending', 'processing']
    
    @property
    def is_completed(self):
        """Check if task is completed (success or failure)"""
        return self.status in ['completed', 'failed', 'cancelled']
    
    def mark_started(self, total_docs=0):
        """Mark task as started"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.total_documents = total_docs
        self.save(update_fields=['status', 'started_at', 'total_documents'])
    
    def update_progress(self, current_doc_name="", progress_pct=None):
        """Update task progress"""
        if progress_pct is not None:
            self.progress_percentage = progress_pct
        if current_doc_name:
            self.current_document = current_doc_name
        self.save(update_fields=['progress_percentage', 'current_document'])
    
    def increment_processed(self, success=True):
        """Increment processed document count"""
        self.processed_documents += 1
        if success:
            self.successful_documents += 1
        else:
            self.failed_documents += 1
        
        # Update progress percentage
        if self.total_documents > 0:
            self.progress_percentage = int((self.processed_documents / self.total_documents) * 100)
        
        self.save(update_fields=[
            'processed_documents', 'successful_documents', 
            'failed_documents', 'progress_percentage'
        ])
    
    def mark_completed(self, result=None):
        """Mark task as completed"""
        self.status = 'completed'
        self.progress_percentage = 100
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save(update_fields=['status', 'progress_percentage', 'completed_at', 'result'])
    
    def mark_failed(self, error_message):
        """Mark task as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])


class ModuleVectorStore(models.Model):
    """Vector store information for each module"""
    
    STATUS_CHOICES = [
        ('empty', 'Empty'),
        ('indexing', 'Indexing'),
        ('ready', 'Ready'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.OneToOneField(
        'rag_app.Module', 
        on_delete=models.CASCADE, 
        related_name='vector_store'
    )
    
    # Vector store details
    collection_name = models.CharField(max_length=255, unique=True)
    persistence_directory = models.CharField(max_length=512, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='empty')
    
    # Configuration
    embedding_model = models.CharField(max_length=255, default='sentence-transformers/all-MiniLM-L6-v2')
    embedding_dimension = models.IntegerField(default=384)
    chunk_size = models.IntegerField(default=1000)
    chunk_overlap = models.IntegerField(default=200)
    
    # Statistics
    document_count = models.IntegerField(default=0)
    total_chunks = models.IntegerField(default=0)
    total_tokens = models.BigIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_indexed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional configuration
    config = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'vectordb_module_store'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"VectorStore for Module: {self.module.name} ({self.status})"
    
    def update_stats(self, doc_count=None, chunk_count=None, token_count=None):
        """Update statistics"""
        if doc_count is not None:
            self.document_count = doc_count
        if chunk_count is not None:
            self.total_chunks += chunk_count
        if token_count is not None:
            self.total_tokens += token_count
        
        self.last_indexed_at = timezone.now()
        self.save(update_fields=[
            'document_count', 'total_chunks', 'total_tokens', 'last_indexed_at'
        ])


class QueryLog(models.Model):
    """Log RAG queries at module level"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('rag_app.User', on_delete=models.CASCADE, related_name='query_logs')
    module = models.ForeignKey('rag_app.Module', on_delete=models.CASCADE, related_name='query_logs')
    
    # Query details
    query_text = models.TextField()
    query_hash = models.CharField(max_length=64, db_index=True)
    
    # Results
    response_text = models.TextField(blank=True)
    retrieved_chunks = models.JSONField(default=list)  # List of chunk info
    similarity_scores = models.JSONField(default=list)
    
    # Performance metrics
    retrieval_time_ms = models.IntegerField(default=0)
    generation_time_ms = models.IntegerField(default=0)
    total_time_ms = models.IntegerField(default=0)
    
    # Feedback
    user_rating = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    user_feedback = models.TextField(blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vectordb_query_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['module', '-created_at']),
            models.Index(fields=['query_hash']),
        ]
    
    def __str__(self):
        return f"Query by {self.user.username}: {self.query_text[:50]}..."


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module_vector_store = models.ForeignKey(
        'ModuleVectorStore', 
        on_delete=models.CASCADE,
        related_name='questions',
    )
    text = models.TextField()
    created_by = models.ForeignKey(
        'rag_app.User', 
        on_delete=models.CASCADE,
        related_name='questions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vectordb_question'
        ordering = ['-created_at']
    def __str__(self):
        return f"Question: {self.text[:50]}..."
    
class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        'Question', 
        on_delete=models.CASCADE,
        related_name='answers',
    )
    time_required = models.FloatField(help_text="Time taken to generate the answer in seconds")
    text = models.TextField()
    created_by = models.ForeignKey(
        'rag_app.User', 
        on_delete=models.CASCADE,
        related_name='answers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vectordb_answer'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Answer: {self.text[:50]}..."
    

class Rating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.ForeignKey(
        'Answer', 
        on_delete=models.CASCADE,
        related_name='ratings',
    )
    score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating value between 1 and 5"
    )
    created_by = models.ForeignKey(
        'rag_app.User', 
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vectordb_rating'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Rating: {self.rating_value} for Answer ID: {self.answer.id}"

