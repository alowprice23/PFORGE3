from __future__ import annotations
import sqlite3
from pathlib import Path

def run_migrations_and_seed(
    db_path: str | Path,
    sql_script_path: str | Path,
) -> dict:
    """
    Runs a SQL script against a SQLite database to perform migrations and seeding.

    Args:
        db_path: The path to the SQLite database file.
        sql_script_path: The path to the .sql file containing the commands.

    Returns:
        A dictionary containing a proof of the action taken.
    """
    try:
        db_path = Path(db_path)
        sql_path = Path(sql_script_path)

        sql_script = sql_path.read_text()

        with sqlite3.connect(db_path) as con:
            cur = con.cursor()
            cur.executescript(sql_script)
            con.commit()

        proof = {
            "action": "run_migrations_and_seed",
            "status": "success",
            "database": str(db_path),
            "script": str(sql_path),
        }
        return proof
    except FileNotFoundError as e:
        return {"action": "run_migrations_and_seed", "status": "error", "error": f"File not found: {e.filename}"}
    except sqlite3.Error as e:
        return {"action": "run_migrations_and_seed", "status": "error", "error": str(e)}
    except Exception as e:
        return {"action": "run_migrations_and_seed", "status": "error", "error": str(e)}
