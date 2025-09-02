from __future__ import annotations
import re
from typing import Any, Dict, Tuple
from pathlib import Path
import yaml
import logging

# Get the root directory of the project
# This assumes the script is run from within the pforge project structure.
# A more robust solution might use importlib.resources or a dedicated config loader.
try:
    from pforge.utils.paths import PFORGE_ROOT
except (ImportError, ModuleNotFoundError):
    # Fallback for environments where pforge is not installed as a package
    PFORGE_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)

REDACTION_PLACEHOLDER = "[REDACTED]"
PATTERNS_FILE = PFORGE_ROOT / "policies/redaction/patterns.yaml"

def load_redaction_patterns(patterns_path: Path = PATTERNS_FILE) -> Dict[str, re.Pattern]:
    """
    Loads redaction patterns from the specified YAML file.
    """
    if not patterns_path.exists():
        logger.warning(f"Redaction patterns file not found at {patterns_path}. Using empty patterns.")
        return {}

    try:
        with open(patterns_path, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing redaction patterns YAML file: {e}")
        return {}

    patterns = {}
    regex_list = config.get('regex', [])
    for i, pattern_str in enumerate(regex_list):
        try:
            # Use the pattern string itself as the key if no name is provided
            key = f"regex_{i}"
            patterns[key] = re.compile(pattern_str)
        except re.error as e:
            logger.error(f"Invalid regex pattern in {patterns_path}: '{pattern_str}'. Error: {e}")
            continue

    logger.info(f"Loaded {len(patterns)} redaction patterns from {patterns_path}.")
    return patterns

# Load patterns once on module import
COMPILED_REDACTION_PATTERNS = load_redaction_patterns()

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
    patterns: Optional[Dict[str, re.Pattern]] = None
) -> Tuple[Any, RedactionReport]:
    """
    Recursively traverses a data structure and redacts sensitive information.

    This function can handle nested dictionaries, lists, and primitive values.
    It applies a set of regular expression patterns to all string values.

    Args:
        data: The data to scrub.
        patterns: A dictionary of compiled regex patterns to apply. If None,
                  the patterns loaded from the default YAML file are used.

    Returns:
        A tuple containing the scrubbed data and a RedactionReport.
    """
    if patterns is None:
        patterns = COMPILED_REDACTION_PATTERNS

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
