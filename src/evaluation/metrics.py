"""
Metrics: Track KPIs for agent system performance.

Measures routing accuracy, SQL validity, latency, etc.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json


@dataclass
class MetricsCollector:
    """Collects and aggregates metrics."""
    
    metrics: Dict[str, List[float]] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)
    
    def record(self, name: str, value: float) -> None:
        """Record a metric value."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(value)
    
    def increment(self, name: str, amount: int = 1) -> None:
        """Increment a counter."""
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += amount
    
    def get_average(self, name: str) -> Optional[float]:
        """Get average value for a metric."""
        values = self.metrics.get(name, [])
        return sum(values) / len(values) if values else None
    
    def get_summary(self) -> Dict:
        """Get summary of all metrics."""
        summary = {
            "counters": self.counters,
            "averages": {
                name: self.get_average(name)
                for name in self.metrics
            }
        }
        return summary


# Global metrics collector
_collector = MetricsCollector()


def record_metric(name: str, value: float) -> None:
    """Record a metric value."""
    _collector.record(name, value)


def increment_counter(name: str, amount: int = 1) -> None:
    """Increment a counter."""
    _collector.increment(name, amount)


def get_metrics_summary() -> Dict:
    """Get summary of all collected metrics."""
    return _collector.get_summary()


# Specific metric helpers
def record_latency(agent_name: str, duration_ms: float) -> None:
    """Record agent latency."""
    record_metric(f"latency_{agent_name}", duration_ms)
    record_metric("latency_total", duration_ms)


def record_sql_validity(is_valid: bool) -> None:
    """Record SQL validity check result."""
    increment_counter("sql_total")
    if is_valid:
        increment_counter("sql_valid")


def record_routing_decision(agents: List[str]) -> None:
    """Record which agents were routed to."""
    for agent in agents:
        increment_counter(f"route_{agent}")


if __name__ == "__main__":
    # Test metrics collection
    record_latency("definition_agent", 150.0)
    record_latency("sql_agent", 250.0)
    record_sql_validity(True)
    record_sql_validity(True)
    record_sql_validity(False)
    
    print(json.dumps(get_metrics_summary(), indent=2))
