"""
Logger: Centralized structured logging.

Outputs JSON logs for easy parsing and analysis.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger("agentic_analytics")


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
    """Log an agent invocation."""
    
    log_event(
        event_type="agent_call",
        message=f"Agent '{agent_name}' completed",
        data={
            "agent": agent_name,
            "input": input_data,
            "output": output_data,
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
