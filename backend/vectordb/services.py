import logging
from typing import Dict, Any
from .models import ModuleVectorStore, QueryLog
from rag_app.models import Document, Module

logger = logging.getLogger(__name__)


class VectorDBService:
    """Lightweight service class for Django integration"""
    
    def __init__(self, vector_store_type='chromadb'):
        self.vector_store_type = vector_store_type
    
    def process_document_for_module(self, document: Document, vector_store: ModuleVectorStore,
                                   chunk_size: int = 1000, chunk_overlap: int = 200) -> Dict[str, Any]:
        """Process a single document - imports heavy modules only when needed"""
        try:
            # Import the actual service when needed
            from .vector_services import VectorDBService as ActualVectorDBService
            actual_service = ActualVectorDBService()
            return actual_service.process_document_for_module(document, vector_store, chunk_size, chunk_overlap)
        except ImportError as e:
            logger.error(f"Vector service dependencies not available: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to process document: {e}")
            raise
    
    def reset_module_vector_store(self, vector_store: ModuleVectorStore):
        """Reset vector store - imports heavy modules only when needed"""
        try:
            from .vector_services import VectorDBService as ActualVectorDBService
            actual_service = ActualVectorDBService()
            return actual_service.reset_module_vector_store(vector_store)
        except ImportError as e:
            logger.error(f"Vector service dependencies not available: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            raise

    def _delete_collection(self, collection_name: str):
        """Placeholder for collection deletion"""
        pass


class RAGService:
    """Lightweight service for RAG query processing"""
    
    def __init__(self):
        pass
    
    def process_query(self, query: str, project, module=None, 
                     user=None, max_results: int = 5) -> Dict[str, Any]:
        """Process RAG query - imports heavy modules only when needed"""
        try:
            from .vector_services import RAGService as ActualRAGService
            actual_service = ActualRAGService()
            return actual_service.process_query(query, project, module, user, max_results)
        except ImportError as e:
            logger.error(f"RAG service dependencies not available: {e}")
            return {
                'query': query,
                'answer': "RAG service not available - missing dependencies",
                'sources': [],
                'retrieval_time_ms': 0,
                'generation_time_ms': 0,
                'total_time_ms': 0,
                'metadata': {}
            }
        except Exception as e:
            logger.error(f"RAG query processing failed: {e}")
            raise
