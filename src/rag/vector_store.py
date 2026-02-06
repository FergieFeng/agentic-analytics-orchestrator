"""
Vector Store: ChromaDB-based vector storage for RAG.

Provides persistent local storage for document embeddings.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config.settings import settings
from .embedder import get_embedder


# ChromaDB storage path
CHROMA_DB_PATH = settings.project_root / "data" / "chroma_db"

# Collection names
KNOWLEDGE_COLLECTION = "knowledge"
SCHEMA_COLLECTION = "schema"
HISTORY_COLLECTION = "query_history"


@dataclass
class SearchResult:
    """A single search result from the vector store."""
    id: str
    content: str
    metadata: Dict[str, Any]
    distance: float  # Lower is more similar
    
    @property
    def score(self) -> float:
        """Convert distance to similarity score (0-1)."""
        # ChromaDB returns L2 distance, convert to similarity
        return 1 / (1 + self.distance)


class VectorStore:
    """
    ChromaDB-based vector store for RAG retrieval.
    
    Usage:
        store = VectorStore()
        
        # Add documents
        store.add_documents(
            collection="knowledge",
            documents=["text1", "text2"],
            metadatas=[{"type": "glossary"}, {"type": "metric"}],
            ids=["doc1", "doc2"]
        )
        
        # Search
        results = store.search("what is net flow?", collection="knowledge", k=3)
    """
    
    def __init__(self, persist_directory: Optional[Path] = None):
        self.persist_directory = persist_directory or CHROMA_DB_PATH
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self._client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Cache for collections
        self._collections: Dict[str, Any] = {}
    
    def _get_collection(self, name: str):
        """Get or create a collection."""
        if name not in self._collections:
            embedder = get_embedder()
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
        return self._collections[name]
    
    def add_documents(
        self,
        collection: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> int:
        """
        Add documents to a collection.
        
        Args:
            collection: Collection name
            documents: List of text documents
            metadatas: Optional metadata for each document
            ids: Optional IDs (auto-generated if not provided)
            
        Returns:
            Number of documents added
        """
        if not documents:
            return 0
        
        coll = self._get_collection(collection)
        
        # Generate IDs if not provided
        if ids is None:
            existing_count = coll.count()
            ids = [f"{collection}_{existing_count + i}" for i in range(len(documents))]
        
        # Ensure metadatas exist
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        # Get embeddings
        embedder = get_embedder()
        embeddings = embedder.embed_documents(documents)
        
        # Add to collection
        coll.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(documents)
    
    def search(
        self,
        query: str,
        collection: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: Query text
            collection: Collection to search
            k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of SearchResult objects
        """
        coll = self._get_collection(collection)
        
        if coll.count() == 0:
            return []
        
        # Get query embedding
        embedder = get_embedder()
        query_embedding = embedder.embed_query(query)
        
        # Build query args
        query_args = {
            "query_embeddings": [query_embedding],
            "n_results": min(k, coll.count()),
            "include": ["documents", "metadatas", "distances"]
        }
        
        if filter_metadata:
            query_args["where"] = filter_metadata
        
        # Execute search
        results = coll.query(**query_args)
        
        # Parse results
        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                search_results.append(SearchResult(
                    id=doc_id,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    distance=results["distances"][0][i] if results["distances"] else 0.0
                ))
        
        return search_results
    
    def delete_collection(self, collection: str) -> bool:
        """Delete a collection."""
        try:
            self._client.delete_collection(collection)
            if collection in self._collections:
                del self._collections[collection]
            return True
        except Exception:
            return False
    
    def get_collection_count(self, collection: str) -> int:
        """Get the number of documents in a collection."""
        coll = self._get_collection(collection)
        return coll.count()
    
    def list_collections(self) -> List[str]:
        """List all collection names."""
        return [c.name for c in self._client.list_collections()]
    
    def reset(self):
        """Reset the entire database (delete all collections)."""
        self._client.reset()
        self._collections = {}


# Global store instance
_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store."""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
