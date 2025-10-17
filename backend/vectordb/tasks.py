import logging
import os
import django
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sop_rag.settings')
django.setup()
from celery import shared_task, current_task
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import VectorDBTask, ModuleVectorStore
from .services import VectorDBService
from rag_app.models import Document, Module

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def create_vectordb_for_module_task(self, task_record_id, module_vector_store_id, chunk_size=1000, chunk_overlap=200, embedding_model=None):
    """Celery task to create vector database for all documents in a module"""
    task_id = self.request.id
    logger.info(f"Starting vector DB task {task_id} for vector store {module_vector_store_id}")
    
    module = None  # Initialize module variable
    vector_store = None
    task_obj = None
    
    try:
        # Get vector store
        vector_store = ModuleVectorStore.objects.get(id=module_vector_store_id)
        
        # Get module from vector store (correct way)
        module = vector_store.module  # This is the Module object directly
        print(f"Processing module: {module.name} (ID: {module.id})")
        
        # Get task record
        task_obj = VectorDBTask.objects.get(id=task_record_id)
        task_obj.task_id = task_id
        task_obj.status = 'processing'
        task_obj.save(update_fields=['task_id', 'status'])
        
        # Get documents
        documents = Document.objects.filter(module=module, active=True)
        
        if not documents.exists():
            result = {
                'message': 'No documents found in module', 
                'module_id': module.id,
                'module_name': module.name
            }
            task_obj.mark_completed(result)
            logger.warning(f"No documents found for module {module.id}")
            return result
        
        total_docs = documents.count()
        task_obj.mark_started(total_docs)
        print(f"Found {total_docs} documents to process")
        
        # Update Celery task state
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': 5,
                'status': f'Starting processing of {total_docs} documents',
                'current_document': '',
                'processed': 0,
                'total': total_docs
            }
        )
        
        # Initialize vector service
        vector_service = VectorDBService()
        
        # Update vector store status
        vector_store.status = 'indexing'
        vector_store.save(update_fields=['status'])
        
        successful_docs = 0
        failed_docs = 0
        total_chunks = 0
        total_tokens = 0
        
        # Process each document
        for i, document in enumerate(documents, 1):
            try:
                # Update progress
                progress = int((i / total_docs) * 90) + 5  # 5-95 range
                current_doc_name = document.title[:50]
                
                task_obj.current_document = current_doc_name
                task_obj.progress_percentage = progress
                task_obj.save(update_fields=['current_document', 'progress_percentage'])
                
                # Update Celery state
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': progress,
                        'status': f'Processing document {i}/{total_docs}',
                        'current_document': current_doc_name,
                        'processed': i - 1,
                        'total': total_docs,
                        'successful': successful_docs,
                        'failed': failed_docs
                    }
                )

                print(f"Processing document {i}/{total_docs}: {document.title}")

                # Process the document
                doc_result = vector_service.process_document_for_module(
                    document=document,
                    vector_store=vector_store,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                
                # Update counters
                successful_docs += 1
                total_chunks += doc_result.get('chunk_count', 0)
                total_tokens += doc_result.get('token_count', 0)
                
                task_obj.increment_processed(success=True)
                logger.info(f"Successfully processed document {document.id}: {document.title}")
                
            except Exception as e:
                error_msg = str(e)
                failed_docs += 1
                task_obj.increment_processed(success=False)
                logger.error(f"Failed to process document {document.id}: {error_msg}", exc_info=True)
                continue
        
        # Finalize vector store
        vector_store.update_stats(
            doc_count=successful_docs,
            chunk_count=total_chunks,
            token_count=total_tokens
        )
        vector_store.status = 'ready' if successful_docs > 0 else 'error'
        vector_store.save(update_fields=['status'])
        
        # Prepare final result
        final_result = {
            'status': 'completed',
            'module_id': module.id,
            'module_name': module.name,
            'vector_store_id': str(vector_store.id),
            'collection_name': vector_store.collection_name,
            'total_documents': total_docs,
            'successful_documents': successful_docs,
            'failed_documents': failed_docs,
            'total_chunks': total_chunks,
            'total_tokens': total_tokens,
            'embedding_model': vector_store.embedding_model,
            'processing_time': str(task_obj.duration) if task_obj.duration else None
        }
        
        # Mark task as completed
        task_obj.mark_completed(final_result)
        
        # Final Celery state update
        self.update_state(
            state='SUCCESS',
            meta={
                'progress': 100,
                'status': 'Completed successfully',
                'result': final_result
            }
        )
        
        logger.info(
            f"Module {module.id} vector DB creation completed: "
            f"{successful_docs} success, {failed_docs} failed, "
            f"{total_chunks} chunks, {total_tokens} tokens"
        )
        return final_result
        
    except ModuleVectorStore.DoesNotExist:
        error_msg = f"ModuleVectorStore with id {module_vector_store_id} does not exist"
        logger.error(error_msg)
        
        # Try to mark task as failed
        try:
            if task_obj:
                task_obj.mark_failed(error_msg)
        except:
            pass
        
        self.update_state(
            state='FAILURE',
            meta={'error': error_msg}
        )
        raise
        
    except VectorDBTask.DoesNotExist:
        error_msg = f"VectorDBTask with id {task_record_id} does not exist"
        logger.error(error_msg)
        
        self.update_state(
            state='FAILURE',
            meta={'error': error_msg}
        )
        raise
        
    except Exception as e:
        error_message = str(e)
        module_id = module.id if module else 'unknown'
        logger.error(f"Vector DB task failed for module {module_id}: {error_message}", exc_info=True)
        
        # Mark task as failed
        try:
            if task_obj:
                task_obj.mark_failed(error_message)
            
            # Update vector store status
            if vector_store:
                vector_store.status = 'error'
                vector_store.save(update_fields=['status'])
                
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup after error: {cleanup_error}")
        
        # Update Celery state
        self.update_state(
            state='FAILURE',
            meta={
                'error': error_message,
                'module_id': module_id
            }
        )
        raise



@shared_task
def cleanup_old_vector_tasks():
    """Cleanup old completed/failed vector tasks (older than 30 days)"""
    from datetime import timedelta
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_tasks = VectorDBTask.objects.filter(
        completed_at__lt=cutoff_date,
        status__in=['completed', 'failed', 'cancelled']
    )
    
    count = old_tasks.count()
    old_tasks.delete()
    
    logger.info(f"Cleaned up {count} old vector DB tasks")
    return f"Cleaned up {count} old tasks"


@shared_task
def update_vector_store_stats():
    """Update vector store statistics"""
    vector_stores = ModuleVectorStore.objects.filter(status='ready')
    
    for vs in vector_stores:
        try:
            # Get actual document count from module
            actual_doc_count = Document.objects.filter(
                module=vs.module, 
                active=True
            ).count()
            
            if vs.document_count != actual_doc_count:
                # Mark for re-indexing if document count changed
                vs.status = 'empty'
                vs.save()
                logger.info(f"Marked vector store {vs.id} for re-indexing due to document count change")
                
        except Exception as e:
            logger.error(f"Failed to update stats for vector store {vs.id}: {e}")
            continue
    
    return "Vector store stats updated"
