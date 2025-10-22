from django.urls import path
from .views import (
    CreateModuleVectorDBView,
    VectorDBTaskStatusView,
    VectorDBTaskCancelView,
    VectorDBTaskListView,
    ModuleVectorStoreListView,
    ModuleVectorStoreDetailView,
    RAGQueryView,
    QueryLogListView,
    QueryLogDetailView,
    VectorDBStatsView,
    ChatView,
    GiveRating
)

app_name = 'vectordb'

urlpatterns = [
    # Vector Database Creation
    path('create/', CreateModuleVectorDBView.as_view(), name='create-module-vectordb'),
    
    # Task Management
    path('tasks/', VectorDBTaskListView.as_view(), name='task-list'),
    path('tasks/status/<str:task_id>/', VectorDBTaskStatusView.as_view(), name='task-status'),
    path('tasks/cancel/<str:task_id>/', VectorDBTaskCancelView.as_view(), name='task-cancel'),
    
    # Vector Store Management
    path('stores/', ModuleVectorStoreListView.as_view(), name='vector-store-list'),
    path('stores/module/<int:module_id>/', ModuleVectorStoreDetailView.as_view(), name='vector-store-detail'),
    
    # RAG Queries
    path('query/', RAGQueryView.as_view(), name='rag-query'),
    
    # Query Logs
    path('queries/', QueryLogListView.as_view(), name='query-log-list'),
    path('queries/<uuid:query_id>/', QueryLogDetailView.as_view(), name='query-log-detail'),
    
    # Statistics and Analytics
    path('stats/', VectorDBStatsView.as_view(), name='vector-db-stats'),
    path("chat/<int:module_id>/", ChatView.as_view(), name='chat-url'),
    path("rating/<str:answer_id>/", GiveRating.as_view(), name='rating-url'),
]
