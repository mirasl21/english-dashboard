"""
telegram_bot.py — Private Telegram Assistant for the English Teacher.

Uses python-telegram-bot.
Monitors messages from the teacher to:
1. Parse schedule changes and update the database + Notion.
2. Check homework answers sent by the teacher using AI.

Usage:
  python telegram_bot.py
"""

import os
import re
import json
import asyncio
from datetime import date
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import data_manager as dm
import notion_sync

load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TEACHER_TELEGRAM_ID = os.environ.get("TEACHER_TELEGRAM_ID")
DEVELOPER_TELEGRAM_ID = os.environ.get("DEVELOPER_TELEGRAM_ID")
ALLOWED_IDS = [str(TEACHER_TELEGRAM_ID), str(DEVELOPER_TELEGRAM_ID)]
AI_API_KEY = os.environ.get("OPENAI_API_KEY") # Or Gemini if configured

# ─── AI Helpers ──────────────────────────────────────────────────────────────

async def call_ai(prompt: str) -> str:
    """Call AI model for text processing asynchronously."""
    # Assuming Gemini or OpenAI. We'll implement a simple OpenAI call here, 
    # but we will use asyncio.to_thread to avoid blocking.
    def _call():
        from openai import OpenAI
        client = OpenAI(api_key=AI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    return await asyncio.to_thread(_call)

async def call_vision_ai(prompt: str, images_bytes: list[bytes]) -> str:
    """Call AI model for multiple images + text processing asynchronously."""
    def _call():
        import base64
        from openai import OpenAI
        client = OpenAI(api_key=AI_API_KEY)
        
        content_array = []
        for img_bytes in images_bytes:
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            content_array.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}", "detail": "high"}})
        content_array.append({"type": "text", "text": prompt})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": content_array,
            }],
            temperature=0.6,
            max_tokens=4096,
        )
        return response.choices[0].message.content.strip()
    return await asyncio.to_thread(_call)

# ─── Handlers ────────────────────────────────────────────────────────────────

pending_homework = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    if str(update.effective_user.id) not in ALLOWED_IDS:
        return

    await update.message.reply_text(
        "👋 Привет! Я твой личный ассистент.\n"
        "Ты можешь отправлять мне изменения в расписании (например, «Настя перенесла урок на пятницу 15:00»)\n"
        "Или отправлять фото домашки учеников для быстрой проверки."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming messages from the teacher."""
    if str(update.effective_user.id) not in ALLOWED_IDS:
        return

    if not AI_API_KEY:
        await update.message.reply_text("⚠️ Ошибка: API ключ AI не настроен.")
        return

    message_text = update.message.text or update.message.caption or ""

    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file(read_timeout=60, connect_timeout=60)
        image_bytes = await photo_file.download_as_bytearray()
        
        chat_id = update.message.chat_id
        if chat_id not in pending_homework:
            pending_homework[chat_id] = image_bytes
            await update.message.reply_text("📸 Ключи (правильные ответы) получены! Теперь отправь фото с ответами ученика.")
            return
            
        student_bytes = image_bytes
        key_bytes = pending_homework.pop(chat_id)
        
        # We process homework directly since two photos were sent
        await handle_homework_photos(update, message_text, key_bytes, student_bytes, "B1")
        return

    # If it's a text message without photo, assume it's a schedule change or simple question
    await update.message.reply_text("⏳ Обрабатываю текст...")

    # 1. Fetch students via to_thread
    students = await asyncio.to_thread(dm.get_students)
    student_info = [f"{s['name']} (TZ: {s.get('contact') or 'Asia/Almaty'})" for s in students]

    # 2. Check intent using AI
    prompt = (
        f"You are a helpful assistant for an English teacher.\n"
        f"The teacher sent this message: \"{message_text}\"\n"
        f"Does this message look like a SCHEDULE CHANGE (reschedule, cancel, add lesson) or HOMEWORK CHECK?\n"
        f"If the message contains words like 'проверь', 'домашка', or consists of a block of English text with mistakes, it is a homework check.\n"
        f"If it mentions a student name and dates/times, it is a schedule change.\n"
        f"Known students: {', '.join(student_info)}\n"
        f"Today's date: {date.today().isoformat()}\n"
        f"IMPORTANT: For schedule changes, the teacher is stating times in the STUDENT'S timezone. You must convert these times from the student's timezone to Kazakhstan Time (Asia/Almaty, UTC+05:00) before returning the JSON.\n\n"
        f"Return JSON:\n"
        f'{{"type": "schedule", "student_name": "...", "action": "reschedule|cancel|add", "old_date": "YYYY-MM-DD", "new_date": "YYYY-MM-DD", "new_time": "HH:MM", "added_lessons": [{{"date": "YYYY-MM-DD", "time": "HH:MM"}}], "topic": "..."}}\n'
        f"(Use 'added_lessons' array ONLY when action is 'add'. It can contain one or multiple lessons).\n"
        f"OR\n"
        f'{{"type": "homework", "student_name": "...", "level": "B2"}}\n'
        f"Return ONLY JSON."
    )
    
    try:
        raw_intent = await call_ai(prompt)
        json_match = re.search(r'\{.*\}', raw_intent, re.DOTALL)
        if not json_match:
            await update.message.reply_text("🤔 Не поняла, это расписание или домашка?")
            return
            
        intent = json.loads(json_match.group())
        msg_type = intent.get("type")
        
        if msg_type == "schedule":
            await handle_schedule(update, intent, students)
        elif msg_type == "homework":
            await handle_homework_text(update, message_text, intent.get("level", "B1"))
        else:
            await update.message.reply_text("🤔 Не распознала команду.")
            
    except Exception as e:
        print(f"Error parsing message: {e}")
        await update.message.reply_text(f"⚠️ Ошибка обработки: {e}")

async def handle_schedule(update: Update, parsed: dict, students: list):
    """Handle schedule updates."""
    action = parsed.get("action", "")
    student_name = parsed.get("student_name", "")
    student = next((s for s in students if s["name"].lower() == student_name.lower()), None)
    
    if not student:
        await update.message.reply_text(f"⚠️ Не нашла ученика с именем {student_name}.")
        return

    if action == "reschedule":
        old_d = parsed.get("old_date", "")
        new_d = parsed.get("new_date", "")
        new_t = parsed.get("new_time", "14:00")

        lessons = await asyncio.to_thread(dm.get_lessons_for_student, student["id"])
        target = next((l for l in lessons if l["date"] == old_d and l["status"] == "scheduled"), None)
        
        if target:
            await asyncio.to_thread(dm.update_lesson_status, target["id"], "rescheduled")
            await asyncio.to_thread(dm.add_lesson, student["id"], new_d, new_t, target.get("topic", ""))
            
            notion_token = os.environ.get("NOTION_TOKEN")
            notion_db = os.environ.get("NOTION_DB_ID")
            if notion_token and notion_db:
                # Basic push logic for Notion (simplified)
                await asyncio.to_thread(
                    notion_sync.push_lesson_to_notion, 
                    notion_token, notion_db, student_name, new_d, new_t, target.get("topic", "")
                )
            await update.message.reply_text(f"✅ Урок перенесён: {old_d} → {new_d} в {new_t}")
        else:
            await update.message.reply_text(f"⚠️ Не нашла урок на {old_d}.")
            
    elif action == "cancel":
        old_d = parsed.get("old_date", "")
        lessons = await asyncio.to_thread(dm.get_lessons_for_student, student["id"])
        target = next((l for l in lessons if l["date"] == old_d and l["status"] == "scheduled"), None)
        
        if target:
            await asyncio.to_thread(dm.update_lesson_status, target["id"], "cancelled")
            await update.message.reply_text(f"✅ Урок на {old_d} отменён.")
        else:
            await update.message.reply_text(f"⚠️ Не нашла урок на {old_d}.")

    elif action == "add":
        topic = parsed.get("topic", "")
        added_lessons = parsed.get("added_lessons", [])
        
        # Fallback to single lesson if AI didn't use added_lessons
        if not added_lessons:
            new_d = parsed.get("new_date", "")
            new_t = parsed.get("new_time", "14:00")
            if new_d:
                added_lessons.append({"date": new_d, "time": new_t})
                
        if not added_lessons:
            await update.message.reply_text("⚠️ Не удалось распознать даты для добавления.")
            return

        notion_token = os.environ.get("NOTION_TOKEN")
        notion_db = os.environ.get("NOTION_DB_ID")
        
        for lesson in added_lessons:
            d = lesson.get("date", "")
            t = lesson.get("time", "14:00")
            if not d: continue
            
            await asyncio.to_thread(dm.add_lesson, student["id"], d, t, topic)
            if notion_token and notion_db:
                await asyncio.to_thread(
                    notion_sync.push_lesson_to_notion, 
                    notion_token, notion_db, student_name, d, t, topic
                )
                
        if len(added_lessons) == 1:
            l = added_lessons[0]
            await update.message.reply_text(f"✅ Урок добавлен: {l.get('date')} в {l.get('time')}")
        else:
            await update.message.reply_text(f"✅ Добавлено уроков: {len(added_lessons)} шт.")

async def handle_homework_text(update: Update, text: str, level: str):
    """Handle homework checking for text only."""
    await update.message.reply_text("🔍 Проверяю домашку (текст)...")
    
    prompt = (
        f"You are a strict and detail-oriented English teacher checking a student's homework.\n"
        f"Level: {level}\n\n"
        f"Student's message text: \"{text}\"\n\n"
        f"IMPORTANT INSTRUCTIONS:\n"
        f"1. Evaluate the text for grammatical or vocabulary mistakes.\n"
        f"2. Point out EVERY mistake. Do NOT be lenient. Explain WHY each mistake is wrong in Russian.\n"
        f"3. If there are no mistakes at all, state that the text is perfect.\n\n"
        f"Please provide a markdown response in the following format:\n"
        f"**Анализ ответов**:\n"
        f"(briefly list what you read and checked to prove you analyzed it properly)\n\n"
        f"1. **Оценка**: X/10\n"
        f"2. **Ошибки**:\n"
        f"   - [Mistake] -> [Correction] (Explanation in Russian)\n"
        f"   (If no mistakes, write: 'Ошибок нет, отличная работа!')\n"
        f"3. **Исправленный текст**: (The full text with all corrections applied)\n\n"
        f"Answer entirely in Russian (except for the English words being corrected)."
    )

    try:
        from telegram_bot import call_ai
        ai_response = await call_ai(prompt)
        await update.message.reply_text(ai_response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обращении к AI: {e}")

async def handle_homework_photos(update: Update, text: str, key_bytes: bytes, student_bytes: bytes, level: str):
    """Handle homework checking with two photos (key + student)."""
    await update.message.reply_text("🔍 Сравниваю ответы ученика с ключами...")
    
    prompt = (
        f"You are a strict and detail-oriented English teacher checking a student's homework.\n"
        f"Level: {level}\n\n"
        f"Student's message text (optional): \"{text}\"\n\n"
        f"You are given TWO images.\n"
        f"1st image: The Answer Key (правильные ответы).\n"
        f"2nd image: The Student's Work (ответы ученика).\n\n"
        f"IMPORTANT INSTRUCTIONS:\n"
        f"1. Compare the Student's Work strictly against the Answer Key.\n"
        f"2. Point out every mistake the student made compared to the Answer Key.\n"
        f"3. Explain WHY each mistake is wrong in Russian.\n"
        f"4. If there are no mistakes at all, state that the text is perfect.\n\n"
        f"Please provide a markdown response in the following format:\n"
        f"**Анализ ответов**:\n"
        f"(briefly list what you checked)\n\n"
        f"1. **Оценка**: X/10\n"
        f"2. **Ошибки**:\n"
        f"   - [Mistake] -> [Correction] (Explanation in Russian)\n"
        f"   (If no mistakes, write: 'Ошибок нет, отличная работа!')\n"
        f"Answer entirely in Russian (except for the English words being corrected)."
    )

    try:
        ai_response = await call_vision_ai(prompt, [key_bytes, student_bytes])
        await update.message.reply_text(ai_response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обращении к AI: {e}")

async def auto_complete_past_lessons():
    while True:
        try:
            notion_token = os.environ.get("NOTION_TOKEN")
            notion_db = os.environ.get("NOTION_DB_ID")
            if notion_token and notion_db:
                import notion_sync
                from data_manager import get_all_lessons, mark_lesson_conducted, get_student_name
                from datetime import datetime, timedelta
                
                now = datetime.now()
                lessons = await asyncio.to_thread(get_all_lessons)
                
                for l in lessons:
                    if l['status'] != 'scheduled': continue
                    dt_str = f"{l.get('date')} {l.get('time')}"
                    try:
                        lesson_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                        if now > lesson_dt + timedelta(hours=1):
                            await asyncio.to_thread(mark_lesson_conducted, l['id'])
                            student_name = await asyncio.to_thread(get_student_name, l['student_id'])
                            await asyncio.to_thread(notion_sync.update_lesson_status_in_notion, notion_token, notion_db, student_name, l['date'], "Done")
                            print(f"Auto-completed lesson for {student_name} on {l['date']}")
                    except Exception as e:
                        print(f"Error auto-completing lesson {l.get('id')}: {e}")
        except Exception as e:
            print(f"Error in auto_complete loop: {e}")
            
        await asyncio.sleep(1800)

async def post_init(application: Application):
    asyncio.create_task(auto_complete_past_lessons())

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN or not ALLOWED_IDS:
        print("WARNING: TELEGRAM_BOT_TOKEN or ALLOWED_IDS missing. Bot will not start.")
    else:
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).post_init(post_init).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
        
        print("Bot started...")
        app.run_polling()
