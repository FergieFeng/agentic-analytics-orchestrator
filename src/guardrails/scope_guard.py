"""
Scope Guard: Check if questions are within the analytics scope.

Rejects off-topic questions before processing.
"""

from typing import Tuple
from dataclasses import dataclass
from enum import Enum


class ScopeStatus(Enum):
    """Status of scope check."""
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    UNCLEAR = "unclear"


@dataclass
class ScopeCheckResult:
    """Result of a scope check."""
    status: ScopeStatus
    reason: str
    confidence: float  # 0.0 to 1.0
    
    @property
    def is_allowed(self) -> bool:
        """Check if the question should be allowed to proceed."""
        return self.status in (ScopeStatus.IN_SCOPE, ScopeStatus.UNCLEAR)


# Keywords that indicate in-scope questions (banking/transaction analytics)
IN_SCOPE_KEYWORDS = [
    # Transaction types
    "transaction", "deposit", "withdrawal", "payment", "transfer",
    "e-transfer", "etransfer",
    # Financial metrics
    "balance", "amount", "total", "sum", "count", "average", "avg",
    "volume", "flow", "net",
    # Channels
    "channel", "digital", "branch", "call center", "batch", "online", "mobile",
    # Entities
    "customer", "account", "client",
    # Products
    "chequing", "checking", "savings", "gic",
    # Time-based
    "daily", "weekly", "monthly", "trend", "period", "date", "month", "year",
    # Analytics terms
    "breakdown", "distribution", "top", "most", "least", "highest", "lowest",
    # Event types
    "fee", "interest", "event",
]

# Keywords that indicate out-of-scope questions
OUT_OF_SCOPE_KEYWORDS = [
    # Completely unrelated topics
    "weather", "stock market", "news", "sports", "politics",
    "recipe", "movie", "music", "game", "joke",
    # Personal/general assistant
    "remind", "alarm", "timer", "calendar",
    "translate", "define", "wikipedia",
    # Code/technical (not analytics)
    "write code", "debug", "compile", "programming",
]

# Patterns that suggest analytics questions even without keywords
ANALYTICS_PATTERNS = [
    "how many", "how much", "what is the",
    "show me", "list", "compare",
    "by month", "by channel", "by product",
    "last month", "this month", "year to date",
    "increase", "decrease", "growth", "change",
]


def check_scope(question: str) -> ScopeCheckResult:
    """
    Check if a question is within the analytics scope.
    
    Args:
        question: User question
        
    Returns:
        ScopeCheckResult with status, reason, and confidence
    """
    question_lower = question.lower()
    
    # Check for explicit out-of-scope keywords (high confidence rejection)
    for keyword in OUT_OF_SCOPE_KEYWORDS:
        if keyword in question_lower:
            return ScopeCheckResult(
                status=ScopeStatus.OUT_OF_SCOPE,
                reason=f"Question appears to be about '{keyword}', which is outside banking analytics scope.",
                confidence=0.9
            )
    
    # Count in-scope keyword matches
    in_scope_matches = sum(1 for kw in IN_SCOPE_KEYWORDS if kw in question_lower)
    pattern_matches = sum(1 for p in ANALYTICS_PATTERNS if p in question_lower)
    
    total_matches = in_scope_matches + pattern_matches
    
    # High confidence in-scope
    if total_matches >= 2:
        return ScopeCheckResult(
            status=ScopeStatus.IN_SCOPE,
            reason="Question contains multiple analytics-related terms.",
            confidence=0.9
        )
    
    # Medium confidence in-scope
    if total_matches == 1:
        return ScopeCheckResult(
            status=ScopeStatus.IN_SCOPE,
            reason="Question appears related to analytics.",
            confidence=0.7
        )
    
    # Check if it looks like a question at all
    is_question = any(question_lower.startswith(q) for q in ["what", "how", "who", "when", "where", "why", "which", "show", "list", "get"])
    
    if is_question:
        # Could be analytics-related, let it through with lower confidence
        return ScopeCheckResult(
            status=ScopeStatus.UNCLEAR,
            reason="Question type unclear. Proceeding with caution.",
            confidence=0.5
        )
    
    # Default: reject unclear non-questions
    return ScopeCheckResult(
        status=ScopeStatus.OUT_OF_SCOPE,
        reason="Unable to determine if this is a banking analytics question. Please ask about transactions, deposits, withdrawals, or account data.",
        confidence=0.6
    )


def format_rejection_message(result: ScopeCheckResult) -> str:
    """
    Format a user-friendly rejection message.
    
    Args:
        result: ScopeCheckResult
        
    Returns:
        Formatted message for the user
    """
    return f"""I can only answer questions about banking transaction analytics.

{result.reason}

**Examples of questions I can help with:**
- "What was the total deposit amount last month?"
- "Show me the transaction breakdown by channel"
- "Which customers had the most withdrawals?"
- "What's the trend in digital vs branch transactions?"

Please rephrase your question to focus on transaction or account analytics."""


if __name__ == "__main__":
    # Test examples
    test_questions = [
        "What's the total deposit amount by channel?",
        "How many customers made transactions last week?",
        "Show me the monthly trend of withdrawals",
        "What's the weather like today?",
        "Tell me a joke",
        "What is the average balance?",
        "Hello",
        "List top 10 customers by transaction volume",
    ]
    
    for q in test_questions:
        result = check_scope(q)
        status_icon = "✓" if result.is_allowed else "✗"
        print(f"{status_icon} Q: {q}")
        print(f"   Status: {result.status.value} (confidence: {result.confidence})")
        print(f"   Reason: {result.reason}\n")
