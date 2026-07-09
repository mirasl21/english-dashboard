import streamlit as st
"""
data_manager.py — Persistent data storage for English Teacher Dashboard.

Uses Supabase (PostgreSQL) for cloud sync.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("WARNING: SUPABASE_URL or SUPABASE_KEY is missing from .env!")

class SafeSupabase:
    @property
    def _client(self):
        from supabase import ClientOptions
        # Disable HTTP2 to prevent Windows socket issues, and set timeout
        opts = ClientOptions()
        return create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

    def table(self, *args, **kwargs):
        return self._client.table(*args, **kwargs)

    @property
    def storage(self):
        return self._client.storage

supabase: Optional[SafeSupabase] = SafeSupabase() if (SUPABASE_URL and SUPABASE_KEY) else None


# ═══════════════════════════════════════════════════════════════════════════════
# STUDENTS
# ═══════════════════════════════════════════════════════════════════════════════

def add_student(name: str, level: str = "B1", contact: str = "") -> dict:
    st.cache_data.clear()
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

@st.cache_data(ttl=60, show_spinner=False)
def get_students() -> list[dict]:
    if not supabase: return []
    res = supabase.table("students").select("*").order("name").execute()
    return res.data

def delete_student(student_id: str) -> None:
    st.cache_data.clear()
    if not supabase: return
    supabase.table("students").delete().eq("id", student_id).execute()

@st.cache_data(ttl=60, show_spinner=False)
def get_student_by_id(student_id: str) -> Optional[dict]:
    if not supabase: return None
    res = supabase.table("students").select("*").eq("id", student_id).execute()
    return res.data[0] if res.data else None

@st.cache_data(ttl=60, show_spinner=False)
def get_student_name(student_id: str) -> str:
    s = get_student_by_id(student_id)
    return s["name"] if s else "Unknown"

@st.cache_data(ttl=60, show_spinner=False)
def get_student_by_telegram(username: str) -> Optional[dict]:
    """Find a student by their Telegram username (without @)."""
    if not supabase: return None
    clean = username.lower().lstrip("@")
    res = supabase.table("students").select("*").execute()
    for s in res.data:
        tg = (s.get("telegram_username") or "").lower().lstrip("@")
        if tg == clean:
            return s
    return None

def update_student(student_id: str, updates: dict) -> None:
    st.cache_data.clear()
    if not supabase: return
    supabase.table("students").update(updates).eq("id", student_id).execute()

def link_telegram(student_id: str, username: str) -> None:
    st.cache_data.clear()
    if not supabase: return
    supabase.table("students").update({"telegram_username": username.replace("@", "")}).eq("id", student_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# LESSONS
# ═══════════════════════════════════════════════════════════════════════════════

def check_time_available(date_str: str, time_str: str, exclude_lesson_id: str = None) -> bool:
    if not supabase: return True
    query = supabase.table("lessons").select("id").eq("date", date_str).eq("time", time_str).eq("status", "scheduled")
    if exclude_lesson_id:
        query = query.neq("id", exclude_lesson_id)
    res = query.execute()
    return len(res.data) == 0

def add_lesson(student_id: str, date_str: str, time_str: str, topic: str = "") -> dict:
    if not check_time_available(date_str, time_str):
        raise ValueError(f"Время {date_str} {time_str} уже занято другим уроком!")
    st.cache_data.clear()
    if not supabase: return {}
    res = supabase.table("lessons").insert({
        "student_id": student_id,
        "date": date_str,
        "time": time_str,
        "topic": topic.strip(),
        "status": "scheduled"
    }).execute()
    return res.data[0]

@st.cache_data(ttl=60, show_spinner=False)
def get_lessons_for_student(student_id: str) -> list[dict]:
    if not supabase: return []
    res = supabase.table("lessons").select("*").eq("student_id", student_id).execute()
    return res.data

@st.cache_data(ttl=60, show_spinner=False)
def get_all_lessons() -> list[dict]:
    if not supabase: return []
    res = supabase.table("lessons").select("*").execute()
    return res.data

@st.cache_data(ttl=60, show_spinner=False)
def get_upcoming_lessons() -> list[dict]:
    if not supabase: return []
    res = supabase.table("lessons").select("*").eq("status", "scheduled").execute()
    return res.data

def update_lesson_status(lesson_id: str, new_status: str) -> None:
    st.cache_data.clear()
    if not supabase: return
    supabase.table("lessons").update({"status": new_status}).eq("id", lesson_id).execute()

def reschedule_lesson(lesson_id: str, new_date: str, new_time: str) -> None:
    if not check_time_available(new_date, new_time, exclude_lesson_id=lesson_id):
        raise ValueError(f"Время {new_date} {new_time} уже занято другим уроком!")
    st.cache_data.clear()
    if not supabase: return
    supabase.table("lessons").update({
        "date": new_date,
        "time": new_time,
        "status": "rescheduled"
    }).eq("id", lesson_id).execute()

def mark_lesson_conducted(lesson_id: str) -> bool:
    st.cache_data.clear()
    """Mark a lesson as conducted and increment conducted_lessons counter.
    Returns True if the student's balance is at or below 0 (payment warning needed).
    """
    if not supabase: return False
    res = supabase.table("lessons").select("*").eq("id", lesson_id).execute()
    if not res.data: return False
    lesson = res.data[0]

    supabase.table("lessons").update({"status": "conducted"}).eq("id", lesson_id).execute()

    # Increment conducted lessons
    pay_res = supabase.table("payments").select("*").eq("student_id", lesson["student_id"]).execute()
    if pay_res.data:
        curr = pay_res.data[0]
        new_conducted = curr.get("conducted_lessons", 0) + 1
        supabase.table("payments").update({
            "conducted_lessons": new_conducted
        }).eq("student_id", lesson["student_id"]).execute()
        # Check if balance <= 0
        paid = curr.get("paid_lessons", 0)
        return (paid - new_conducted) <= 0
    return False

def delete_lesson(lesson_id: str) -> None:
    st.cache_data.clear()
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

@st.cache_data(ttl=60, show_spinner=False)
def get_payment_balance(student_id: str) -> dict:
    if not supabase: return {"paid": 0, "conducted": 0, "balance": 0}
    res = supabase.table("payments").select("*").eq("student_id", student_id).execute()
    if res.data:
        p = res.data[0]
        paid = p.get("paid_lessons", 0)
        conducted = p.get("conducted_lessons", 0)
        return {"paid": paid, "conducted": conducted, "balance": paid - conducted}
    return {"paid": 0, "conducted": 0, "balance": 0}

@st.cache_data(ttl=60, show_spinner=False)
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

def create_homework(student_id: str, assignment: str, due_date: str = "") -> dict:
    """Create a homework record. due_date is optional (YYYY-MM-DD)."""
    if not supabase: return {}
    res = supabase.table("homework").insert({
        "student_id": student_id,
        "assignment": assignment.strip(),
        "status": "sent"
    }).execute()
    return res.data[0]

@st.cache_data(ttl=60, show_spinner=False)
def get_all_homework() -> list[dict]:
    if not supabase: return []
    res = supabase.table("homework").select("*").order("created_at", desc=True).execute()
    return res.data

@st.cache_data(ttl=60, show_spinner=False)
def get_homework_by_id(hw_id: str) -> Optional[dict]:
    """Retrieve a single homework record by its ID."""
    if not supabase: return None
    res = supabase.table("homework").select("*").eq("id", hw_id).execute()
    return res.data[0] if res.data else None

@st.cache_data(ttl=60, show_spinner=False)
def get_pending_homeworks() -> list[dict]:
    if not supabase: return []
    res = supabase.table("homework").select("*").eq("status", "sent").execute()
    return res.data

# Alias for backwards compatibility with telegram_bot.py
get_pending_homework = get_pending_homeworks

def mark_homework_delivered(hw_id: str) -> None:
    st.cache_data.clear()
    if not supabase: return
    supabase.table("homework").update({"status": "delivered", "tg_delivered": True}).eq("id", hw_id).execute()

def submit_homework(hw_id: str, student_answer: str) -> None:
    """Record the student's answer for a homework assignment."""
    if not supabase: return
    supabase.table("homework").update({
        "status": "submitted",
        "student_answer": student_answer,
    }).eq("id", hw_id).execute()

def save_homework_check(hw_id: str, feedback: str, grade: str = "") -> None:
    st.cache_data.clear()
    """Save AI check results for a homework."""
    if not supabase: return
    supabase.table("homework").update({
        "status": "checked",
        "check_result": feedback,
        "grade": grade,
    }).eq("id", hw_id).execute()

def update_homework(hw_id: str, updates: dict) -> None:
    st.cache_data.clear()
    if not supabase: return
    supabase.table("homework").update(updates).eq("id", hw_id).execute()


# ═══════════════════════════════════════════════════════════════════════════════
# MATERIALS — Supabase Storage & DB for books and audio files
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Books ────────────────────────────────────────────────────────────────────

def add_book(title: str, filename: str, file_type: str = "image", file_bytes: bytes = b"") -> None:
    st.cache_data.clear()
    """Add a book to the library."""
    if not supabase: return
    
    # Upload to Supabase Storage
    try:
        supabase.storage.from_("materials").upload(filename, file_bytes)
    except Exception as e:
        print(f"Error uploading file: {e}")

    # Add to database
    supabase.table("materials_books").insert({
        "title": title,
        "filename": filename,
        "file_type": file_type,
        "file_path": filename,
    }).execute()

def get_file(filename: str, bucket: str = "materials") -> bytes:
    """Download file bytes from Supabase storage."""
    if not supabase: return b""
    try:
        res = supabase.storage.from_(bucket).download(filename)
        return res
    except Exception as e:
        print(f"Error downloading file: {e}")
        return b""

@st.cache_data(ttl=60, show_spinner=False)
def get_books() -> list[dict]:
    if not supabase: return []
    res = supabase.table("materials_books").select("*").order("created_at", desc=True).execute()
    return res.data

def delete_book(book_id: str) -> None:
    st.cache_data.clear()
    """Delete a book by its unique ID. Also removes the file from storage."""
    if not supabase: return
    res = supabase.table("materials_books").select("*").eq("id", book_id).execute()
    if res.data:
        filename = res.data[0].get("filename")
        if filename:
            try:
                supabase.storage.from_("materials").remove([filename])
            except Exception:
                pass
        supabase.table("materials_books").delete().eq("id", book_id).execute()

@st.cache_data(ttl=60, show_spinner=False)
def get_book_file(filename: str) -> bytes:
    """Download book file from Supabase Storage."""
    if not supabase: return b""
    try:
        return supabase.storage.from_("materials").download(filename)
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return b""


# ─── Audio Files ──────────────────────────────────────────────────────────────

def add_audio_file(title: str, filename: str, file_bytes: bytes, book_id: str = "",
                   topic: str = "", level: str = "B2") -> None:
    """Add an audio file to the library."""
    if not supabase: return
    
    try:
        supabase.storage.from_("materials").upload(filename, file_bytes)
    except Exception as e:
        print(f"Error uploading audio file: {e}")

    supabase.table("materials_audio").insert({
        "title": title,
        "filename": filename,
        "file_path": filename,
        "book_id": book_id,
        "topic": topic,
        "level": level,
    }).execute()

@st.cache_data(ttl=60, show_spinner=False)
def get_audio_files() -> list[dict]:
    if not supabase: return []
    res = supabase.table("materials_audio").select("*").order("created_at", desc=True).execute()
    return res.data

def delete_audio_file(audio_id: str) -> None:
    st.cache_data.clear()
    """Delete an audio file by its unique ID. Also removes the file from storage."""
    if not supabase: return
    res = supabase.table("materials_audio").select("*").eq("id", audio_id).execute()
    if res.data:
        filename = res.data[0].get("filename")
        if filename:
            try:
                supabase.storage.from_("materials").remove([filename])
            except Exception:
                pass
        supabase.table("materials_audio").delete().eq("id", audio_id).execute()

@st.cache_data(ttl=60, show_spinner=False)
def get_audio_file(filename: str) -> bytes:
    """Download audio file from Supabase Storage."""
    if not supabase: return b""
    try:
        return supabase.storage.from_("materials").download(filename)
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return b""

