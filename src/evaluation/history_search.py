"""
History Search: Find similar past queries using vector similarity.

Embeds user questions and searches query history for similar past queries
to provide context and improve answer quality.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

from src.config.settings import settings
from src.rag.embedder import embed_text, embed_texts
from src.rag.vector_store import get_vector_store, SearchResult, HISTORY_COLLECTION
from .query_store import get_query_store, QueryRecord


@dataclass
class HistoryMatch:
    """A matching historical query."""
    session_id: str
    question: str
    sql_query: Optional[str]
    final_response: Optional[str]
    user_score: Optional[int]
    self_score: Optional[float]
    similarity: float  # 0-1 score
    
    @property
    def was_successful(self) -> bool:
        """Check if this query was successful based on scores."""
        if self.user_score is not None and self.user_score >= 3:
            return True
        if self.self_score is not None and self.self_score >= 60:
            return True
        return False


class HistorySearcher:
    """
    Search past queries by semantic similarity.
    
    Usage:
        searcher = HistorySearcher()
        
        # Index a new query
        searcher.index_question(session_id="123", question="What is net flow?")
        
        # Find similar past queries
        matches = searcher.find_similar("Show net flow trend", k=3)
        for match in matches:
            print(f"{match.similarity:.2f}: {match.question}")
    """
    
    def __init__(self):
        self.store = get_vector_store()
        self.query_store = get_query_store()
    
    def index_question(self, session_id: str, question: str) -> bool:
        """
        Index a question for future similarity search.
        
        Args:
            session_id: Session ID to associate with question
            question: The question text to index
            
        Returns:
            True if indexed successfully
        """
        try:
            self.store.add_documents(
                collection=HISTORY_COLLECTION,
                documents=[question],
                metadatas=[{"session_id": session_id}],
                ids=[f"history_{session_id}"]
            )
            return True
        except Exception as e:
            return False
    
    def find_similar(
        self,
        question: str,
        k: int = 5,
        min_similarity: float = 0.3,
        successful_only: bool = False
    ) -> List[HistoryMatch]:
        """
        Find similar past queries.
        
        Args:
            question: Current question to match
            k: Number of results to return
            min_similarity: Minimum similarity score (0-1)
            successful_only: If True, only return successful queries
            
        Returns:
            List of HistoryMatch objects sorted by similarity
        """
        # Search vector store
        results = self.store.search(
            query=question,
            collection=HISTORY_COLLECTION,
            k=k * 2  # Get extra to filter
        )
        
        if not results:
            return []
        
        # Convert to HistoryMatch by looking up full records
        matches = []
        for result in results:
            similarity = result.score
            
            # Skip if below threshold
            if similarity < min_similarity:
                continue
            
            session_id = result.metadata.get("session_id", "")
            if not session_id:
                continue
            
            # Look up full record from query store
            record = self.query_store.get_by_id(session_id)
            if not record:
                # Use basic info from vector result
                match = HistoryMatch(
                    session_id=session_id,
                    question=result.content,
                    sql_query=None,
                    final_response=None,
                    user_score=None,
                    self_score=None,
                    similarity=similarity
                )
            else:
                match = HistoryMatch(
                    session_id=record.id,
                    question=record.question,
                    sql_query=record.sql_query,
                    final_response=record.final_response,
                    user_score=record.user_score,
                    self_score=record.self_score,
                    similarity=similarity
                )
            
            # Filter by success if requested
            if successful_only and not match.was_successful:
                continue
            
            matches.append(match)
        
        # Sort by similarity and take top k
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:k]
    
    def get_context_from_history(
        self,
        question: str,
        k: int = 3,
        min_similarity: float = 0.5
    ) -> str:
        """
        Get context string from similar past queries.
        
        Args:
            question: Current question
            k: Number of matches to include
            min_similarity: Minimum similarity threshold
            
        Returns:
            Formatted context string for LLM prompt
        """
        matches = self.find_similar(
            question,
            k=k,
            min_similarity=min_similarity,
            successful_only=True
        )
        
        if not matches:
            return ""
        
        lines = ["### Similar Past Queries\n"]
        
        for i, match in enumerate(matches, 1):
            lines.append(f"**Query {i}** (similarity: {match.similarity:.2f})")
            lines.append(f"Question: {match.question}")
            if match.sql_query:
                # Truncate long SQL
                sql = match.sql_query[:200] + "..." if len(match.sql_query) > 200 else match.sql_query
                lines.append(f"SQL: {sql}")
            lines.append("")
        
        return "\n".join(lines)
    
    def index_all_unindexed(self) -> int:
        """
        Index all queries that haven't been indexed yet.
        
        Returns:
            Number of queries indexed
        """
        # Get recent queries from store
        records = self.query_store.get_recent(limit=1000)
        
        # Get already indexed IDs
        indexed_count = self.store.get_collection_count(HISTORY_COLLECTION)
        
        # Index each unindexed query
        count = 0
        for record in records:
            # Check if already indexed (simple check - could be more robust)
            try:
                existing = self.store.search(
                    query=record.question,
                    collection=HISTORY_COLLECTION,
                    k=1
                )
                if existing and existing[0].id == f"history_{record.id}":
                    continue  # Already indexed
            except:
                pass
            
            if self.index_question(record.id, record.question):
                count += 1
        
        return count


# Global searcher instance
_searcher: Optional[HistorySearcher] = None


def get_history_searcher() -> HistorySearcher:
    """Get or create the global history searcher."""
    global _searcher
    if _searcher is None:
        _searcher = HistorySearcher()
    return _searcher


def find_similar_queries(
    question: str,
    k: int = 5,
    min_similarity: float = 0.3
) -> List[HistoryMatch]:
    """
    Convenience function to find similar past queries.
    
    Args:
        question: Question to match
        k: Number of results
        min_similarity: Minimum similarity threshold
        
    Returns:
        List of HistoryMatch objects
    """
    searcher = get_history_searcher()
    return searcher.find_similar(question, k, min_similarity)


def get_history_context(question: str, k: int = 3) -> str:
    """
    Convenience function to get history context for a question.
    
    Args:
        question: Current question
        k: Number of similar queries to include
        
    Returns:
        Formatted context string
    """
    searcher = get_history_searcher()
    return searcher.get_context_from_history(question, k)


if __name__ == "__main__":
    # Test history search
    print("Testing History Search...\n")
    
    searcher = HistorySearcher()
    
    # Index some test queries
    test_queries = [
        ("test_1", "What is the monthly net flow?"),
        ("test_2", "Show deposit trends by product type"),
        ("test_3", "How many transactions per channel?"),
    ]
    
    print("Indexing test queries...")
    for session_id, question in test_queries:
        result = searcher.index_question(session_id, question)
        print(f"  {session_id}: {result}")
    
    # Search for similar
    print("\nSearching for similar queries to 'Show me net flow trend'...")
    matches = searcher.find_similar("Show me net flow trend", k=3)
    
    for match in matches:
        print(f"  {match.similarity:.2f}: {match.question}")
    
    # Get context
    print("\nHistory context:")
    context = searcher.get_context_from_history("Net flow by month")
    print(context or "(No matching history)")
