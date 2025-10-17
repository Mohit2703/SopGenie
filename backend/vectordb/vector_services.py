import os
import time
import hashlib
import logging
import sys
import django
from typing import List, Dict, Any, Optional
from django.conf import settings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sop_rag.settings')
django.setup()
from django.utils import timezone
from vectordb.models import ModuleVectorStore, QueryLog
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
                print(f"Collection '{collection_name}' has been deleted.")
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
            print(f"Vector store for module {vector_store.module.id} has been reset.")
            return True
        except Exception as e:
            print(f"Failed to reset vector store: {e}")
            raise

    def process_document_for_module(self, document: Document, vector_store: ModuleVectorStore = None, chunk_size: int = 1000, chunk_overlap: int = 200) -> Dict[str, Any]:
        """Process a single document and add to module vector store"""
        try:
            print(f"Debug: Starting process_document_for_module for document ID {document.id}")
            print(f"Document title: {document.title}")
            print(f"Document file path: {document.file.path if document.file else 'No file'}")
            # Import here to avoid startup issues
            
            # Load document content
            file_path = document.file.path
            print(f"Resolved file path: {file_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Media root: {getattr(settings, 'MEDIA_ROOT', 'Not set')}")
            print(f"Media URL: {getattr(settings, 'MEDIA_URL', 'Not set')}")

            file_exists = os.path.exists(file_path)
            print(f"File exists: {file_exists}")
            # Check if file physically exists
            if not file_exists:
                actual_files = os.listdir(os.path.dirname(file_path)) if os.path.isdir(os.path.dirname(file_path)) else []
                print(f"File does not exist at path: {file_path}")
                print(f"Abs path: {os.path.abspath(file_path)}")
                print(f"Dir exists: {os.path.isdir(os.path.dirname(file_path))}")
                print(f"Dir contents: {os.listdir(os.path.dirname(file_path)) if os.path.isdir(os.path.dirname(file_path)) else 'N/A'}")
                
                # case - insensitive file systems
                matching_files = [f for f in actual_files if f.lower() == os.path.basename(file_path).lower()]
                if matching_files:
                    print(f"Case mismatch found. Did you mean: {matching_files[0]}?")
                raise FileNotFoundError(f"Document file not found: {file_path}")
            
            # Get file information
            file_size = os.path.getsize(file_path)
            file_name = document.title or os.path.basename(file_path)
            
            print(f"File name: {file_name}, File size: {file_size} bytes")

            from langchain_community.embeddings import HuggingFaceEmbeddings
            from vectordb.create_vector_db import CreateVectorStore

            # Ensure file name has extension
            if not os.path.splitext(file_name)[1] and hasattr(document, 'file_type') and document.file_type:
                file_name = f"{file_name}{document.file_type}"
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'

            print(f"Determined MIME type: {mime_type}")

            model_name = vector_store.embedding_model
            collection_name = vector_store.collection_name
            persist_directory = vector_store.persistence_directory

            print(f"Using embedding model: {model_name}")
            print(f"Using collection name: {collection_name}")
            print(f"Using persistence directory: {persist_directory}")
            print(f"Using persistence directory: {persist_directory}")

            # Ensure directory exists
            os.makedirs(persist_directory, exist_ok=True)

            print(f"Created persistence directory: {persist_directory}")

            create_vector_store = CreateVectorStore(file_path)
            # create_vector_store.embeddings = HuggingFaceEmbeddings(model_name=model_name)
            create_vector_store.load_vector_store(collection_name=collection_name, persist_directory=persist_directory)

            print("creating vector store...")

            result = create_vector_store.create_vector_store()
            
            print(f"Vector store created with {result.get('chunk_count', 0)} chunks and {result.get('token_count', 0)} tokens.")
            return {
                'document_id': document.id,
                'chunk_count': result.get('chunk_count', 0),
                'token_count': result.get('token_count', 0),
                'status': 'success'
            }
            
        except ImportError as e:
            print(f"Required dependencies not installed: {e}")
            raise
        except FileNotFoundError as e:
            print(f"File not found: {e}")
            raise
        except Exception as e:
            print(f"Failed to process document {document.id}: {e}")
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
            print(f"Required dependencies not installed: {e}")
            return [], 0
        except Exception as e:
            print(f"Query failed: {e}")
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
            print(f"RAG query processing failed: {e}")
            raise

if __name__ == "__main__":
    # Simple test to verify setup
    service = VectorDBService()
    print("VectorDBService initialized with embedding model:", service.embedding_model)
    
    document = Document.objects.filter(active=True).first()
    
    if not document:
        print("❌ No active documents found")
        sys.exit(1)
    
    print(f"📄 Document: {document.title}")
    print(f"📁 File: {document.file.name if document.file else 'No file'}")
    
    module = document.module
    print(f"📦 Module: {module.name}")
    
    # Use get_or_create instead of create to avoid IntegrityError
    module_vector_store, created = ModuleVectorStore.objects.get_or_create(
        module=module,
        defaults={
            'collection_name': f"module_{module.id}_{module.name.lower().replace(' ', '_')}",
            'persistence_directory': os.path.join(
                settings.MEDIA_ROOT, 
                'vector_stores', 
                f'module_{module.id}'
            ),
            'embedding_model': service.embedding_model,
            'status': 'empty',
            'chunk_size': 1000,
            'chunk_overlap': 200
        }
    )
    
    if created:
        print(f"✅ Created new vector store: {module_vector_store.collection_name}")
    else:
        print(f"♻️  Using existing vector store: {module_vector_store.collection_name}")
        print(f"   Status: {module_vector_store.status}")
    
    print(f"\n🔄 Processing document...")
    try:
        result = service.process_document_for_module(
            document=document, 
            vector_store=module_vector_store
        )
        
        print(f"\n✅ Success!")
        print(f"   Chunks: {result['chunk_count']}")
        print(f"   Tokens: {result['token_count']}")
        print(f"   Status: {result['status']}")
        
        # Update vector store status
        module_vector_store.status = 'ready'
        module_vector_store.document_count = 1
        module_vector_store.total_chunks = result['chunk_count']
        module_vector_store.total_tokens = result['token_count']
        module_vector_store.save()
        
        print(f"\n📊 Vector store updated:")
        print(f"   Status: {module_vector_store.status}")
        print(f"   Documents: {module_vector_store.document_count}")
        print(f"   Chunks: {module_vector_store.total_chunks}")
        print(f"   Tokens: {module_vector_store.total_tokens}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
