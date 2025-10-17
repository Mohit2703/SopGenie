import os
import base64
import time
import random
import httpx
import uuid
from IPython.display import Image, display
from unstructured.partition.pdf import partition_pdf
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chat_models import init_chat_model
from langchain.schema.document import Document
from langchain_chroma import Chroma
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryStore

os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGCHAIN_API_KEY'] = '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'
os.environ["MISTRAL_API_KEY"] = "AlDrAPD0LXNXU4xMMXaUFIiG5KvWgNUX"

llm = init_chat_model("mistral-small-latest", model_provider="mistralai", temperature=0.0)

class Summarize:
    def __init__(self, file_path):
        self.file_path = file_path
    
    def summarize_chain(self):
        raise NotImplementedError("Subclasses must implement summarize_chain method")
    
    def batch_summarize(self, chunks, concurrency: int = 1):
        raise NotImplementedError("Subclasses must implement batch_summarize method")

class TextSummarize(Summarize):
    def __init__(self, file_path, prompt_text):
        super().__init__(file_path)
        self.prompt = ChatPromptTemplate.from_template(prompt_text)
    
    def summarize_chain(self):
        """Create the summarization chain for text"""
        # FIXED: Added the missing implementation
        chain = self.prompt | llm | StrOutputParser()
        return chain
    
    def batch_summarize(self, chunks, concurrency: int = 1):
        """Summarize multiple chunks in a single API call"""
        print(f"📝 Batch summarizing {len(chunks)} chunks...")
        
        if not chunks:
            return []
        
        try:
            # Extract text from chunks
            texts = []
            for chunk in chunks:
                if isinstance(chunk, dict):
                    text = chunk.get('element', str(chunk))
                elif hasattr(chunk, 'text'):
                    text = chunk.text
                else:
                    text = str(chunk)
                texts.append(text)
            
            # Combine texts with separators
            combined_text = "\n\n---CHUNK_SEPARATOR---\n\n".join(texts)
            
            # Create prompt
            prompt_text = f"""Summarize each of the following text chunks separated by '---CHUNK_SEPARATOR---'.
Return the summaries in order, separated by '---SUMMARY_SEPARATOR---'.

Text chunks:
{combined_text}

Summaries (one for each chunk, separated by '---SUMMARY_SEPARATOR---'):"""
            
            # Get chain and invoke
            chain = self.summarize_chain()
            result = chain.invoke({"element": prompt_text})

            time.sleep(10)  # To avoid rate limits
            
            # Parse result
            if "---SUMMARY_SEPARATOR---" in result:
                summaries = result.split("---SUMMARY_SEPARATOR---")
                summaries = [s.strip() for s in summaries if s.strip()]
                print(f"✅ Generated {len(summaries)} summaries")
            else:
                # If no separator, treat whole response as single summary
                summaries = [result.strip()]
                print(f"⚠️  Single summary generated for {len(chunks)} chunks")
            
            # Ensure we have same number of summaries as chunks
            while len(summaries) < len(chunks):
                summaries.append(summaries[-1] if summaries else "No summary available")
            
            return summaries[:len(chunks)]
            
        except Exception as e:
            print(f"❌ Batch summarization failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: return truncated text
            return [str(chunk).get('element', str(chunk))[:500] + "..." 
                    if isinstance(chunk, dict) 
                    else getattr(chunk, 'text', str(chunk))[:500] + "..." 
                    for chunk in chunks]
    
    def summarize(self, chunks):
        """Main summarize method"""
        if not chunks:
            return []
        
        # Single chunk
        if len(chunks) == 1:
            try:
                chain = self.summarize_chain()
                chunk = chunks[0]
                
                # Extract text
                if isinstance(chunk, dict):
                    text = chunk.get('element', str(chunk))
                elif hasattr(chunk, 'text'):
                    text = chunk.text
                else:
                    text = str(chunk)
                
                result = chain.invoke({"element": text})
                return [result]
            except Exception as e:
                print(f"❌ Single chunk summarization failed: {e}")
                chunk = chunks[0]
                text = chunk.get('element', str(chunk)) if isinstance(chunk, dict) else str(chunk)
                return [text[:500] + "..."]
        
        time.sleep(10)
        # Multiple chunks
        return self.batch_summarize(chunks)

class ImageSummarize(Summarize):
    def __init__(self, file_path, prompt_image):
        super().__init__(file_path)
        messages = [
            (
                "user",
                [
                    {"type": "text", "text": prompt_image},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,{image}"},
                    },
                ],
            )
        ]
        self.prompt = ChatPromptTemplate.from_messages(messages)
    
    def summarize_chain(self):
        """Create the summarization chain for images"""
        def get_image_base64(x):
            if hasattr(x, 'metadata'):
                if hasattr(x.metadata, 'image_base64'):
                    return x.metadata.image_base64
                elif isinstance(x.metadata, dict) and 'image_base64' in x.metadata:
                    return x.metadata['image_base64']
            return ""
        
        chain = {"image": get_image_base64} | self.prompt | llm | StrOutputParser()
        return chain
    
    def batch_summarize(self, chunks, concurrency: int = 1):
        """Batch summarize images"""
        valid_chunks = []
        for chunk in chunks:
            has_image = False
            if hasattr(chunk, 'metadata'):
                if hasattr(chunk.metadata, 'image_base64') and chunk.metadata.image_base64:
                    has_image = True
                elif isinstance(chunk.metadata, dict) and chunk.metadata.get('image_base64'):
                    has_image = True
            
            if has_image:
                valid_chunks.append(chunk)
            else:
                print(f"⚠️  Skipping image chunk without base64 data")
        
        if not valid_chunks:
            return []
        
        try:
            chain = self.summarize_chain()
            summaries = chain.batch(valid_chunks, {"max_concurrency": concurrency})
            time.sleep(10)  # To avoid rate limits
            return summaries
        except Exception as e:
            print(f"❌ Image batch summarization failed: {e}")
            return ["[Image description unavailable]" for _ in valid_chunks]

class SummarizeFactory:
    @staticmethod
    def get_summarizer(file_path, prompt, summarize_type="text"):
        if summarize_type == "text":
            return TextSummarize(file_path, prompt)
        elif summarize_type == "image":
            return ImageSummarize(file_path, prompt)
        else:
            raise ValueError(f"Unknown summarize type: {summarize_type}")

class CreateVectorStore:
    def __init__(self, file_path, max_characters=10000, combine_text_under_n_chars=2000, new_after_n_chars=6000):
        self.chunks = partition_pdf(
            filename=file_path,
            infer_table_structure=True,
            strategy="hi_res",
            extract_image_block_types=["Image"],
            extract_images_in_pdf=True,
            extract_image_block_to_payload=True,
            max_characters=max_characters,
            combine_text_under_n_chars=combine_text_under_n_chars,
            new_after_n_chars=new_after_n_chars,
        )
        
        self.text_prompt = """Summarize the following text. 
For context, the text is part of a SOP documentation. 
Be specific about commands and code snippets. 
Just return the summary.

Text:
{element}
"""
        self.text_summarizer = SummarizeFactory.get_summarizer(file_path, self.text_prompt, "text")
        
        self.image_prompt = """Describe the image in detail. For context, the image is part of a SOP documentation. Be specific about screenshots of console and code. Just return the description and summary."""
        self.image_summarizer = SummarizeFactory.get_summarizer(file_path, self.image_prompt, "image")
        
        self.id_key = "doc_id"
        self.store = InMemoryStore()
    
    def load_vector_store(self, collection_name, persist_directory, embedding_model_name="all-MiniLM-L6-v2"):
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=HuggingFaceEmbeddings(model_name=embedding_model_name),
            persist_directory=persist_directory,
        )
        self.retriever = MultiVectorRetriever(
            vectorstore=self.vector_store,
            docstore=self.store,
            id_key=self.id_key,
        )
    
    def summarize(self, chunks):
        """Summarize chunks (text or image)"""
        if not chunks:
            return []
        
        chunk = chunks[0] if isinstance(chunks, list) else chunks
        
        # Check if it's an image chunk
        if "Image" in str(type(chunk)):
            print(f"Processing {len(chunks) if isinstance(chunks, list) else 1} image chunk(s)...")
            image_summaries = self.image_summarizer.batch_summarize(chunks if isinstance(chunks, list) else [chunks])
            print(f"✅ Image summaries: {len(image_summaries)}")
            return image_summaries
        else:
            # Text chunks
            processed_chunks = []
            for c in (chunks if isinstance(chunks, list) else [chunks]):
                if hasattr(c, 'text'):
                    processed_chunks.append({"element": c.text})
                else:
                    processed_chunks.append({"element": str(c)})
            
            print(f"Processing {len(processed_chunks)} text chunk(s)...")
            text_summaries = self.text_summarizer.batch_summarize(processed_chunks)
            print(f"✅ Text summaries: {len(text_summaries)}")
            return text_summaries
    
    def create_vector_store(self):
        """Create vector store with optimized batching"""
        summaries = []
        summary_docs = []
        txt_chunks = []
        doc_ids = []
        
        BATCH_SIZE = 20  # Reduced to avoid rate limits
        total_chunks = len(self.chunks)
        
        print(f"📊 Total chunks to process: {total_chunks}")
        print(f"📦 Batch size: {BATCH_SIZE} chunks per API call")
        
        for i, chunk in enumerate(self.chunks):
            if "Image" in str(type(chunk)):
                # Process accumulated text first
                if txt_chunks:
                    print(f"🔄 Processing batch of {len(txt_chunks)} text chunks...")
                    text_summaries = self.summarize(txt_chunks)
                    
                    for summary in text_summaries:
                        doc_id = str(uuid.uuid4())
                        summaries.append(summary)
                        summary_docs.append(Document(
                            page_content=summary,
                            metadata={self.id_key: doc_id}
                        ))
                        doc_ids.append(doc_id)
                    
                    txt_chunks = []
                    import gc; gc.collect()
                    time.sleep(20)
                
                # Process image
                print(f"🖼️  Processing image chunk {i+1}/{total_chunks}")
                image_summaries = self.summarize([chunk])
                for summary in image_summaries:
                    doc_id = str(uuid.uuid4())
                    summaries.append(summary)
                    summary_docs.append(Document(
                        page_content=summary,
                        metadata={self.id_key: doc_id}
                    ))
                    doc_ids.append(doc_id)
                time.sleep(20)
            
            else:
                txt_chunks.append(chunk)
                
                if len(txt_chunks) >= BATCH_SIZE:
                    print(f"🔄 Processing batch at chunk {i+1}/{total_chunks}")
                    text_summaries = self.summarize(txt_chunks)
                    
                    for summary in text_summaries:
                        doc_id = str(uuid.uuid4())
                        summaries.append(summary)
                        summary_docs.append(Document(
                            page_content=summary,
                            metadata={self.id_key: doc_id}
                        ))
                        doc_ids.append(doc_id)
                    
                    print(f"✅ Progress: {((i+1)/total_chunks)*100:.1f}%")
                    txt_chunks = []
                    import gc; gc.collect()
                    time.sleep(20)
        
        # Process remaining
        if txt_chunks:
            print(f"🔄 Processing final batch of {len(txt_chunks)} chunks...")
            text_summaries = self.summarize(txt_chunks)
            
            for summary in text_summaries:
                doc_id = str(uuid.uuid4())
                summaries.append(summary)
                summary_docs.append(Document(
                    page_content=summary,
                    metadata={self.id_key: doc_id}
                ))
                doc_ids.append(doc_id)
        
        print(f"\n✅ Summarization complete! Generated {len(summaries)} summaries")
        
        # Store in vector database
        print("💾 Storing in vector database...")
        self.retriever.vectorstore.add_documents(summary_docs)
        self.retriever.docstore.mset(list(zip(doc_ids, self.chunks)))
        print("✅ Vector store creation complete!")
        
        return {
            "total_original_chunks": total_chunks,
            "total_summaries": len(summaries),
            "summaries": summaries,
            "chunk_count": total_chunks,
            "token_count": sum(len(str(s).split()) for s in summaries)
        }

def main_create_vector_db(file_path, model_name, collection_name, persist_directory):
    print("Creating vector store...")
    print(f"File path: {file_path}")
    create_vector_store = CreateVectorStore(file_path)
    create_vector_store.load_vector_store(
        collection_name=collection_name,
        persist_directory=persist_directory,
        embedding_model_name=model_name
    )
    return create_vector_store.create_vector_store()
