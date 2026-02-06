"""
Logger: Structured session-based logging for query analysis.

Features:
- Session tracking with unique IDs
- Per-agent step logging with timing
- Token usage tracking
- JSON export for analysis
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger("agentic_analytics")

# Log directory
LOG_DIR = settings.project_root / "logs"


@dataclass
class AgentTrace:
    """Record of a single agent execution."""
    agent_name: str
    action: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: Optional[float] = None
    tokens_used: int = 0
    input_summary: Optional[str] = None  # Truncated input
    output_summary: Optional[str] = None  # Truncated output
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class QuerySession:
    """Complete record of a query session."""
    session_id: str
    question: str
    timestamp: str
    
    # Agent traces
    traces: List[AgentTrace] = field(default_factory=list)
    
    # Results
    definition: Optional[Dict[str, Any]] = None
    sql_query: Optional[str] = None
    sql_result: Optional[Dict[str, Any]] = None
    final_response: Optional[str] = None
    
    # Scores (filled in by self_eval)
    self_scores: Dict[str, float] = field(default_factory=dict)
    
    # User feedback (filled in later)
    user_score: Optional[int] = None
    user_feedback: Optional[str] = None
    
    # Metadata
    total_tokens: int = 0
    total_duration_ms: float = 0
    errors: List[str] = field(default_factory=list)
    end_timestamp: Optional[str] = None
    
    def add_trace(self, trace: AgentTrace):
        """Add an agent trace to the session."""
        self.traces.append(trace)
        self.total_tokens += trace.tokens_used
        if trace.duration_ms:
            self.total_duration_ms += trace.duration_ms
        if trace.error:
            self.errors.append(f"{trace.agent_name}: {trace.error}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "question": self.question,
            "timestamp": self.timestamp,
            "end_timestamp": self.end_timestamp,
            "traces": [asdict(t) for t in self.traces],
            "definition": self.definition,
            "sql_query": self.sql_query,
            "sql_result_summary": self._summarize_result(self.sql_result),
            "final_response": self.final_response,
            "self_scores": self.self_scores,
            "user_score": self.user_score,
            "user_feedback": self.user_feedback,
            "total_tokens": self.total_tokens,
            "total_duration_ms": self.total_duration_ms,
            "errors": self.errors
        }
    
    def _summarize_result(self, result: Optional[Dict]) -> Optional[Dict]:
        """Summarize SQL result for logging (avoid huge data)."""
        if not result:
            return None
        return {
            "row_count": result.get("row_count", 0),
            "columns": result.get("columns", []),
            "sample_rows": result.get("data", [])[:3]  # Only first 3 rows
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


class SessionLogger:
    """
    Manages logging for a query session.
    
    Usage:
        session = SessionLogger.start("What is total deposit?")
        session.log_agent_start("definition_agent")
        # ... agent runs ...
        session.log_agent_complete("definition_agent", output, duration_ms, tokens)
        session.finish(state)
    """
    
    _current_session: Optional[QuerySession] = None
    
    @classmethod
    def start(cls, question: str) -> "SessionLogger":
        """Start a new logging session."""
        session = QuerySession(
            session_id=str(uuid.uuid4()),
            question=question,
            timestamp=datetime.now().isoformat()
        )
        cls._current_session = session
        
        logger.info(json.dumps({
            "event": "session_start",
            "session_id": session.session_id,
            "question": question[:100]  # Truncate for console
        }))
        
        return cls()
    
    @classmethod
    def get_current(cls) -> Optional[QuerySession]:
        """Get the current session."""
        return cls._current_session
    
    def log_agent_start(self, agent_name: str, input_data: Optional[Dict] = None):
        """Log agent execution start."""
        if not self._current_session:
            return
        
        trace = AgentTrace(
            agent_name=agent_name,
            action="started",
            input_summary=self._truncate_dict(input_data) if input_data else None
        )
        self._current_session.add_trace(trace)
        
        logger.debug(json.dumps({
            "event": "agent_start",
            "session_id": self._current_session.session_id,
            "agent": agent_name
        }))
    
    def log_agent_complete(
        self,
        agent_name: str,
        output: Optional[Dict] = None,
        duration_ms: float = 0,
        tokens: int = 0,
        error: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """Log agent execution completion."""
        if not self._current_session:
            return
        
        trace = AgentTrace(
            agent_name=agent_name,
            action="completed" if not error else "failed",
            duration_ms=duration_ms,
            tokens_used=tokens,
            output_summary=self._truncate_dict(output) if output else None,
            error=error,
            details=details or {}
        )
        self._current_session.add_trace(trace)
        
        logger.debug(json.dumps({
            "event": "agent_complete",
            "session_id": self._current_session.session_id,
            "agent": agent_name,
            "duration_ms": duration_ms,
            "tokens": tokens,
            "error": error
        }))
    
    def log_event(self, event_type: str, message: str, data: Optional[Dict] = None):
        """Log a generic event."""
        if not self._current_session:
            return
        
        trace = AgentTrace(
            agent_name="system",
            action=event_type,
            details={"message": message, **(data or {})}
        )
        self._current_session.add_trace(trace)
        
        logger.info(json.dumps({
            "event": event_type,
            "session_id": self._current_session.session_id,
            "message": message,
            "data": data
        }))
    
    def finish(self, state: Dict[str, Any]) -> QuerySession:
        """
        Finish the session and extract final data from state.
        
        Returns the completed QuerySession.
        """
        if not self._current_session:
            raise ValueError("No active session to finish")
        
        session = self._current_session
        session.end_timestamp = datetime.now().isoformat()
        
        # Extract results from state
        session.definition = state.get("definition_result")
        session.sql_query = state.get("sql_query")
        session.sql_result = state.get("sql_result")
        session.final_response = state.get("final_response")
        session.total_tokens = state.get("total_tokens", session.total_tokens)
        
        # Copy errors from state
        state_errors = state.get("errors", [])
        for err in state_errors:
            if err not in session.errors:
                session.errors.append(err)
        
        logger.info(json.dumps({
            "event": "session_end",
            "session_id": session.session_id,
            "duration_ms": session.total_duration_ms,
            "tokens": session.total_tokens,
            "error_count": len(session.errors)
        }))
        
        # Save to file
        self._save_session(session)
        
        return session
    
    def _save_session(self, session: QuerySession):
        """Save session to a JSON file."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Use date-based filename
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{session.session_id[:8]}.json"
        filepath = LOG_DIR / filename
        
        with open(filepath, "w") as f:
            f.write(session.to_json())
        
        logger.debug(f"Session saved to {filepath}")
    
    def _truncate_dict(self, d: Dict, max_len: int = 200) -> str:
        """Truncate dictionary to string for logging."""
        if not d:
            return ""
        s = json.dumps(d, default=str)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s


# --- Legacy functions for backward compatibility ---

def log_event(
    event_type: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    level: str = "info"
) -> None:
    """
    Log a structured event.
    
    Args:
        event_type: Type of event (e.g., "agent_call", "error", "metric")
        message: Human-readable message
        data: Additional structured data
        level: Log level (debug, info, warning, error)
    """
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "message": message,
        "data": data or {}
    }
    
    log_json = json.dumps(log_entry)
    
    if level == "debug":
        logger.debug(log_json)
    elif level == "warning":
        logger.warning(log_json)
    elif level == "error":
        logger.error(log_json)
    else:
        logger.info(log_json)


def log_agent_call(
    agent_name: str,
    input_data: Dict,
    output_data: Dict,
    duration_ms: float
) -> None:
    """Log an agent invocation (legacy)."""
    current = SessionLogger.get_current()
    if current:
        SessionLogger().log_agent_complete(
            agent_name=agent_name,
            output=output_data,
            duration_ms=duration_ms
        )
    else:
        log_event(
            event_type="agent_call",
            message=f"Agent '{agent_name}' completed",
            data={
                "agent": agent_name,
                "duration_ms": duration_ms
            }
        )


def log_error(error: Exception, context: Optional[Dict] = None) -> None:
    """Log an error with context."""
    log_event(
        event_type="error",
        message=str(error),
        data={
            "error_type": type(error).__name__,
            "context": context or {}
        },
        level="error"
    )
