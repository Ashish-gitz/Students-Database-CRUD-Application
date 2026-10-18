[README.md](https://github.com/user-attachments/files/33620507/README.md)
# Students-Database-CRUD-Application
Backend for managing student records: **FastAPI + SQLite**, with an optional **Ollama** extension that answers natural-language questions about the data. Built for the EWB Edu Tech Python Backend Internship.
# Students Database CRUD API

Backend for managing student records: **FastAPI + SQLite**, with an optional
**Ollama** extension that answers natural-language questions about the data.
Built for the EWB Edu Tech Python Backend Internship.

## Features
- Create / Read (list, filter, single) / Update (PUT + PATCH) / Delete
- Input validation (valid email, phone format, DOB not in future, at least one contact)
- Proper errors: `404` missing record, `409` duplicate email, `422` invalid input
- Persistent storage in `students.db` (SQLite, created on first run)
- Optional `POST /ask` for grounded AI answers (local model, no unrestricted SQL)

## Project structure
```
main.py        API routes
database.py    SQLite connection + schema
schemas.py     Pydantic validation models
ai.py          Optional Ollama integration
seed.py        Dummy data loader
tests/         Automated API tests
```

## Prerequisites
- Python 3.10+
- (Optional AI) [Ollama](https://ollama.com) installed

## Installation
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python seed.py                   # optional: load 6 DUMMY students
uvicorn main:app --reload
```
Interactive docs (test every endpoint in the browser): http://127.0.0.1:8000/docs

## API endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/students` | Create a student |
| GET | `/students` | List / filter (`name`, `course`, `born_after`, `born_before`, `limit`, `offset`) |
| GET | `/students/{student_id}` | View one student |
| PUT | `/students/{student_id}` | Replace all details |
| PATCH | `/students/{student_id}` | Update selected fields |
| DELETE | `/students/{student_id}` | Delete a student |
| POST | `/ask` | (Optional) Ask the local AI a question |

Fields: `id` (auto, unique), `name`, `date_of_birth` (YYYY-MM-DD), `email` and/or `phone`
(at least one required), optional `course`, `address`, `enrollment_date`.

## Sample requests (curl)
```bash
# Create
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"name":"Priya Menon","date_of_birth":"2005-04-10","email":"priya@example.com","course":"Electronics"}'

# List all / filter
curl http://127.0.0.1:8000/students
curl "http://127.0.0.1:8000/students?course=Electronics&born_after=2004-12-31"

# View one
curl http://127.0.0.1:8000/students/1

# Update (partial)
curl -X PATCH http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" \
  -d '{"course":"Data Science"}'

# Delete
curl -X DELETE http://127.0.0.1:8000/students/1
```

## Run tests
```bash
pytest -q
```

## Optional: AI extension (Ollama)
```bash
ollama pull llama3.2:1b
ollama serve                     # skip if already running
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"List students born after 2005"}'
```
**How it stays grounded and safe:** the model never writes or runs SQL. Backend code
extracts simple filters (year, course) from the question, runs fixed parameterised
queries, and sends only the retrieved rows plus exact counts to the model, which is
instructed to answer only from that context. The response also returns `records_used`
so answers can be verified. If Ollama is not running, `/ask` returns `503`; the CRUD
API is unaffected.

Config (env vars): `OLLAMA_MODEL` (default `llama3.2:1b`), `OLLAMA_URL`
(default `http://localhost:11434`), `STUDENTS_DB` (default `students.db`).

## Notes
- Only dummy data is used; no secrets or real personal information are committed (`.gitignore` excludes `*.db` and `.env`).
