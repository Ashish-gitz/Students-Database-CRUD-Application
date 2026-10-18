"""Students Database CRUD API - FastAPI + SQLite (+ optional Ollama Q&A)."""
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from pydantic import ValidationError

import ai
from database import get_db, init_db
from schemas import AskRequest, AskResponse, Student, StudentCreate, StudentUpdate

FIELDS = ["name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Students Database API", version="1.0.0", lifespan=lifespan)


def _to_db(data: dict) -> dict:
    """Convert date objects to ISO strings for SQLite."""
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in data.items()}


def _fetch(db: sqlite3.Connection, student_id: int) -> dict:
    row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Student {student_id} not found")
    return dict(row)


def _write_row(db: sqlite3.Connection, sql: str, params) -> sqlite3.Cursor:
    try:
        cur = db.execute(sql, params)
        db.commit()
        return cur
    except sqlite3.IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A student with this email already exists")


# ---------- CREATE ----------
@app.post("/students", response_model=Student, status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    data = _to_db(student.model_dump())
    cols = ", ".join(FIELDS)
    marks = ", ".join("?" for _ in FIELDS)
    cur = _write_row(db, f"INSERT INTO students ({cols}) VALUES ({marks})",
                     [data[f] for f in FIELDS])
    return _fetch(db, cur.lastrowid)


# ---------- READ (list + filter) ----------
@app.get("/students", response_model=list[Student])
def list_students(
    name: Optional[str] = Query(None, description="Partial, case-insensitive match"),
    course: Optional[str] = Query(None, description="Exact course name (case-insensitive)"),
    born_after: Optional[date] = Query(None, description="DOB strictly after this date"),
    born_before: Optional[date] = Query(None, description="DOB strictly before this date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    where, params = [], []
    if name:
        where.append("name LIKE ?")
        params.append(f"%{name}%")
    if course:
        where.append("LOWER(course) = LOWER(?)")
        params.append(course)
    if born_after:
        where.append("date_of_birth > ?")
        params.append(born_after.isoformat())
    if born_before:
        where.append("date_of_birth < ?")
        params.append(born_before.isoformat())
    clause = f" WHERE {' AND '.join(where)}" if where else ""
    rows = db.execute(
        f"SELECT * FROM students{clause} ORDER BY id LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- READ (single) ----------
@app.get("/students/{student_id}", response_model=Student)
def get_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    return _fetch(db, student_id)


# ---------- UPDATE (full replace) ----------
@app.put("/students/{student_id}", response_model=Student)
def replace_student(student_id: int, student: StudentCreate,
                    db: sqlite3.Connection = Depends(get_db)):
    _fetch(db, student_id)
    data = _to_db(student.model_dump())
    sets = ", ".join(f"{f} = ?" for f in FIELDS)
    _write_row(db, f"UPDATE students SET {sets} WHERE id = ?",
               [*(data[f] for f in FIELDS), student_id])
    return _fetch(db, student_id)


# ---------- UPDATE (partial) ----------
@app.patch("/students/{student_id}", response_model=Student)
def update_student(student_id: int, changes: StudentUpdate,
                   db: sqlite3.Connection = Depends(get_db)):
    existing = _fetch(db, student_id)
    updates = changes.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")
    merged = {**{f: existing[f] for f in FIELDS}, **updates}
    try:  # re-validate the final record (e.g. at least one contact must remain)
        valid = StudentCreate(**merged)
    except ValidationError as e:
        raise HTTPException(422, json.loads(e.json()))
    data = _to_db(valid.model_dump())
    keys = list(updates)
    sets = ", ".join(f"{k} = ?" for k in keys)
    _write_row(db, f"UPDATE students SET {sets} WHERE id = ?",
               [*(data[k] for k in keys), student_id])
    return _fetch(db, student_id)


# ---------- DELETE ----------
@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    _fetch(db, student_id)
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- OPTIONAL: local AI (Ollama) ----------
@app.post("/ask", response_model=AskResponse, tags=["AI (optional)"])
def ask(req: AskRequest, db: sqlite3.Connection = Depends(get_db)):
    rows, matched, total = ai.retrieve(db, req.question)
    try:
        answer = ai.ask_ollama(req.question, rows, matched, total)
    except (httpx.HTTPError, KeyError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ollama is not reachable. Start it with `ollama serve` and "
            f"`ollama pull {ai.OLLAMA_MODEL}`.")
    return AskResponse(answer=answer, records_used=rows,
                       matched_count=matched, total_students=total)
