import os
import sys

import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sop_rag.settings')

import django
django.setup()

from django.conf import settings

os.environ['LANGCHAIN_TRACING_V2'] = settings.LANGCHAIN_TRACING_V2
os.environ['LANGCHAIN_ENDPOINT'] = settings.LANGCHAIN_ENDPOINT
os.environ['LANGCHAIN_API_KEY'] = settings.LANGCHAIN_API_KEY
os.environ["MISTRAL_API_KEY"] = settings.MISTRAL_API_KEY

from langchain_core.documents import Document
from typing_extensions import List, TypedDict
from langchain_chroma import Chroma
from langchain.chat_models import init_chat_model
from langgraph.graph import START, StateGraph
import threading
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryStore
from langchain import hub 
from langchain.prompts.chat import ChatPromptTemplate

class State(TypedDict):
    question: str
    context: List[Document]
    previous_chat: List[dict]
    answer: str
                                                                                        
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

class Retrieval:
    def __init__(self, collection_name: str, persist_directory: str, embedding_model_name: str = "all-MiniLM-L6-v2", model_provider: str = "mistralai", temperature: float = 0.0):
        self.vector_store_db = CREATE_VECTOR_DB(
            model_name=embedding_model_name,
            model_provider=model_provider,
            temperature=temperature,
        )
        self.vector_store = self.vector_store_db.load_model(
            collection_name=collection_name,
            persist_directory=persist_directory
        )
        self.llm = self.vector_store_db.llm_model()
        prompt_text = """Answer the question based on the context below and previous chat history.
            If the answer is not contained within the text below, say "I don't know".

            Context:
            {context}

            Previous Chat History:
            {previous_chat}

            Question: {question}

            Answer:"""
                    
        self.prompt = ChatPromptTemplate.from_template(prompt_text)

    def retrieve(self, state: State):
        similarity_text = f"""
        Previous Chat History: {state["previous_chat"]}
        Question: {state["question"]}
        Answer:
        """
        retrieved_docs = self.vector_store.similarity_search(similarity_text)
        return {"context": retrieved_docs}


    def generate(self, state: State):
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
        messages = self.prompt.invoke({"question": state["question"], "context": docs_content, "previous_chat": state["previous_chat"]})
        response = self.llm.invoke(messages)
        return {"answer": response.content}
    
class Graph:
    def __init__(self, collection_name: str, persist_directory: str, embedding_model_name: str = "all-MiniLM-L6-v2", model_provider: str = "mistralai", temperature: float = 0.0):
        self.retrieval = Retrieval(
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedding_model_name=embedding_model_name,
            model_provider=model_provider,
            temperature=temperature
        )

    def retrieve(self, state: State):
        return self.retrieval.retrieve(state)

    def generate(self, state: State):
        return self.retrieval.generate(state)
    
    def graph_builder(self):
        graph_builder = StateGraph(State).add_sequence([self.retrieve, self.generate])
        graph_builder.add_edge(START, "retrieve")
        graph = graph_builder.compile()
        return graph

def singleton(cls):
    """Singleton decorator"""
    instances = {}
    lock = threading.Lock()
    
    def get_instance(*args, **kwargs):
        # Create key from collection_name
        key = kwargs.get('collection_name', args[0] if args else None)
        
        with lock:
            if key not in instances:
                print(f"🆕 Creating instance for: {key}")
                instances[key] = cls(*args, **kwargs)
            else:
                print(f"♻️  Reusing instance for: {key}")
        
        return instances[key]
    
    return get_instance

@singleton
class RUN_GRAPH:
    def __init__(self, collection_name: str, persist_directory: str, 
                 embedding_model_name: str = "all-MiniLM-L6-v2", 
                 model_provider: str = "mistralai", 
                 temperature: float = 0.0):
        
        print(f"🚀 Initializing graph for: {collection_name}")
        
        self.collection_name = collection_name
        self.graph = Graph(
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedding_model_name=embedding_model_name,
            model_provider=model_provider,
            temperature=temperature
        ).graph_builder()
        
        print("✅ Graph initialized")
    
    def run(self, question: str, previous_chat: List[dict] = []):
        result = self.graph.invoke({
            "question": question,
            "previous_chat": previous_chat
        })
        print(f"Answer: {result['answer']}")
        return result


if __name__ == "__main__":
    persist_directory = "/media/mohit/storage/projects/SOP_RAG/backend/vector_data/project_1/"
    collection_name = "module_3_vector_store"
    run_graph = RUN_GRAPH(
        collection_name=collection_name,
        persist_directory=persist_directory,
        embedding_model_name="all-MiniLM-L6-v2",
        model_provider="mistralai",
        temperature=0.0
    )
    run_graph.run(question="How we are parsisg large xml files?", previous_chat=[])

