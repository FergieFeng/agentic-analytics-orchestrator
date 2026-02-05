"""
Tracer: Track agent execution flow for debugging.

Records the sequence of agent calls and their inputs/outputs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import uuid


@dataclass
class TraceSpan:
    """A single span in the trace."""
    
    span_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    input_data: Optional[Dict] = None
    output_data: Optional[Dict] = None
    error: Optional[str] = None
    children: List["TraceSpan"] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "span_id": self.span_id,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": (self.end_time - self.start_time).total_seconds() * 1000 if self.end_time else None,
            "input": self.input_data,
            "output": self.output_data,
            "error": self.error,
            "children": [c.to_dict() for c in self.children]
        }


class Tracer:
    """Manages trace collection."""
    
    def __init__(self):
        self.traces: List[TraceSpan] = []
        self.current_trace: Optional[TraceSpan] = None
        self.span_stack: List[TraceSpan] = []
    
    def start_trace(self, name: str) -> str:
        """Start a new trace."""
        span = TraceSpan(
            span_id=str(uuid.uuid4())[:8],
            name=name,
            start_time=datetime.utcnow()
        )
        self.current_trace = span
        self.span_stack = [span]
        return span.span_id
    
    def start_span(self, name: str, input_data: Optional[Dict] = None) -> str:
        """Start a child span."""
        span = TraceSpan(
            span_id=str(uuid.uuid4())[:8],
            name=name,
            start_time=datetime.utcnow(),
            input_data=input_data
        )
        
        if self.span_stack:
            self.span_stack[-1].children.append(span)
        
        self.span_stack.append(span)
        return span.span_id
    
    def end_span(self, output_data: Optional[Dict] = None, error: Optional[str] = None) -> None:
        """End the current span."""
        if self.span_stack:
            span = self.span_stack.pop()
            span.end_time = datetime.utcnow()
            span.output_data = output_data
            span.error = error
    
    def end_trace(self) -> Dict:
        """End the current trace and return it."""
        if self.current_trace:
            self.current_trace.end_time = datetime.utcnow()
            self.traces.append(self.current_trace)
            result = self.current_trace.to_dict()
            self.current_trace = None
            self.span_stack = []
            return result
        return {}
    
    def get_all_traces(self) -> List[Dict]:
        """Get all completed traces."""
        return [t.to_dict() for t in self.traces]


# Global tracer instance
_tracer = Tracer()


def trace_call(name: str):
    """Decorator to trace function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            _tracer.start_span(name, {"args": str(args)[:100], "kwargs": str(kwargs)[:100]})
            try:
                result = func(*args, **kwargs)
                _tracer.end_span({"result": str(result)[:100]})
                return result
            except Exception as e:
                _tracer.end_span(error=str(e))
                raise
        return wrapper
    return decorator


def start_trace(name: str) -> str:
    """Start a new trace."""
    return _tracer.start_trace(name)


def end_trace() -> Dict:
    """End the current trace."""
    return _tracer.end_trace()


def get_traces() -> List[Dict]:
    """Get all traces."""
    return _tracer.get_all_traces()


if __name__ == "__main__":
    # Test tracing
    start_trace("test_request")
    _tracer.start_span("agent_1", {"input": "test"})
    _tracer.end_span({"output": "result"})
    trace = end_trace()
    print(json.dumps(trace, indent=2))
