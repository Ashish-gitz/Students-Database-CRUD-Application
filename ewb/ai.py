"""Optional bonus: grounded Q&A using a local Ollama model.

Safety design: the model NEVER writes or runs SQL. Backend code picks a fixed,
parameterised query from a small whitelist of filters, then passes only the
retrieved rows to the model as context.
"""
import json
import os
import re
import sqlite3

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
MAX_ROWS = 50
FIELDS = "id, name, date_of_birth, email, course, enrollment_date"


def retrieve(conn: sqlite3.Connection, question: str) -> tuple[list[dict], int, int]:
    """Return (rows, matched_count, total_students) using whitelisted filters."""
    q = question.lower()
    total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    where, params = [], []

    if m := re.search(r"(?:born\s+)?(?:after|since)\s+(\d{4})", q):
        where.append("date_of_birth > ?")
        params.append(f"{m.group(1)}-12-31")
    if m := re.search(r"(?:born\s+)?before\s+(\d{4})", q):
        where.append("date_of_birth < ?")
        params.append(f"{m.group(1)}-01-01")

    courses = [r[0] for r in conn.execute(
        "SELECT DISTINCT course FROM students WHERE course IS NOT NULL")]
    for c in courses:
        if c.lower() in q:
            where.append("course = ?")
            params.append(c)

    clause = f" WHERE {' AND '.join(where)}" if where else ""
    matched = conn.execute(f"SELECT COUNT(*) FROM students{clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT {FIELDS} FROM students{clause} ORDER BY id LIMIT {MAX_ROWS}", params
    ).fetchall()
    return [dict(r) for r in rows], matched, total


def ask_ollama(question: str, rows: list[dict], matched: int, total: int) -> str:
    context = (
        f"Total students in database: {total}\n"
        f"Students matching the question's filters: {matched}\n"
        f"Records (up to {MAX_ROWS}):\n{json.dumps(rows, indent=2)}"
    )
    messages = [
        {"role": "system", "content": (
            "You answer questions about a student database. Use ONLY the context "
            "provided. If the answer is not in the context, say you don't know. "
            "Be brief and do not invent records.")},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
    ]
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": OLLAMA_MODEL, "messages": messages, "stream": False,
              "options": {"temperature": 0}},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()
