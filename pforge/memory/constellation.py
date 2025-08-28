import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, List

SCHEMA = """
CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    context TEXT,
    action TEXT,
    command TEXT,
    rc INT,
    stdout TEXT,
    before TEXT,
    after TEXT,
    reward REAL
);

CREATE TABLE IF NOT EXISTS action_stats (
    context TEXT,
    action TEXT,
    n INT,
    mean REAL,
    PRIMARY KEY (context, action)
);
"""

class Constellation:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._create_schema()

    def _create_schema(self):
        with self.conn:
            self.conn.executescript(SCHEMA)

    def record_transition(self, **kwargs) -> int:
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO transitions (ts, context, action, command, rc, stdout, before, after, reward)
                VALUES (:ts, :context, :action, :command, :rc, :stdout, :before, :after, :reward)
                """,
                {
                    "ts": time.time(),
                    "context": kwargs["context"],
                    "action": kwargs["action"],
                    "command": kwargs["command"],
                    "rc": kwargs["rc"],
                    "stdout": kwargs["stdout"],
                    "before": json.dumps(kwargs["before"]),
                    "after": json.dumps(kwargs["after"]),
                    "reward": kwargs["reward"],
                },
            )
            return cursor.lastrowid

    def update_action_stats(self, context: str, action: str, reward: float):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT n, mean FROM action_stats WHERE context = ? AND action = ?",
                (context, action),
            )
            row = cursor.fetchone()

            if row is None:
                cursor.execute(
                    "INSERT INTO action_stats (context, action, n, mean) VALUES (?, ?, ?, ?)",
                    (context, action, 1, reward),
                )
            else:
                n, mean = row
                new_n = n + 1
                new_mean = mean + (reward - mean) / new_n
                cursor.execute(
                    "UPDATE action_stats SET n = ?, mean = ? WHERE context = ? AND action = ?",
                    (new_n, new_mean, context, action),
                )

    def get_top_routes(self, top_k: int = 10) -> List[Dict[str, Any]]:
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, ts, context, action, reward FROM transitions ORDER BY reward DESC LIMIT ?",
                (top_k,),
            )
            rows = cursor.fetchall()
            return [
                {"id": r[0], "ts": r[1], "context": r[2], "action": r[3], "reward": r[4]}
                for r in rows
            ]
