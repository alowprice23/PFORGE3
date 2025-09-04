from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# It's good practice to define the default location for the database
DB_PATH = Path(__file__).parent.parent / "data/pforge.db"
SCHEMA_PATH = Path(__file__).parent / "sqlite/risk_model_schema.sql"

class RiskModelDB:
    """
    A class to manage the SQLite database for the PredictorAgent's risk model.
    """
    DEFAULT_ALPHA = 2.0
    DEFAULT_BETA = 1.0

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self._connect_and_initialize()

    def _connect_and_initialize(self):
        """Establishes a database connection and creates tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            with open(SCHEMA_PATH, 'r') as f:
                schema = f.read()
            self.conn.executescript(schema)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise

    def get_risk_params(self, file_path: str) -> Dict[str, float]:
        """
        Retrieves the alpha and beta risk parameters for a given file.
        If the file is not in the database, returns default values.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT alpha, beta FROM risk_model WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        if row:
            logger.info(f"Retrieved risk params for {file_path}: {dict(row)}")
            return dict(row)
        else:
            logger.info(f"No risk params found for {file_path}, returning defaults.")
            return {"alpha": self.DEFAULT_ALPHA, "beta": self.DEFAULT_BETA}

    def update_risk_params(self, file_path: str, success: bool):
        """
        Updates the alpha or beta parameter for a file based on the success
        of an edit. If the file does not exist, it is inserted first.
        """
        current_params = self.get_risk_params(file_path)
        logger.info(f"Updating risk for {file_path}. Current params: {current_params}")

        # A higher beta (rate) should mean lower risk (lower mean effort).
        # So, success increases beta, failure decreases it.
        if success:
            new_alpha = current_params['alpha']
            new_beta = current_params['beta'] + 0.5 # Increase rate on success
        else:
            new_alpha = current_params['alpha']
            # Decrease rate on failure, but clamp to avoid zero or negative.
            new_beta = max(0.1, current_params['beta'] - 0.5)

        logger.info(f"New params for {file_path}: alpha={new_alpha}, beta={new_beta}")
        cursor = self.conn.cursor()
        # Use INSERT OR REPLACE (UPSERT) to handle both cases
        cursor.execute(
            """
            INSERT OR REPLACE INTO risk_model (file_path, alpha, beta)
            VALUES (?, ?, ?)
            """,
            (file_path, new_alpha, new_beta)
        )
        self.conn.commit()

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
