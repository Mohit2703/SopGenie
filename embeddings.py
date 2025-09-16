import os
from langchain.chat_models import init_chat_model
from langchain_mistralai import MistralAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from text_splitting import TEXT_SPLITTING

os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGCHAIN_API_KEY'] = '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'
os.environ["MISTRAL_API_KEY"] = "hrDF1J8v9kDfT9UZXss6oCXoJk46AZNO"

class CREATE_VECTOR_DB:
    def __init__(self, model_name: str, model_provider: str, temperature: float):
        self.llm = init_chat_model("mistral-large-latest", model_provider=model_provider, temperature=temperature)

        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)

    def load_model(self, collection_name, persist_directory):
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
        )

        return self.vector_store
    
    def llm_model(self):
        return self.llm
    
    def create_vector_db(self, split_texts):
        doc_ids = self.vector_store.add_documents(documents=split_texts)
        return doc_ids

class VECTOR_DB_PDF:
    def __init__(self, model_name: str, model_provider: str, temperature: float, collection_name: str, persist_directory: str):
        self.create_vector_db = CREATE_VECTOR_DB(model_name, model_provider, temperature)
        self.create_vector_db.load_model(collection_name, persist_directory)

    def process_pdf(self, file_path: str, chunk_size: int, chunk_overlap: int, add_start_index: bool):
        text_splitter = TEXT_SPLITTING(chunk_size=chunk_size, chunk_overlap=chunk_overlap, add_start_index=add_start_index)
        split_texts = text_splitter.split_pdf(file_path)
        split_texts = split_texts[0]
        doc_ids = self.create_vector_db.create_vector_db(split_texts)
        return doc_ids


if __name__ == "__main__":
    load_vector_db_pdf = VECTOR_DB_PDF(
        model_name="all-MiniLM-L6-v2",
        model_provider="mistralai",
        temperature=0.0,
        collection_name="my_pdf_collection",
        persist_directory="./chroma_db"
    )
    document_ids = load_vector_db_pdf.process_pdf(
        file_path="./docs/ERCS_4G_PM_SOP.pdf",
        chunk_size=500,
        chunk_overlap=50,
        add_start_index=True
    )
    print(f"Document IDs: {document_ids}")