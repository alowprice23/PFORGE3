from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Tuple

def check_schema_drift(
    db_path: str | Path, expected_version: int
) -> Tuple[bool, dict]:
    """
    Checks for database schema drift by comparing the version in a
    'schema_version' table to an expected version.

    Args:
        db_path: The path to the SQLite database file.
        expected_version: The expected schema version number.

    Returns:
        A tuple containing a boolean indicating if the check passed, and a
        details dictionary.
    """
    if not Path(db_path).exists():
        return False, {"status": "error", "error": f"Database not found at {db_path}"}

    try:
        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            # Check for the existence of the version table first.
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
            if cur.fetchone() is None:
                return False, {"status": "missing_version_table"}

            # Get the current version.
            cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cur.fetchone()
            actual_version = row[0] if row else 0

            is_ok = actual_version == expected_version
            witness = {
                "expected_version": expected_version,
                "actual_version": actual_version,
            }
            return is_ok, witness

    except sqlite3.Error as e:
        return False, {"status": "error", "error": str(e)}
