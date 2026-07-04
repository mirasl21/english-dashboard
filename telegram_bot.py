"""
telegram_bot.py — Telethon Userbot for English Teacher Dashboard.

Monitors incoming Telegram messages from students to:
1. Detect schedule changes (reschedule/cancel) via AI parsing
2. Receive homework answers and auto-check them via AI

Requires:
  - Telegram API ID & Hash (from https://my.telegram.org)
  - Phone number for one-time authorization
  - AI API key (OpenAI or Gemini)

Usage:
  python telegram_bot.py                    # Start the userbot
  python telegram_bot.py --test             # Test connection
"""

import asyncio
import json
import os
import re
import sys
import signal
from datetime import date, datetime
from pathlib import Path

# ─── Configuration file ─────────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).parent / "telegram_config.json"

DEFAULT_CONFIG = {
    "api_id": "",
    "api_hash": "",
    "phone": "",
    "ai_api_key": "",
    "ai_provider": "OpenAI (GPT-4o)",
    "notion_token": "",
    "notion_db_id": "",
    "monitored_usernames": [],  # Telegram usernames of students to watch
}


def load_config() -> dict:
    """Load bot configuration from JSON file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """Save bot configuration to JSON file."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ─── AI Helpers (standalone, no Streamlit dependency) ────────────────────────

def call_ai(prompt: str, api_key: str, provider: str) -> str:
    """Call AI model for text processing."""
    if "openai" in provider.lower() or "gpt" in provider.lower():
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    else:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text.strip()


def call_vision_ai_standalone(prompt: str, image_bytes: bytes, api_key: str, provider: str) -> str:
    """Call AI model for image + text processing."""
    import base64
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

    if "openai" in provider.lower() or "gpt" in provider.lower():
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}", "detail": "high"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            temperature=0.6,
            max_tokens=4096,
        )
        return response.choices[0].message.content.strip()
    else:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}
        response = model.generate_content([prompt, image_part])
        return response.text.strip()


# ─── Schedule parsing ────────────────────────────────────────────────────────

def parse_schedule_message(text: str, student_name: str, api_key: str,
                           provider: str, all_student_names: list[str]) -> dict | None:
    """Use AI to parse a student message for schedule changes.
    Returns parsed dict or None if the message is not schedule-related."""
    prompt = (
        f"You are a scheduling assistant for an English teacher.\n"
        f"Analyze this message from student '{student_name}' and determine "
        f"if it contains a request to change, cancel, or add a lesson.\n\n"
        f"Known students: {', '.join(all_student_names)}\n"
        f"Today's date: {date.today().isoformat()}\n\n"
        f"Message: \"{text}\"\n\n"
        f"If this message IS about scheduling, return a JSON object:\n"
        f'{{"is_schedule": true, "student_name": "...", "action": "reschedule|cancel|add", '
        f'"old_date": "YYYY-MM-DD", "new_date": "YYYY-MM-DD", "new_time": "HH:MM", "topic": "..."}}\n\n'
        f"If this message is NOT about scheduling (e.g. just chatting, asking a question), return:\n"
        f'{{"is_schedule": false}}\n\n'
        f"Return ONLY the JSON, no extra text."
    )
    try:
        raw = call_ai(prompt, api_key, provider)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if parsed.get("is_schedule"):
                return parsed
    except Exception as e:
        print(f"[Bot] Error parsing schedule message: {e}")
    return None


# ─── Homework checking ──────────────────────────────────────────────────────

def check_homework_with_ai(assignment: str, student_answer: str,
                            student_level: str, api_key: str,
                            provider: str, image_bytes: bytes = None) -> str:
    """Check homework using AI and return feedback text."""
    prompt = (
        f"You are a professional English teacher checking homework.\n"
        f"Student Level: {student_level}\n\n"
        f"ASSIGNMENT:\n\"\"\"\n{assignment}\n\"\"\"\n\n"
    )
    if student_answer:
        prompt += f"STUDENT'S ANSWER:\n\"\"\"\n{student_answer}\n\"\"\"\n\n"
    if image_bytes:
        prompt += "The student's answer is also attached as an image.\n\n"

    prompt += (
        "Provide a clear response in Russian:\n"
        "1. **Оценка**: X/10\n"
        "2. **Правильные ответы**: показать правильную версию\n"
        "3. **Ошибки**: перечислить каждую ошибку с объяснением\n"
        "4. **Исправленная версия**: ответ ученика со всеми исправлениями\n"
        "5. **Рекомендации**: советы для улучшения\n"
        "Keep it friendly and encouraging."
    )

    if image_bytes:
        return call_vision_ai_standalone(prompt, image_bytes, api_key, provider)
    return call_ai(prompt, api_key, provider)


# ═════════════════════════════════════════════════════════════════════════════
# TELETHON USERBOT
# ═════════════════════════════════════════════════════════════════════════════

async def run_userbot():
    """Start the Telethon userbot to monitor student messages."""
    try:
        from telethon import TelegramClient, events
    except ImportError:
        print("[Bot] ERROR: Telethon is not installed. Run: pip install telethon")
        return

    import data_manager as dm
    import notion_sync

    config = load_config()

    if not config["api_id"] or not config["api_hash"]:
        print("[Bot] ERROR: api_id and api_hash are required.")
        print("[Bot] Get them at https://my.telegram.org")
        print("[Bot] Then configure via the Dashboard sidebar or edit telegram_config.json")
        return

    session_file = str(Path(__file__).parent / "teacher_session")
    client = TelegramClient(session_file, int(config["api_id"]), config["api_hash"])

    # Track pending homework per user (telegram_id -> hw_id)
    pending_hw_answers = {}

    @client.on(events.NewMessage(incoming=True))
    async def handle_message(event):
        """Process incoming messages from monitored students."""
        if not event.is_private:
            return

        sender = await event.get_sender()
        if not sender or not sender.username:
            return

        username = sender.username.lower()
        # Dynamically fetch monitored usernames from the database
        monitored = [
            s.get("telegram_username", "").lower().lstrip("@")
            for s in dm.get_students()
            if s.get("telegram_username")
        ]

        if username not in monitored:
            return

        # Find the student in our database
        student = dm.get_student_by_telegram(username)
        if not student:
            print(f"[Bot] Message from @{username} — not linked to any student")
            return

        message_text = event.text or ""
        student_name = student["name"]
        api_key = config.get("ai_api_key", "")
        provider = config.get("ai_provider", "OpenAI (GPT-4o)")

        if not api_key:
            print(f"[Bot] No AI API key configured — cannot process messages")
            return

        # ─── 1. Check intent using AI for schedule changes ───────────────────
        all_students = dm.get_students()
        all_names = [s["name"] for s in all_students]

        parsed = parse_schedule_message(
            message_text, student_name, api_key, provider, all_names
        )

        if parsed:
            action = parsed.get("action", "")
            if action in ["reschedule", "cancel", "add"]:
                print(f"[Bot] Schedule change detected from {student_name}: {action}")
                try:
                    if action == "reschedule":
                        old_d = parsed.get("old_date", "")
                        new_d = parsed.get("new_date", "")
                        new_t = parsed.get("new_time", "14:00")

                        lessons = dm.get_lessons_for_student(student["id"])
                        target = next(
                            (l for l in lessons if l["date"] == old_d and l["status"] == "scheduled"),
                            None
                        )
                        if target:
                            dm.update_lesson_status(target["id"], "rescheduled")
                            dm.add_lesson(student["id"], new_d, new_t, target.get("topic", ""))
                            if config.get("notion_token") and config.get("notion_db_id"):
                                # Try to find the old lesson in Notion
                                page_id = notion_sync.find_lesson_in_notion(
                                    config["notion_token"], config["notion_db_id"],
                                    student_name, old_d
                                )
                                if page_id:
                                    # Update existing card to the new date and time
                                    notion_sync.update_lesson_in_notion(
                                        config["notion_token"], page_id, "Scheduled", new_d, new_t
                                    )
                                else:
                                    # Fallback: push a new lesson for the new date
                                    notion_sync.push_lesson_to_notion(
                                        config["notion_token"], config["notion_db_id"],
                                        student_name, new_d, new_t,
                                        target.get("topic", ""),
                                        status="Scheduled",
                                    )
                            await event.reply(
                                f"✅ Урок перенесён: {old_d} → {new_d} в {new_t}\n"
                                f"Расписание обновлено!"
                            )
                        else:
                            await event.reply(
                                f"⚠️ Не нашла урок на {old_d}. Проверь расписание или уточни дату."
                            )

                    elif action == "cancel":
                        old_d = parsed.get("old_date", "")
                        lessons = dm.get_lessons_for_student(student["id"])
                        target = next(
                            (l for l in lessons if l["date"] == old_d and l["status"] == "scheduled"),
                            None
                        )
                        if target:
                            dm.update_lesson_status(target["id"], "cancelled")
                            await event.reply(f"✅ Урок на {old_d} отменён.")
                        else:
                            await event.reply(f"⚠️ Не нашла урок на {old_d}.")

                    elif action == "add":
                        new_d = parsed.get("new_date", "")
                        new_t = parsed.get("new_time", "14:00")
                        topic = parsed.get("topic", "")
                        dm.add_lesson(student["id"], new_d, new_t, topic)
                        if config.get("notion_token") and config.get("notion_db_id"):
                            notion_sync.push_lesson_to_notion(
                                config["notion_token"], config["notion_db_id"],
                                student_name, new_d, new_t, topic,
                            )
                        await event.reply(
                            f"✅ Урок добавлен: {new_d} в {new_t}\n"
                            f"{'Тема: ' + topic if topic else ''}"
                        )
                except Exception as e:
                    print(f"[Bot] Error processing schedule change: {e}")
                    await event.reply("⚠️ Произошла ошибка при обновлении расписания.")
                return

        # ─── 2. If not a schedule change, check if it's a homework answer ─────
        hw_id = pending_hw_answers.get(sender.id)
        if hw_id:
            hw = dm.get_homework_by_id(hw_id)
            if hw and hw["status"] == "sent":
                print(f"[Bot] Homework answer from {student_name}: {message_text[:80]}...")

                # Get image if attached
                image_bytes = None
                if event.photo:
                    image_bytes = await event.download_media(bytes)

                answer_text = message_text if message_text else "(фото-ответ)"
                dm.submit_homework(hw_id, answer_text)

                # AI check
                try:
                    feedback = check_homework_with_ai(
                        hw["assignment"], answer_text,
                        student.get("level", "B1"),
                        api_key, provider, image_bytes,
                    )
                    # Extract grade from feedback
                    grade_match = re.search(r'(\d+)\s*/\s*10', feedback)
                    grade = grade_match.group(0) if grade_match else ""

                    dm.save_homework_check(hw_id, feedback, grade)

                    await event.reply(
                        f"✅ Домашка проверена!\n\n{feedback}"
                    )
                    print(f"[Bot] Homework checked for {student_name}: {grade}")
                except Exception as e:
                    await event.reply("⚠️ Не удалось проверить домашку автоматически. Учитель проверит вручную.")
                    print(f"[Bot] Error checking homework: {e}")

                del pending_hw_answers[sender.id]
                return

        print(f"[Bot] Non-schedule message from {student_name}: {message_text[:60]}...")

    # ─── Function to send homework to a student ─────────────────────────
    async def send_homework_to_student(telegram_username: str, hw_id: str,
                                        assignment_text: str):
        """Send homework assignment to a student via Telegram."""
        try:
            entity = await client.get_entity(telegram_username)
            await client.send_message(
                entity,
                f"📝 **Домашнее задание:**\n\n{assignment_text}\n\n"
                f"Отправь мне ответ текстом или фото, и я проверю! 📚"
            )
            pending_hw_answers[entity.id] = hw_id
            print(f"[Bot] Homework sent to @{telegram_username}")
            return True
        except Exception as e:
            print(f"[Bot] Error sending homework to @{telegram_username}: {e}")
            return False

    # ─── Background Polling for New Homework ────────────────────────────
    async def poll_for_homework():
        """Poll data_manager for newly created homework to send."""
        # 1. Restore pending homework associations from previous runs
        try:
            for hw in dm.get_pending_homework():
                if hw.get("tg_delivered"):
                    student = dm.get_student_by_id(hw["student_id"])
                    if student and student.get("telegram_username"):
                        try:
                            entity = await client.get_entity(student["telegram_username"])
                            pending_hw_answers[entity.id] = hw["id"]
                        except Exception:
                            pass
        except Exception as e:
            print(f"[Bot] Error restoring pending homework: {e}")

        # 2. Poll for new homework
        while True:
            try:
                for hw in dm.get_pending_homework():
                    if not hw.get("tg_delivered"):
                        student = dm.get_student_by_id(hw["student_id"])
                        if student and student.get("telegram_username"):
                            print(f"[Bot] Found new homework for @{student['telegram_username']}")
                            success = await send_homework_to_student(
                                student["telegram_username"], hw["id"], hw["assignment"]
                            )
                            if success:
                                dm.mark_homework_delivered(hw["id"])
            except Exception as e:
                print(f"[Bot] Polling error: {e}")
            await asyncio.sleep(5)

    print("[Bot] ═══════════════════════════════════════════")
    print("[Bot]   English Teacher Telegram Userbot")
    print("[Bot] ═══════════════════════════════════════════")
    print(f"[Bot] Monitoring: {config.get('monitored_usernames', [])}")
    print(f"[Bot] AI Provider: {config.get('ai_provider', 'N/A')}")
    print("[Bot] Waiting for messages...\n")

    await client.start(phone=config.get("phone", ""))
    
    # Start the polling task
    client.loop.create_task(poll_for_homework())
    
    await client.run_until_disconnected()


# ═════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def test_connection():
    """Test the Telegram connection."""
    from telethon import TelegramClient
    config = load_config()

    if not config["api_id"] or not config["api_hash"]:
        print("[Test] ERROR: Configure api_id and api_hash first!")
        return False

    async def _test():
        session_file = str(Path(__file__).parent / "teacher_session")
        client = TelegramClient(session_file, int(config["api_id"]), config["api_hash"])
        await client.start(phone=config.get("phone", ""))
        me = await client.get_me()
        print(f"[Test] ✅ Connected as: {me.first_name} (@{me.username})")
        await client.disconnect()
        return True

    return asyncio.run(_test())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_connection()
    else:
        asyncio.run(run_userbot())
