import os
import base64
from pyexpat.errors import messages
from IPython.display import Image, display
from unstructured.partition.pdf import partition_pdf
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chat_models import init_chat_model
import uuid
from langchain.schema.document import Document
from langchain_chroma import Chroma
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryStore
import time, random, httpx


os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGCHAIN_API_KEY'] = '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'
os.environ["MISTRAL_API_KEY"] = "hrDF1J8v9kDfT9UZXss6oCXoJk46AZNO"
llm = init_chat_model("mistral-small-latest", model_provider="mistralai", temperature=0.0)
output_path = "./content"
file_path = "./docs/ERCS_4G_PM_SOP.pdf"
    
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

    def safe_batch(self, chain, chunks, concurrency=1, retries=5):
        for i in range(retries):
            try:
                return chain.batch(chunks, {"max_concurrency": concurrency})
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = (2 ** i) + random.random()
                    print(f"429 rate limit hit. Retrying in {wait:.2f}s...")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError("Max retries exceeded for summarization")
    
    def summarize_chain(self):
        # Summary chain
        summarize_chain = (
            {"element": lambda x: getattr(x, "text", str(x))}
            | self.prompt   # now prompt has {element} placeholder
            | llm
            | StrOutputParser()
        )
        return summarize_chain

    
    def batch_summarize(self, chunks, concurrency: int = 1):
        print("Starting batch summarization...")
        print(f"Number of chunks to summarize: {len(chunks)}", chunks)
        chain = self.summarize_chain()
        summaries = chain.batch(chunks, {"max_concurrency": concurrency})
        print("Completed batch summarization.")
        return summaries
        # return self.safe_batch(chain, chunks, concurrency)

class ImageSummarize(Summarize):
    def __init__(self, file_path, prompt_image):
        super().__init__(file_path)
        messages = [(
                "user",
                [
                    {"type": "text", "text": prompt_image},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,{image}"},
                    },
                ],
            )]
        self.prompt = ChatPromptTemplate.from_messages(messages)
    
    def summarize_chain(self):
        summarize_chain = {"image": lambda x: x.metadata.image_base64} | self.prompt | llm | StrOutputParser()
        return summarize_chain
    
    def batch_summarize(self, chunks, concurrency: int = 1):
        chain = self.summarize_chain()
        summaries = chain.batch(chunks, {"max_concurrency": concurrency})
        return summaries


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
                For context, the text is part of a sop documentation. 
                Be specific about commands and code snippets. 
                Just return the summary.

                Text:
                {element}
                """
        self.text_summarizer = SummarizeFactory.get_summarizer(file_path, self.text_prompt, "text")
        self.image_prompt = """Describe the image in detail. For context, the image is part of a sop documentation. Be specific about screenshots of console and code. just return the description and summary."""
        self.image_summarizer = SummarizeFactory.get_summarizer(file_path, self.image_prompt, "image")
        self.id_key = "doc_id"
        self.store = InMemoryStore()

    def load_vector_store(self, collection_name, persist_directory):
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
        )
        self.retriever = MultiVectorRetriever(
            vectorstore=self.vector_store,
            docstore=self.store,
            id_key=self.id_key,
        )

    def summarize(self, chunk):
        if type(chunk) == list:
            processed_chunks = [{"element": getattr(c, "text", str(c))} for c in chunk]
            print("Processing text chunks: ", len(processed_chunks), "chunks", processed_chunks)
            text_summary = self.text_summarizer.batch_summarize(processed_chunks)
            print("Text Summary: ", text_summary)
            return text_summary
        elif "Image" in str(type(chunk)):
            image_summary = self.image_summarizer.batch_summarize([chunk])
            print("Image Summary: ", image_summary)
            return image_summary
        else:
            processed_chunk = [{"element": getattr(chunk, "text", str(chunk))}]
            print("Processing text chunks: ", len(processed_chunk), "chunks", processed_chunk)
            text_summary = self.text_summarizer.batch_summarize(processed_chunk)
            print("Text Summary: ", text_summary)
            return text_summary
    
    def create_vector_store(self):
        summaries = []
        summary_docs = []
        txt_chunks = []
        doc_ids = []

        total_chunks = len(self.chunks)
        print(f"Total chunks to process: {total_chunks}")

        for i, chunk in enumerate(self.chunks):
            if "Image" in str(type(chunk)):
                # Flush pending text chunks first
                if txt_chunks:
                    text_summary = self.summarize(txt_chunks)
                    if text_summary:
                        for s in text_summary:  # flatten results
                            doc_id = str(uuid.uuid4())
                            summaries.append(s)
                            summary_docs.append(Document(page_content=s, metadata={self.id_key: doc_id}))
                            doc_ids.append(doc_id)
                            time.sleep(5)  # To avoid rate limiting
                    txt_chunks = []

                # Summarize image
                image_summary = self.summarize(chunk)
                if image_summary:
                    for s in image_summary:
                        doc_id = str(uuid.uuid4())
                        summaries.append(s)
                        summary_docs.append(Document(page_content=s, metadata={self.id_key: doc_id}))
                        doc_ids.append(doc_id)
                        time.sleep(5)  # To avoid rate limiting
                print(f"Processed chunk {i+1}/{total_chunks} (Image)")

            else:
                txt_chunks.append(chunk)

                # Group every 5 text chunks
                if len(txt_chunks) == 500:
                    text_summary = self.summarize(txt_chunks)
                    if text_summary:
                        for s in text_summary:
                            doc_id = str(uuid.uuid4())
                            summaries.append(s)
                            summary_docs.append(Document(page_content=s, metadata={self.id_key: doc_id}))
                            doc_ids.append(doc_id)
                            time.sleep(5)  # To avoid rate limiting
                    txt_chunks = []
                print(f"Processed chunk {i+1}/{total_chunks} (Text)")

        # Handle leftover text chunks
        if txt_chunks:
            text_summary = self.summarize(txt_chunks)
            if text_summary:
                for s in text_summary:
                    doc_id = str(uuid.uuid4())
                    summaries.append(s)
                    summary_docs.append(Document(page_content=s, metadata={self.id_key: doc_id}))
                    doc_ids.append(doc_id)
                    time.sleep(5)  # To avoid rate limiting
        print(f"Processed all {total_chunks} chunks.")

        # Store in vector DB
        self.retriever.vectorstore.add_documents(summary_docs)
        self.retriever.docstore.mset(list(zip(doc_ids, self.chunks)))

        token_count = sum(len(chunk.split()) for chunk in self.chunks)
        return {
            'chunk_count': len(self.chunks),
            'token_count': token_count,
        }


def main_create_vector_db(file_path, model_name, collection_name, persist_directory):
    create_vector_store = CreateVectorStore(file_path)
    create_vector_store.embeddings = HuggingFaceEmbeddings(model_name=model_name)
    create_vector_store.load_vector_store(collection_name=collection_name, persist_directory=persist_directory)
    create_vector_store.create_vector_store()

if __name__ == "__main__":
    main_create_vector_db(
        file_path=file_path,
        model_name="all-MiniLM-L6-v2",
        collection_name="my_pdf_collection",
        persist_directory="./pdf_chroma_db"
    )
