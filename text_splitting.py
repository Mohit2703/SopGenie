from load_pdf import LOAD_PDF
from langchain_text_splitters import RecursiveCharacterTextSplitter

class TEXT_SPLITTING:
    def __init__(self, chunk_size: int, chunk_overlap: int, add_start_index: bool):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,  # chunk size (characters)
            chunk_overlap=chunk_overlap,  # chunk overlap (characters)
            add_start_index=add_start_index,  # track index in original document
        )

    def split_texts(self, texts):
        print("texts:", texts)
        return self.text_splitter.split_documents(texts)
    
    def split_pdf(self, file_path):
        load_pdf = LOAD_PDF(file_path)
        docs, metadata = load_pdf.extract_info()
        return self.split_texts(docs), metadata
    
if __name__ == "__main__":
    text_splits = TEXT_SPLITTING(chunk_size=1000, chunk_overlap=200, add_start_index=True)
    pdf_splits, metadata = text_splits.split_pdf("./docs/ERCS_4G_PM_SOP.pdf")
    print("\nSample Chunk:")
    print(pdf_splits)
    print("="*50)
    print("Metadata:")
    print(metadata)
