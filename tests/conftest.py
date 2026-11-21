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


# ---------------------------------------------------------------- API helpers
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api")
API_KEY = os.getenv("API_KEY", "dev-key")


@pytest.fixture
def api_url():
    return API_URL


@pytest.fixture
def auth_headers():
    return {"X-API-Key": API_KEY}