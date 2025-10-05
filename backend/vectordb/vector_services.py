import os
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
from .models import ModuleVectorStore, QueryLog
from rag_app.models import Document, Module
import mimetypes

logger = logging.getLogger(__name__)


class VectorDBService:
    """Service class for module-level vector database operations"""
    
    def __init__(self, vector_store_type='chromadb'):
        self.vector_store_type = vector_store_type
        self.embedding_model = getattr(settings, 'VECTOR_DB_CONFIG', {}).get(
            'EMBEDDINGS_MODEL', 
            'all-MiniLM-L6-v2'
        )
    
    def reset_module_vector_store(self, vector_store: ModuleVectorStore):
        """Reset/clear a module's vector store"""
        try:
            persistence_path = vector_store.persistence_directory
            collection_name = vector_store.collection_name

            # Import here to avoid Django startup issues
            import chromadb
            client = chromadb.PersistentClient(path=persistence_path)

            # Delete the collection
            try:
                client.delete_collection(name=collection_name)
                logger.info(f"Collection '{collection_name}' has been deleted.")
            except Exception as e:
                logger.warning(f"Failed to delete collection: {e}")

            # Update vector store status
            vector_store.status = 'empty'
            vector_store.document_count = 0
            vector_store.total_chunks = 0
            vector_store.total_tokens = 0
            vector_store.last_indexed_at = None
            vector_store.save(update_fields=[
                'status', 'document_count', 'total_chunks', 'total_tokens', 'last_indexed_at'
            ])
            logger.info(f"Vector store for module {vector_store.module.id} has been reset.")
            return True
        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            raise
    
    def process_document_for_module(self, document: Document, vector_store: ModuleVectorStore, 
                                   chunk_size: int = 1000, chunk_overlap: int = 200) -> Dict[str, Any]:
        """Process a single document and add to module vector store"""
        try:
            # Import here to avoid startup issues
            from langchain_huggingface import HuggingFaceEmbeddings
            from .create_vector_db import CreateVectorStore
            
            # Load document content
            file_path = document.file.path
            
            # Check if file physically exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Document file not found: {file_path}")
            
            # Get file information
            file_size = os.path.getsize(file_path)
            file_name = document.title or os.path.basename(file_path)
            
            # Ensure file name has extension
            if not os.path.splitext(file_name)[1] and hasattr(document, 'file_type') and document.file_type:
                file_name = f"{file_name}{document.file_type}"
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            model_name = vector_store.embedding_model
            collection_name = vector_store.collection_name
            persist_directory = vector_store.persistence_directory

            # Ensure directory exists
            os.makedirs(persist_directory, exist_ok=True)

            create_vector_store = CreateVectorStore(file_path)
            create_vector_store.embeddings = HuggingFaceEmbeddings(model_name=model_name)
            create_vector_store.load_vector_store(collection_name=collection_name, persist_directory=persist_directory)
            result = create_vector_store.create_vector_store()
            
            return {
                'document_id': document.id,
                'chunk_count': result.get('chunk_count', 0),
                'token_count': result.get('token_count', 0),
                'status': 'success'
            }
            
        except ImportError as e:
            logger.error(f"Required dependencies not installed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to process document {document.id}: {e}")
            raise
    
    def query_module_vectors(self, query: str, module: Module, max_results: int = 5, 
                            similarity_threshold: float = 0.7) -> tuple:
        """Query vectors in a module and return relevant content"""
        try:
            vector_store = ModuleVectorStore.objects.get(module=module, status='ready')
        except ModuleVectorStore.DoesNotExist:
            logger.warning(f"No ready vector store found for module {module.id}")
            return [], 0
        
        start_time = time.time()

        try:
            # Import here to avoid startup issues
            from .query_model import RUN_GRAPH
            
            model_name = vector_store.embedding_model
            collection_name = vector_store.collection_name
            persist_directory = vector_store.persistence_directory

            retrieval_service = RUN_GRAPH(
                chat_model_name="mistral-large-latest",
                model_name=model_name,
                model_provider="mistralai",
                temperature=0.0,
                persist_directory=persist_directory,
                collection_name=collection_name,
                k=max_results,
                score_threshold=similarity_threshold
            )

            answers = retrieval_service.run(query)

            return answers['context'], int((time.time() - start_time) * 1000)
            
        except ImportError as e:
            logger.error(f"Required dependencies not installed: {e}")
            return [], 0
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return [], 0


class RAGService:
    """Service for RAG query processing"""
    
    def __init__(self):
        self.vector_service = VectorDBService()
    
    def process_query(self, query: str, project, module=None, 
                     user=None, max_results: int = 5) -> Dict[str, Any]:
        """Process RAG query and return response"""
        start_time = time.time()
        
        try:
            # Search for relevant documents
            search_results, retrieval_time = self.vector_service.query_module_vectors(
                query, module, max_results
            )
            
            generation_start = time.time()
            
            # Generate response - use the context from your RAG system
            if search_results:
                # Your RAG system returns the answer in the context
                response = search_results.get('answer', 'No answer generated')
                # Format sources from context
                sources = []
                if isinstance(search_results, dict) and 'context' in search_results:
                    for doc in search_results['context']:
                        sources.append({
                            'content': doc.page_content if hasattr(doc, 'page_content') else str(doc),
                            'metadata': doc.metadata if hasattr(doc, 'metadata') else {}
                        })
            else:
                response = "I couldn't find relevant information to answer your question."
                sources = []
            
            generation_time = int((time.time() - generation_start) * 1000)
            total_time = int((time.time() - start_time) * 1000)
            
            # Log query
            if user and module:
                QueryLog.objects.create(
                    user=user,
                    module=module,
                    query_text=query,
                    query_hash=hashlib.md5(query.encode()).hexdigest(),
                    response_text=response,
                    retrieved_chunks=sources,
                    similarity_scores=[],
                    retrieval_time_ms=retrieval_time,
                    generation_time_ms=generation_time,
                    total_time_ms=total_time
                )
            
            return {
                'query': query,
                'answer': response,
                'sources': sources,
                'retrieval_time_ms': retrieval_time,
                'generation_time_ms': generation_time,
                'total_time_ms': total_time,
                'metadata': {
                    'module_id': module.id if module else None,
                }
            }
            
        except Exception as e:
            logger.error(f"RAG query processing failed: {e}")
            raise
