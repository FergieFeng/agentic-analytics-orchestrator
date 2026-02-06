"""
Query Store: SQLite database for storing query history.

Features:
- Persistent storage of all query sessions
- Support for embeddings (for future similarity search)
- Query history retrieval
- Performance analytics
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from src.config.settings import settings

# Database path
DB_PATH = settings.project_root / "data" / "query_logs.db"


@dataclass
class QueryRecord:
    """A stored query record."""
    id: str
    question: str
    question_embedding: Optional[bytes]  # For future similarity search
    definition_json: Optional[str]
    sql_query: Optional[str]
    result_summary_json: Optional[str]
    final_response: Optional[str]
    agent_traces_json: Optional[str]
    
    # Scores
    self_score: Optional[float]
    self_scores_json: Optional[str]  # Detailed breakdown
    user_score: Optional[int]
    user_feedback: Optional[str]
    
    # Metadata
    latency_ms: float
    total_tokens: int
    error_count: int
    tags: Optional[str]  # Comma-separated tags
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "question": self.question,
            "definition": json.loads(self.definition_json) if self.definition_json else None,
            "sql_query": self.sql_query,
            "result_summary": json.loads(self.result_summary_json) if self.result_summary_json else None,
            "final_response": self.final_response,
            "self_score": self.self_score,
            "self_scores": json.loads(self.self_scores_json) if self.self_scores_json else None,
            "user_score": self.user_score,
            "user_feedback": self.user_feedback,
            "latency_ms": self.latency_ms,
            "total_tokens": self.total_tokens,
            "error_count": self.error_count,
            "tags": self.tags.split(",") if self.tags else [],
            "created_at": self.created_at
        }


class QueryStore:
    """
    SQLite-based query storage.
    
    Usage:
        store = QueryStore()
        store.save_session(session)
        
        # Retrieve history
        records = store.get_recent(limit=10)
        record = store.get_by_id("abc123")
        
        # Update feedback
        store.update_feedback("abc123", user_score=5, comment="Great!")
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_logs (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    question_embedding BLOB,
                    definition_json TEXT,
                    sql_query TEXT,
                    result_summary_json TEXT,
                    final_response TEXT,
                    agent_traces_json TEXT,
                    
                    -- Scores
                    self_score REAL,
                    self_scores_json TEXT,
                    user_score INTEGER,
                    user_feedback TEXT,
                    
                    -- Metadata
                    latency_ms REAL DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    tags TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Index for recent queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON query_logs(created_at DESC)
            """)
            
            # Index for feedback queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_score 
                ON query_logs(user_score)
            """)
    
    def save_session(self, session) -> str:
        """
        Save a QuerySession to the database.
        
        Args:
            session: QuerySession object from logger
            
        Returns:
            session_id
        """
        from .logger import QuerySession
        
        if not isinstance(session, QuerySession):
            raise ValueError("Expected QuerySession object")
        
        # Summarize SQL result
        result_summary = None
        if session.sql_result:
            result_summary = json.dumps({
                "row_count": session.sql_result.get("row_count", 0),
                "columns": session.sql_result.get("columns", []),
                "sample": session.sql_result.get("data", [])[:3]
            })
        
        # Calculate overall self score
        overall_score = None
        if session.self_scores:
            scores = [v for v in session.self_scores.values() if isinstance(v, (int, float))]
            if scores:
                overall_score = sum(scores) / len(scores)
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO query_logs (
                    id, question, definition_json, sql_query, 
                    result_summary_json, final_response, agent_traces_json,
                    self_score, self_scores_json, user_score, user_feedback,
                    latency_ms, total_tokens, error_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.question,
                json.dumps(session.definition) if session.definition else None,
                session.sql_query,
                result_summary,
                session.final_response,
                json.dumps([{
                    "agent": t.agent_name,
                    "action": t.action,
                    "duration_ms": t.duration_ms,
                    "tokens": t.tokens_used,
                    "error": t.error
                } for t in session.traces]),
                overall_score,
                json.dumps(session.self_scores) if session.self_scores else None,
                session.user_score,
                session.user_feedback,
                session.total_duration_ms,
                session.total_tokens,
                len(session.errors),
                session.timestamp
            ))
        
        return session.session_id
    
    def get_by_id(self, session_id: str) -> Optional[QueryRecord]:
        """Get a query record by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM query_logs WHERE id = ?",
                (session_id,)
            ).fetchone()
            
            if row:
                return self._row_to_record(row)
        return None
    
    def get_recent(self, limit: int = 20, offset: int = 0) -> List[QueryRecord]:
        """Get recent query records."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM query_logs 
                   ORDER BY created_at DESC 
                   LIMIT ? OFFSET ?""",
                (limit, offset)
            ).fetchall()
            
            return [self._row_to_record(row) for row in rows]
    
    def get_by_score_range(
        self, 
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        score_type: str = "self"  # "self" or "user"
    ) -> List[QueryRecord]:
        """Get records by score range."""
        score_col = "self_score" if score_type == "self" else "user_score"
        
        conditions = []
        params = []
        
        if min_score is not None:
            conditions.append(f"{score_col} >= ?")
            params.append(min_score)
        if max_score is not None:
            conditions.append(f"{score_col} <= ?")
            params.append(max_score)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with self._get_connection() as conn:
            rows = conn.execute(
                f"""SELECT * FROM query_logs 
                    WHERE {where_clause}
                    ORDER BY created_at DESC""",
                params
            ).fetchall()
            
            return [self._row_to_record(row) for row in rows]
    
    def get_unrated(self, limit: int = 20) -> List[QueryRecord]:
        """Get records without user feedback."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM query_logs 
                   WHERE user_score IS NULL
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,)
            ).fetchall()
            
            return [self._row_to_record(row) for row in rows]
    
    def update_feedback(
        self, 
        session_id: str, 
        user_score: int, 
        user_feedback: Optional[str] = None
    ) -> bool:
        """
        Update user feedback for a query.
        
        Args:
            session_id: Query session ID
            user_score: Rating 1-5
            user_feedback: Optional text feedback
            
        Returns:
            True if updated, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """UPDATE query_logs 
                   SET user_score = ?, user_feedback = ?
                   WHERE id = ?""",
                (user_score, user_feedback, session_id)
            )
            return cursor.rowcount > 0
    
    def update_self_scores(
        self,
        session_id: str,
        scores: Dict[str, float]
    ) -> bool:
        """Update self-evaluation scores."""
        overall = sum(scores.values()) / len(scores) if scores else None
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """UPDATE query_logs 
                   SET self_score = ?, self_scores_json = ?
                   WHERE id = ?""",
                (overall, json.dumps(scores), session_id)
            )
            return cursor.rowcount > 0
    
    def add_embedding(self, session_id: str, embedding: bytes) -> bool:
        """Add question embedding for similarity search."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """UPDATE query_logs 
                   SET question_embedding = ?
                   WHERE id = ?""",
                (embedding, session_id)
            )
            return cursor.rowcount > 0
    
    def add_tags(self, session_id: str, tags: List[str]) -> bool:
        """Add tags to a query."""
        tags_str = ",".join(tags)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """UPDATE query_logs 
                   SET tags = ?
                   WHERE id = ?""",
                (tags_str, session_id)
            )
            return cursor.rowcount > 0
    
    def search_by_tag(self, tag: str) -> List[QueryRecord]:
        """Search queries by tag."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM query_logs 
                   WHERE tags LIKE ?
                   ORDER BY created_at DESC""",
                (f"%{tag}%",)
            ).fetchall()
            
            return [self._row_to_record(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(self_score) as avg_self_score,
                    AVG(user_score) as avg_user_score,
                    AVG(latency_ms) as avg_latency_ms,
                    AVG(total_tokens) as avg_tokens,
                    SUM(CASE WHEN error_count > 0 THEN 1 ELSE 0 END) as error_count,
                    SUM(CASE WHEN user_score IS NOT NULL THEN 1 ELSE 0 END) as rated_count
                FROM query_logs
            """).fetchone()
            
            return {
                "total_queries": row["total_queries"],
                "avg_self_score": round(row["avg_self_score"], 2) if row["avg_self_score"] else None,
                "avg_user_score": round(row["avg_user_score"], 2) if row["avg_user_score"] else None,
                "avg_latency_ms": round(row["avg_latency_ms"], 2) if row["avg_latency_ms"] else None,
                "avg_tokens": round(row["avg_tokens"], 0) if row["avg_tokens"] else None,
                "error_rate": round(row["error_count"] / row["total_queries"] * 100, 1) if row["total_queries"] else 0,
                "rated_percentage": round(row["rated_count"] / row["total_queries"] * 100, 1) if row["total_queries"] else 0
            }
    
    def _row_to_record(self, row: sqlite3.Row) -> QueryRecord:
        """Convert database row to QueryRecord."""
        return QueryRecord(
            id=row["id"],
            question=row["question"],
            question_embedding=row["question_embedding"],
            definition_json=row["definition_json"],
            sql_query=row["sql_query"],
            result_summary_json=row["result_summary_json"],
            final_response=row["final_response"],
            agent_traces_json=row["agent_traces_json"],
            self_score=row["self_score"],
            self_scores_json=row["self_scores_json"],
            user_score=row["user_score"],
            user_feedback=row["user_feedback"],
            latency_ms=row["latency_ms"],
            total_tokens=row["total_tokens"],
            error_count=row["error_count"],
            tags=row["tags"],
            created_at=row["created_at"]
        )


# Global store instance
_store: Optional[QueryStore] = None


def get_query_store() -> QueryStore:
    """Get or create the global query store."""
    global _store
    if _store is None:
        _store = QueryStore()
    return _store
