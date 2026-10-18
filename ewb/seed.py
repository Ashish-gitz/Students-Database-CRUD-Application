"""Load DUMMY students for testing. No real personal data."""
from database import get_conn, init_db

DUMMY = [
    ("Aarav Sharma", "2004-03-12", "aarav@example.com", "9876500001", "Computer Science", "2022-08-01"),
    ("Diya Nair", "2005-07-25", "diya@example.com", "9876500002", "Electronics", "2023-08-01"),
    ("Rohan Gupta", "2006-01-09", "rohan@example.com", None, "Computer Science", "2024-08-01"),
    ("Meera Iyer", "2003-11-30", "meera@example.com", "9876500004", "Mechanical", "2021-08-01"),
    ("Kabir Singh", "2005-12-02", None, "9876500005", "Electronics", "2023-08-01"),
    ("Ananya Rao", "2006-05-18", "ananya@example.com", "9876500006", "Data Science", "2024-08-01"),
]

init_db()
conn = get_conn()
for name, dob, email, phone, course, enrolled in DUMMY:
    conn.execute(
        "INSERT OR IGNORE INTO students (name, date_of_birth, email, phone, course, enrollment_date) "
        "VALUES (?,?,?,?,?,?)", (name, dob, email, phone, course, enrolled))
conn.commit()
conn.close()
print(f"Seeded {len(DUMMY)} dummy students.")
