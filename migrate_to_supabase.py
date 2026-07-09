import json
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

with open("dashboard_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Migrate students
for student in data.get("students", []):
    supabase.table("students").insert({
        "id": student["id"],
        "name": student["name"],
        "level": student.get("level", "B1"),
        "contact": student.get("contact", ""),
        "telegram_username": student.get("telegram_username", ""),
        "created_at": student.get("created_at")
    }).execute()

# Migrate payments
for payment in data.get("payments", []):
    supabase.table("payments").insert({
        "student_id": payment["student_id"],
        "paid_lessons": payment.get("paid_lessons", 0),
        "conducted_lessons": payment.get("conducted_lessons", 0)
    }).execute()

# Migrate lessons
for lesson in data.get("lessons", []):
    print(f"Migrating lesson {lesson.get('id', '')}")
    supabase.table("lessons").insert({
        "id": lesson["id"],
        "student_id": lesson["student_id"],
        "date": lesson["date"],
        "time": lesson["time"],
        "topic": lesson.get("topic", ""),
        "status": lesson.get("status", "scheduled"),
        "created_at": lesson.get("created_at")
    }).execute()

# Migrate homework
for hw in data.get("homework", []):
    print(f"Migrating homework {hw.get('id', '')}")
    supabase.table("homework").insert({
        "id": hw["id"],
        "student_id": hw["student_id"],
        "assignment": hw["assignment"],
        "status": hw.get("status", "sent"),
        "check_result": hw.get("check_result", ""),
        "grade": hw.get("grade", ""),
        "created_at": hw.get("created_at")
    }).execute()

print("Migration completed!")
