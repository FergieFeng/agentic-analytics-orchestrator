# RAG Module
"""
Retrieval-Augmented Generation components.

Components:
- embedder: Text to vector embeddings (OpenAI)
- vector_store: ChromaDB for vector storage
- indexer: Index knowledge and schema documents
- retriever: Query vectors for relevant context
"""

from .embedder import get_embedder, embed_text, embed_texts
from .vector_store import get_vector_store, VectorStore
from .retriever import retrieve_context, RAGRetriever, get_retriever
from .indexer import index_knowledge_base, is_indexed

__all__ = [
    # Embedder
    "get_embedder",
    "embed_text",
    "embed_texts",
    
    # Vector Store
    "get_vector_store",
    "VectorStore",
    
    # Retriever
    "retrieve_context",
    "RAGRetriever",
    "get_retriever",
    
    # Indexer
    "index_knowledge_base",
    "is_indexed",
]
