from langgraph.graph import START, StateGraph
from langchain_core.documents import Document
from typing_extensions import List, TypedDict
from langchain import hub
from langchain.chat_models import init_chat_model
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


class State(TypedDict):
    question: str
    context: List[Document]
    answer: str


class CREATE_VECTOR_DB:
    def __init__(self, chat_model_name: str, model_name: str, model_provider: str, temperature: float):
        self.llm = init_chat_model(chat_model_name, model_provider=model_provider, temperature=temperature)

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
    def __init__(self, chat_model_name, model_name, model_provider, temperature, persist_directory, collection_name, k=5, score_threshold=0.7):
        self.vector_store_db = CREATE_VECTOR_DB(
            chat_model_name=chat_model_name,
            model_name=model_name,
            model_provider=model_provider,
            temperature=temperature,
        )
        self.vector_store = self.vector_store_db.load_model(
            collection_name=collection_name,
            persist_directory=persist_directory
        )
        self.llm = self.vector_store_db.llm_model()
        self.prompt = hub.pull("rlm/rag-prompt")
        self.k = k
        self.score_threshold = score_threshold 

    def retrieve(self, state: State):
        retrieved_docs = self.vector_store.similarity_search(state["question"], k=self.k, score_threshold=self.score_threshold)
        for doc in retrieved_docs:
            print(f"Retrieved Document: {doc.page_content}\n")
        return {"context": retrieved_docs}


    def generate(self, state: State):
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
        messages = self.prompt.invoke({"question": state["question"], "context": docs_content})
        response = self.llm.invoke(messages)
        return {"answer": response.content}

class Graph:
    def __init__(self, chat_model_name, model_name, model_provider, temperature, persist_directory, collection_name, k=5, score_threshold=0.7):
        self.retrieval = Retrieval(
            chat_model_name=chat_model_name,
            model_name=model_name,
            model_provider=model_provider,
            temperature=temperature,
            persist_directory=persist_directory,
            collection_name=collection_name,
            k=k,
            score_threshold=score_threshold
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
    
class RUN_GRAPH:
    def __init__(self, chat_model_name, model_name, model_provider, temperature, persist_directory, collection_name, k=5, score_threshold=0.7):
        self.graph = Graph(
            chat_model_name=chat_model_name,
            model_name=model_name,
            model_provider=model_provider,
            temperature=temperature,
            persist_directory=persist_directory,
            collection_name=collection_name,
            k=k,
            score_threshold=score_threshold
        ).graph_builder()
    def run(self, question: str):
        result = self.graph.invoke({"question": question})
        return result
        print(f"Context: {result['context']}\n\n")
        print(f"Answer: {result['answer']}")

if __name__ == "__main__":
    run_graph = RUN_GRAPH()
    run_graph.run("how we handle iceberg snapshots for incremental data loading to druid in cm tables?")
    #run_graph.run("What is the purpose of the ERCS 4G PM SOP document?")


