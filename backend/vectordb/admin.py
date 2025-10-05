from django.contrib import admin
from .models import VectorDBTask, ModuleVectorStore, QueryLog


@admin.register(VectorDBTask)
class VectorDBTaskAdmin(admin.ModelAdmin):
    list_display = [
        'task_id', 'module', 'status', 'progress_percentage',
        'total_documents', 'successful_documents', 'failed_documents',
        'created_by', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'force_recreate']
    search_fields = ['task_id', 'module__name', 'created_by__username']
    readonly_fields = [
        'task_id', 'progress_percentage', 'processed_documents',
        'successful_documents', 'failed_documents', 'result',
        'created_at', 'started_at', 'completed_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('task_id', 'module', 'status', 'created_by')
        }),
        ('Progress', {
            'fields': (
                'progress_percentage', 'current_step', 'current_document',
                'total_documents', 'processed_documents', 'successful_documents', 'failed_documents'
            )
        }),
        ('Configuration', {
            'fields': ('force_recreate', 'chunk_size', 'chunk_overlap', 'embedding_model')
        }),
        ('Results', {
            'fields': ('result', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
    )


@admin.register(ModuleVectorStore)
class ModuleVectorStoreAdmin(admin.ModelAdmin):
    list_display = [
        'module', 'status',  'document_count',
        'total_chunks', 'embedding_model', 'last_indexed_at'
    ]
    list_filter = ['status',  'created_at']
    search_fields = ['module__name', 'collection_name']
    readonly_fields = ['created_at', 'updated_at', 'last_indexed_at']
    ordering = ['-last_indexed_at']
    
    fieldsets = (
        (None, {
            'fields': ('module', 'collection_name',  'status')
        }),
        ('Configuration', {
            'fields': ('embedding_model', 'embedding_dimension', 'chunk_size', 'chunk_overlap')
        }),
        ('Statistics', {
            'fields': ('document_count', 'total_chunks', 'total_tokens')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_indexed_at')
        }),
        ('Advanced', {
            'fields': ('config',),
            'classes': ('collapse',)
        })
    )


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'module', 'query_text_short', 'user_rating',
        'total_time_ms', 'created_at'
    ]
    list_filter = ['user_rating', 'created_at', 'module']
    search_fields = ['query_text', 'response_text', 'user__username']
    readonly_fields = ['query_hash', 'created_at']
    ordering = ['-created_at']
    
    def query_text_short(self, obj):
        return obj.query_text[:50] + '...' if len(obj.query_text) > 50 else obj.query_text
    query_text_short.short_description = 'Query'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'module', 'query_text', 'response_text')
        }),
        ('Performance', {
            'fields': ('retrieval_time_ms', 'generation_time_ms', 'total_time_ms')
        }),
        ('Feedback', {
            'fields': ('user_rating', 'user_feedback')
        }),
        ('Technical', {
            'fields': ('query_hash', 'retrieved_chunks', 'similarity_scores', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )
