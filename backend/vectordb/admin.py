from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import VectorDBTask, ModuleVectorStore, QueryLog, Question, Answer, Rating
import json

@admin.register(VectorDBTask)
class VectorDBTaskAdmin(admin.ModelAdmin):
    list_display = [
        'task_id_short', 'get_module_name', 'status_badge', 'progress_bar',
        'document_stats', 'created_by', 'duration_display', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'task_id', 
        'module_vector_store__module__name', 
        'created_by__username',
        'module_vector_store__collection_name'
    ]
    readonly_fields = [
        'task_id', 'progress_percentage', 'processed_documents',
        'successful_documents', 'failed_documents', 'result_display',
        'created_at', 'started_at', 'completed_at', 'duration_display'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Task Information', {
            'fields': ('task_id', 'module_vector_store', 'status', 'created_by')
        }),
        ('Progress', {
            'fields': (
                'progress_percentage', 'current_step', 'current_document',
                'total_documents', 'processed_documents', 
                'successful_documents', 'failed_documents'
            )
        }),
        ('Configuration', {
            'fields': ('chunk_size', 'chunk_overlap', 'embedding_model')
        }),
        ('Results', {
            'fields': ('result_display', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration_display')
        }),
    )
    
    def task_id_short(self, obj):
        """Display shortened task ID"""
        return f"{obj.task_id[:8]}..." if len(obj.task_id) > 8 else obj.task_id
    task_id_short.short_description = 'Task ID'
    
    def get_module_name(self, obj):
        """Get module name through module_vector_store"""
        if obj.module_vector_store and obj.module_vector_store.module:
            module = obj.module_vector_store.module
            url = reverse('admin:rag_app_module_change', args=[module.id])
            return format_html('<a href="{}">{}</a>', url, module.name)
        return '-'
    get_module_name.short_description = 'Module'
    
    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'pending': '#ffc107',
            'processing': '#007bff',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def progress_bar(self, obj):
        """Display visual progress bar"""
        if obj.status == 'completed':
            color = '#28a745'
        elif obj.status == 'failed':
            color = '#dc3545'
        elif obj.status == 'processing':
            color = '#007bff'
        else:
            color = '#ffc107'
        
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; '
            'border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background-color: {}; '
            'color: white; text-align: center; padding: 2px; '
            'font-size: 11px;">{}</div></div>',
            obj.progress_percentage, color, f"{obj.progress_percentage}%"
        )
    progress_bar.short_description = 'Progress'
    
    def document_stats(self, obj):
        """Display document processing statistics"""
        return format_html(
            '<span style="color: #28a745;">✓ {}</span> / '
            '<span style="color: #dc3545;">✗ {}</span> / '
            '<span style="color: #6c757d;">Total: {}</span>',
            obj.successful_documents,
            obj.failed_documents,
            obj.total_documents
        )
    document_stats.short_description = 'Documents (Success/Failed/Total)'
    
    def duration_display(self, obj):
        """Display task duration in human-readable format"""
        duration = obj.duration
        if not duration:
            return '-'
        
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    duration_display.short_description = 'Duration'
    
    def result_display(self, obj):
        """Display formatted result JSON"""
        if obj.result:
            try:
                formatted = json.dumps(obj.result, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            except:
                return obj.result
        return '-'
    result_display.short_description = 'Result'
    
    def has_delete_permission(self, request, obj=None):
        """Only allow deletion of completed/failed/cancelled tasks"""
        if obj and obj.status in ['pending', 'processing']:
            return False
        return super().has_delete_permission(request, obj)

@admin.register(ModuleVectorStore)
class ModuleVectorStoreAdmin(admin.ModelAdmin):
    list_display = [
        'get_module_link', 'status_badge', 'stats_display',
        'embedding_model_short', 'last_indexed_display'
    ]
    list_filter = ['status', 'created_at', 'embedding_model']
    search_fields = [
        'module__name', 
        'module__project__name',
        'collection_name',
        'persistence_directory'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'last_indexed_at',
        'document_count', 'total_chunks', 'total_tokens',
        'config_display', 'recent_tasks_display'
    ]
    ordering = ['-last_indexed_at']
    
    fieldsets = (
        ('Module Information', {
            'fields': ('id', 'module', 'collection_name', 'persistence_directory', 'status')
        }),
        ('Configuration', {
            'fields': (
                'embedding_model', 'embedding_dimension', 
                'chunk_size', 'chunk_overlap'
            )
        }),
        ('Statistics', {
            'fields': ('document_count', 'total_chunks', 'total_tokens')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_indexed_at')
        }),
        ('Advanced', {
            'fields': ('config_display', 'recent_tasks_display'),
            'classes': ('collapse',)
        })
    )
    
    def get_module_link(self, obj):
        """Display module with link"""
        if obj.module:
            url = reverse('admin:rag_app_module_change', args=[obj.module.id])
            return format_html(
                '<a href="{}">{}</a><br>'
                '<small style="color: #666;">Project: {}</small>',
                url, obj.module.name, obj.module.project.name
            )
        return '-'
    get_module_link.short_description = 'Module'
    
    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'empty': '#6c757d',
            'indexing': '#ffc107',
            'ready': '#28a745',
            'error': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def stats_display(self, obj):
        """Display statistics in compact format"""
        return format_html(
            '<div style="font-size: 11px;">'
            '<strong>Docs:</strong> {} | '
            '<strong>Chunks:</strong> {} | '
            '<strong>Tokens:</strong> {}'
            '</div>',
            obj.document_count,
            f"{obj.total_chunks:,}",
            f"{obj.total_tokens:,}"
        )
    stats_display.short_description = 'Statistics'
    
    def embedding_model_short(self, obj):
        """Display shortened embedding model name"""
        if '/' in obj.embedding_model:
            return obj.embedding_model.split('/')[-1]
        return obj.embedding_model
    embedding_model_short.short_description = 'Embedding Model'
    
    def last_indexed_display(self, obj):
        """Display last indexed time in human-readable format"""
        if not obj.last_indexed_at:
            return '-'
        
        from django.utils.timesince import timesince
        return f"{timesince(obj.last_indexed_at)} ago"
    last_indexed_display.short_description = 'Last Indexed'
    
    def config_display(self, obj):
        """Display formatted config JSON"""
        if obj.config:
            try:
                formatted = json.dumps(obj.config, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            except:
                return obj.config
        return '-'
    config_display.short_description = 'Configuration'
    
    def recent_tasks_display(self, obj):
        """Display recent tasks for this vector store"""
        tasks = obj.tasks.all().order_by('-created_at')[:5]
        if not tasks:
            return 'No tasks yet'
        
        html = '<table style="width: 100%; font-size: 11px;">'
        html += '<tr><th>Task ID</th><th>Status</th><th>Progress</th><th>Created</th></tr>'
        
        for task in tasks:
            url = reverse('admin:vectordb_vectordbtask_change', args=[task.id])
            html += f'<tr>'
            html += f'<td><a href="{url}">{task.task_id[:8]}...</a></td>'
            html += f'<td>{task.status}</td>'
            html += f'<td>{task.progress_percentage}%</td>'
            html += f'<td>{task.created_at.strftime("%Y-%m-%d %H:%M")}</td>'
            html += f'</tr>'
        
        html += '</table>'
        return mark_safe(html)
    recent_tasks_display.short_description = 'Recent Tasks'

@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = [
        'query_text_short', 'get_user_link', 'get_module_link',
        'rating_stars', 'performance_display', 'created_at'
    ]
    list_filter = ['user_rating', 'created_at', 'module']
    search_fields = [
        'query_text', 
        'response_text', 
        'user__username',
        'module__name'
    ]
    readonly_fields = [
        'id', 'query_hash', 'created_at',
        'retrieved_chunks_display', 'similarity_scores_display',
        'metadata_display'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Query Information', {
            'fields': ('id', 'user', 'module', 'query_text', 'query_hash')
        }),
        ('Response', {
            'fields': ('response_text',)
        }),
        ('Performance Metrics', {
            'fields': (
                'retrieval_time_ms', 'generation_time_ms', 'total_time_ms'
            )
        }),
        ('User Feedback', {
            'fields': ('user_rating', 'user_feedback')
        }),
        ('Technical Details', {
            'fields': (
                'retrieved_chunks_display', 
                'similarity_scores_display', 
                'metadata_display'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )
    
    def query_text_short(self, obj):
        """Display shortened query text"""
        max_length = 60
        if len(obj.query_text) > max_length:
            return f"{obj.query_text[:max_length]}..."
        return obj.query_text
    query_text_short.short_description = 'Query'
    
    def get_user_link(self, obj):
        """Display user with link"""
        if obj.user:
            url = reverse('admin:rag_app_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    get_user_link.short_description = 'User'
    
    def get_module_link(self, obj):
        """Display module with link"""
        if obj.module:
            url = reverse('admin:rag_app_module_change', args=[obj.module.id])
            return format_html('<a href="{}">{}</a>', url, obj.module.name)
        return '-'
    get_module_link.short_description = 'Module'
    
    def rating_stars(self, obj):
        """Display rating as stars"""
        if not obj.user_rating:
            return '-'
        
        filled = '★' * obj.user_rating
        empty = '☆' * (5 - obj.user_rating)
        color = '#ffc107' if obj.user_rating >= 3 else '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-size: 16px;">{}{}</span>',
            color, filled, empty
        )
    rating_stars.short_description = 'Rating'
    
    def performance_display(self, obj):
        """Display performance metrics"""
        return format_html(
            '<div style="font-size: 11px;">'
            '<strong>Retrieval:</strong> {}ms<br>'
            '<strong>Generation:</strong> {}ms<br>'
            '<strong>Total:</strong> {}ms'
            '</div>',
            obj.retrieval_time_ms,
            obj.generation_time_ms,
            obj.total_time_ms
        )
    performance_display.short_description = 'Performance'
    
    def retrieved_chunks_display(self, obj):
        """Display formatted retrieved chunks"""
        if obj.retrieved_chunks:
            try:
                formatted = json.dumps(obj.retrieved_chunks, indent=2)
                return format_html('<pre style="max-height: 300px; overflow: auto;">{}</pre>', formatted)
            except:
                return str(obj.retrieved_chunks)
        return '-'
    retrieved_chunks_display.short_description = 'Retrieved Chunks'
    
    def similarity_scores_display(self, obj):
        """Display formatted similarity scores"""
        if obj.similarity_scores:
            try:
                formatted = json.dumps(obj.similarity_scores, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            except:
                return str(obj.similarity_scores)
        return '-'
    similarity_scores_display.short_description = 'Similarity Scores'
    
    def metadata_display(self, obj):
        """Display formatted metadata"""
        if obj.metadata:
            try:
                formatted = json.dumps(obj.metadata, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            except:
                return str(obj.metadata)
        return '-'
    metadata_display.short_description = 'Metadata'

# Optional: Add inline admin for tasks in ModuleVectorStore
class VectorDBTaskInline(admin.TabularInline):
    model = VectorDBTask
    extra = 0
    fields = ['task_id', 'status', 'progress_percentage', 'created_at']
    readonly_fields = ['task_id', 'status', 'progress_percentage', 'created_at']
    can_delete = False
    show_change_link = True
    max_num = 5
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'text_short', 'created_at']
    search_fields = ['text']
    readonly_fields = ['id', 'text', 'created_at']
    ordering = ['-created_at']
    
    def text_short(self, obj):
        max_length = 75
        if len(obj.text) > max_length:
            return f"{obj.text[:max_length]}..."
        return obj.text
    text_short.short_description = 'Question'
    

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'text_short', 'question_link', 'created_at']
    search_fields = ['text', 'question__text']
    readonly_fields = ['id', 'text', 'question', 'created_at']
    ordering = ['-created_at']
    
    def text_short(self, obj):
        max_length = 75
        if len(obj.text) > max_length:
            return f"{obj.text[:max_length]}..."
        return obj.text
    text_short.short_description = 'Answer'
    
    def question_link(self, obj):
        if obj.question:
            url = reverse('admin:rag_app_question_change', args=[obj.question.id])
            return format_html('<a href="{}">{}</a>', url, obj.question.text_short())
        return '-'
    question_link.short_description = 'Question'

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['id', 'score', 'created_at']
    search_fields = ['created_by__username']
    readonly_fields = ['id', 'score', 'created_by', 'created_at']
    ordering = ['-created_at']
    
    def user_link(self, obj):
        if obj.created_by:
            url = reverse('admin:rag_app_user_change', args=[obj.created_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.created_by.username)
        return '-'
    user_link.short_description = 'User'
