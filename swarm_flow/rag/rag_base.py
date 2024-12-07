from abc import ABC, abstractmethod
from typing import List


class RAGBase(ABC):
    def __init__(self):
        """Initialization method"""
        pass

    @abstractmethod
    def init_kb(self, kb_path: str=None):
        """Initialize the vector database, load and process documents"""
        pass

    @abstractmethod
    def encode(self, texts: List[str], batch_size: int=1):
        """Compute the embeddings of texts, compatible with various methods"""
        pass

    @abstractmethod
    def search(self, query_texts: List[str], kb_name: str="default", top_k: int=4):
        """Retrieve relevant content from the vector database based on the query"""
        pass
