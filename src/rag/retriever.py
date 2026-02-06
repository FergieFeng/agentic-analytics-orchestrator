"""
Retriever: Query vector store for relevant context.

Provides RAG retrieval for augmenting LLM prompts with relevant
knowledge and schema information.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .vector_store import (
    get_vector_store,
    SearchResult,
    KNOWLEDGE_COLLECTION,
    SCHEMA_COLLECTION
)
from .indexer import is_indexed, index_knowledge_base


@dataclass
class RetrievalResult:
    """Result of RAG retrieval."""
    query: str
    knowledge_results: List[SearchResult] = field(default_factory=list)
    schema_results: List[SearchResult] = field(default_factory=list)
    
    @property
    def total_results(self) -> int:
        return len(self.knowledge_results) + len(self.schema_results)
    
    @property
    def has_results(self) -> bool:
        return self.total_results > 0
    
    def get_context_string(self, max_chunks: int = 10) -> str:
        """
        Format retrieval results as a context string for LLM prompts.
        
        Args:
            max_chunks: Maximum number of chunks to include
            
        Returns:
            Formatted context string
        """
        sections = []
        
        # Knowledge context
        if self.knowledge_results:
            knowledge_text = "### Retrieved Knowledge\n"
            for i, result in enumerate(self.knowledge_results[:max_chunks // 2]):
                knowledge_text += f"\n{i+1}. {result.content}\n"
            sections.append(knowledge_text)
        
        # Schema context  
        if self.schema_results:
            schema_text = "### Retrieved Schema Information\n"
            for i, result in enumerate(self.schema_results[:max_chunks // 2]):
                schema_text += f"\n{i+1}. {result.content}\n"
            sections.append(schema_text)
        
        if not sections:
            return ""
        
        return "\n".join(sections)
    
    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get summary of retrieved metadata."""
        knowledge_types = {}
        schema_types = {}
        
        for r in self.knowledge_results:
            t = r.metadata.get("type", "unknown")
            knowledge_types[t] = knowledge_types.get(t, 0) + 1
        
        for r in self.schema_results:
            t = r.metadata.get("type", "unknown")
            schema_types[t] = schema_types.get(t, 0) + 1
        
        return {
            "knowledge_types": knowledge_types,
            "schema_types": schema_types,
            "total_knowledge": len(self.knowledge_results),
            "total_schema": len(self.schema_results)
        }


class RAGRetriever:
    """
    RAG retriever for querying knowledge and schema.
    
    Usage:
        retriever = RAGRetriever()
        
        # Retrieve context for a question
        result = retriever.retrieve("What is net flow?")
        context = result.get_context_string()
        
        # Use in prompt
        prompt = f"Context:\n{context}\n\nQuestion: What is net flow?"
    """
    
    def __init__(self, auto_index: bool = True):
        """
        Initialize the retriever.
        
        Args:
            auto_index: If True, automatically index if not already done
        """
        self.store = get_vector_store()
        
        if auto_index and not is_indexed():
            index_knowledge_base()
    
    def retrieve(
        self,
        query: str,
        k_knowledge: int = 5,
        k_schema: int = 3,
        filter_knowledge: Optional[Dict[str, Any]] = None,
        filter_schema: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: User query
            k_knowledge: Number of knowledge chunks to retrieve
            k_schema: Number of schema chunks to retrieve
            filter_knowledge: Optional metadata filter for knowledge
            filter_schema: Optional metadata filter for schema
            
        Returns:
            RetrievalResult with matching documents
        """
        result = RetrievalResult(query=query)
        
        # Search knowledge collection
        if k_knowledge > 0:
            result.knowledge_results = self.store.search(
                query=query,
                collection=KNOWLEDGE_COLLECTION,
                k=k_knowledge,
                filter_metadata=filter_knowledge
            )
        
        # Search schema collection
        if k_schema > 0:
            result.schema_results = self.store.search(
                query=query,
                collection=SCHEMA_COLLECTION,
                k=k_schema,
                filter_metadata=filter_schema
            )
        
        return result
    
    def retrieve_for_definition(self, query: str) -> RetrievalResult:
        """
        Retrieve context optimized for Definition Agent.
        
        Focuses on glossary terms, business rules, and metrics.
        """
        return self.retrieve(
            query=query,
            k_knowledge=5,
            k_schema=2,
            filter_knowledge=None  # Could filter to glossary/metrics
        )
    
    def retrieve_for_sql(self, query: str) -> RetrievalResult:
        """
        Retrieve context optimized for SQL Agent.
        
        Focuses on schema columns, enums, and SQL patterns.
        """
        return self.retrieve(
            query=query,
            k_knowledge=3,  # Metrics and SQL patterns
            k_schema=5  # Schema details
        )
    
    def retrieve_metrics(self, query: str, k: int = 5) -> List[SearchResult]:
        """Retrieve only metric definitions."""
        return self.store.search(
            query=query,
            collection=KNOWLEDGE_COLLECTION,
            k=k,
            filter_metadata={"type": "metric"}
        )
    
    def retrieve_glossary(self, query: str, k: int = 5) -> List[SearchResult]:
        """Retrieve only glossary terms."""
        return self.store.search(
            query=query,
            collection=KNOWLEDGE_COLLECTION,
            k=k,
            filter_metadata={"type": "glossary"}
        )
    
    def retrieve_columns(self, query: str, k: int = 5) -> List[SearchResult]:
        """Retrieve only column definitions."""
        return self.store.search(
            query=query,
            collection=SCHEMA_COLLECTION,
            k=k,
            filter_metadata={"type": "column"}
        )


# Global retriever instance
_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    """Get or create the global retriever."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever(auto_index=True)
    return _retriever


def retrieve_context(
    query: str,
    k_knowledge: int = 5,
    k_schema: int = 3
) -> str:
    """
    Convenience function to retrieve context as a string.
    
    Args:
        query: User query
        k_knowledge: Number of knowledge chunks
        k_schema: Number of schema chunks
        
    Returns:
        Formatted context string for LLM prompt
    """
    retriever = get_retriever()
    result = retriever.retrieve(query, k_knowledge, k_schema)
    return result.get_context_string()


if __name__ == "__main__":
    # Test retrieval
    print("Testing RAG retriever...\n")
    
    retriever = RAGRetriever()
    
    test_queries = [
        "What is net flow?",
        "What columns are available?",
        "How do I calculate total deposits?",
    ]
    
    for query in test_queries:
        print(f"Query: {query}")
        print("-" * 50)
        
        result = retriever.retrieve(query)
        print(f"Found: {result.total_results} results")
        print(f"Metadata: {result.get_metadata_summary()}")
        
        print("\nContext:")
        print(result.get_context_string(max_chunks=4))
        print("\n" + "=" * 60 + "\n")
