import os
import sqlite3

import pytest

DB_PATH = os.getenv("DB_PATH", "regwatch.db")


@pytest.fixture
def db():
    """Open a connection to the app's database, give it to the test, close it after."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read columns by name: row["title"]
    yield conn
    conn.close()
