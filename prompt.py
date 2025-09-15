from langgraph.graph import START, StateGraph
from langchain_core.documents import Document
from typing_extensions import List, TypedDict
from langchain import hub
from embeddings import CREATE_VECTOR_DB

class State(TypedDict):
    question: str
    context: List[Document]
    answer: str


class Retrieval:
    def __init__(self):
        self.vector_store_db = CREATE_VECTOR_DB(
            model_name="all-MiniLM-L6-v2",
            model_provider="mistralai",
            temperature=0.0,
        )
        self.vector_store = self.vector_store_db.load_model(
            collection_name="my_pdf_collection",
            persist_directory="./chroma_db"
        )
        self.llm = self.vector_store_db.llm_model()
        self.prompt = hub.pull("rlm/rag-prompt")

    def retrieve(self, state: State):
        retrieved_docs = self.vector_store.similarity_search(state["question"])
        return {"context": retrieved_docs}


    def generate(self, state: State):
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
        messages = self.prompt.invoke({"question": state["question"], "context": docs_content})
        response = self.llm.invoke(messages)
        return {"answer": response.content}

class Graph:
    def __init__(self):
        self.retrieval = Retrieval()

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
    def __init__(self):
        self.graph = Graph().graph_builder()
    def run(self, question: str):
        result = self.graph.invoke({"question": question})
        print(f"Context: {result['context']}\n\n")
        print(f"Answer: {result['answer']}")

if __name__ == "__main__":
    run_graph = RUN_GRAPH()
    run_graph.run("How we parse large xml files?")
    #run_graph.run("What is the purpose of the ERCS 4G PM SOP document?")


