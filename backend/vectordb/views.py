import logging
import hashlib
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from celery.result import AsyncResult
from django.db.models import Q, Prefetch
import time
from .models import VectorDBTask, ModuleVectorStore, QueryLog, Question, Answer, Rating, ChatSession
from .serializers import (
    VectorDBTaskSerializer, ModuleVectorStoreSerializer, QueryLogSerializer,
    VectorDBCreateSerializer, RAGQuerySerializer, RAGResponseSerializer,
    QuestionSerializer, AnswerSerializer, RatingSerializer, ChatSessionSerializer
)
from .tasks import create_vectordb_for_module_task
from .services import VectorDBService
from .chat_bot import RUN_GRAPH
from rag_app.models import Module, Project

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CreateModuleVectorDBView(APIView):
    """Create vector database for a module (async)"""    
    def post(self, request):
        """Start vector DB creation for a module"""
        try:
            module = get_object_or_404(Module, id=request.data.get('module_id'), is_active=True)
            
            ### check if ModuleVectorStore already exists for this module otherwise create it
            module_vector_store = ModuleVectorStore.objects.filter(module=module).first()

            if not module_vector_store:
                persistence_directory = f"vector_data/project_{module.project.id}/"
                module_vector_store = ModuleVectorStore.objects.create(
                    module=module,
                    collection_name=f"module_{module.id}_vector_store",
                    persistence_directory=persistence_directory, 
                    status='empty',
                    embedding_model=request.data.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2'),
                    embedding_dimension=request.data.get('embedding_dimension', 384),
                    chunk_size=request.data.get('chunk_size', 1000),
                    chunk_overlap=request.data.get('chunk_overlap', 200),
                    config=request.data.get('config', {})
                )

            pending_processing_tasks = VectorDBTask.objects.filter(
                module_vector_store=module_vector_store,
                status__in=['pending', 'processing']
            )

            if pending_processing_tasks.exists():
                return Response({
                    "error": "Vector DB creation already in progress for this module",
                    "existing_task_id": str(pending_processing_tasks.first().id),
                    "status_url": f"/api/vectordb/status/{pending_processing_tasks.first().task_id}/"
                }, status=status.HTTP_409_CONFLICT)
            
            ## create new task
            task_obj = VectorDBTask.objects.create(
                module_vector_store=module_vector_store,
                current_step='initializing',
                total_documents=module.documents.filter(active=True).count(),
                created_by=request.user,
                chunk_size=module_vector_store.chunk_size,
                chunk_overlap=module_vector_store.chunk_overlap,
                embedding_model=module_vector_store.embedding_model
            )
            
            # Start Celery task
            celery_task = create_vectordb_for_module_task.delay(
                str(task_obj.id),
                str(module_vector_store.id),
                task_obj.chunk_size,
                task_obj.chunk_overlap,
                task_obj.embedding_model
            )
            
            # Update task with Celery task ID
            task_obj.task_id = celery_task.id
            task_obj.save(update_fields=['task_id'])
            
            return Response({
                "success": True,
                "message": f"Vector DB creation started for module: {module.name}",
                "task_id": celery_task.id,
                "task_record_id": str(task_obj.id),
                "module_id": module_vector_store.module.id,
                "module_vector_id": module_vector_store.id,
                "module_name": module_vector_store.module.name,
                "status_url": f"/api/vectordb/status/{celery_task.id}/",
                "estimated_documents": module.documents.filter(active=True).count()
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Failed to start vector DB creation: {str(e)}")
            return Response(
                {"error": f"Failed to start vector DB creation: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VectorDBTaskStatusView(APIView):
    """Get status and progress of vector DB creation task"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, task_id):
        """Get detailed task status and progress"""
        try:
            # Get Celery task result
            celery_result = AsyncResult(task_id)
            
            # Get task from database
            try:
                task_obj = VectorDBTask.objects.get(task_id=task_id)
            except VectorDBTask.DoesNotExist:
                return Response(
                    {"error": "Task not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Prepare response data
            response_data = {
                "task_id": task_id,
                "task_record_id": str(task_obj.id),
                "module_id": task_obj.module.id,
                "module_name": task_obj.module.name,
                "project_name": task_obj.module.project.name,
                "status": task_obj.status,
                "progress_percentage": task_obj.progress_percentage,
                "current_step": task_obj.current_step,
                "current_document": task_obj.current_document,
                "total_documents": task_obj.total_documents,
                "processed_documents": task_obj.processed_documents,
                "successful_documents": task_obj.successful_documents,
                "failed_documents": task_obj.failed_documents,
                "created_at": task_obj.created_at,
                "started_at": task_obj.started_at,
                "completed_at": task_obj.completed_at,
                "duration": str(task_obj.duration) if task_obj.duration else None,
                "is_running": task_obj.is_running,
                "is_completed": task_obj.is_completed,
                "created_by": task_obj.created_by.username,
                "force_recreate": task_obj.force_recreate,
                "chunk_size": task_obj.chunk_size,
                "chunk_overlap": task_obj.chunk_overlap
            }
            
            # Add Celery-specific information
            if celery_result.state == 'PENDING':
                response_data["celery_status"] = "Task is waiting to be processed"
                
            elif celery_result.state == 'PROGRESS':
                celery_info = celery_result.info or {}
                response_data["celery_status"] = celery_info.get('status', 'Processing...')
                response_data["celery_progress"] = celery_info.get('progress', 0)
                
            elif celery_result.state == 'SUCCESS':
                response_data["celery_status"] = "Task completed successfully"
                if celery_result.info:
                    response_data["celery_result"] = celery_result.info
                    
            elif celery_result.state == 'FAILURE':
                response_data["celery_status"] = "Task failed"
                response_data["celery_error"] = str(celery_result.info)
            
            # Add database-specific information
            if task_obj.result:
                response_data["result"] = task_obj.result
                
            if task_obj.error_message:
                response_data["error_message"] = task_obj.error_message
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}")
            return Response(
                {"error": f"Failed to get task status: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VectorDBTaskCancelView(APIView):
    """Cancel a running vector DB creation task"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, task_id):
        """Cancel the specified task"""
        try:
            # Get task from database
            try:
                task_obj = VectorDBTask.objects.get(task_id=task_id)
            except VectorDBTask.DoesNotExist:
                return Response(
                    {"error": "Task not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if user has permission to cancel (task creator or admin)
            if task_obj.created_by != request.user and not request.user.is_staff:
                return Response(
                    {"error": "Permission denied"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if task is still running
            if not task_obj.is_running:
                return Response(
                    {"error": "Task is not running and cannot be cancelled"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Revoke Celery task
            from celery import current_app
            current_app.control.revoke(task_id, terminate=True)
            
            # Update database record
            task_obj.status = 'cancelled'
            task_obj.completed_at = timezone.now()
            task_obj.error_message = f"Cancelled by user: {request.user.username}"
            task_obj.save()
            
            # Update module vector store status if needed
            try:
                vector_store = ModuleVectorStore.objects.get(module=task_obj.module)
                if vector_store.status == 'indexing':
                    vector_store.status = 'empty'
                    vector_store.save()
            except ModuleVectorStore.DoesNotExist:
                pass
            
            return Response({
                "success": True,
                "message": "Task cancelled successfully",
                "task_id": task_id,
                "module_name": task_obj.module.name
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to cancel task: {str(e)}")
            return Response(
                {"error": f"Failed to cancel task: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VectorDBTaskListView(APIView):
    """List vector DB tasks with filtering and pagination"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        """Get list of vector DB tasks"""
        try:
            queryset = VectorDBTask.objects.select_related(
                'module_vector_store__module', 'module_vector_store__module__project', 'created_by'
            )
            
            # Filter by status
            status_filter = request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Filter by module
            module_id = request.query_params.get('module_id')
            if module_id:
                queryset = queryset.filter(module_vector_store__module_id=module_id)
            
            # Filter by project
            project_id = request.query_params.get('project_id')
            if project_id:
                queryset = queryset.filter(module_vector_store__module__project_id=project_id)
            
            # Filter by user (show only user's tasks unless admin)
            if not request.user.is_staff:
                queryset = queryset.filter(created_by=request.user)
            
            # Order by creation date (newest first)
            queryset = queryset.order_by('-created_at')
            
            # Paginate
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            
            if page is not None:
                serializer = VectorDBTaskSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = VectorDBTaskSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to get task list: {str(e)}")
            return Response(
                {"error": f"Failed to get task list: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModuleVectorStoreListView(APIView):
    """List module vector stores"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        """Get list of module vector stores"""
        try:
            queryset = ModuleVectorStore.objects.select_related(
                'module', 'module__project'
            )
            
            # Filter by status
            status_filter = request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Filter by module
            module_id = request.query_params.get('module_id')
            if module_id:
                queryset = queryset.filter(module_id=module_id)
            
            # Filter by project
            project_id = request.query_params.get('project_id')
            if project_id:
                queryset = queryset.filter(module__project_id=project_id)
            
            # Order by last indexed date
            queryset = queryset.order_by('-last_indexed_at', '-created_at')
            
            # Paginate
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            
            if page is not None:
                serializer = ModuleVectorStoreSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = ModuleVectorStoreSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to get vector store list: {str(e)}")
            return Response(
                {"error": f"Failed to get vector store list: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModuleVectorStoreDetailView(APIView):
    def get(self, request, module_id):
        """Get vector store details for a module"""
        try:
            module = get_object_or_404(Module, id=module_id, is_active=True)
            
            try:
                vector_store = ModuleVectorStore.objects.get(module=module)
                serializer = ModuleVectorStoreSerializer(vector_store)
                
                # Add additional information
                data = serializer.data
                data['recent_tasks'] = VectorDBTaskSerializer(
                    VectorDBTask.objects.filter(module_vector_store=vector_store).order_by('-created_at')[:5],
                    many=True
                ).data
                
                return Response(data, status=status.HTTP_200_OK)
                
            except ModuleVectorStore.DoesNotExist:
                return Response({
                    "module_id": module_id,
                    "module_name": module.name,
                    "status": "no_vector_store",
                    "message": "No vector store found for this module",
                    "recent_tasks": []
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Failed to get vector store details: {str(e)}")
            return Response(
                {"error": f"Failed to get vector store details: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, module_id):
        """Delete vector store for a module"""
        try:
            module = get_object_or_404(Module, id=module_id, is_active=True)
            
            try:
                vector_store = ModuleVectorStore.objects.get(module=module)
                
                # Check for running tasks
                running_tasks = VectorDBTask.objects.filter(
                    module=module,
                    status__in=['pending', 'processing']
                )
                
                if running_tasks.exists():
                    return Response({
                        "error": "Cannot delete vector store while tasks are running",
                        "running_tasks": [str(task.id) for task in running_tasks]
                    }, status=status.HTTP_409_CONFLICT)
                
                # Delete vector store data
                vector_service = VectorDBService()
                vector_service._delete_collection(vector_store.collection_name)
                
                # Delete database record
                vector_store.delete()
                
                return Response({
                    "success": True,
                    "message": f"Vector store deleted for module: {module.name}"
                }, status=status.HTTP_200_OK)
                
            except ModuleVectorStore.DoesNotExist:
                return Response(
                    {"error": "Vector store not found for this module"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Failed to delete vector store: {str(e)}")
            return Response(
                {"error": f"Failed to delete vector store: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RAGQueryView(APIView):
    """Handle RAG queries against module vector stores"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Process RAG query"""
        try:
            serializer = RAGQuerySerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            query = serializer.validated_data['query']
            module_id = serializer.validated_data['module_id']
            max_results = serializer.validated_data.get('max_results', 5)
            similarity_threshold = serializer.validated_data.get('similarity_threshold', 0.7)
            include_metadata = serializer.validated_data.get('include_metadata', True)
            
            # Get module
            module = get_object_or_404(Module, id=module_id, is_active=True)
            
            # Check if vector store exists and is ready
            try:
                vector_store = ModuleVectorStore.objects.get(module=module, status='ready')
            except ModuleVectorStore.DoesNotExist:
                return Response({
                    "error": "Vector store not ready for this module",
                    "module_name": module.name,
                    "suggestion": "Please create vector database for this module first"
                }, status=status.HTTP_412_PRECONDITION_FAILED)
            
            # Process RAG query
            rag_service = RAGService()
            result = rag_service.process_query(
                query=query,
                project=module.project,
                module=module,
                user=request.user,
                max_results=max_results
            )
            
            response_serializer = RAGResponseSerializer(data=result)
            if response_serializer.is_valid():
                return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"RAG query processing failed: {str(e)}")
            return Response(
                {"error": f"Query processing failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QueryLogListView(APIView):
    """List query logs with filtering"""
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        """Get query logs"""
        try:
            queryset = QueryLog.objects.select_related('user', 'module', 'module__project')
            
            # Filter by module
            module_id = request.query_params.get('module_id')
            if module_id:
                queryset = queryset.filter(module_id=module_id)
            
            # Filter by user (show only user's queries unless admin)
            if not request.user.is_staff:
                queryset = queryset.filter(user=request.user)
            
            # Filter by date range
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            if date_from:
                queryset = queryset.filter(created_at__gte=date_from)
            if date_to:
                queryset = queryset.filter(created_at__lte=date_to)
            
            # Search in query text
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(query_text__icontains=search) |
                    Q(response_text__icontains=search)
                )
            
            # Order by creation date (newest first)
            queryset = queryset.order_by('-created_at')
            
            # Paginate
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            
            if page is not None:
                serializer = QueryLogSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            serializer = QueryLogSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to get query logs: {str(e)}")
            return Response(
                {"error": f"Failed to get query logs: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QueryLogDetailView(APIView):
    """Get details of a specific query log"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, query_id):
        """Get query log details"""
        try:
            queryset = QueryLog.objects.select_related('user', 'module', 'module__project')
            
            # Filter by user unless admin
            if not request.user.is_staff:
                queryset = queryset.filter(user=request.user)
            
            query_log = get_object_or_404(queryset, id=query_id)
            serializer = QueryLogSerializer(query_log)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to get query log details: {str(e)}")
            return Response(
                {"error": f"Failed to get query log details: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, query_id):
        """Update query log (for user feedback)"""
        try:
            queryset = QueryLog.objects.select_related('user', 'module')
            query_log = get_object_or_404(queryset, id=query_id, user=request.user)
            
            # Only allow updating rating and feedback
            allowed_fields = ['user_rating', 'user_feedback']
            update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
            
            if not update_data:
                return Response(
                    {"error": "No valid fields to update"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = QueryLogSerializer(query_log, data=update_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Failed to update query log: {str(e)}")
            return Response(
                {"error": f"Failed to update query log: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VectorDBStatsView(APIView):
    """Get vector database statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get comprehensive vector DB statistics"""
        try:
            # Overall statistics
            total_vector_stores = ModuleVectorStore.objects.count()
            ready_vector_stores = ModuleVectorStore.objects.filter(status='ready').count()
            
            # Task statistics
            total_tasks = VectorDBTask.objects.count()
            completed_tasks = VectorDBTask.objects.filter(status='completed').count()
            failed_tasks = VectorDBTask.objects.filter(status='failed').count()
            running_tasks = VectorDBTask.objects.filter(status__in=['pending', 'processing']).count()
            
            # Query statistics
            total_queries = QueryLog.objects.count()
            user_queries = QueryLog.objects.filter(user=request.user).count()
            
            # Recent activity
            recent_tasks = VectorDBTaskSerializer(
                VectorDBTask.objects.select_related('module', 'created_by')
                .order_by('-created_at')[:10],
                many=True
            ).data
            
            recent_queries = QueryLogSerializer(
                QueryLog.objects.filter(user=request.user)
                .select_related('module')
                .order_by('-created_at')[:10],
                many=True
            ).data
            
            # Vector store breakdown by status
            vector_store_stats = {}
            for status_choice in ModuleVectorStore.STATUS_CHOICES:
                status_key = status_choice[0]
                count = ModuleVectorStore.objects.filter(status=status_key).count()
                vector_store_stats[status_key] = count
            
            return Response({
                "overview": {
                    "total_vector_stores": total_vector_stores,
                    "ready_vector_stores": ready_vector_stores,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "failed_tasks": failed_tasks,
                    "running_tasks": running_tasks,
                    "total_queries": total_queries,
                    "user_queries": user_queries
                },
                "vector_store_stats": vector_store_stats,
                "recent_activity": {
                    "recent_tasks": recent_tasks,
                    "recent_queries": recent_queries
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to get vector DB stats: {str(e)}")
            return Response(
                {"error": f"Failed to get statistics: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatView(APIView):
    """Chat interface using RAG"""
    permission_classes = [IsAuthenticated]

    def post(self, request, module_id, session_id=None):
        """Handle chat message"""
        try:
            data = request.data
            question = data.get('question')
            title = data.get('title', '')
            
            if not question:
                return Response(
                    {"error": "Question is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            module_vector_store = get_object_or_404(
                ModuleVectorStore, 
                module_id=module_id, 
                status='ready'
            )

            if session_id:
                get_session = get_object_or_404(
                    ChatSession,
                    session_id=session_id,
                    user=request.user
                )
            else:
                session_id = hashlib.sha256(
                    f"{request.user.id}_{module_id}_{time.time()}".encode()
                ).hexdigest()
                # session_id = get_session.session_id

                get_session = ChatSession.objects.create(
                    title = title if title or title != '' else f"Chat Session {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    session_id = session_id,
                    user = request.user,
                    module_vector_store = module_vector_store
                )
            create_question = Question.objects.create(
                module_vector_store=module_vector_store,
                text=question,
                created_by=request.user,
                chat_session=get_session
            )


            ## fetch latest 5 chat history for the session
            previous_chat_history = Answer.objects.select_related('question').filter(
                question__chat_session = get_session,
                question__created_by = request.user
            ).order_by('created_at').reverse()[:5]

            print("Previous chat history objects:", previous_chat_history)
            

            previous_chat = []

            for ans in previous_chat_history:
                question_obj = ans.question
                  # Get first answer
                ratings = Rating.objects.filter(
                    answer=ans,
                )
                
                rate = [
                    {"score": r.score, "feedback": r.feedback_text} 
                    for r in ratings
                ]
                    
                previous_chat.append({
                    "question": question_obj.text,
                    "answer": ans.text,
                    "rating": rate
                })

            print("Previous chat:", previous_chat)

            ## get time to process RAG

            start_time = time.time()
            rag_service = RUN_GRAPH(
                collection_name=module_vector_store.collection_name,
                persist_directory=module_vector_store.persistence_directory,
                embedding_model_name=module_vector_store.embedding_model,
                model_provider="mistralai",
                temperature=0.0
            )

            answer_text = rag_service.run(
                question=question,
                previous_chat=previous_chat
            )

            end_time = time.time()
            processing_time = end_time - start_time

            answer_content = answer_text.get('answer', answer_text) if isinstance(answer_text, dict) else answer_text

            create_answer = Answer.objects.create(
                question=create_question,
                text=answer_content,
                created_by=request.user,
                time_required=processing_time
            )

            logger.info(f"Chat processed for module {module_id} by user {request.user.username} in {processing_time:.3f}s")

            return Response({
                "question": question,
                "answer": answer_content,
                "processing_time": round(processing_time, 3),
                "session_id": session_id,
                "answer_id": str(create_answer.id)
            }, status=status.HTTP_200_OK)
        except Exception as e:

            logger.error(f"Chat processing failed: {str(e)}")
            return Response(
                {"error": f"Chat processing failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GiveRating(APIView):

    """Give rating to a chat answer"""
    permission_classes = [IsAuthenticated]

    def post(self, request, answer_id):
        """Submit rating for an answer"""
        try:
            data = request.data
            rating_value = data.get('rating')
            feedback_text = data.get('feedback', '')

            answer = get_object_or_404(Answer, id=answer_id)

            # Check if user has already rated this answer
            existing_rating = Rating.objects.filter(
                answer=answer,
                created_by=request.user
            ).first()

            if existing_rating:
                return Response(
                    {"error": "You have already rated this answer"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create new rating
            rating = Rating.objects.create(
                answer=answer,
                score=rating_value,
                feedback_text=feedback_text,
                created_by=request.user
            )

            return Response({
                "success": True,
                "message": "Rating submitted successfully",
                "rating_id": str(rating.id)
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to submit rating: {str(e)}")
            return Response(
                {"error": f"Failed to submit rating: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
