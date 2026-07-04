"""
data_manager.py — Persistent data storage for English Teacher Dashboard.

Uses Supabase (PostgreSQL) for cloud sync.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

BOOKS_DIR = Path(__file__).parent / "books"
AUDIO_DIR = Path(__file__).parent / "audio_files"
BOOKS_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("WARNING: SUPABASE_URL or SUPABASE_KEY is missing from .env!")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# STUDENTS
# ═══════════════════════════════════════════════════════════════════════════════

def add_student(name: str, level: str = "B1", contact: str = "") -> dict:
    if not supabase: return {}
    res = supabase.table("students").insert({
        "name": name.strip(),
        "level": level,
        "contact": contact.strip(),
    }).execute()
    student = res.data[0]
    
    supabase.table("payments").insert({
        "student_id": student["id"],
        "paid_lessons": 0,
        "conducted_lessons": 0,
    }).execute()
    return student

def get_students() -> list[dict]:
    if not supabase: return []
    res = supabase.table("students").select("*").order("name").execute()
    return res.data

def delete_student(student_id: str) -> None:
    if not supabase: return
    supabase.table("students").delete().eq("id", student_id).execute()

def get_student_by_id(student_id: str) -> Optional[dict]:
    if not supabase: return None
    res = supabase.table("students").select("*").eq("id", student_id).execute()
    return res.data[0] if res.data else None

def get_student_name(student_id: str) -> str:
    s = get_student_by_id(student_id)
    return s["name"] if s else "Unknown"

def update_student(student_id: str, updates: dict) -> None:
    if not supabase: return
    supabase.table("students").update(updates).eq("id", student_id).execute()

def link_telegram(student_id: str, username: str) -> None:
    if not supabase: return
    supabase.table("students").update({"telegram_username": username.replace("@", "")}).eq("id", student_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# LESSONS
# ═══════════════════════════════════════════════════════════════════════════════

def add_lesson(student_id: str, date_str: str, time_str: str, topic: str = "") -> dict:
    if not supabase: return {}
    res = supabase.table("lessons").insert({
        "student_id": student_id,
        "date": date_str,
        "time": time_str,
        "topic": topic.strip(),
        "status": "scheduled"
    }).execute()
    return res.data[0]

def get_lessons_for_student(student_id: str) -> list[dict]:
    if not supabase: return []
    res = supabase.table("lessons").select("*").eq("student_id", student_id).execute()
    return res.data

def get_all_lessons() -> list[dict]:
    if not supabase: return []
    res = supabase.table("lessons").select("*").execute()
    return res.data

def get_upcoming_lessons() -> list[dict]:
    if not supabase: return []
    res = supabase.table("lessons").select("*").eq("status", "scheduled").execute()
    return res.data

def update_lesson_status(lesson_id: str, new_status: str) -> None:
    if not supabase: return
    supabase.table("lessons").update({"status": new_status}).eq("id", lesson_id).execute()

def reschedule_lesson(lesson_id: str, new_date: str, new_time: str) -> None:
    if not supabase: return
    supabase.table("lessons").update({
        "date": new_date,
        "time": new_time,
        "status": "rescheduled"
    }).eq("id", lesson_id).execute()

def mark_lesson_conducted(lesson_id: str) -> None:
    if not supabase: return
    res = supabase.table("lessons").select("*").eq("id", lesson_id).execute()
    if not res.data: return
    lesson = res.data[0]
    
    supabase.table("lessons").update({"status": "conducted"}).eq("id", lesson_id).execute()
    
    # Increment conducted lessons
    pay_res = supabase.table("payments").select("*").eq("student_id", lesson["student_id"]).execute()
    if pay_res.data:
        curr = pay_res.data[0]
        supabase.table("payments").update({
            "conducted_lessons": curr.get("conducted_lessons", 0) + 1
        }).eq("student_id", lesson["student_id"]).execute()

def delete_lesson(lesson_id: str) -> None:
    if not supabase: return
    supabase.table("lessons").delete().eq("id", lesson_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENTS
# ═══════════════════════════════════════════════════════════════════════════════

def record_payment(student_id: str, paid_lessons: int, amount: float = None) -> None:
    if not supabase: return
    res = supabase.table("payments").select("*").eq("student_id", student_id).execute()
    if res.data:
        curr = res.data[0]
        supabase.table("payments").update({
            "paid_lessons": curr.get("paid_lessons", 0) + paid_lessons
        }).eq("student_id", student_id).execute()

def get_payment_balance(student_id: str) -> dict:
    if not supabase: return {"paid": 0, "conducted": 0, "balance": 0}
    res = supabase.table("payments").select("*").eq("student_id", student_id).execute()
    if res.data:
        p = res.data[0]
        paid = p.get("paid_lessons", 0)
        conducted = p.get("conducted_lessons", 0)
        return {"paid": paid, "conducted": conducted, "balance": paid - conducted}
    return {"paid": 0, "conducted": 0, "balance": 0}

def get_all_payment_summaries() -> list[dict]:
    if not supabase: return []
    students = supabase.table("students").select("*").execute().data
    payments = supabase.table("payments").select("*").execute().data
    
    p_map = {p["student_id"]: p for p in payments}
    summaries = []
    for s in students:
        p = p_map.get(s["id"], {})
        conducted = p.get("conducted_lessons", 0)
        paid = p.get("paid_lessons", 0)
        balance = paid - conducted
        summaries.append({
            "student_id": s["id"],
            "name": s["name"],
            "level": s.get("level", "B1"),
            "paid": paid,
            "balance": balance,
            "conducted": conducted
        })
    return summaries


# ═══════════════════════════════════════════════════════════════════════════════
# HOMEWORK
# ═══════════════════════════════════════════════════════════════════════════════

def create_homework(student_id: str, assignment: str) -> dict:
    if not supabase: return {}
    res = supabase.table("homework").insert({
        "student_id": student_id,
        "assignment": assignment.strip(),
        "status": "sent"
    }).execute()
    return res.data[0]

def get_all_homework() -> list[dict]:
    if not supabase: return []
    res = supabase.table("homework").select("*").execute()
    return res.data

def get_pending_homeworks() -> list[dict]:
    if not supabase: return []
    res = supabase.table("homework").select("*").eq("status", "sent").execute()
    return res.data

# Alias for backwards compatibility with telegram_bot.py
get_pending_homework = get_pending_homeworks

def mark_homework_delivered(hw_id: str) -> None:
    if not supabase: return
    supabase.table("homework").update({"status": "delivered"}).eq("id", hw_id).execute()

def update_homework(hw_id: str, updates: dict) -> None:
    if not supabase: return
    supabase.table("homework").update(updates).eq("id", hw_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# MATERIALS (Local for now)
# ═══════════════════════════════════════════════════════════════════════════════

import json
MATERIALS_DB = Path(__file__).parent / "materials.json"

def _load_materials():
    if MATERIALS_DB.exists():
        with open(MATERIALS_DB, "r") as f:
            return json.load(f)
    return {"books": [], "audio": []}

def _save_materials(data):
    with open(MATERIALS_DB, "w") as f:
        json.dump(data, f)

def add_book(title: str, filename: str) -> None:
    data = _load_materials()
    data["books"].append({"title": title, "filename": filename})
    _save_materials(data)

def get_books() -> list[dict]:
    return _load_materials()["books"]

def delete_book(filename: str) -> None:
    data = _load_materials()
    data["books"] = [b for b in data["books"] if b["filename"] != filename]
    _save_materials(data)

def add_audio_file(title: str, filename: str) -> None:
    data = _load_materials()
    data["audio"].append({"title": title, "filename": filename})
    _save_materials(data)

def get_audio_files() -> list[dict]:
    return _load_materials()["audio"]

def delete_audio_file(filename: str) -> None:
    data = _load_materials()
    data["audio"] = [a for a in data["audio"] if a["filename"] != filename]
    _save_materials(data)
