"""SQLite helpers: connection management and schema creation."""
import os
import sqlite3

DB_PATH = os.getenv("STUDENTS_DB", "students.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    date_of_birth   TEXT NOT NULL,          -- ISO format YYYY-MM-DD
    email           TEXT UNIQUE,
    phone           TEXT,
    course          TEXT,
    address         TEXT,
    enrollment_date TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_db():
    """FastAPI dependency: one connection per request."""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
