from __future__ import annotations
import re
from typing import Any, Dict, Tuple

# In a real system, these patterns would be loaded from a config file
# like `policies/redaction/patterns.yaml` and would be much more extensive.
DEFAULT_REDACTION_PATTERNS = {
    # Matches common API key formats (e.g., sk-..., pk_..., etc.)
    "api_key": re.compile(r'(sk|pk)_[a-zA-Z0-9]{20,}'),
    # Matches common secret formats (e.g., AWS keys)
    "aws_secret": re.compile(r'(?<![A-Z0-9])[A-Z0-9]{20,}(?![A-Z0-9])'),
    # A simple email pattern
    "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
}

REDACTION_PLACEHOLDER = "[REDACTED]"

class RedactionReport:
    """
    A report detailing the results of a redaction operation.
    """
    def __init__(self):
        self.redacted_counts: Dict[str, int] = {}

    def add_redaction(self, pattern_name: str, count: int = 1):
        self.redacted_counts[pattern_name] = self.redacted_counts.get(pattern_name, 0) + count

    @property
    def total_redactions(self) -> int:
        return sum(self.redacted_counts.values())

    def __repr__(self) -> str:
        return f"RedactionReport(counts={self.redacted_counts})"

def scrub(
    data: Any,
    patterns: Dict[str, re.Pattern] = DEFAULT_REDACTION_PATTERNS
) -> Tuple[Any, RedactionReport]:
    """
    Recursively traverses a data structure and redacts sensitive information.

    This function can handle nested dictionaries, lists, and primitive values.
    It applies a set of regular expression patterns to all string values.

    Args:
        data: The data to scrub.
        patterns: A dictionary of compiled regex patterns to apply.

    Returns:
        A tuple containing the scrubbed data and a RedactionReport.
    """
    report = RedactionReport()
    scrubbed_data = _scrub_recursive(data, patterns, report)
    return scrubbed_data, report

def _scrub_recursive(data: Any, patterns: Dict[str, re.Pattern], report: RedactionReport) -> Any:
    """The internal recursive worker for the scrub function."""

    if isinstance(data, dict):
        # For dictionaries, scrub each value
        return {key: _scrub_recursive(value, patterns, report) for key, value in data.items()}

    elif isinstance(data, list):
        # For lists, scrub each item
        return [_scrub_recursive(item, patterns, report) for item in data]

    elif isinstance(data, str):
        # For strings, apply all redaction patterns
        scrubbed_string = data
        for name, pattern in patterns.items():
            # Use a function for the replacement to count matches
            match_count = 0
            def repl(match):
                nonlocal match_count
                match_count += 1
                return REDACTION_PLACEHOLDER

            scrubbed_string = pattern.sub(repl, scrubbed_string)
            if match_count > 0:
                report.add_redaction(name, match_count)
        return scrubbed_string

    else:
        # For all other data types, return them as is
        return data
