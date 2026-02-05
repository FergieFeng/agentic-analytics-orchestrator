"""
Output Guard: Check output before returning to user.

Validates responses don't contain sensitive or inappropriate content.
"""

from typing import Tuple, Any
import re


def check_output(output: Any) -> Tuple[bool, str]:
    """
    Check if output is safe to return to user.
    
    Args:
        output: Agent output (string, dict, or list)
        
    Returns:
        Tuple of (is_safe, reason)
    """
    
    if output is None:
        return True, "Output is empty (None)"
    
    # Convert to string for checking
    output_str = str(output)
    
    # Check for potential PII patterns (simplified)
    pii_patterns = [
        (r'\b\d{3}-\d{2}-\d{4}\b', "Social Security Number pattern"),
        (r'\b\d{16}\b', "Credit card number pattern"),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "Email address"),
    ]
    
    for pattern, description in pii_patterns:
        if re.search(pattern, output_str):
            return False, f"Output may contain PII: {description}"
    
    # Check for error messages that shouldn't be exposed
    error_patterns = [
        r"password",
        r"secret",
        r"api_key",
        r"token",
    ]
    
    for pattern in error_patterns:
        if re.search(pattern, output_str, re.IGNORECASE):
            return False, f"Output may contain sensitive information: {pattern}"
    
    return True, "Output is safe."


def redact_sensitive(text: str) -> str:
    """
    Redact potentially sensitive information from text.
    
    Args:
        text: Input text
        
    Returns:
        Text with sensitive patterns redacted
    """
    
    # Redact patterns
    redactions = [
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),
        (r'\b\d{16}\b', '[CARD REDACTED]'),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]'),
    ]
    
    for pattern, replacement in redactions:
        text = re.sub(pattern, replacement, text)
    
    return text


if __name__ == "__main__":
    # Test examples
    test_outputs = [
        "The total deposit amount is $15,400",
        "User email: test@example.com",
        "Card number: 1234567890123456",
        {"result": "normal data", "count": 10}
    ]
    
    for output in test_outputs:
        safe, reason = check_output(output)
        print(f"Output: {str(output)[:50]}...")
        print(f"   Safe: {safe} - {reason}\n")
