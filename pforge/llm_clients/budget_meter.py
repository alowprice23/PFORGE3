from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from typing import Optional

class BudgetExceededError(Exception):
    """Raised when an operation would exceed the allocated token budget."""
    pass

class BudgetMeter:
    """
    Tracks and enforces token budgets for LLM API calls.

    This class connects to a persistent SQLite database to maintain an
    auditable ledger of all token spend.
    """

    def __init__(self, db_path: Path | str, tenant: str = "default"):
        """
        Args:
            db_path: The path to the SQLite database file for the budget ledger.
            tenant: The tenant whose budget is being managed.
        """
        self.db_path = Path(db_path)
        self.tenant = tenant
        self._ensure_db_and_schema()
        # In a real system, quotas would be loaded from config/quotas.yaml
        self.daily_quota = 1_500_000 # Placeholder default

    def _ensure_db_and_schema(self):
        """Ensures the database and its schema exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            # We assume the schema file is available relative to this package
            # This is a bit fragile, but ok for the foundational slice.
            schema_path = Path(__file__).parent.parent / "storage/sqlite/budget_ledger_schema.sql"
            if schema_path.exists():
                conn.executescript(schema_path.read_text())
            else:
                # Fallback schema if file not found
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS token_spend (
                        id INTEGER PRIMARY KEY, ts REAL, vendor TEXT, op_id TEXT,
                        prompt_tokens INTEGER, completion_tokens INTEGER, cost_usd REAL
                    )
                """)

    def check_and_spend(
        self,
        vendor: str,
        op_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float
    ) -> bool:
        """
        Checks if the current spend is within budget and records it.
        This is a simplified version; a real one would be more transactional.
        """
        # 1. Check current usage
        with sqlite3.connect(self.db_path) as conn:
            today_start = time.time() - (24 * 60 * 60)
            cursor = conn.execute(
                "SELECT SUM(prompt_tokens + completion_tokens) FROM token_spend WHERE ts >= ?",
                (today_start,)
            )
            current_usage = cursor.fetchone()[0] or 0

        total_spend = prompt_tokens + completion_tokens

        # 2. Check against quota
        if (current_usage + total_spend) > self.daily_quota:
            return False

        # 3. Record the spend
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO token_spend (ts, vendor, op_id, prompt_tokens, completion_tokens, cost_usd)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (time.time(), vendor, op_id, prompt_tokens, completion_tokens, cost_usd)
            )
        return True

    def get_today_usage(self) -> int:
        """Returns the total tokens used in the last 24 hours."""
        with sqlite3.connect(self.db_path) as conn:
            today_start = time.time() - (24 * 60 * 60)
            cursor = conn.execute(
                "SELECT SUM(prompt_tokens + completion_tokens) FROM token_spend WHERE ts >= ?",
                (today_start,)
            )
            return cursor.fetchone()[0] or 0
