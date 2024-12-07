import numpy as np
import chromadb
from typing import List

from .rag_base import RAGBase
from .semchunk import chunkerify

"""
# rag_settings example:

rag_settings = {
    "openai": {
        "base_url": "",
        "api_key": "",
        "embedding_model": "text-embedding-3-small",
    },
    "ollama": {
        "host": "localhost:11434",
        "embedding_model": "all-minilm",
    },
    "local": {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    },
}
"""

class RAGSimple(RAGBase):
    def __init__(self, rag_settings: dict, rag_provider: str, kb_path: str=None):
        """Initialize custom RAG module"""
        super().__init__()
        self.rag_provider = rag_provider
        self.rag_params = rag_settings[rag_provider]
        self.embedding_model = self.rag_params["embedding_model"]
        self.collections = {}

        # Initialize embedding model
        if self.rag_provider == "local":
            from sentence_transformers import SentenceTransformer
            self.client = SentenceTransformer(self.embedding_model)
        elif self.rag_provider == "openai":
            import openai
            self.client = openai
            self.client.api_key = self.rag_params["api_key"]
            base_url = self.rag_params.get("base_url")
            if base_url and len(base_url) > 0:
                self.client.api_base = base_url
        elif self.rag_provider == "ollama":
            import ollama
            # Initialize Ollama API
            self.client = ollama.Client(host=self.rag_params["host"])
        else:
            raise ValueError(f"Unsupported embedding method: {self.rag_provider}")

        self.kb_client = None
        self.init_kb(kb_path)

    def init_kb(self, kb_path: str=None):
        """Initialize knowledge base"""
        if kb_path is None:
            self.kb_client = chromadb.Client()
        else:
            self.kb_client = chromadb.PersistentClient(path=kb_path)

    def encode(self, texts: List[str], batch_size: int=16):
        """Compute text embeddings, compatible with various methods"""
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            if self.rag_provider == "local":
                # Use SentenceTransformer to get batch embeddings
                batch_embeddings = self.client.encode(batch_texts, show_progress_bar=True)
            elif self.rag_provider == "openai":
                # Use OpenAI API to get batch embeddings
                response = self.client.embeddings.create(
                    input=batch_texts,
                    model=self.embedding_model
                )
                batch_embeddings = [item.embedding for item in response.data]
            elif self.rag_provider == "ollama":
                # Use Ollama API to get batch embeddings
                batch_embeddings = self.client.embed(self.embedding_model, batch_texts)["embeddings"]
            else:
                raise ValueError(f"Unsupported embedding method: {self.rag_provider}")
            embeddings.extend(batch_embeddings)
        embeddings = np.array(embeddings, dtype="float32")

        return embeddings

    def search(self, query_texts: list[str], kb_name: str="default", top_k: int=4):
        """Retrieve the most relevant document content based on the query"""
        if self.collections.get(kb_name) is None:
            self.collections[kb_name] = self.kb_client.get_or_create_collection(name=kb_name)

        results = self.collections[kb_name].query(
            query_embeddings=self.encode(query_texts),
            query_texts=query_texts,
            n_results=top_k
        )
        return results

    def kb_exists(self, kb_name: str="default"):
        """Check if the knowledge base exists"""
        try:
            collection = self.kb_client.get_collection(kb_name)
            if collection:
                self.collections[kb_name] = collection
                return True
        except:
            pass
        return False

    def read_pdf(self, pdf_path: str, fix_break_line: bool=True):
        """Read a PDF document and extract text"""
        text = ""
        try:
            import fitz  # PyMuPDF
            # Open the PDF file
            document = fitz.open(pdf_path)
            # Iterate over each page
            for page_num in range(len(document)):
                page = document[page_num]
                text += page.get_text()

            if not fix_break_line:
                return text

            # Fix forced line breaks
            text_fix = ""
            break_line = False
            for line in text.split("\n"):
                l = line.strip()
                if len(l) < 1:
                    break_line = False
                    text_fix += "\n"
                    continue
                if break_line:
                    text_fix += l
                else:
                    text_fix += "\n" + l
                if len(l) > 20 and l[-1] not in '。！？':
                    break_line = True
                else:
                    break_line = False
            return text_fix
        except ImportError:
            print("'PyMuPDF' needs to be installed to read PDF files.")
        return text

    def add_texts(self, texts: List[str], metadatas: list[dict]=None, kb_name: str="default"):
        if self.collections.get(kb_name) is None:
            self.collections[kb_name] = self.kb_client.get_or_create_collection(name=kb_name)

        count = self.collections[kb_name].count()
        ids = [f"{i}" for i in range(count, count+len(texts))]
        self.collections[kb_name].add(
            embeddings=self.encode(texts),
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def add_documents(self, document_paths: List[str], chunk_size: int=500, kb_name: str="default"):
        """Load documents and build vector database"""
        texts = []
        for doc_path in document_paths:
            if doc_path.endswith(".txt"):
                with open(doc_path, "r", encoding="utf-8") as f:
                    text = f.read()
            elif doc_path.endswith(".pdf"):
                text = self.read_pdf(doc_path)
            else:
                print(f"Unsupported file format: {doc_path}")
                return
            chunker = chunkerify(lambda text: len(text), chunk_size)
            texts.extend(chunker(text, progress=True))
            metadatas = [{"source": doc_path} for _ in range(len(texts))]
            self.add_texts(texts, metadatas, kb_name)
