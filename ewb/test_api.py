import os
import sys
import tempfile

os.environ["STUDENTS_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

GOOD = {"name": "Test User", "date_of_birth": "2004-01-15",
        "email": "test@example.com", "course": "CS"}


def test_full_crud_flow():
    with TestClient(app) as c:
        r = c.post("/students", json=GOOD)
        assert r.status_code == 201
        sid = r.json()["id"]

        assert c.get(f"/students/{sid}").json()["name"] == "Test User"
        assert len(c.get("/students").json()) == 1
        assert len(c.get("/students?born_after=2003-01-01").json()) == 1
        assert c.get("/students?course=nope").json() == []

        r = c.patch(f"/students/{sid}", json={"course": "ECE"})
        assert r.status_code == 200 and r.json()["course"] == "ECE"

        r = c.put(f"/students/{sid}", json={**GOOD, "name": "Renamed"})
        assert r.json()["name"] == "Renamed"

        assert c.delete(f"/students/{sid}").status_code == 204
        assert c.get(f"/students/{sid}").status_code == 404


def test_validation_and_errors():
    with TestClient(app) as c:
        assert c.post("/students", json={"name": "X", "date_of_birth": "2004-01-01"}).status_code == 422
        assert c.post("/students", json={**GOOD, "date_of_birth": "2999-01-01"}).status_code == 422
        assert c.post("/students", json={**GOOD, "email": "bad"}).status_code == 422
        assert c.get("/students/9999").status_code == 404
        assert c.delete("/students/9999").status_code == 404
        assert c.patch("/students/9999", json={"name": "A"}).status_code == 404


def test_duplicate_email_and_contact_rule():
    with TestClient(app) as c:
        a = c.post("/students", json={**GOOD, "email": "dup@example.com"})
        assert a.status_code == 201
        assert c.post("/students", json={**GOOD, "email": "dup@example.com"}).status_code == 409
        # removing the only contact via PATCH must fail
        sid = a.json()["id"]
        assert c.patch(f"/students/{sid}", json={"email": None}).status_code == 422
