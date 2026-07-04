"""
data_manager.py — Persistent data storage for English Teacher Dashboard.

Stores students, lessons and payment records in a local JSON file.
Designed for easy future migration to a cloud database (Supabase, Firebase, etc.).
"""

import json
import os
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Optional

DATA_FILE = Path(__file__).parent / "dashboard_data.json"

# ─── Default empty structure ─────────────────────────────────────────────────
_EMPTY_DATA = {
    "students": [],
    "lessons": [],
    "payments": [],
}


# ═══════════════════════════════════════════════════════════════════════════════
# LOW-LEVEL I/O
# ═══════════════════════════════════════════════════════════════════════════════

def load_data() -> dict:
    """Load the entire data store from disk (or return empty structure)."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure all keys exist (forward-compatible)
            for key in _EMPTY_DATA:
                data.setdefault(key, [])
            return data
        except (json.JSONDecodeError, IOError):
            return {k: list(v) for k, v in _EMPTY_DATA.items()}
    return {k: list(v) for k, v in _EMPTY_DATA.items()}


def save_data(data: dict) -> None:
    """Persist the entire data store to disk."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════════════
# STUDENTS
# ═══════════════════════════════════════════════════════════════════════════════

def add_student(name: str, level: str = "B1", contact: str = "") -> dict:
    """Add a new student and return the created record."""
    data = load_data()
    student = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "level": level,
        "contact": contact.strip(),
        "created_at": datetime.now().isoformat(),
    }
    data["students"].append(student)

    # Initialise payment record
    data["payments"].append({
        "student_id": student["id"],
        "paid_lessons": 0,
        "conducted_lessons": 0,
    })

    save_data(data)
    return student


def get_students() -> list[dict]:
    """Return all students sorted by name."""
    data = load_data()
    return sorted(data["students"], key=lambda s: s["name"])


def delete_student(student_id: str) -> None:
    """Remove a student and all associated lessons / payments."""
    data = load_data()
    data["students"] = [s for s in data["students"] if s["id"] != student_id]
    data["lessons"] = [l for l in data["lessons"] if l["student_id"] != student_id]
    data["payments"] = [p for p in data["payments"] if p["student_id"] != student_id]
    save_data(data)


def get_student_by_id(student_id: str) -> Optional[dict]:
    """Look up a single student by ID."""
    data = load_data()
    for s in data["students"]:
        if s["id"] == student_id:
            return s
    return None


def get_student_name(student_id: str) -> str:
    """Return student name or '???' if not found."""
    s = get_student_by_id(student_id)
    return s["name"] if s else "???"


# ═══════════════════════════════════════════════════════════════════════════════
# LESSONS / SCHEDULE
# ═══════════════════════════════════════════════════════════════════════════════

LESSON_STATUSES = ["scheduled", "conducted", "cancelled", "rescheduled"]


def add_lesson(student_id: str, lesson_date: str, lesson_time: str,
               topic: str = "") -> dict:
    """Create a new lesson entry. date = 'YYYY-MM-DD', time = 'HH:MM'."""
    data = load_data()
    lesson = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "date": lesson_date,
        "time": lesson_time,
        "topic": topic.strip(),
        "status": "scheduled",
        "created_at": datetime.now().isoformat(),
    }
    data["lessons"].append(lesson)
    save_data(data)
    return lesson


def get_all_lessons() -> list[dict]:
    """Return all lessons sorted by date+time descending (newest first)."""
    data = load_data()
    return sorted(data["lessons"], key=lambda l: (l["date"], l["time"]), reverse=True)


def get_lessons_for_student(student_id: str) -> list[dict]:
    """Return lessons for a specific student."""
    return [l for l in get_all_lessons() if l["student_id"] == student_id]


def get_upcoming_lessons() -> list[dict]:
    """Return only future scheduled lessons, sorted chronologically."""
    today = date.today().isoformat()
    all_lessons = get_all_lessons()
    upcoming = [l for l in all_lessons if l["date"] >= today and l["status"] == "scheduled"]
    return sorted(upcoming, key=lambda l: (l["date"], l["time"]))


def update_lesson_status(lesson_id: str, new_status: str) -> None:
    """Change a lesson's status (scheduled / conducted / cancelled / rescheduled)."""
    data = load_data()
    for lesson in data["lessons"]:
        if lesson["id"] == lesson_id:
            lesson["status"] = new_status
            break
    save_data(data)


def reschedule_lesson(lesson_id: str, new_date: str, new_time: str) -> None:
    """Move a lesson to a new date/time."""
    data = load_data()
    for lesson in data["lessons"]:
        if lesson["id"] == lesson_id:
            lesson["date"] = new_date
            lesson["time"] = new_time
            lesson["status"] = "scheduled"
            break
    save_data(data)


def mark_lesson_conducted(lesson_id: str) -> Optional[str]:
    """Mark lesson as conducted and decrement student's paid balance.
    Returns student_id if balance warning needed, else None."""
    data = load_data()
    student_id = None
    for lesson in data["lessons"]:
        if lesson["id"] == lesson_id:
            lesson["status"] = "conducted"
            student_id = lesson["student_id"]
            break

    warn_student = None
    if student_id:
        for pay in data["payments"]:
            if pay["student_id"] == student_id:
                pay["conducted_lessons"] += 1
                balance = pay["paid_lessons"] - pay["conducted_lessons"]
                if balance <= 0:
                    warn_student = student_id
                break

    save_data(data)
    return warn_student


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def record_payment(student_id: str, num_lessons: int) -> None:
    """Add paid lessons to a student's balance."""
    data = load_data()
    found = False
    for pay in data["payments"]:
        if pay["student_id"] == student_id:
            pay["paid_lessons"] += num_lessons
            found = True
            break
    if not found:
        data["payments"].append({
            "student_id": student_id,
            "paid_lessons": num_lessons,
            "conducted_lessons": 0,
        })
    save_data(data)


def get_payment_balance(student_id: str) -> dict:
    """Return payment info for a student: {paid, conducted, balance}."""
    data = load_data()
    for pay in data["payments"]:
        if pay["student_id"] == student_id:
            return {
                "paid": pay["paid_lessons"],
                "conducted": pay["conducted_lessons"],
                "balance": pay["paid_lessons"] - pay["conducted_lessons"],
            }
    return {"paid": 0, "conducted": 0, "balance": 0}


def get_all_payment_summaries() -> list[dict]:
    """Return payment summaries for all students."""
    students = get_students()
    result = []
    for s in students:
        bal = get_payment_balance(s["id"])
        result.append({
            "student_id": s["id"],
            "name": s["name"],
            "level": s["level"],
            "paid": bal["paid"],
            "conducted": bal["conducted"],
            "balance": bal["balance"],
        })
    return result
