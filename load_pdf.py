from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.parsers import RapidOCRBlobParser
import pprint

class LOAD_PDF:
    def __init__(self, file_path):
        self.file_path = file_path

    def load_pdf(self):
        loader = PyPDFLoader(
            self.file_path,
            mode="page",
            images_inner_format="markdown-img",
            images_parser=RapidOCRBlobParser(),
        )
        
        return loader.load()
    
    def extract_info(self):
        docs = self.load_pdf()
        print("Loaded PDF documents:", docs)
        file_metadata = docs[0].metadata
        print("File Metadata:", file_metadata)
        metadata = {
            "source": file_metadata.get("source", ""),
            "author": file_metadata.get("author", ""),
            "created": file_metadata.get("created", ""),
            "last_updated": file_metadata.get("moddate", ""),
            "total_pages": file_metadata.get("total_pages", 0)
        }
        return docs, metadata

if __name__ == "__main__":
    file_path = "./docs/ERCS_4G_PM_SOP.pdf"
    pdf_loader = LOAD_PDF(file_path)
    texts, metadata = pdf_loader.extract_info()
    print("Extracted Texts:")
    for text in texts:
        print(text)
    print("\nMetadata:")
    pprint.pprint(metadata)
