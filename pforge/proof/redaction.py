from __future__ import annotations
import re
from typing import Any, Dict, Optional, Tuple, List
from pathlib import Path
import yaml
import logging

from pforge.math_models.entropy import is_potential_secret

# Get the root directory of the project
try:
    from pforge.utils.paths import PFORGE_ROOT
except (ImportError, ModuleNotFoundError):
    PFORGE_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)

REDACTION_PLACEHOLDER = "[REDACTED]"
PATTERNS_FILE = PFORGE_ROOT / "policies/redaction/patterns.yaml"
POLICIES_FILE = PFORGE_ROOT / "config/policies.yaml"

class RedactionReport:
    """A report detailing the results of a redaction operation."""
    def __init__(self):
        self.redacted_counts: Dict[str, int] = {}

    def add_redaction(self, pattern_name: str, count: int = 1):
        self.redacted_counts[pattern_name] = self.redacted_counts.get(pattern_name, 0) + count

    @property
    def total_redactions(self) -> int:
        return sum(self.redacted_counts.values())

    def __repr__(self) -> str:
        return f"RedactionReport(counts={self.redacted_counts})"

class RedactionManager:
    """Manages the redaction process, including loading patterns and configuration."""
    def __init__(
        self,
        patterns_path: Path = PATTERNS_FILE,
        policies_path: Path = POLICIES_FILE,
    ):
        self.patterns_path = patterns_path
        self.policies_path = policies_path
        self.redaction_config = self._load_redaction_config()
        self.compiled_patterns = self._load_redaction_patterns()
        self.whitelist = self._load_whitelist()

    def _load_redaction_config(self) -> Dict[str, Any]:
        """Loads redaction configuration from the policies YAML file."""
        if not self.policies_path.exists():
            logger.warning(f"Policies file not found at {self.policies_path}. Using default redaction config.")
            return {
                "entropy_scan_enabled": True,
                "entropy_threshold": 4.5,
                "min_secret_length": 20,
            }
        try:
            with open(self.policies_path, 'r') as f:
                config = yaml.safe_load(f)
            return config.get("redaction", {})
        except yaml.YAMLError as e:
            logger.error(f"Error parsing policies YAML file: {e}")
            return {}

    def _load_redaction_patterns(self) -> Dict[str, re.Pattern]:
        """Loads and compiles redaction patterns from the patterns YAML file."""
        if not self.patterns_path.exists():
            logger.warning(f"Redaction patterns file not found at {self.patterns_path}. Using empty patterns.")
            return {}
        try:
            with open(self.patterns_path, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing redaction patterns YAML file: {e}")
            return {}

        patterns = {}
        regex_list = config.get('regex', [])
        for i, pattern_str in enumerate(regex_list):
            try:
                key = f"regex_{i}"
                patterns[key] = re.compile(pattern_str)
            except re.error as e:
                logger.error(f"Invalid regex pattern: '{pattern_str}'. Error: {e}")
                continue
        logger.info(f"Loaded {len(patterns)} redaction patterns.")
        return patterns

    def _load_whitelist(self) -> List[str]:
        """Loads the whitelist from the patterns YAML file."""
        if not self.patterns_path.exists():
            return []
        try:
            with open(self.patterns_path, 'r') as f:
                config = yaml.safe_load(f)
            return config.get("whitelist", [])
        except yaml.YAMLError as e:
            logger.error(f"Error parsing patterns YAML file for whitelist: {e}")
            return []

    def scrub(self, data: Any) -> Tuple[Any, RedactionReport]:
        """
        Recursively traverses a data structure and redacts sensitive information.
        """
        report = RedactionReport()
        scrubbed_data = self._scrub_recursive(data, report)
        return scrubbed_data, report

    def _scrub_recursive(self, data: Any, report: RedactionReport) -> Any:
        """The internal recursive worker for the scrub function."""
        if isinstance(data, dict):
            return {key: self._scrub_recursive(value, report) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._scrub_recursive(item, report) for item in data]
        elif isinstance(data, str):
            # Check whitelist first
            # Use word boundaries to prevent partial matches (e.g., "example" in "thisisnotanexample")
            if any(re.search(r'\b' + re.escape(term) + r'\b', data, re.IGNORECASE) for term in self.whitelist):
                return data

            # Apply regex patterns
            scrubbed_string = data
            for name, pattern in self.compiled_patterns.items():
                match_count = 0
                def repl(match):
                    nonlocal match_count
                    match_count += 1
                    return REDACTION_PLACEHOLDER
                scrubbed_string, num_subs = pattern.subn(repl, scrubbed_string)
                if num_subs > 0:
                    report.add_redaction(name, num_subs)

            # Apply entropy scan if enabled and not already redacted
            if self.redaction_config.get("entropy_scan_enabled") and REDACTION_PLACEHOLDER not in scrubbed_string:
                if is_potential_secret(
                    scrubbed_string,
                    self.redaction_config.get("entropy_threshold", 4.5),
                    self.redaction_config.get("min_secret_length", 20),
                ):
                    report.add_redaction("entropy")
                    return REDACTION_PLACEHOLDER

            return scrubbed_string
        else:
            return data

# Global instance for convenience
redaction_manager = RedactionManager()

def scrub(data: Any) -> Tuple[Any, RedactionReport]:
    """
    Public-facing scrub function that uses the global RedactionManager.
    """
    return redaction_manager.scrub(data)
