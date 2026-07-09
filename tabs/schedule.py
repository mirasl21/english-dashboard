import streamlit as st
import os
import pandas as pd
import data_manager as dm
import notion_sync
from utils import *
import re
from pathlib import Path
import io
import json
from datetime import datetime, date, time as dt_time, timedelta

def render():
    st.markdown("### 📅 Lesson Schedule")
    st.markdown(
        "<p style='color:#94a3b8;'>Manage your lesson timetable. Add, reschedule, "
        "cancel lessons, or paste a text message for AI to handle schedule changes.</p>",
        unsafe_allow_html=True,
    )

    all_students = dm.get_students()

    if not all_students:
        st.info("👈 Add students in the sidebar first to start scheduling lessons.")
    else:
        # ─── Add New Lesson ──────────────────────────────────────────────
        with st.expander("➕ Add New Lesson", expanded=False):
            col_s, col_d, col_t = st.columns(3)
            with col_s:
                sched_student = st.selectbox(
                    "Student",
                    options=all_students,
                    format_func=lambda s: f"{s['name']} ({s['level']})",
                    key="sched_student",
                )
            with col_d:
                sched_date = st.date_input("Date", key="sched_date")
            with col_t:
                sched_time = st.time_input("Time", value=dt_time(14, 0), key="sched_time")
            sched_topic = st.text_input("Topic (optional)", placeholder="e.g. Modal verbs", key="sched_topic")

            if st.button("📅 Add Lesson", key="add_lesson_btn", use_container_width=True):
                try:
                    lesson = dm.add_lesson(
                        sched_student["id"],
                        sched_date.isoformat(),
                        sched_time.strftime("%H:%M"),
                        sched_topic,
                    )
                    # Push to Notion if configured
                    from dotenv import dotenv_values
                    env_vars = dotenv_values(".env")
                    notion_token = env_vars.get("NOTION_TOKEN") or os.environ.get("NOTION_TOKEN")
                    notion_db_id = env_vars.get("NOTION_DB_ID") or os.environ.get("NOTION_DB_ID")
                    if notion_token and notion_db_id:
                        notion_sync.push_lesson_to_notion(
                            notion_token, notion_db_id,
                            sched_student["name"],
                            sched_date.isoformat(),
                            sched_time.strftime("%H:%M"),
                            sched_topic,
                        )
                    st.success(f"✅ Lesson added: {sched_student['name']} on {sched_date} at {sched_time.strftime('%H:%M')}")
                except ValueError as e:
                    st.error(str(e))

        # ─── AI Schedule Parser ──────────────────────────────────────────
        with st.expander("🤖 AI Schedule Change (text input)", expanded=False):
            st.markdown(
                "<p style='color:#94a3b8; font-size:0.85rem;'>"
                "Paste a message like: <i>«Настя перенесла урок с 5 июля на 7 июля в 15:00»</i></p>",
                unsafe_allow_html=True,
            )
            sched_text = st.text_area(
                "Message",
                placeholder="Настя перенесла урок с пятницы на воскресенье в 16:00...",
                key="sched_ai_text",
                height=100,
            )
            if st.button("🔍 Parse & Update", key="sched_ai_btn", use_container_width=True):
                if not require_api_key():
                    st.stop()
                if not sched_text.strip():
                    st.warning("Enter a message first")
                else:
                    student_names = [s["name"] for s in all_students]
                    with st.spinner("AI is parsing the message..."):
                        parse_prompt = (
                            f"You are a scheduling assistant. Parse this message and extract schedule change information.\n"
                            f"Known students: {', '.join(student_names)}\n"
                            f"Today's date: {date.today().isoformat()}\n\n"
                            f"Message: \"{sched_text}\"\n\n"
                            f"Return a JSON object with these fields:\n"
                            f"- student_name: string (match to one of the known students)\n"
                            f"- action: 'reschedule' or 'cancel' or 'add'\n"
                            f"- old_date: 'YYYY-MM-DD' (if reschedule/cancel)\n"
                            f"- new_date: 'YYYY-MM-DD' (if reschedule/add)\n"
                            f"- new_time: 'HH:MM' (if reschedule/add)\n"
                            f"- topic: string (if mentioned)\n"
                            f"Return ONLY the JSON, no extra text."
                        )
                        try:
                            raw = call_text_ai(parse_prompt, st.session_state.api_key, st.session_state.get("provider", "OpenAI (GPT-4o)"))
                            # Extract JSON from response
                            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                            if json_match:
                                parsed = json.loads(json_match.group())
                                st.json(parsed)

                                action = parsed.get("action", "")
                                student_name = parsed.get("student_name", "")
                                matched_student = next((s for s in all_students if s["name"].lower() == student_name.lower()), None)

                                if matched_student and action == "add":
                                    new_d = parsed.get("new_date", "")
                                    new_t = parsed.get("new_time", "14:00")
                                    topic = parsed.get("topic", "")
                                    if st.button("✅ Confirm — Add this lesson", key="ai_confirm_add"):
                                        try:
                                            dm.add_lesson(matched_student["id"], new_d, new_t, topic)
                                            from dotenv import dotenv_values
                                            env_vars = dotenv_values(".env")
                                            n_tok = env_vars.get("NOTION_TOKEN") or os.environ.get("NOTION_TOKEN")
                                            n_db = env_vars.get("NOTION_DB_ID") or os.environ.get("NOTION_DB_ID")
                                            if n_tok and n_db:
                                                notion_sync.push_lesson_to_notion(n_tok, n_db, student_name, new_d, new_t, topic)
                                            st.success(f"Added lesson for {student_name} on {new_d} at {new_t}")
                                        except ValueError as e:
                                            st.error(str(e))

                                elif matched_student and action == "reschedule":
                                    old_d = parsed.get("old_date", "")
                                    new_d = parsed.get("new_date", "")
                                    new_t = parsed.get("new_time", "14:00")
                                    # Find matching lesson
                                    lessons = dm.get_lessons_for_student(matched_student["id"])
                                    target = next((l for l in lessons if l["date"] == old_d and l["status"] == "scheduled"), None)
                                    if target:
                                        if st.button("✅ Confirm — Reschedule", key="ai_confirm_resc"):
                                            try:
                                                dm.reschedule_lesson(target["id"], new_d, new_t)
                                                st.success(f"Rescheduled {student_name}: {old_d} → {new_d} at {new_t}")
                                            except ValueError as e:
                                                st.error(str(e))
                                    else:
                                        st.warning(f"No scheduled lesson found for {student_name} on {old_d}")

                                elif matched_student and action == "cancel":
                                    old_d = parsed.get("old_date", "")
                                    lessons = dm.get_lessons_for_student(matched_student["id"])
                                    target = next((l for l in lessons if l["date"] == old_d and l["status"] == "scheduled"), None)
                                    if target:
                                        if st.button("✅ Confirm — Cancel lesson", key="ai_confirm_cancel"):
                                            dm.update_lesson_status(target["id"], "cancelled")
                                            st.success(f"Cancelled lesson for {student_name} on {old_d}")
                                    else:
                                        st.warning(f"No scheduled lesson found for {student_name} on {old_d}")
                                else:
                                    st.warning("Could not match the student name. Check the sidebar list.")
                            else:
                                st.error("AI could not parse the message. Try rephrasing.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ─── Upcoming Lessons Table ──────────────────────────────────────
        st.markdown("#### 📋 Upcoming Lessons")
        upcoming = dm.get_upcoming_lessons()
        if upcoming:
            student_map = {s["id"]: s["name"] for s in all_students}
            for lesson in upcoming:
                s_name = student_map.get(lesson["student_id"], "Unknown")
                col_info, col_done, col_resc, col_cancel = st.columns([4, 1, 1, 1])
                with col_info:
                    topic_str = f" — *{lesson['topic']}*" if lesson.get("topic") else ""
                    st.markdown(f"**{lesson['date']}** {lesson['time']} | **{s_name}**{topic_str}")
                with col_done:
                    if st.button("✅", key=f"done_{lesson['id']}", help="Mark as conducted"):
                        needs_payment = dm.mark_lesson_conducted(lesson["id"])
                        from dotenv import dotenv_values
                        env_vars = dotenv_values(".env")
                        n_tok = env_vars.get("NOTION_TOKEN") or os.environ.get("NOTION_TOKEN")
                        n_db = env_vars.get("NOTION_DB_ID") or os.environ.get("NOTION_DB_ID")
                        if n_tok and n_db:
                            import notion_sync
                            notion_sync.update_lesson_status_in_notion(n_tok, n_db, s_name, lesson['date'], "Done")
                        if needs_payment:
                            st.toast(f"💸 {s_name} — пора платить!", icon="🔴")
                        st.rerun()
                with col_resc:
                    if st.button("🔄", key=f"resc_{lesson['id']}", help="Reschedule"):
                        st.session_state[f"resc_open_{lesson['id']}"] = True
                        st.rerun()
                with col_cancel:
                    if st.button("❌", key=f"canc_{lesson['id']}", help="Cancel"):
                        dm.update_lesson_status(lesson["id"], "cancelled")
                        from dotenv import dotenv_values
                        env_vars = dotenv_values(".env")
                        n_tok = env_vars.get("NOTION_TOKEN") or os.environ.get("NOTION_TOKEN")
                        n_db = env_vars.get("NOTION_DB_ID") or os.environ.get("NOTION_DB_ID")
                        if n_tok and n_db:
                            import notion_sync
                            notion_sync.delete_lesson_in_notion(n_tok, n_db, s_name, lesson['date'])
                        st.rerun()

                # Reschedule form (inline)
                if st.session_state.get(f"resc_open_{lesson['id']}"):
                    rc1, rc2, rc3 = st.columns([2, 2, 1])
                    with rc1:
                        new_d = st.date_input("New date", key=f"new_d_{lesson['id']}")
                    with rc2:
                        new_t = st.time_input("New time", key=f"new_t_{lesson['id']}")
                    with rc3:
                        if st.button("Save", key=f"save_resc_{lesson['id']}"):
                            try:
                                dm.reschedule_lesson(lesson["id"], new_d.isoformat(), new_t.strftime("%H:%M"))
                                from dotenv import dotenv_values
                                env_vars = dotenv_values(".env")
                                n_tok = env_vars.get("NOTION_TOKEN") or os.environ.get("NOTION_TOKEN")
                                n_db = env_vars.get("NOTION_DB_ID") or os.environ.get("NOTION_DB_ID")
                                if n_tok and n_db:
                                    import notion_sync
                                    notion_sync.update_lesson_in_notion(n_tok, n_db, s_name, lesson['date'], new_d.isoformat(), new_t.strftime("%H:%M"), lesson.get('topic', ''))
                                del st.session_state[f"resc_open_{lesson['id']}"]
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
        else:
            st.info("No upcoming lessons scheduled.")

        # ─── Recent History ──────────────────────────────────────────────
        with st.expander("📜 Lesson History", expanded=False):
            all_lessons = dm.get_all_lessons()
            past = [l for l in all_lessons if l["status"] != "scheduled"]
            if past:
                student_map = {s["id"]: s["name"] for s in all_students}
                history_data = []
                for l in past[:30]:
                    history_data.append({
                        "Date": l["date"],
                        "Time": l["time"],
                        "Student": student_map.get(l["student_id"], "Unknown"),
                        "Topic": l.get("topic", ""),
                        "Status": {"conducted": "✅ Done", "cancelled": "❌ Cancelled", "rescheduled": "🔄 Moved"}.get(l["status"], l["status"]),
                    })
                st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)
            else:
                st.caption("No lesson history yet.")


    # ═══════════════════════════════════════════════════════════════════════════════
    # TAB 7 — PAYMENTS
    # ═══════════════════════════════════════════════════════════════════════════════
